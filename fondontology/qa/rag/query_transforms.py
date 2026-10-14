"""Query-only transformation ports; scope and evidence remain outside this module."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Protocol

from fondontology.corpus import CorpusError


QUERY_TRANSFORMS = ("identity", "rewrite", "hyde")
MAX_QUERY_CHARACTERS = 16000
MAX_TRANSFORM_CHARACTERS = 4000
TRANSFORM_PROMPT_VERSION = "retrieval-query-transform-v1"


class QueryModel(Protocol):
    def __call__(self, query: str, mode: str) -> str: ...


@dataclass
class QueryTransformResource:
    transform: QueryModel
    provider: str
    model: str
    requires_network: bool = True
    events: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class QueryTransformResult:
    lexical_query: str
    dense_query: str
    trace: dict


class QueryTransformError(CorpusError):
    def __init__(self, reason: str, trace: dict):
        super().__init__(reason)
        self.reason = reason
        self.trace = trace


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def transform_query(query: str, *, mode: str = "identity", allow_network: bool = False,
                    resource: QueryTransformResource | Callable[[], QueryTransformResource] | None = None,
                    bypass: bool = False) -> QueryTransformResult:
    if mode not in QUERY_TRANSFORMS:
        raise CorpusError("Unknown query transformation")
    if not isinstance(query, str) or not query.strip():
        raise CorpusError("Query transformation requires a nonempty query")
    if type(allow_network) is not bool or type(bypass) is not bool:
        raise CorpusError("Query transformation flags must be boolean")
    trace = {
        "mode": mode, "status": "identity", "input": query, "output": query,
        "input_sha256": text_hash(query), "output_sha256": text_hash(query),
        "provider": "none", "model": "none", "network": False,
        "prompt_version": TRANSFORM_PROMPT_VERSION, "elapsed_ms": 0.0,
        "resource_events": [], "reason": None,
    }
    if mode == "identity" or bypass:
        if bypass:
            trace["status"] = "bypassed"
        return QueryTransformResult(query, query, trace)
    started = perf_counter()

    def fail(reason: str):
        trace.update(status="error", output=None, output_sha256=None, reason=reason,
                     elapsed_ms=round((perf_counter() - started) * 1000, 3))
        raise QueryTransformError(reason, trace)

    if len(query) > MAX_QUERY_CHARACTERS:
        fail("query_transform_input_too_long")
    try:
        resource = resource() if callable(resource) else resource
    except Exception:
        fail("query_transform_configuration_failed")
    if not isinstance(resource, QueryTransformResource):
        fail("query_transform_resource_unavailable")
    if (not callable(resource.transform) or type(resource.requires_network) is not bool
            or not isinstance(resource.events, list)
            or not all(isinstance(value, str) and value.strip()
                       for value in (resource.provider, resource.model))):
        fail("query_transform_resource_invalid")
    trace.update(provider=resource.provider, model=resource.model)
    if resource.requires_network and not allow_network:
        fail("query_transform_network_not_allowed")
    trace["network"] = resource.requires_network
    event_start = len(resource.events)
    try:
        output = resource.transform(query, mode)
    except Exception:
        trace["resource_events"] = resource.events[event_start:]
        fail("query_transform_call_failed")
    trace["resource_events"] = resource.events[event_start:]
    if not isinstance(output, str) or not output.strip() or len(output) > MAX_TRANSFORM_CHARACTERS:
        fail("query_transform_output_invalid")
    output = output.strip()
    trace.update(status="completed", output=output, output_sha256=text_hash(output),
                 elapsed_ms=round((perf_counter() - started) * 1000, 3))
    return QueryTransformResult(output if mode == "rewrite" else query, output, trace)
