# -*- coding: utf-8 -*-
"""Embedding 客户端与向量索引（M7-R4）。

- embed_texts()：OpenAI 兼容 /embeddings 调用（批量化，含重试）；
- build_vectors()：chunk 池全量向量化 → artifacts/cnfo/rag/vectors.npy
  （行号对齐 chunks.jsonl 顺序；文件头 JSON 记录模型名与 chunk 哈希，
  失配即视为过期）；
- VectorIndex：numpy 点积余弦检索（规模 ~千级，不引入向量数据库）。

降级：embedding 未配置/网络失败/文件过期 → 调用方退化为 BM25-only，
不阻断问答链路。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from ..config import embedding_config, embedding_configured

VECTORS_NPY = Path("artifacts/cnfo/rag/vectors.npy")
# 阿里 MaaS compatible-mode 实测批量 25 通过（Ark coding 端点曾为 10，已切换服务商）
_BATCH = 25


def embed_texts(texts: list[str]) -> Optional[list[list[float]]]:
    """批量文本 → 向量（保持输入顺序）。失败返回 None（调用方降级）。"""
    if not texts:
        return []
    if not embedding_configured():
        return None
    import httpx

    cfg = embedding_config()
    url = cfg["EMBEDDING_URL"].rstrip("/") + "/embeddings"
    headers = {"Authorization": f"Bearer {cfg['EMBEDDING_KEY']}"}
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i:i + _BATCH]
        last_err: Exception | None = None
        for attempt in range(5):
            try:
                r = httpx.post(url, headers=headers,
                               json={"model": cfg["EMBEDDING_MODEL"],
                                     "input": batch},
                               timeout=60)
                r.raise_for_status()
                data = r.json()["data"]
                # 按 index 归位（服务端不保证顺序）
                ordered = sorted(data, key=lambda d: d.get("index", 0))
                out.extend([d["embedding"] for d in ordered])
                last_err = None
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # 账户级限流：指数退避（2/4/8/16/32s），扛过限流窗口
                    last_err = e
                    time.sleep(2.0 * (2 ** attempt))
                    continue
                # 4xx 参数错误重试无意义（如批量超限），直接失败并透出信息
                body = e.response.text[:200]
                raise RuntimeError(
                    f"embeddings HTTP {e.response.status_code}: {body}") from e
            except Exception as e:  # 网络：短退避重试
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        if last_err is not None:
            return None
        # 批间基础间隔（账户级 QPS 限流，连发必触发）
        if i + _BATCH < len(texts):
            time.sleep(0.6)
    return out


def build_vectors(chunks_path: Path, out_path: Path = VECTORS_NPY) -> Optional[int]:
    """全量构建 chunk 向量索引。返回向量数（失败 None）。

    写两件东西：vectors.npy（float32 矩阵）+ 同名 .meta.json
    （模型名 + chunk_id 列表哈希，加载时校验一致性）。
    """
    import hashlib

    lines = [l for l in Path(chunks_path).read_text(encoding="utf-8").splitlines()
             if l.strip()]
    chunk_ids = [json.loads(l)["chunk_id"] for l in lines]
    texts = [json.loads(l)["text"] for l in lines]
    vecs = embed_texts(texts)
    if vecs is None:
        return None
    import numpy as np

    arr = np.array(vecs, dtype=np.float32)
    # 归一化（点积即余弦）
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = arr / norms
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, arr)
    meta = {
        "model": embedding_config()["EMBEDDING_MODEL"],
        "chunk_ids_sha": hashlib.sha256(
            "\n".join(chunk_ids).encode("utf-8")).hexdigest()[:16],
        "dim": int(arr.shape[1]),
        "count": int(arr.shape[0]),
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return len(chunk_ids)


class VectorIndex:
    """只读向量索引：query 向量 → 相似 chunk 序号。"""

    def __init__(self, matrix, chunk_ids: list[str]):
        import numpy as np
        self._np = np
        self.matrix = matrix          # 已归一化
        self.chunk_ids = chunk_ids

    def search(self, query_vec: list[float], k: int = 20) -> list[tuple[str, float]]:
        q = self._np.array(query_vec, dtype=self.matrix.dtype)
        n = float(self._np.linalg.norm(q))
        if n > 0:
            q = q / n
        scores = self.matrix @ q
        top = self._np.argsort(-scores)[:k]
        return [(self.chunk_ids[i], float(scores[i])) for i in top if scores[i] > 0]


_INDEX_SINGLETON: Optional[VectorIndex] = None
_INDEX_LOADED: bool = False


def get_vector_index(chunks_path: Path = Path("artifacts/cnfo/rag/chunks.jsonl"),
                     vectors_path: Path = VECTORS_NPY) -> Optional[VectorIndex]:
    """进程内单例加载；未配置/文件缺失/哈希失配 → None（BM25-only 降级）。"""
    global _INDEX_SINGLETON, _INDEX_LOADED
    if _INDEX_LOADED:
        return _INDEX_SINGLETON
    _INDEX_LOADED = True
    if not (embedding_configured() and vectors_path.is_file()
            and vectors_path.with_suffix(".meta.json").is_file()):
        return None
    try:
        import numpy as np

        meta = json.loads(vectors_path.with_suffix(".meta.json")
                          .read_text(encoding="utf-8"))
        import hashlib

        lines = [l for l in Path(chunks_path).read_text(encoding="utf-8")
                 .splitlines() if l.strip()]
        chunk_ids = [json.loads(l)["chunk_id"] for l in lines]
        sha = hashlib.sha256("\n".join(chunk_ids).encode("utf-8")).hexdigest()[:16]
        if meta.get("chunk_ids_sha") != sha or meta.get("count") != len(chunk_ids):
            return None   # chunk 池已变化，向量过期
        arr = np.load(vectors_path)
        if arr.shape[0] != len(chunk_ids):
            return None
        _INDEX_SINGLETON = VectorIndex(arr, chunk_ids)
        return _INDEX_SINGLETON
    except Exception:
        return None
