# -*- coding: utf-8 -*-
"""Rerank 客户端（M7-R4 扩展）：RRF 粗排 → 语义精排。

服务端：MaaS 原生 text-rerank API（仅此调用方式，无 OpenAI 兼容路径），
官方 curl 形态：
    POST {host}/api/v1/services/rerank/text-rerank/text-rerank
    {"model": ..., "input": {"query": ..., "documents": [...]},
     "parameters": {"top_n": ...}}
出参 output.results[{index, relevance_score}]。

接入位置（对齐 V2 设计"重排在 RRF 之后"）：
- retrieve 三路 RRF 产出 top-k*2 粗排 → rerank 精排取 top_k；
- section_hint/锚定场景不 rerank（确定性信号优先于模型分数，
  防串台的物理保证不交给概率模型）；
- 降级：未配置/网络失败/超时 → 保持 RRF 序（不阻断，静默）。
"""
from __future__ import annotations

from typing import Optional

from ..config import rerank_config, rerank_configured


def rerank(query: str, documents: list[str],
           top_k: Optional[int] = None) -> Optional[list[tuple[int, float]]]:
    """query × documents → [(原序号, relevance_score)] 按相关度降序。

    返回 None = 不可用/失败（调用方保持原序）；空文档返回 []。
    top_n 截断由服务端 parameters 执行。
    """
    if not documents:
        return []
    if not rerank_configured():
        return None
    import httpx

    cfg = rerank_config()
    payload: dict = {
        "model": cfg["RERANK_MODEL"],
        "input": {"query": query, "documents": documents},
    }
    if top_k is not None:
        payload["parameters"] = {"top_n": top_k}
    try:
        r = httpx.post(
            cfg["RERANK_URL"],
            headers={"Authorization": f"Bearer {cfg['RERANK_KEY']}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        results = r.json()["output"]["results"]
        scored = [(int(item["index"]), float(item["relevance_score"]))
                  for item in results]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored
    except Exception:
        return None
