"""Fixed-denominator paired retrieval diagnostics from independently audited runs."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import median

from .artifact_audit import audit_artifact
from .legal_retrieval import load_oracle, load_questions, score_retrieval


def _matches(evidence: dict, target: dict) -> bool:
    return (evidence.get("complete_article") is True
            and evidence["doc_id"] == target["doc_id"]
            and evidence["locator"].get("article_number") == target["article_number"]
            and (target.get("version_id") is None
                 or evidence["version_id"] == target["version_id"]))


def _distribution(values: list[float], denominator: int) -> dict:
    ordered = sorted(values)
    complete = len(values) == denominator and denominator > 0
    return {"denominator": denominator, "observed": len(values),
            "mean": sum(values) / denominator if complete else None,
            "p50": median(ordered) if complete else None,
            "p95": ordered[math.ceil(len(ordered) * 0.95) - 1] if complete else None}


def _cache_state(strategy: dict) -> str:
    if strategy.get("status") == "bypassed":
        return "bypassed"
    if strategy.get("requested_strategy") != "hybrid_rrf":
        return "not_used"
    cache = strategy.get("cache", {})
    if not cache.get("enabled"):
        return "disabled"
    hits, misses = cache.get("hits", 0), cache.get("misses", 0)
    if hits and misses:
        return "mixed"
    return "warm" if hits else ("cold" if misses else "unused")


def _paired_identity(audit: dict, envelope: dict) -> dict:
    provenance = envelope["provenance"]
    configuration = provenance["retrieval_config"]
    variable_fields = {"retrieval", "retrieval_strategy", "retrieval_cache", "allow_retrieval_network",
                       "query_transform"}
    return {
        "snapshot": audit["snapshot_id"], "members": audit["snapshot_members_sha256"],
        "code_version": provenance["code_version"],
        "ontology_version": provenance["ontology_version"],
        "fixed_configuration": {key: value for key, value in configuration.items()
                                if key not in variable_fields},
    }


def summarize_run(audit: dict, questions: list[dict], oracle: list[dict]) -> dict:
    score = score_retrieval(questions, oracle, audit)
    expected = {row["id"]: row for row in oracle}
    diagnostics = []
    for row in audit["rows"]:
        evidence = row["evidence"]
        targets = expected[row["id"]]["target_articles"]
        positive = sum(any(_matches(item, target) for target in targets) for item in evidence)
        strategy = row.get("strategy_trace", {})
        events = (strategy.get("resource_events", [])
                  + strategy.get("query_transform", {}).get("resource_events", []))
        diagnostics.append({
            "id": row["id"], "expected_status": expected[row["id"]]["expected_status"],
            "target_only_precision": positive / len(evidence) if evidence else 0.0,
            "evidence_characters": sum(len(item["text"]) for item in evidence),
            "retrieval_latency_ms": row.get("retrieval_latency_ms"),
            "http_request_count": len(events),
            "http_transport_error_count": sum(event.get("status") != "ok" for event in events),
            "provider_validation_error_count": sum(
                event.get("response_validation_status") == "error" for event in events),
            "cache_state": _cache_state(strategy),
            "embedding_cache": strategy.get("cache", {}),
        })

    def summarize(rows):
        count = len(rows)
        latencies = [row["retrieval_latency_ms"] for row in rows
                     if type(row["retrieval_latency_ms"]) in {int, float}
                     and math.isfinite(row["retrieval_latency_ms"])]
        return {
            "denominator": count,
            "target_only_precision": (sum(row["target_only_precision"] for row in rows) / count
                                      if count else None),
            "evidence_characters": _distribution([row["evidence_characters"] for row in rows], count),
            "retrieval_latency_ms": _distribution(latencies, count),
            "http_request_count": sum(row["http_request_count"] for row in rows),
            "http_transport_error_count": sum(row["http_transport_error_count"] for row in rows),
            "provider_validation_error_count": sum(row["provider_validation_error_count"] for row in rows),
        }

    return {"retrieval_score": score, "diagnostics": summarize(diagnostics),
            "by_expected_status": {
                status: summarize([row for row in diagnostics if row["expected_status"] == status])
                for status in ("retrieved", "unresolved")},
            "by_cache_state": {
                state: summarize([row for row in diagnostics if row["cache_state"] == state])
                for state in sorted({row["cache_state"] for row in diagnostics})},
            "cases": diagnostics}


def compare_runs(database: Path, questions_path: Path, oracle_path: Path,
                 runs: dict[str, Path]) -> dict:
    if not runs:
        raise ValueError("At least one run is required")
    questions = load_questions(questions_path)
    authorship, oracle = load_oracle(oracle_path)
    reports = {}
    identity = None
    for name, path in runs.items():
        audit = audit_artifact(path, database, questions=questions)
        envelope = json.loads(path.read_text(encoding="utf-8"))
        configuration = envelope["provenance"]["retrieval_config"]
        current = _paired_identity(audit, envelope)
        if identity is not None and current != identity:
            raise ValueError("Paired runs must share snapshot, code, scopes, dates, and retrieval budgets")
        identity = current
        audit["oracle_authorship"] = authorship["kind"]
        reports[name] = {
            "actual_path": str(path.resolve()),
            "actual_sha256": audit["input_file_sha256"],
            "trace_sha256": audit["trace_sha256"],
            "configuration": configuration,
            **summarize_run(audit, questions, oracle),
        }
    return {
        "schema_version": "1.0", "acceptance": False,
        "scope": "Paired retrieval diagnostics; no proof of legal currency or user-answer correctness",
        "questions_sha256": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
        "oracle_sha256": hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
        "oracle_authorship": authorship,
        "metric_policy": {
            "precision": "Oracle-target-only; targets are not exhaustive relevance labels",
            "latency": "Trace per-query wall time excluding CLI corpus load/index construction; cache states separate; p95 nearest rank; incomplete timing => null",
            "cache": "cold=no hits and at least one miss; mixed=hits and misses; warm=only hits; workload aggregates are not pure cold-start or warmed-query benchmarks",
            "calls": "Recorded provider HTTP attempts, including failures; cached embeddings count zero requests",
            "errors": "Transport and response-validation errors are separate; zero HTTP errors does not imply valid provider outputs",
            "paired_identity": "Same corpus, implementation, questions, scopes, dates, candidate/output budgets; only retrieval strategy, cache path and network switch may differ",
            "denominator": "All declared IDs; expected-status subgroups fixed by oracle, never observed success",
        },
        "runs": reports,
    }
