"""Independent document retrieval/extractive QA; generation requires --generate."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.corpus import CorpusError
from fondontology.qa.rag.document_pipeline import (
    PROMPT_VERSION, UNRESOLVED_RESPONSE, answer_document,
)
from fondontology.qa.rag.store import load_corpus_store
from fondontology.qa.rag.document_retrieval import STRATEGIES


def _provider_resources():
    from fondontology.qa.rag.document_providers import build_resources
    return build_resources()


def load_cases(path: Path) -> list[dict]:
    def pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CorpusError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def reject_constant(value):
        raise CorpusError(f"Non-finite JSON number: {value}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"),
                             object_pairs_hook=pairs,
                             parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        raise CorpusError(f"Invalid cases JSON: {error}") from error
    if (not isinstance(payload, dict) or set(payload) != {"schema_version", "cases"}
            or payload["schema_version"] != "1.0"
            or not isinstance(payload["cases"], list) or not payload["cases"]):
        raise CorpusError("Cases require {schema_version: '1.0', cases: [nonempty rows]}")
    identifiers = set()
    allowed = {"id", "question", "as_of", "entity_iri", "doc_ids", "version_ids", "reference",
               "reference_contexts", "review_status"}
    for case in payload["cases"]:
        if not isinstance(case, dict) or set(case) - allowed:
            raise CorpusError("Unknown case fields")
        if any(not isinstance(case.get(field), str) or not case[field].strip()
               for field in ("id", "question")):
            raise CorpusError("Every case requires nonempty id and question")
        if case["id"] in identifiers:
            raise CorpusError("Case IDs must be unique")
        identifiers.add(case["id"])
        for field in ("as_of", "entity_iri"):
            if field in case and (not isinstance(case[field], str) or not case[field].strip()):
                raise CorpusError(f"Case {field} must be a nonempty string")
        for field in ("doc_ids", "version_ids"):
            if field in case and case[field] is not None and (
                    not isinstance(case[field], list)
                    or any(not isinstance(item, str) or not item.strip()
                           for item in case[field])):
                raise CorpusError(f"{field} must be a list of nonempty strings")
        if "reference" in case and (
                not isinstance(case["reference"], str) or not case["reference"].strip()):
            raise CorpusError("reference must be a nonempty string")
        if "reference_contexts" in case and (
                not isinstance(case["reference_contexts"], list)
                or any(not isinstance(item, str) or not item.strip()
                       for item in case["reference_contexts"])):
            raise CorpusError("reference_contexts must be a list of nonempty strings")
        if "review_status" in case and (
                not isinstance(case["review_status"], str)
                or case["review_status"] not in {"draft", "reviewed"}):
            raise CorpusError("review_status must be draft or reviewed")
    return payload["cases"]


def _code_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                            text=True, capture_output=True, check=False)
    identity = {"head": result.stdout.strip() if result.returncode == 0 else "unknown",
                "python": platform.python_version(), "dependencies": {}}
    for package in ("rdflib", "owlrl", "httpx", "python-dotenv"):
        try:
            identity["dependencies"][package] = version(package)
        except PackageNotFoundError:
            identity["dependencies"][package] = "not-installed"
    for path in (
        root / "fondontology/qa/rag/document_pipeline.py",
        root / "fondontology/qa/rag/document_scope.py",
        root / "fondontology/qa/rag/document_retrieval.py",
        root / "tools/document_rag.py",
        root / "fondontology/qa/rag/store.py",
        root / "fondontology/qa/rag/retrieve.py",
        root / "fondontology/corpus/store.py",
        root / "fondontology/qa/config.py",
        root / "fondontology/qa/intent.py",
    ):
        identity[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    provider = root / "fondontology/qa/rag/document_providers.py"
    if provider.is_file():
        identity[str(provider.relative_to(root))] = hashlib.sha256(provider.read_bytes()).hexdigest()
    return identity


def _failed_result(question: str, as_of: str, entity_iri: str | None,
                   base: dict, args, error: Exception) -> dict:
    return {
        "user_input": question, "response": UNRESOLVED_RESPONSE,
        "retrieved_contexts": [], "status": "error", "answer_mode": "extractive",
        "evidence": [], "warnings": [
            f"Case execution failed ({type(error).__name__}); retained in the fixed denominator."
        ],
        "corpus": {**base, "as_of": as_of},
        "scope": {"policy": "document-body-scope-v1", "status": "unresolved",
                  "reason": "case_execution_error", "requested_doc_ids": None,
                  "requested_version_ids": None, "entity_iri": entity_iri,
                  "title_mentions": [], "title_candidates": [],
                  "selected_doc_ids": [], "selected_version_ids": [],
                  "eligible_chunk_ids": [], "article_numbers": [],
                  "requested_articles": [], "missing_articles": [],
                  "body_query": question, "metadata_excluded_ids": []},
        "retrieval_candidates": [], "unresolved_reason": "case_execution_error",
        "retrieval_latency_ms": None, "generation_latency_ms": None,
        "config": {
            "top_k": args.top_k, "entity_iri": entity_iri,
            "generate_requested": args.generate,
            "retrieval": "bm25-only" if args.retrieval_strategy == "bm25" else args.retrieval_strategy,
            "pipeline_sha256": hashlib.sha256(
                (Path(__file__).resolve().parents[1]
                 / "fondontology/qa/rag/document_pipeline.py").read_bytes()).hexdigest(),
            "llm": {"provider": "none", "model": "none",
                    "prompt_version": PROMPT_VERSION, "used_llm": False},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--as-of", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--question")
    source.add_argument("--cases", type=Path)
    parser.add_argument("--id", default="single-question")
    parser.add_argument("--entity-iri")
    parser.add_argument("--doc-id", action="append")
    parser.add_argument("--version-id", action="append")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--retrieval-strategy", choices=STRATEGIES, default="bm25")
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--retrieval-cache", type=Path)
    parser.add_argument("--allow-retrieval-network", action="store_true")
    parser.add_argument("--allow-nontrusted", action="store_true")
    parser.add_argument("--include-undated-research", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--traces", type=Path)
    args = parser.parse_args(argv)
    if args.include_undated_research and not args.allow_nontrusted:
        parser.error("--include-undated-research requires --allow-nontrusted")
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if args.candidate_k < 1 or args.candidate_k < args.top_k:
        parser.error("--candidate-k must be positive and at least --top-k")
    if args.cases and (args.entity_iri or args.doc_id is not None or args.version_id is not None):
        parser.error("Use case-level entity_iri/doc_ids/version_ids when --cases is supplied")
    traces_path = args.traces or args.output.with_suffix(".traces.jsonl")
    if traces_path.resolve() == args.output.resolve():
        parser.error("--traces and --output must be different files")
    input_paths = [args.db, args.cases] if args.cases else [args.db]
    if any(output.resolve() == source_path.resolve()
           for output in (args.output, traces_path)
           for source_path in input_paths):
        parser.error("Output paths must not overwrite the database or cases file")
    if args.retrieval_cache is not None:
        forbidden = [args.db, args.output, traces_path]
        if args.cases is not None:
            forbidden.append(args.cases)
        if (args.retrieval_cache.exists() and not args.retrieval_cache.is_dir()
                or any(args.retrieval_cache.resolve() == path.resolve() for path in forbidden)):
            parser.error("--retrieval-cache must be a separate directory")
    try:
        cases = (load_cases(args.cases) if args.cases else
                 [{"id": args.id, "question": args.question, "entity_iri": args.entity_iri,
                   "doc_ids": args.doc_id, "version_ids": args.version_id}])
        if not isinstance(args.id, str) or not args.id.strip():
            raise CorpusError("--id must be nonempty")
        traces = []
        rows = []
        default_store = load_corpus_store(
            args.db, args.snapshot, as_of=args.as_of,
            allow_nontrusted=args.allow_nontrusted,
            include_undated_research=args.include_undated_research)
        stores = {args.as_of: default_store}
        for case in cases:
            case_as_of = case.get("as_of", args.as_of)
            try:
                if case_as_of not in stores:
                    stores[case_as_of] = load_corpus_store(
                        args.db, args.snapshot, as_of=case_as_of,
                        allow_nontrusted=args.allow_nontrusted,
                        include_undated_research=args.include_undated_research)
                result = answer_document(
                    case["question"], db_path=args.db, snapshot_id=args.snapshot,
                    as_of=case_as_of, top_k=args.top_k,
                    entity_iri=case.get("entity_iri"), allow_nontrusted=args.allow_nontrusted,
                    include_undated_research=args.include_undated_research, generate=args.generate,
                    store=stores[case_as_of], doc_ids=case.get("doc_ids"),
                    version_ids=case.get("version_ids"),
                    **({
                        "retrieval_strategy": args.retrieval_strategy,
                        "candidate_k": args.candidate_k,
                        "retrieval_cache": args.retrieval_cache,
                        "allow_retrieval_network": args.allow_retrieval_network,
                        "resources": _provider_resources
                        if args.retrieval_strategy in ("hybrid_rrf", "bm25_rerank") else None,
                    } if (args.retrieval_strategy != "bm25" or args.candidate_k != 20
                          or args.retrieval_cache is not None
                          or args.allow_retrieval_network) else {}))
            except Exception as error:
                result = _failed_result(
                    case["question"], case_as_of, case.get("entity_iri"),
                    default_store.corpus_metadata, args, error)
                result["config"].update({
                    "doc_ids": case.get("doc_ids"), "version_ids": case.get("version_ids"),
                    "scope_policy": "document-body-scope-v1",
                    "retrieval_strategy": args.retrieval_strategy,
                    "candidate_k": args.candidate_k,
                    "retrieval_cache": str(args.retrieval_cache.resolve())
                    if args.retrieval_cache else None,
                    "allow_retrieval_network": args.allow_retrieval_network})
                result["scope"].update({
                    "requested_doc_ids": case.get("doc_ids"),
                    "requested_version_ids": case.get("version_ids")})
            traces.append({"id": case["id"], **result})
            rows.append({"id": case["id"], **{
                field: result[field] for field in ("user_input", "response", "retrieved_contexts")
            }})
        trace_bytes = "".join(
            json.dumps(trace, ensure_ascii=False) + "\n" for trace in traces).encode("utf-8")
        first = traces[0]
        calls = [trace["config"]["llm"] for trace in traces
                 if trace["config"]["llm"]["used_llm"]]
        llm = calls[0] if calls else first["config"]["llm"]
        identity = _code_identity()
        envelope = {
            "schema_version": "1.0",
            "provenance": {
                "dataset_snapshot": args.snapshot,
                "corpus_version": first["corpus"]["members_sha256"],
                "ontology_version": "not-used-document-only",
                "code_version": hashlib.sha256(
                    json.dumps(identity, sort_keys=True).encode()).hexdigest(),
                "retrieval_config": {
                    "retrieval": "bm25-only" if args.retrieval_strategy == "bm25"
                    else args.retrieval_strategy,
                    "top_k": args.top_k, "as_of": args.as_of,
                    "retrieval_strategy": args.retrieval_strategy,
                    "candidate_k": args.candidate_k, "rrf_k": 60,
                    "child_target_chars": 240,
                    "retrieval_cache": str(args.retrieval_cache.resolve())
                    if args.retrieval_cache else None,
                    "allow_retrieval_network": args.allow_retrieval_network,
                    "allow_nontrusted": args.allow_nontrusted,
                    "include_undated_research": args.include_undated_research,
                    "generate_requested": args.generate,
                    "scope_policy": "document-body-scope-v1",
                    "per_case_dates": {
                        trace["id"]: trace["corpus"]["as_of"] for trace in traces
                    },
                    "pipeline_sha256": first["config"]["pipeline_sha256"],
                    "code_identity": identity,
                    "cases_sha256": (hashlib.sha256(args.cases.read_bytes()).hexdigest()
                                     if args.cases else None),
                    "case_scopes": [{
                        "id": trace["id"], "as_of": trace["corpus"]["as_of"],
                        "entity_iri": trace["config"]["entity_iri"],
                        "doc_ids": trace["config"].get("doc_ids"),
                        "version_ids": trace["config"].get("version_ids"),
                    } for trace in traces],
                },
                "llm": {field: llm[field] for field in
                        ("provider", "model", "prompt_version", "used_llm")},
                "execution_origin": "rag_pipeline",
                "trace_path": str(traces_path.resolve()),
                "trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
            },
            "rows": rows,
        }
        traces_path.parent.mkdir(parents=True, exist_ok=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        traces_path.write_bytes(trace_bytes)
        if args.output.suffix.lower() == ".jsonl":
            rendered = "".join(
                json.dumps({
                    "schema_version": "1.0", "provenance": envelope["provenance"], **row,
                }, ensure_ascii=False) + "\n" for row in rows)
        else:
            rendered = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({
            "output": str(args.output.resolve()), "traces": str(traces_path.resolve()),
            "rows": len(rows), "unresolved": sum(trace["status"] == "unresolved" for trace in traces),
            "errors": sum(trace["status"] == "error" for trace in traces),
            "answer_modes": sorted({trace["answer_mode"] for trace in traces}),
        }, ensure_ascii=False))
        return 1 if any(trace["status"] == "error" for trace in traces) else 0
    except (CorpusError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
