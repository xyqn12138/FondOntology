# -*- coding: utf-8 -*-
"""CNFO 文本检索（RAG）子包（M7-R2）：chunk 池 + 两级检索 + explain 生成。

设计依据 docs/rag-design.md V2：
- L1 语境层（文档/章节/条文实体）在图里，L3 内容层（chunk 正文）在外部 JSONL；
- 一级检索（锚定过滤）：实体锚点命中 → 检索范围收窄到该实体的文档（消灭串台）；
- 二级检索（全局池）：无锚点解释类问题 → BM25 全局召回 + T-BOX 定义卡；
- 生成层复用 Evidence 合同（kind=document 证据），本版（R2）为确定性模板，
  LLM 表达接入是 R3。
"""
from __future__ import annotations

from .store import ChunkStore, RagChunk, get_store
from .retrieve import RetrievalResult, retrieve
from .answer import answer_classify, answer_explain

__all__ = ["ChunkStore", "RagChunk", "get_store", "RetrievalResult", "retrieve",
           "answer_classify", "answer_explain"]
