"""Typed, explicit public ports for graph QA and snapshot-backed document QA."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol, TypeVar

from .rag.document_retrieval import STRATEGIES
from .rag.query_transforms import QUERY_TRANSFORMS, QueryTransformResource
from .rag.retrieval_stages import RetrievalResources

if TYPE_CHECKING:
    from .graph import DataStack
    from .rag.store import ChunkStore


def _nonblank(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")


@dataclass(frozen=True)
class RetrievalPlan:
    strategy: str = "bm25"
    query_transform: str = "identity"
    top_k: int = 5
    candidate_k: int = 20

    def __post_init__(self):
        if self.strategy not in STRATEGIES or self.query_transform not in QUERY_TRANSFORMS:
            raise ValueError("Unknown retrieval strategy or query transformation")
        if (type(self.top_k) is not int or type(self.candidate_k) is not int
                or self.top_k < 1 or self.candidate_k < self.top_k):
            raise ValueError("Retrieval budgets require candidate_k >= top_k >= 1")
        if self.query_transform == "hyde" and self.strategy != "hybrid_rrf":
            raise ValueError("HyDE requires a dense retrieval channel (hybrid_rrf)")


@dataclass(frozen=True)
class DocumentRequest:
    question: str
    db_path: Path | str
    snapshot_id: str
    as_of: str
    plan: RetrievalPlan = field(default_factory=RetrievalPlan)
    entity_iri: str | None = None
    doc_ids: tuple[str, ...] | None = None
    version_ids: tuple[str, ...] | None = None
    generate: bool = False
    allow_retrieval_network: bool = False
    allow_nontrusted: bool = False
    include_undated_research: bool = False
    retrieval_cache: Path | str | None = None

    def __post_init__(self):
        for name in ("question", "snapshot_id", "as_of"):
            _nonblank(getattr(self, name), name)
        if not isinstance(self.db_path, (str, Path)) or not str(self.db_path).strip():
            raise ValueError("db_path is required")
        if self.retrieval_cache is not None and (
                not isinstance(self.retrieval_cache, (str, Path)) or not str(self.retrieval_cache).strip()):
            raise ValueError("retrieval_cache must be a path or None")
        if date.fromisoformat(self.as_of).isoformat() != self.as_of:
            raise ValueError("as_of must use YYYY-MM-DD")
        if not isinstance(self.plan, RetrievalPlan):
            raise ValueError("plan must be a RetrievalPlan")
        if self.entity_iri is not None:
            _nonblank(self.entity_iri, "entity_iri")
        for name in ("doc_ids", "version_ids"):
            values = getattr(self, name)
            if values is not None:
                if not isinstance(values, tuple):
                    raise ValueError(f"{name} must be a tuple or None")
                for value in values:
                    _nonblank(value, name)
                if len(values) != len(set(values)):
                    raise ValueError(f"{name} must be unique")
        for name in ("generate", "allow_retrieval_network", "allow_nontrusted", "include_undated_research"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if self.include_undated_research and not self.allow_nontrusted:
            raise ValueError("Unknown-date research requires allow_nontrusted")


@dataclass(frozen=True)
class KnowledgeGraphRequest:
    question: str
    use_llm: bool | None = None

    def __post_init__(self):
        _nonblank(self.question, "question")
        if self.use_llm is not None and type(self.use_llm) is not bool:
            raise ValueError("use_llm must be boolean or None")


@dataclass(frozen=True)
class QaResponse:
    route: str
    status: str
    text: str
    evidence: tuple
    trace: dict
    payload: Any = field(repr=False)


RequestType = TypeVar("RequestType", contravariant=True)


class AnswerService(Protocol[RequestType]):
    def answer(self, request: RequestType) -> QaResponse: ...


class DocumentService:
    def __init__(self, *, store: ChunkStore | None = None,
                 resources: RetrievalResources | Callable[[], RetrievalResources] | None = None,
                 query_transform_resource: QueryTransformResource
                 | Callable[[], QueryTransformResource] | None = None,
                 handler: Callable[..., dict] | None = None):
        self.store = store
        self.resources = resources
        self.query_transform_resource = query_transform_resource
        self.handler = handler

    def answer(self, request: DocumentRequest) -> QaResponse:
        if not isinstance(request, DocumentRequest):
            raise TypeError("DocumentService requires DocumentRequest")
        from .rag.document_pipeline import answer_document
        resources = self.resources
        if resources is None and request.plan.strategy in {"hybrid_rrf", "bm25_rerank"}:
            from .rag.document_providers import build_resources
            resources = build_resources
        result = (self.handler or answer_document)(
            request.question, db_path=request.db_path, snapshot_id=request.snapshot_id,
            as_of=request.as_of, top_k=request.plan.top_k, candidate_k=request.plan.candidate_k,
            retrieval_strategy=request.plan.strategy, query_transform=request.plan.query_transform,
            entity_iri=request.entity_iri,
            doc_ids=None if request.doc_ids is None else list(request.doc_ids),
            version_ids=None if request.version_ids is None else list(request.version_ids),
            generate=request.generate, allow_retrieval_network=request.allow_retrieval_network,
            allow_nontrusted=request.allow_nontrusted,
            include_undated_research=request.include_undated_research,
            retrieval_cache=request.retrieval_cache, store=self.store,
            resources=resources, query_transform_resource=self.query_transform_resource)
        if result["status"] not in {"retrieved", "answered", "unresolved", "error"}:
            raise ValueError("Unsupported document response status")
        return QaResponse("document_rag", result["status"], result["response"],
                          tuple(result["evidence"]), {
                              "corpus": result["corpus"], "scope": result["scope"],
                              "retrieval": result["strategy_trace"],
                              "config": result["config"],
                          }, result)


class KnowledgeGraphService:
    def __init__(self, stack: DataStack, *, rag_store: ChunkStore | None = None,
                 handler: Callable | None = None):
        if stack is None:
            raise ValueError("KnowledgeGraphService requires an explicit graph stack")
        self.stack, self.rag_store, self.handler = stack, rag_store, handler

    def answer(self, request: KnowledgeGraphRequest) -> QaResponse:
        if not isinstance(request, KnowledgeGraphRequest):
            raise TypeError("KnowledgeGraphService requires KnowledgeGraphRequest")
        from .engine import answer_question
        result = (self.handler or answer_question)(
            request.question, self.stack, use_llm=request.use_llm, rag_store=self.rag_store)
        statuses = {"ok": "answered", "ambiguous": "clarification", "invalid": "invalid",
                    "unresolved": "unresolved", "error": "error"}
        if result.status not in statuses:
            raise ValueError("Unsupported graph response status")
        return QaResponse("knowledge_graph", statuses[result.status], result.text,
                          tuple((result.report or {}).get("evidence", [])), {
                              "schema": result.schema_trace, "report": result.report,
                              "kind": result.kind, "verdict": result.verdict,
                              "explanation": result.explanation,
                          }, result)
