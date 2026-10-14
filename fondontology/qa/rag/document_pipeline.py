"""Explicit snapshot-backed document retrieval, separate from ontology intent routing."""

from __future__ import annotations

import hashlib
from pathlib import Path
from time import perf_counter

from fondontology.corpus import CorpusError

from .document_scope import SCOPE_POLICY, resolve_scope
from .document_retrieval import RetrievalStrategyError, retrieve_documents
from .generation import PROMPT_VERSION, generate_answer as _generate
from .store import ChunkStore, RagChunk, load_corpus_store


UNRESOLVED_RESPONSE = "UNRESOLVED: no matching evidence in the selected snapshot, date and entity scope."


def _evidence(chunk: RagChunk, position: int) -> dict:
    return {
        "evidence_id": f"R{position}", "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id, "version_id": chunk.version_id,
        "text": chunk.text, "locator": dict(chunk.locator),
        "sha256": chunk.locator.get("sha256"),
        "authority": chunk.authority, "status": chunk.status,
        "provenance": dict(chunk.provenance), "entity_links": list(chunk.entity_links),
        "issued_date": chunk.issued_date, "effective_from": chunk.effective_from,
        "withdrawn_date": chunk.withdrawn_date,
        "extraction_quality": chunk.extraction_quality,
    }


def answer_document(question: str, *, db_path: Path | str, snapshot_id: str,
                    as_of: str, top_k: int = 5, entity_iri: str | None = None,
                    doc_ids: list[str] | None = None, version_ids: list[str] | None = None,
                    allow_nontrusted: bool = False,
                    include_undated_research: bool = False,
                    generate: bool = False, store: ChunkStore | None = None,
                    retrieval_strategy: str = "bm25", candidate_k: int = 20,
                    retrieval_cache: Path | str | None = None,
                    allow_retrieval_network: bool = False, resources=None,
                    query_transform: str = "identity", query_transform_resource=None) -> dict:
    """Return actual contexts and an auditable trace; no reference/gold arguments exist."""
    if not isinstance(question, str) or not question.strip():
        raise CorpusError("question must be a nonempty string")
    if type(top_k) is not int or top_k < 1:
        raise CorpusError("top_k must be a positive integer")
    if type(candidate_k) is not int or candidate_k < top_k:
        raise CorpusError("candidate_k must be an integer at least top_k")
    if doc_ids is not None and not isinstance(doc_ids, list):
        raise CorpusError("doc_ids must be a list or null")
    if version_ids is not None and not isinstance(version_ids, list):
        raise CorpusError("version_ids must be a list or null")
    if entity_iri is not None and (not isinstance(entity_iri, str) or not entity_iri.strip()):
        raise CorpusError("entity_iri must be a nonempty explicit entity ID")
    if type(generate) is not bool:
        raise CorpusError("generate must be boolean")
    started = perf_counter()
    store = store or load_corpus_store(
        db_path, snapshot_id, as_of=as_of, allow_nontrusted=allow_nontrusted,
        include_undated_research=include_undated_research)
    metadata = store.corpus_metadata
    if (not store.strict_scope or metadata.get("snapshot_id") != snapshot_id
            or metadata.get("db_path") != str(Path(db_path).resolve())
            or metadata.get("as_of") != as_of
            or metadata.get("include_undated_research") != include_undated_research
            or (metadata.get("kind") != "trusted" and not allow_nontrusted)):
        raise CorpusError("Preloaded store must match the explicit snapshot, date and trust policy")
    scope = resolve_scope(question, store, doc_ids=doc_ids, version_ids=version_ids,
                          entity_iri=entity_iri)
    if query_transform != "identity" and query_transform_resource is None:
        from .document_providers import build_query_transform_resource
        query_transform_resource = build_query_transform_resource
    strategy_error = None
    try:
        retrieval = retrieve_documents(
            store, scope, strategy=retrieval_strategy, candidate_k=candidate_k,
            cache_path=retrieval_cache, allow_network=allow_retrieval_network,
            resources=resources, query_transform=query_transform,
            query_transform_resource=query_transform_resource)
        ranking, hits, strategy_trace = (
            retrieval.ranking, retrieval.hits, retrieval.strategy_trace)
    except RetrievalStrategyError as error:
        strategy_error = error.reason
        ranking, hits, strategy_trace = retrieval_strategy, [], error.strategy_trace
    evidence = [_evidence(chunk, position)
                for position, (chunk, score) in enumerate(hits[:top_k], 1)]
    candidates = [{
        "rank": position, "chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id,
        "version_id": chunk.version_id, "score": score, "ranking": ranking,
        "selected": position <= top_k,
    } for position, (chunk, score) in enumerate(hits, 1)]
    selected_article_addresses = {
        (chunk.doc_id, chunk.version_id, chunk.locator.get("article_number"))
        for chunk, score in hits[:top_k]}
    budget_excluded_articles = [
        article for article in scope["requested_articles"]
        if scope["status"] == "resolved"
        and (article["doc_id"], article["version_id"],
             article["article_number"]) not in selected_article_addresses]
    retrieval_debug = {
        "ranking": ranking, "top_k": top_k,
        "candidate_count": len(hits), "selected_count": len(evidence),
        "budget_excluded_chunk_ids": [chunk.chunk_id for chunk, score in hits[top_k:]],
        "budget_excluded_articles": budget_excluded_articles,
        "article_budget_sufficient": not budget_excluded_articles,
    }
    retrieval_latency = (perf_counter() - started) * 1000
    warnings = [
        "Extracts establish what the stored bytes say, not legal currency, completeness "
        "or original-source authenticity. A source URI alone does not verify these."
    ]
    if store.corpus_metadata["kind"] != "trusted":
        warnings.append("Non-trusted snapshot: research/regression evidence is not authoritative law.")
    if any(item["issued_date"] is None for item in evidence):
        warnings.append("Unknown issue dates: inclusion does not establish historical availability.")
    if any(item["extraction_quality"] for item in evidence):
        warnings.append("Extracted content must be checked against original source locators.")
    if budget_excluded_articles:
        warnings.append(
            "Retrieval budget excluded requested articles; the selected evidence is incomplete.")
    if strategy_error:
        warnings.append(f"Retrieval strategy failed: {strategy_error}; no fallback was used.")
    mode = "extractive"
    status = "error" if strategy_error else ("retrieved" if evidence else "unresolved")
    response = ("\n\n".join(f"[{item['evidence_id']}] {item['text']}" for item in evidence)
                if evidence else UNRESOLVED_RESPONSE)
    if not evidence and scope["reason"]:
        response += f" Reason: {scope['reason']}."
    if strategy_error:
        response += f" Retrieval error: {strategy_error}."
    llm = {"provider": "none", "model": "none", "prompt_version": PROMPT_VERSION,
           "used_llm": False}
    generation_latency = 0.0
    if generate and evidence:
        started = perf_counter()
        generated, llm = _generate(question, evidence)
        generation_latency = (perf_counter() - started) * 1000
        if generated is not None:
            response, mode, status = generated, "generated", "answered"
            warnings.append("Generation validates citation IDs only, not semantic faithfulness.")
        elif llm["validation"] == "model_unresolved":
            response, mode, status = UNRESOLVED_RESPONSE, "generated", "unresolved"
        else:
            warnings.append("Generation failed validation; response is the extractive baseline.")
    return {
        "user_input": question, "response": response,
        "retrieved_contexts": [item["text"] for item in evidence],
        "status": status, "answer_mode": mode, "evidence": evidence,
        "scope": scope, "retrieval_candidates": candidates,
        "retrieval_debug": retrieval_debug,
        "strategy_trace": strategy_trace,
        "unresolved_reason": strategy_error or scope["reason"] or (
            "no_lexical_match" if not evidence else None),
        "warnings": warnings,
        "corpus": {**store.corpus_metadata,
                   "retrieval": "bm25-only" if retrieval_strategy == "bm25" else retrieval_strategy},
        "retrieval_latency_ms": retrieval_latency,
        "generation_latency_ms": generation_latency,
        "config": {
            "top_k": top_k, "entity_iri": entity_iri, "generate_requested": generate,
            "doc_ids": doc_ids, "version_ids": version_ids, "scope_policy": SCOPE_POLICY,
            "retrieval": "bm25-only" if retrieval_strategy == "bm25" else retrieval_strategy,
            "allow_nontrusted": allow_nontrusted,
            "retrieval_strategy": retrieval_strategy, "candidate_k": candidate_k,
            "query_transform": query_transform,
            "rrf_k": 60, "child_target_chars": 240,
            "retrieval_cache": str(Path(retrieval_cache).resolve()) if retrieval_cache else None,
            "allow_retrieval_network": allow_retrieval_network,
            "include_undated_research": include_undated_research,
            "pipeline_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "snapshot_members_sha256": store.corpus_metadata["members_sha256"],
            "llm": llm,
        },
    }
