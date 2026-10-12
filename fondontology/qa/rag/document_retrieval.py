"""Explicit, scope-first retrieval strategies with injectable model resources."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from fondontology.corpus import CorpusError

from .store import ChunkStore, RagChunk


STRATEGIES = ("bm25", "parent_child", "hybrid_rrf", "bm25_rerank")
RRF_K = 60
CHILD_TARGET_CHARS = 240


@dataclass
class RetrievalResources:
    embed: Callable[[list[str]], list[list[float]]] | None = None
    rerank: Callable[[str, list[str]], list[tuple[int, float]]] | None = None
    embedding_config: dict = field(default_factory=dict)
    rerank_config: dict = field(default_factory=dict)
    embed_requires_network: bool = True
    rerank_requires_network: bool = True
    events: list[dict] = field(default_factory=list)


@dataclass
class RetrievalOutcome:
    hits: list[tuple[RagChunk, float | None]]
    ranking: str
    strategy_trace: dict


class RetrievalStrategyError(CorpusError):
    def __init__(self, reason: str, trace: dict):
        super().__init__(reason)
        self.reason = reason
        self.strategy_trace = trace


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


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


def _fail(trace: dict, reason: str):
    trace["status"], trace["reason"] = "error", reason
    raise RetrievalStrategyError(reason, trace)


def _ranked(hits: list[tuple[RagChunk, float]]) -> list[dict]:
    return [{"chunk_id": chunk.chunk_id, "rank": rank, "score": score}
            for rank, (chunk, score) in enumerate(hits, 1)]


def child_chunks(parents: list[RagChunk]) -> tuple[list[RagChunk], dict[str, dict]]:
    children = []
    origins = {}
    for parent in parents:
        start = 0
        parent_start = parent.locator.get("char_start")
        if (type(parent_start) is not int
                or parent.locator.get("char_end") != parent_start + len(parent.text)):
            raise CorpusError("Parent-child retrieval requires original character offsets")
        while start < len(parent.text):
            end = min(start + CHILD_TARGET_CHARS, len(parent.text))
            if end < len(parent.text):
                boundaries = list(re.finditer(r"[。！？.!?；;\n]", parent.text[start:end]))
                if boundaries and boundaries[-1].end() >= CHILD_TARGET_CHARS // 2:
                    end = start + boundaries[-1].end()
            text = parent.text[start:end]
            identifier = "child_" + _digest({
                "parent": parent.chunk_id, "start": start, "end": end, "text": text,
                "policy": "sentence-boundary-240-v1"})
            origin = {
                "child_id": identifier, "parent_chunk_id": parent.chunk_id,
                "char_start": parent_start + start, "char_end": parent_start + end,
                "parent_char_start": parent_start,
                "parent_char_end": parent_start + len(parent.text),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            origins[identifier] = origin
            children.append(replace(parent, chunk_id=identifier, text=text,
                                    locator={**parent.locator, **origin}))
            start = end
    return children, origins


def _vector(value, trace: dict) -> list[float]:
    if (not isinstance(value, (list, tuple)) or not value
            or any(type(number) not in (int, float) or not math.isfinite(number)
                   for number in value)):
        _fail(trace, "invalid_embedding_vector")
    result = [float(number) for number in value]
    if not any(result):
        _fail(trace, "zero_embedding_vector")
    return result


def _cosine(left: list[float], right: list[float], trace: dict) -> float:
    if len(left) != len(right):
        _fail(trace, "embedding_dimension_mismatch")
    numerator = sum(first * second for first, second in zip(left, right))
    denominator = math.sqrt(sum(number * number for number in left)) * math.sqrt(
        sum(number * number for number in right))
    value = numerator / denominator if denominator else float("nan")
    if not math.isfinite(value):
        _fail(trace, "invalid_cosine_score")
    return value


def _embed(texts: list[str], *, resources: RetrievalResources, store: ChunkStore,
           trace: dict, cache_path: Path | str | None, allow_network: bool,
           stage: str) -> list[list[float]]:
    if resources.embed is None:
        _fail(trace, "embedding_resource_unavailable")
    directory = Path(cache_path) if cache_path is not None else None
    entries = {}
    order = []
    for text in texts:
        key = _digest({
            "schema_version": "1.0", "snapshot": store.corpus_metadata.get("members_sha256"),
            "embedding": resources.embedding_config, "kind": stage, "text": text,
        })
        order.append(key)
        if key in entries:
            continue
        path = directory / f"{key}.json" if directory is not None else None
        if path is not None and path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or payload.get("key") != key:
                    _fail(trace, "invalid_embedding_cache")
                entries[key] = _vector(payload.get("vector"), trace)
                if payload.get("vector_sha256") != _digest(entries[key]):
                    _fail(trace, "invalid_embedding_cache")
            except (OSError, ValueError) as error:
                if isinstance(error, RetrievalStrategyError):
                    raise
                _fail(trace, "invalid_embedding_cache")
            trace["cache"]["hits"] += 1
        else:
            entries[key] = None
            trace["cache"]["misses"] += 1
    missing = [key for key, vector in entries.items() if vector is None]
    if missing:
        event = {"stage": stage, "status": "started", "input_count": len(missing),
                 "network": resources.embed_requires_network}
        trace["stages"].append(event)
        if resources.embed_requires_network and not allow_network:
            event["status"] = "blocked"
            _fail(trace, "retrieval_network_not_allowed")
        indices = {key: index for index, key in enumerate(order)}
        try:
            event_start = len(resources.events)
            values = resources.embed([texts[indices[key]] for key in missing])
        except Exception:
            trace["resource_events"].extend(resources.events[event_start:])
            event["status"] = "failed"
            _fail(trace, "embedding_call_failed")
        trace["resource_events"].extend(resources.events[event_start:])
        if not isinstance(values, list) or len(values) != len(missing):
            event["status"] = "failed"
            _fail(trace, "invalid_embedding_count")
        for key, value in zip(missing, values):
            entries[key] = _vector(value, trace)
        if directory is not None:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                for key in missing:
                    path = directory / f"{key}.json"
                    temporary = directory / f"{key}.{os.getpid()}.tmp"
                    temporary.write_text(json.dumps(
                        {"key": key, "vector": entries[key],
                         "vector_sha256": _digest(entries[key])},
                        allow_nan=False), encoding="utf-8")
                    temporary.replace(path)
            except OSError:
                event["status"] = "failed"
                _fail(trace, "embedding_cache_write_failed")
        event["status"] = "completed"
    else:
        trace["stages"].append({
            "stage": stage, "status": "cache_hit", "input_count": 0, "network": False})
    trace["cache"]["entries"].extend([
        {"key": key, "kind": stage, "vector_sha256": _digest(entries[key])}
        for key in dict.fromkeys(order)])
    return [entries[key] for key in order]


def retrieve_documents(store: ChunkStore, scope: dict, *, strategy: str = "bm25",
                       candidate_k: int = 20, cache_path: Path | str | None = None,
                       allow_network: bool = False,
                       resources: RetrievalResources | Callable[[], RetrievalResources] | None = None,
                       ) -> RetrievalOutcome:
    if strategy not in STRATEGIES:
        raise CorpusError("Unknown retrieval strategy")
    if type(candidate_k) is not int or candidate_k < 1:
        raise CorpusError("candidate_k must be positive")
    if type(allow_network) is not bool:
        raise CorpusError("allow_network must be boolean")
    trace = _base_trace(strategy, candidate_k, cache_path)
    if scope["status"] != "resolved" or not scope["eligible_chunk_ids"]:
        trace.update(status="bypassed", effective_strategy="none", reason="unresolved_scope")
        return RetrievalOutcome([], "bm25", trace)
    identifiers = scope["eligible_chunk_ids"]
    if any(identifier not in store.by_id for identifier in identifiers):
        _fail(trace, "unknown_scope_chunk")
    parents = [store.by_id[identifier] for identifier in identifiers]
    if scope["article_numbers"]:
        trace.update(status="bypassed", effective_strategy="article_locator", reason="direct_address")
        return RetrievalOutcome([(parent, None) for parent in parents], "article_locator", trace)
    query = scope["body_query"]
    lexical = store.bm25_search(
        query, k=len(store.chunks) if strategy == "bm25" else candidate_k,
        scope_chunk_ids=set(identifiers))
    trace["channels"]["bm25"] = _ranked(lexical)
    trace["stages"].append({"stage": "bm25", "status": "completed", "network": False})
    if strategy == "bm25":
        return RetrievalOutcome(lexical, "bm25", trace)
    if strategy == "parent_child":
        children, origins = child_chunks(parents)
        child_store = ChunkStore(children)
        matches = child_store.bm25_search(query, k=candidate_k)
        trace["channels"]["child_bm25"] = [
            {**origins[child.chunk_id], "rank": rank, "score": score}
            for rank, (child, score) in enumerate(matches, 1)]
        trace["child_matches"] = list(trace["channels"]["child_bm25"])
        trace["stages"].append({
            "stage": "parent_child", "status": "completed", "network": False,
            "input_count": len(children)})
        seen = set()
        hits = []
        for child, score in matches:
            parent_id = origins[child.chunk_id]["parent_chunk_id"]
            if parent_id not in seen:
                hits.append((store.by_id[parent_id], score))
                seen.add(parent_id)
        return RetrievalOutcome(hits, "parent_bm25", trace)
    if strategy == "bm25_rerank" and not lexical:
        trace.update(status="bypassed", reason="no_lexical_candidates")
        return RetrievalOutcome([], "rerank", trace)
    try:
        resources = resources() if callable(resources) else resources
    except Exception:
        _fail(trace, "retrieval_resource_configuration_failed")
    if not isinstance(resources, RetrievalResources):
        _fail(trace, "retrieval_resource_unavailable")
    trace["model_config"] = {
        "embedding": dict(resources.embedding_config), "rerank": dict(resources.rerank_config)}
    if strategy == "hybrid_rrf":
        parent_vectors = _embed(
            [parent.text for parent in parents], resources=resources, store=store, trace=trace,
            cache_path=cache_path, allow_network=allow_network, stage="embed_documents")
        query_vector = _embed(
            [query], resources=resources, store=store, trace=trace, cache_path=cache_path,
            allow_network=allow_network, stage="embed_query")[0]
        dense = sorted(
            [(parent, _cosine(vector, query_vector, trace))
             for parent, vector in zip(parents, parent_vectors)],
            key=lambda item: (-item[1], item[0].chunk_id))[:candidate_k]
        trace["channels"]["dense"] = _ranked(dense)
        ranks = {
            "bm25": {parent.chunk_id: rank for rank, (parent, score) in enumerate(lexical, 1)},
            "dense": {parent.chunk_id: rank for rank, (parent, score) in enumerate(dense, 1)}}
        fused = {}
        for channel in ranks.values():
            for identifier, rank in channel.items():
                fused[identifier] = fused.get(identifier, 0.0) + 1.0 / (RRF_K + rank)
        ordered = sorted(fused.items(), key=lambda item: (-item[1], item[0]))[:candidate_k]
        trace["fusion"] = [{
            "chunk_id": identifier, "score": score,
            "bm25_rank": ranks["bm25"].get(identifier),
            "dense_rank": ranks["dense"].get(identifier),
        } for identifier, score in ordered]
        trace["stages"].append({"stage": "hybrid_rrf", "status": "completed", "network": False})
        return RetrievalOutcome(
            [(store.by_id[identifier], score) for identifier, score in ordered], "hybrid_rrf", trace)
    if resources.rerank is None:
        _fail(trace, "rerank_resource_unavailable")
    event = {"stage": "rerank", "status": "started", "input_count": len(lexical),
             "network": resources.rerank_requires_network}
    trace["stages"].append(event)
    if resources.rerank_requires_network and not allow_network:
        event["status"] = "blocked"
        _fail(trace, "retrieval_network_not_allowed")
    try:
        event_start = len(resources.events)
        scores = resources.rerank(query, [parent.text for parent, score in lexical])
    except Exception:
        trace["resource_events"].extend(resources.events[event_start:])
        event["status"] = "failed"
        _fail(trace, "rerank_call_failed")
    trace["resource_events"].extend(resources.events[event_start:])
    if (not isinstance(scores, list) or len(scores) != len(lexical)
            or any(not isinstance(item, (list, tuple)) or len(item) != 2
                   or type(item[0]) is not int or item[0] < 0 or item[0] >= len(lexical)
                   or type(item[1]) not in (int, float) or not math.isfinite(item[1])
                   for item in scores)
            or len({item[0] for item in scores}) != len(lexical)):
        event["status"] = "failed"
        _fail(trace, "invalid_rerank_scores")
    scores.sort(key=lambda item: (-item[1], item[0]))
    trace["rerank"] = [{
        "chunk_id": lexical[index][0].chunk_id, "index": index, "score": score}
        for index, score in scores]
    event["status"] = "completed"
    return RetrievalOutcome(
        [(lexical[index][0], score) for index, score in scores], "rerank", trace)
