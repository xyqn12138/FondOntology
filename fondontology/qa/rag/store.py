# -*- coding: utf-8 -*-
"""chunk 池加载与 BM25 词法索引（R2：零依赖，中文友好）。

chunk 契约（gen_text_assets.py 产出）：
  {"chunk_id", "doc_id", "fund_code", "doc_type", "period", "section", "text", "locator"}

索引：字符 2-gram + 英文/数字词元混合的 BM25。中文无分词依赖，
2-gram 对"货币市场基金"这类词的召回足够（子串命中即词元命中）。
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import llm_config

DEFAULT_CHUNKS = Path("artifacts/cnfo/rag/chunks.jsonl")
_LATIN_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass
class RagChunk:
    chunk_id: str
    doc_id: str
    fund_code: Optional[str]
    doc_type: str          # periodic_report | regulation_article
    period: Optional[str]
    section: str
    text: str
    locator: dict


def tokenize(text: str) -> list[str]:
    """中文 2-gram + 英文数字词元（小写化）。"""
    out: list[str] = []
    for word in _LATIN_RE.findall(text):
        out.append(word.lower())
    # 非拉丁段落按字符 2-gram
    buf: list[str] = []
    for seg in _LATIN_RE.split(text):
        seg = seg.strip()
        if not seg:
            continue
        buf.extend(seg)
        for i in range(len(seg) - 1):
            out.append(seg[i:i + 2])
    return out


class ChunkStore:
    """只读 chunk 池 + BM25 索引；进程内单例（经 get_store）。"""

    def __init__(self, chunks: list[RagChunk]):
        self.chunks = chunks
        self.by_id = {c.chunk_id: c for c in chunks}
        # 倒排：词元 → {chunk 序号: 词频}
        self._postings: dict[str, dict[int, int]] = {}
        self._doc_len: list[int] = []
        self._avg_len = 1.0
        self._build_index()

    # ---- 索引 ----
    def _build_index(self) -> None:
        for idx, chunk in enumerate(self.chunks):
            tokens = tokenize(chunk.text)
            self._doc_len.append(len(tokens))
            freq: dict[str, int] = {}
            for t in tokens:
                freq[t] = freq.get(t, 0) + 1
            for t, n in freq.items():
                self._postings.setdefault(t, {})[idx] = n
        self._avg_len = (sum(self._doc_len) / len(self._doc_len)) if self._doc_len else 1.0

    def bm25_search(self, query: str, k: int = 20,
                    scope_fund_codes: Optional[set[str]] = None) -> list[tuple[RagChunk, float]]:
        """BM25 检索。scope_fund_codes 非空时只在范围内检索（一级检索的过滤形态）。

        返回 [(chunk, score)] 按 score 降序；分数只用于排序，不作为置信度。
        """
        if not self.chunks:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        N = len(self.chunks)
        k1, b = 1.5, 0.75
        scores: dict[int, float] = {}
        candidates: Optional[set[int]] = None
        if scope_fund_codes is not None:
            candidates = {i for i, c in enumerate(self.chunks)
                          if c.fund_code in scope_fund_codes}
            if not candidates:
                return []
        for t in set(q_tokens):
            posting = self._postings.get(t)
            if not posting:
                continue
            df = len(posting)
            idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
            for idx, tf in posting.items():
                if candidates is not None and idx not in candidates:
                    continue
                dl = self._doc_len[idx]
                denom = tf + k1 * (1 - b + b * dl / self._avg_len)
                scores[idx] = scores.get(idx, 0.0) + idf * (tf * (k1 + 1)) / denom
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [(self.chunks[i], s) for i, s in ranked]

    # ---- 元数据访问 ----
    def chunks_for_fund(self, fund_code: str) -> list[RagChunk]:
        return [c for c in self.chunks if c.fund_code == fund_code]

    def chunks_by_doc_type(self, doc_type: str) -> list[RagChunk]:
        return [c for c in self.chunks if c.doc_type == doc_type]


_STORE_SINGLETON: Optional[ChunkStore] = None


def get_store(chunks_path: Path | str = DEFAULT_CHUNKS) -> ChunkStore:
    """进程内单例加载 chunk 池。文件缺失时返回空池（调用方负责降级话术）。"""
    global _STORE_SINGLETON
    if _STORE_SINGLETON is not None:
        return _STORE_SINGLETON
    path = Path(chunks_path)
    chunks: list[RagChunk] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            chunks.append(RagChunk(
                chunk_id=d["chunk_id"], doc_id=d.get("doc_id", ""),
                fund_code=d.get("fund_code"), doc_type=d.get("doc_type", ""),
                period=d.get("period"), section=d.get("section", ""),
                text=d.get("text", ""), locator=d.get("locator", {}),
            ))
    _STORE_SINGLETON = ChunkStore(chunks)
    return _STORE_SINGLETON
