# -*- coding: utf-8 -*-
"""Document RAG and graph-explanation compatibility adapters.

New callers use qa.service.DocumentService for explicit snapshot-backed retrieval.
document_scope resolves the original question before query_transforms; reusable
retrieval_stages and ranking feed document_pipeline and grounded generation.
The exports below remain active graph-explanation APIs, not obsolete code.
See docs/modular-qa-architecture-20261014.md for route and trace contracts.
"""
from __future__ import annotations

from .store import ChunkStore, RagChunk, get_store
from .retrieve import RetrievalResult, retrieve
from .answer import answer_classify, answer_explain
from .reranker import rerank

__all__ = ["ChunkStore", "RagChunk", "get_store", "RetrievalResult", "retrieve",
           "answer_classify", "answer_explain", "rerank"]
