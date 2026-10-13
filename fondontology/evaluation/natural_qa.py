"""Source-bound natural questions with evaluation-only evidence spans."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from fondontology.corpus.data_catalog import build_catalog_records
from .search_scope import input_cues


class NaturalQAError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NaturalQAError(message)


def read_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_sources(data_root: Path) -> tuple[dict, dict, list[dict]]:
    catalog = read_json(data_root / "source_catalog.json")
    lock = read_json(data_root / "rag_source_lock.json")
    audit = build_catalog_records(data_root / "source_catalog.json", data_root=data_root)
    require(len(audit["records"]) == lock["document_count"], "Frozen source count differs")
    sources = {document["id"]: document for document in catalog["documents"]
               if document["status"] == "ready"}
    registry = [{"doc_id": identifier, "title": document["title"]}
                for identifier, document in sources.items()]
    return lock, sources, registry


def validate_cases(cases: list[dict], data_root: Path) -> tuple[list[dict], dict]:
    lock, sources, registry = load_sources(data_root)
    require(isinstance(cases, list) and bool(cases), "Cases must be nonempty")
    identifiers = set()
    validated = []
    texts = {}
    for case in cases:
        required = {"id", "question", "category", "task_type", "difficulty", "reference",
                    "expected_behavior", "evidence", "answer_points", "forbidden_claims",
                    "source_notes"}
        require(isinstance(case, dict) and set(case) == required, "Unexpected author case fields")
        for field in ("id", "question", "reference", "source_notes"):
            require(isinstance(case[field], str) and bool(case[field].strip()),
                    f"Invalid {field}")
        identifier = case["id"]
        require(identifier not in identifiers, f"Duplicate ID: {identifier}")
        identifiers.add(identifier)
        require(not input_cues(case, registry)["has_source_cues"],
                f"Source cue in question: {identifier}")
        base_titles = [re.sub(r"[（(].*?[）)]", "", source["title"]).strip()
                       for source in registry]
        require(not any(title and title in case["question"] for title in base_titles)
                and not re.search(r"\b(?:ver|version|v)\s*\d+(?:\.\d+)+\b",
                                  case["question"], flags=re.I),
                f"Document title or technical version cue: {identifier}")
        require(case["category"] in {"user", "business", "system"}, "Invalid category")
        require(case["task_type"] in {"fact", "workflow", "comparison", "boundary"},
                "Invalid task type")
        require(case["difficulty"] in {"single", "multi"}, "Invalid difficulty")
        require(case["expected_behavior"] in {"answer", "clarify", "abstain"}, "Invalid behavior")
        for field in ("answer_points", "forbidden_claims"):
            require(isinstance(case[field], list) and bool(case[field])
                    and all(isinstance(item, str) and item.strip() for item in case[field]),
                    f"Invalid {field}: {identifier}")
        require(isinstance(case["evidence"], list), "Evidence must be an array")
        require(bool(case["evidence"]) == (case["expected_behavior"] == "answer"),
                f"Only answerable cases have positive evidence: {identifier}")
        evidence = []
        for target in case["evidence"]:
            require(isinstance(target, dict) and set(target) == {"doc_id", "quote"},
                    "Author evidence requires doc_id and quote only")
            document = sources.get(target["doc_id"])
            require(document is not None, f"Target outside frozen sources: {identifier}")
            quote = target["quote"]
            require(isinstance(quote, str) and len(quote.strip()) >= 10, "Evidence quote too short")
            if document["id"] not in texts:
                texts[document["id"]] = (data_root / document["markdown_path"]).read_bytes().decode("utf-8")
            text = texts[document["id"]]
            require(text.count(quote) == 1, f"Evidence must match exactly once: {identifier}/{document['id']}")
            start = text.index(quote)
            body_line = document["verification"]["body_start_line"]
            body_start = sum(len(line) for line in text.splitlines(keepends=True)[:body_line - 1])
            require(start >= body_start, f"Metadata cannot be gold evidence: {identifier}")
            evidence.append({
                **target, "markdown_path": document["markdown_path"],
                "markdown_sha256": document["markdown_sha256"],
                "raw_sha256": document["raw_sha256"],
                "char_start": start, "char_end": start + len(quote),
            })
        spans = [(item["doc_id"], item["char_start"], item["char_end"]) for item in evidence]
        require(len(spans) == len(set(spans)), f"Duplicate evidence: {identifier}")
        validated.append({**case, "evidence": evidence})
    report = {
        "source_version": lock["source_version"], "catalog_sha256": lock["catalog_sha256"],
        "case_count": len(validated),
        "source_cue_case_count": 0,
        "by_category": dict(Counter(case["category"] for case in validated)),
        "by_behavior": dict(Counter(case["expected_behavior"] for case in validated)),
        "by_task": dict(Counter(case["task_type"] for case in validated)),
        "target_document_count": len({target["doc_id"] for case in validated for target in case["evidence"]}),
        "cross_document_case_count": sum(len({target["doc_id"] for target in case["evidence"]}) > 1
                                         for case in validated),
    }
    return validated, report


def validate_release(directory: Path, data_root: Path) -> dict:
    freeze = read_json(directory / "freeze.json")
    require(freeze.get("schema_version") == "1.0", "Invalid freeze schema")
    require(freeze.get("review_status") == "draft"
            and freeze.get("independent_human_review") is False, "Invalid draft review declaration")
    expected_files = {"questions.json", "oracle.json", "references.json", "protocol.json", "sources.json"}
    if "domain-review.json" in freeze.get("files", {}):
        expected_files.add("domain-review.json")
    require(set(freeze.get("files", {})) == expected_files, "Incomplete freeze file binding")
    for name, digest in freeze["files"].items():
        require(sha(directory / name) == digest, f"Frozen QA file hash mismatch: {name}")
    questions = read_json(directory / "questions.json")
    oracle = read_json(directory / "oracle.json")
    references = read_json(directory / "references.json")
    protocol = read_json(directory / "protocol.json")
    lock, _sources, registry = load_sources(data_root)
    require(read_json(directory / "sources.json") == {"schema_version": "1.0", "sources": registry},
            "Scope registry differs from frozen sources")
    require(protocol.get("require_unscoped") is True
            and protocol.get("runtime_fields") == ["id", "question", "as_of"]
            and protocol.get("source_version") == lock["source_version"]
            and protocol.get("catalog_sha256") == lock["catalog_sha256"]
            and protocol.get("baseline_snapshot") == lock["snapshot_id"]
            and protocol.get("as_of") == freeze.get("as_of") == "2026-10-13"
            and protocol.get("baseline_members_sha256") == lock["snapshot_members_sha256"],
            "Protocol scope or source binding mismatch")
    require(questions.get("schema_version") == "1.0", "Invalid questions schema")
    require(set(questions) == {"schema_version", "cases"}, "Runtime questions contain metadata")
    require(oracle.get("schema_version") == "2.0", "Invalid oracle schema")
    require(oracle.get("source_version") == lock["source_version"], "Oracle source version mismatch")
    require(oracle.get("authorship") == {
        "kind": "source_authored_model_draft", "created_without_actuals": True,
        "independent_human_review": False,
    }, "Oracle must retain model-draft authorship")
    if "domain-review.json" in expected_files:
        review = read_json(directory / "domain-review.json")
        require(review.get("full_batch_approved") is True
                and review.get("human_reviewed") is False
                and review.get("author_input_sha256") == freeze.get("author_input_sha256")
                and review.get("source_version") == lock["source_version"]
                and review.get("catalog_sha256") == lock["catalog_sha256"],
                "Independent model review binding mismatch")
        reviewed = review.get("cases", [])
        require(len(reviewed) == len(oracle["rows"])
                and {case["id"] for case in reviewed} == {row["id"] for row in oracle["rows"]}
                and all(case.get("decision") == "accept" for case in reviewed),
                "Incomplete question-by-question model acceptance")
    reconstructed = []
    for row in oracle["rows"]:
        require("split" in row and row["split"] in {"dev", "challenge"}, "Invalid split")
        reconstructed.append({key: value for key, value in row.items() if key != "split"})
        reconstructed[-1]["evidence"] = [
            {"doc_id": target["doc_id"], "quote": target["quote"]} for target in row["evidence"]]
    validated, report = validate_cases(reconstructed, data_root)
    require(len(questions["cases"]) == len(validated) == freeze["case_count"], "QA count mismatch")
    for case, row in zip(questions["cases"], validated):
        require(set(case) == {"id", "question", "as_of"}, "Gold or scope leaked into runtime case")
        require(case == {"id": row["id"], "question": row["question"], "as_of": freeze["as_of"]},
                "Question/oracle mismatch")
    require([case["evidence"] for case in validated] == [row["evidence"] for row in oracle["rows"]],
            "Gold offsets or source hashes differ from frozen text")
    expected_references = [{"id": row["id"], "reference": row["reference"],
                            "reference_contexts": [target["quote"] for target in row["evidence"]],
                            "review_status": "draft"} for row in validated]
    require(references == {"schema_version": "1.0", "rows": expected_references},
            "References differ from source-authored oracle")
    require(report["source_version"] == freeze["source_version"]
            and report["catalog_sha256"] == freeze["catalog_sha256"], "QA source version mismatch")
    return report


def span_coverage(target: dict, evidence: list[dict]) -> float:
    intervals = []
    for item in evidence:
        if item.get("doc_id") != target["doc_id"] or item.get("sha256") != target["markdown_sha256"]:
            continue
        locator = item.get("locator", {})
        start, end = locator.get("char_start"), locator.get("char_end")
        if type(start) is int and type(end) is int:
            start, end = max(start, target["char_start"]), min(end, target["char_end"])
            if start < end:
                intervals.append((start, end))
    covered = 0
    cursor = target["char_start"]
    for start, end in sorted(intervals):
        if end > cursor:
            covered += end - max(start, cursor)
            cursor = end
    return covered / (target["char_end"] - target["char_start"])


def score_spans(oracle: list[dict], audited_rows: list[dict]) -> dict:
    actual = {row["id"]: row for row in audited_rows}
    require(len(actual) == len(audited_rows) and len(oracle) == len(actual)
            and {row["id"] for row in oracle} == set(actual), "Score IDs must match exactly")
    results = []
    for row in oracle:
        trace = actual[row["id"]]
        coverage = [span_coverage(target, trace.get("evidence", [])) for target in row["evidence"]]
        execution_error = trace.get("status") == "error"
        answerable = row["expected_behavior"] == "answer"
        results.append({
            "id": row["id"], "category": row["category"], "split": row["split"],
            "source_count": len({target["doc_id"] for target in row["evidence"]}),
            "expected_behavior": row["expected_behavior"], "status": trace.get("status"),
            "target_span_coverage": coverage,
            "complete_evidence": (all(value == 1 for value in coverage) and not execution_error)
            if answerable else None,
            "execution_error": execution_error,
            "response_behavior_requires_review": not answerable,
        })
    answer_rows = [row for row in results if row["expected_behavior"] == "answer"]
    by_category = {}
    for category in ("user", "business", "system"):
        category_rows = [row for row in results if row["category"] == category]
        category_answers = [row for row in category_rows if row["expected_behavior"] == "answer"]
        by_category[category] = {
            "denominator": len(category_rows),
            "answerable_denominator": len(category_answers),
            "complete_evidence_count": sum(row["complete_evidence"] for row in category_answers),
            "behavior_review_denominator": len(category_rows) - len(category_answers),
        }
    return {
        "scoring_scope": "retrieval_evidence_span_coverage_only",
        "denominator": len(results), "answerable_denominator": len(answer_rows),
        "complete_evidence_count": sum(row["complete_evidence"] for row in answer_rows),
        "complete_evidence_rate": sum(row["complete_evidence"] for row in answer_rows) / len(answer_rows)
        if answer_rows else None,
        "execution_error_count": sum(row["execution_error"] for row in results),
        "behavior_review_denominator": len(results) - len(answer_rows),
        "by_category": by_category,
        "cases": results,
        "limits": [
            "Span coverage is stricter than semantic sufficiency; cite-boundary verbosity can affect it.",
            "Clarification and abstention are not inferred from retrieval status; review their responses separately.",
            "Coverage does not establish answer correctness, legal currency, or authentic system execution.",
        ],
    }
