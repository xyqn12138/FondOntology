"""Reusable candidate, embedding-cache and reranking stages; no routing or scope decisions."""

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
from .ranking import reciprocal_rank_fusion, validate_rerank_scores


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


def fail_strategy(trace: dict, reason: str):
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
        fail_strategy(trace, "invalid_embedding_vector")
    result = [float(number) for number in value]
    if not any(result):
        fail_strategy(trace, "zero_embedding_vector")
    return result


def _cosine(left: list[float], right: list[float], trace: dict) -> float:
    if len(left) != len(right):
        fail_strategy(trace, "embedding_dimension_mismatch")
    numerator = sum(first * second for first, second in zip(left, right))
    denominator = math.sqrt(sum(number * number for number in left)) * math.sqrt(
        sum(number * number for number in right))
    value = numerator / denominator if denominator else float("nan")
    if not math.isfinite(value):
        fail_strategy(trace, "invalid_cosine_score")
    return value


def _embed(texts: list[str], *, resources: RetrievalResources, store: ChunkStore,
           trace: dict, cache_path: Path | str | None, allow_network: bool,
           stage: str) -> list[list[float]]:
    if resources.embed is None:
        fail_strategy(trace, "embedding_resource_unavailable")
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
                    fail_strategy(trace, "invalid_embedding_cache")
                entries[key] = _vector(payload.get("vector"), trace)
                if payload.get("vector_sha256") != _digest(entries[key]):
                    fail_strategy(trace, "invalid_embedding_cache")
            except (OSError, ValueError) as error:
                if isinstance(error, RetrievalStrategyError):
                    raise
                fail_strategy(trace, "invalid_embedding_cache")
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
            fail_strategy(trace, "retrieval_network_not_allowed")
        indices = {key: index for index, key in enumerate(order)}
        try:
            event_start = len(resources.events)
            values = resources.embed([texts[indices[key]] for key in missing])
        except Exception:
            trace["resource_events"].extend(resources.events[event_start:])
            event["status"] = "failed"
            fail_strategy(trace, "embedding_call_failed")
        trace["resource_events"].extend(resources.events[event_start:])
        if not isinstance(values, list) or len(values) != len(missing):
            event["status"] = "failed"
            fail_strategy(trace, "invalid_embedding_count")
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
                fail_strategy(trace, "embedding_cache_write_failed")
        event["status"] = "completed"
    else:
        trace["stages"].append({
            "stage": stage, "status": "cache_hit", "input_count": 0, "network": False})
    trace["cache"]["entries"].extend([
        {"key": key, "kind": stage, "vector_sha256": _digest(entries[key])}
        for key in dict.fromkeys(order)])
    return [entries[key] for key in order]


def lexical_candidates(store: ChunkStore, identifiers: list[str], query: str, *,
                       limit: int, trace: dict) -> list[tuple[RagChunk, float]]:
    hits = store.bm25_search(query, k=limit, scope_chunk_ids=set(identifiers))
    trace["channels"]["bm25"] = _ranked(hits)
    trace["stages"].append({"stage": "bm25", "status": "completed", "network": False})
    return hits


def parent_candidates(store: ChunkStore, parents: list[RagChunk], query: str, *,
                      candidate_k: int, trace: dict) -> list[tuple[RagChunk, float]]:
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
    return hits


def dense_candidates(store: ChunkStore, parents: list[RagChunk], query: str, *,
                     candidate_k: int, resources: RetrievalResources, trace: dict,
                     cache_path: Path | str | None, allow_network: bool) -> list[tuple[RagChunk, float]]:
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
    return dense


def fuse_candidates(store: ChunkStore, lexical: list[tuple[RagChunk, float]],
                    dense: list[tuple[RagChunk, float]], *,
                    candidate_k: int, trace: dict) -> list[tuple[RagChunk, float]]:
    ranks = {
        "bm25": {parent.chunk_id: rank for rank, (parent, score) in enumerate(lexical, 1)},
        "dense": {parent.chunk_id: rank for rank, (parent, score) in enumerate(dense, 1)}}
    ordered = reciprocal_rank_fusion(
        {name: list(channel) for name, channel in ranks.items()},
        limit=candidate_k, rank_constant=RRF_K)
    trace["fusion"] = [{
        "chunk_id": identifier, "score": score,
        "bm25_rank": ranks["bm25"].get(identifier),
        "dense_rank": ranks["dense"].get(identifier),
    } for identifier, score in ordered]
    trace["stages"].append({"stage": "hybrid_rrf", "status": "completed", "network": False})
    return [(store.by_id[identifier], score) for identifier, score in ordered]


def rerank_candidates(lexical: list[tuple[RagChunk, float]], query: str, *,
                      resources: RetrievalResources, allow_network: bool,
                      trace: dict) -> list[tuple[RagChunk, float]]:
    if resources.rerank is None:
        fail_strategy(trace, "rerank_resource_unavailable")
    event = {"stage": "rerank", "status": "started", "input_count": len(lexical),
             "network": resources.rerank_requires_network}
    trace["stages"].append(event)
    if resources.rerank_requires_network and not allow_network:
        event["status"] = "blocked"
        fail_strategy(trace, "retrieval_network_not_allowed")
    try:
        event_start = len(resources.events)
        scores = resources.rerank(query, [parent.text for parent, score in lexical])
    except Exception:
        trace["resource_events"].extend(resources.events[event_start:])
        event["status"] = "failed"
        fail_strategy(trace, "rerank_call_failed")
    trace["resource_events"].extend(resources.events[event_start:])
    try:
        scores = validate_rerank_scores(scores, len(lexical))
    except ValueError:
        event["status"] = "failed"
        fail_strategy(trace, "invalid_rerank_scores")
    trace["rerank"] = [{
        "chunk_id": lexical[index][0].chunk_id, "index": index, "score": score}
        for index, score in scores]
    event["status"] = "completed"
    return [(lexical[index][0], score) for index, score in scores]
