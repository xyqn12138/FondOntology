"""Scope-first orchestration of explicit, independently testable retrieval stages."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from fondontology.corpus import CorpusError

from .store import ChunkStore
from .query_transforms import (
    QUERY_TRANSFORMS, QueryTransformError, QueryTransformResource, transform_query,
)
from .retrieval_stages import (
    CHILD_TARGET_CHARS, RRF_K, RetrievalOutcome, RetrievalResources, RetrievalStrategyError,
    child_chunks, dense_candidates, fail_strategy, fuse_candidates, lexical_candidates,
    parent_candidates, rerank_candidates,
)


STRATEGIES = ("bm25", "parent_child", "hybrid_rrf", "bm25_rerank")


def _base_trace(strategy: str, candidate_k: int, cache_path: Path | str | None) -> dict:
    return {
        "requested_strategy": strategy, "effective_strategy": strategy, "status": "ok",
        "candidate_k": candidate_k, "rrf_k": RRF_K,
        "child_target_chars": CHILD_TARGET_CHARS, "channels": {}, "child_matches": [],
        "model_config": {"embedding": {}, "rerank": {}},
        "cache": {"enabled": cache_path is not None, "hits": 0, "misses": 0,
                  "path": str(Path(cache_path).resolve()) if cache_path is not None else None,
                  "entries": []},
        "stages": [], "fusion": [], "rerank": [],
        "resource_events": [],
    }


def retrieve_documents(store: ChunkStore, scope: dict, *, strategy: str = "bm25",
                       candidate_k: int = 20, cache_path: Path | str | None = None,
                       allow_network: bool = False,
                       resources: RetrievalResources | Callable[[], RetrievalResources] | None = None,
                       query_transform: str = "identity",
                       query_transform_resource: QueryTransformResource
                       | Callable[[], QueryTransformResource] | None = None) -> RetrievalOutcome:
    if strategy not in STRATEGIES:
        raise CorpusError("Unknown retrieval strategy")
    if type(candidate_k) is not int or candidate_k < 1:
        raise CorpusError("candidate_k must be positive")
    if type(allow_network) is not bool:
        raise CorpusError("allow_network must be boolean")
    if query_transform not in QUERY_TRANSFORMS:
        raise CorpusError("Unknown query transformation")
    if query_transform == "hyde" and strategy != "hybrid_rrf":
        raise CorpusError("HyDE requires hybrid_rrf so hypothetical text is used only for dense retrieval")
    trace = _base_trace(strategy, candidate_k, cache_path)
    if scope["status"] != "resolved" or not scope["eligible_chunk_ids"]:
        trace.update(status="bypassed", effective_strategy="none", reason="unresolved_scope")
        return RetrievalOutcome([], "bm25", trace)
    identifiers = scope["eligible_chunk_ids"]
    if any(identifier not in store.by_id for identifier in identifiers):
        fail_strategy(trace, "unknown_scope_chunk")
    parents = [store.by_id[identifier] for identifier in identifiers]
    if scope["article_numbers"]:
        trace.update(status="bypassed", effective_strategy="article_locator", reason="direct_address")
        return RetrievalOutcome([(parent, None) for parent in parents], "article_locator", trace)
    query = scope["body_query"]
    dense_query = query
    if query_transform != "identity":
        try:
            transformed = transform_query(
                query, mode=query_transform, resource=query_transform_resource,
                allow_network=allow_network)
        except QueryTransformError as error:
            trace["query_transform"] = error.trace
            fail_strategy(trace, error.reason)
        query, dense_query = transformed.lexical_query, transformed.dense_query
        trace["query_transform"] = transformed.trace
    lexical = lexical_candidates(
        store, identifiers, query,
        limit=len(store.chunks) if strategy == "bm25" else candidate_k, trace=trace)
    if strategy == "bm25":
        return RetrievalOutcome(lexical, "bm25", trace)
    if strategy == "parent_child":
        hits = parent_candidates(store, parents, query, candidate_k=candidate_k, trace=trace)
        return RetrievalOutcome(hits, "parent_bm25", trace)
    if strategy == "bm25_rerank" and not lexical:
        trace.update(status="bypassed", reason="no_lexical_candidates")
        return RetrievalOutcome([], "rerank", trace)
    try:
        resources = resources() if callable(resources) else resources
    except Exception:
        fail_strategy(trace, "retrieval_resource_configuration_failed")
    if not isinstance(resources, RetrievalResources):
        fail_strategy(trace, "retrieval_resource_unavailable")
    trace["model_config"] = {
        "embedding": dict(resources.embedding_config), "rerank": dict(resources.rerank_config)}
    if strategy == "hybrid_rrf":
        dense = dense_candidates(
            store, parents, dense_query, candidate_k=candidate_k, resources=resources,
            trace=trace, cache_path=cache_path, allow_network=allow_network)
        hits = fuse_candidates(store, lexical, dense, candidate_k=candidate_k, trace=trace)
        return RetrievalOutcome(hits, "hybrid_rrf", trace)
    hits = rerank_candidates(
        lexical, scope["body_query"], resources=resources, allow_network=allow_network, trace=trace)
    return RetrievalOutcome(hits, "rerank", trace)
