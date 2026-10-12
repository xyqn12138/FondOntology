"""Source-authored, deterministic legal retrieval scoring.

This scorer evaluates article retrieval and scope discipline only. It never
judges whether a user's prose answer is legally correct.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .artifact_audit import _iso, _obj, _parse, _text


class LegalRetrievalError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LegalRetrievalError(message)


def _ids(value: Any, where: str) -> list[str]:
    _require(isinstance(value, list), f"{where}: expected array")
    for item in value:
        _text(item, where)
    _require(len(value) == len(set(value)), f"{where}: duplicate IDs")
    return value


def load_questions(path: Path) -> list[dict[str, Any]]:
    payload = _obj(_parse(path.read_text(encoding="utf-8")),
                   {"schema_version", "cases"}, set(), "questions")
    _require(payload["schema_version"] == "1.0", "questions schema_version must be 1.0")
    _require(isinstance(payload["cases"], list) and payload["cases"], "questions.cases must be nonempty")
    allowed = {"id", "question", "as_of", "doc_ids", "version_ids", "entity_iri",
               "category", "scenario", "split", "source_notes"}
    identifiers = set()
    for index, case in enumerate(payload["cases"]):
        case = _obj(case, {"id", "question", "as_of"}, allowed - {"id", "question", "as_of"},
                    f"questions.cases[{index}]")
        identifier = _text(case["id"], f"questions.cases[{index}].id")
        _require(identifier not in identifiers, "duplicate question ID")
        identifiers.add(identifier)
        _text(case["question"], f"questions.cases[{index}].question")
        _iso(case["as_of"], f"questions.cases[{index}].as_of")
        _ids(case.get("doc_ids", []), f"questions.cases[{index}].doc_ids")
        _ids(case.get("version_ids", []), f"questions.cases[{index}].version_ids")
        if "entity_iri" in case:
            _text(case["entity_iri"], f"questions.cases[{index}].entity_iri")
        if "category" in case:
            _require(case["category"] in {"system", "business", "user"}, "invalid question category")
        if "scenario" in case:
            _text(case["scenario"], f"questions.cases[{index}].scenario")
        if "split" in case:
            _require(case["split"] in {"train", "dev", "test", "challenge"}, "invalid question split")
        if "source_notes" in case:
            _text(case["source_notes"], f"questions.cases[{index}].source_notes")
    return payload["cases"]


def load_oracle(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _obj(_parse(path.read_text(encoding="utf-8")),
                   {"schema_version", "authorship", "rows"}, set(), "oracle")
    _require(payload["schema_version"] == "1.0", "oracle schema_version must be 1.0")
    authorship = _obj(payload["authorship"], {"kind", "created_without_actuals",
                                              "review_status", "source_description"},
                      set(), "oracle.authorship")
    _require(authorship["kind"] in {"source_authored", "synthetic"}, "invalid oracle authorship kind")
    _require(type(authorship["created_without_actuals"]) is bool and authorship["created_without_actuals"],
             "oracle must declare created_without_actuals=true")
    _require(authorship["review_status"] in {"draft", "reviewed"}, "invalid oracle review status")
    _text(authorship["source_description"], "oracle.source_description")
    _require(isinstance(payload["rows"], list) and payload["rows"], "oracle.rows must be nonempty")
    allowed = {"id", "expected_status", "target_articles", "required_groups",
               "allowed_doc_ids", "allowed_version_ids", "category", "scenario",
               "split", "source_notes"}
    identifiers = set()
    for index, row in enumerate(payload["rows"]):
        row = _obj(row, {"id", "expected_status", "target_articles", "required_groups",
                         "allowed_doc_ids"},
                   allowed - {"id", "expected_status", "target_articles", "required_groups",
                              "allowed_doc_ids"}, f"oracle.rows[{index}]")
        identifier = _text(row["id"], f"oracle.rows[{index}].id")
        _require(identifier not in identifiers, "duplicate oracle ID")
        identifiers.add(identifier)
        _require(row["expected_status"] in {"retrieved", "unresolved"}, "invalid expected_status")
        _ids(row["allowed_doc_ids"], f"oracle.rows[{index}].allowed_doc_ids")
        _ids(row.get("allowed_version_ids", []), f"oracle.rows[{index}].allowed_version_ids")
        targets = row["target_articles"]
        _require(isinstance(targets, list), "target_articles must be an array")
        if row["expected_status"] == "retrieved":
            _require(targets, "retrieved oracle row requires target_articles")
        else:
            _require(not targets and not row["required_groups"], "unresolved row cannot require targets/groups")
        for target in targets:
            _obj(target, {"doc_id", "article_number"}, {"version_id"}, "target_article")
            _text(target["doc_id"], "target_article.doc_id")
            _require(type(target["article_number"]) is int and target["article_number"] > 0,
                     "target article_number must be positive integer")
            if "version_id" in target:
                _text(target["version_id"], "target_article.version_id")
        _require(len({_target_key(target) for target in targets}) == len(targets), "duplicate target article")
        groups = row["required_groups"]
        _require(isinstance(groups, list), "required_groups must be an array")
        for group in groups:
            _require(isinstance(group, list) and group, "required group must be nonempty")
            for target in group:
                _obj(target, {"doc_id", "article_number"}, {"version_id"}, "required_group target")
                _text(target["doc_id"], "required_group doc_id")
                _require(type(target["article_number"]) is int and target["article_number"] > 0,
                         "required_group article_number must be positive integer")
                if "version_id" in target:
                    _text(target["version_id"], "required_group version_id")
            _require(len({_target_key(target) for target in group}) == len(group), "duplicate required-group alternative")
        for field in ("category", "scenario", "split", "source_notes"):
            if field in row:
                if field == "category":
                    _require(row[field] in {"system", "business", "user"}, "invalid oracle category")
                elif field == "split":
                    _require(row[field] in {"train", "dev", "test", "challenge"}, "invalid oracle split")
                else:
                    _text(row[field], f"oracle.{field}")
    return authorship, payload["rows"]


def _target_key(target: dict[str, Any]) -> tuple[str, int, str | None]:
    return target["doc_id"], target["article_number"], target.get("version_id")


@dataclass
class RetrievalCaseResult:
    id: str
    target_article_recall: float
    first_target_mrr: float
    required_group_coverage: float
    scope_violations: int
    unresolved: int
    errors: int
    retrieved_count: int
    status: str
    expected_status_match: bool
    category: str | None = None
    split: str | None = None


def _matches(item: dict[str, Any], target: dict[str, Any]) -> bool:
    locator = item.get("locator", {})
    return (item.get("complete_article") is True
            and locator.get("content_kind") == "legal_article"
            and type(locator.get("article_number")) is int
            and item["doc_id"] == target["doc_id"]
            and locator["article_number"] == target["article_number"]
            and (target.get("version_id") is None or target["version_id"] == item["version_id"]))


def _summary(
    results: list[RetrievalCaseResult], oracle_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    denominator = len(results)
    nonpass_count = sum(
        item.errors > 0 or item.scope_violations > 0 or not item.expected_status_match
        or (oracle_by_id[item.id]["expected_status"] == "retrieved"
            and (item.target_article_recall < 1
                 or (bool(oracle_by_id[item.id]["required_groups"]) and item.required_group_coverage < 1)))
        for item in results
    )
    totals = {
        "target_article_recall": sum(item.target_article_recall for item in results),
        "first_target_mrr": sum(item.first_target_mrr for item in results),
        "required_group_coverage": sum(item.required_group_coverage for item in results),
        "scope_violation_rate": sum(item.scope_violations > 0 for item in results),
        "unresolved_rate": sum(item.unresolved > 0 for item in results),
        "error_rate": sum(item.errors > 0 for item in results),
        "expected_status_match_rate": sum(item.expected_status_match for item in results),
    }
    return {
        "denominator": denominator, "pass_count": denominator - nonpass_count,
        "nonpass_count": nonpass_count, "acceptance": False,
        **{name: total / denominator if denominator else None for name, total in totals.items()},
    }


def score_retrieval(
    questions: list[dict[str, Any]], oracle: list[dict[str, Any]],
    audit: dict[str, Any],
) -> dict[str, Any]:
    """Score only deterministic retrieval properties from a verified audit."""
    _require(audit.get("verified") is True, "retrieval scoring requires a verified artifact audit")
    _require(audit.get("verification_kind") == "local_artifact_consistency_only",
             "unsupported audit verification kind")
    question_by_id = {case["id"]: case for case in questions}
    oracle_by_id = {row["id"]: row for row in oracle}
    audited_rows = {row["id"]: row for row in audit.get("rows", [])}
    _require(bool(questions) and len(question_by_id) == len(questions)
             and len(oracle_by_id) == len(oracle) and len(audited_rows) == len(audit.get("rows", [])),
             "empty or duplicate input IDs")
    _require(set(question_by_id) == set(oracle_by_id) == set(audited_rows),
             "questions/oracle/audit IDs must match exactly")
    case_results: list[RetrievalCaseResult] = []
    for identifier, question in question_by_id.items():
        expected = oracle_by_id[identifier]
        actual = audited_rows[identifier]
        evidence = actual.get("evidence", [])
        allowed_docs = set(expected["allowed_doc_ids"])
        allowed_versions = set(expected.get("allowed_version_ids", []))
        violations = sum(
            bool((item["doc_id"] not in allowed_docs)
                 or (allowed_versions and item["version_id"] not in allowed_versions))
            for item in evidence
        )
        matched: list[int] = []
        ranks: list[int] = []
        for position, item in enumerate(evidence, start=1):
            locator = item.get("locator", {})
            if not item.get("complete_article"):
                continue
            if locator.get("content_kind") != "legal_article" or type(locator.get("article_number")) is not int:
                continue
            for target_index, target in enumerate(expected["target_articles"]):
                if _matches(item, target):
                    matched.append(target_index)
                    ranks.append(position)
        unique_matched = set(matched)
        target_count = len(expected["target_articles"])
        recall = (len(unique_matched) / target_count) if target_count else 0.0
        mrr = (1.0 / min(ranks)) if ranks else 0.0
        group_hits = 0
        for group in expected["required_groups"]:
            if any(_matches(item, target) for item in evidence for target in group):
                group_hits += 1
        group_coverage = (group_hits / len(expected["required_groups"])) if expected["required_groups"] else 0.0
        expected_unresolved = expected["expected_status"] == "unresolved"
        unresolved = int(actual.get("status") == "unresolved")
        errors = int(actual.get("status") == "error")
        case_results.append(RetrievalCaseResult(
            identifier, recall, mrr, group_coverage, violations, unresolved, errors,
            len(evidence), actual.get("status", "unknown"),
            actual.get("status") == "unresolved" if expected_unresolved
            else actual.get("status") in {"retrieved", "answered"},
            expected.get("category"), expected.get("split"),
        ))
    summary = _summary(case_results, oracle_by_id)
    result = {
        "schema_version": "1.0",
        "scoring_scope": "retrieval_only; not user_answer_correctness",
        "audit": {
            "verified": True, "execution_origin": audit.get("execution_origin"),
            "source_authenticity_verified": False, "legal_currency_verified": False,
            "input_file_sha256": audit.get("input_file_sha256"),
            "trace_sha256": audit.get("trace_sha256"),
            "snapshot_members_sha256": audit.get("snapshot_members_sha256"),
        },
        "oracle_authorship": {
            "kind": audit.get("oracle_authorship", "unknown"),
        },
        "denominator": summary["denominator"],
        "acceptance": False,
        "pass_count": summary["pass_count"],
        "nonpass_count": summary["nonpass_count"],
        "expected_status_match_rate": summary["expected_status_match_rate"],
        "nonpass_policy": "any execution error, scope violation, expected-status mismatch, missing target or required group",
        "metric_policy": {
            "denominator": "all declared cases, including unresolved/error controls",
            "no_target_or_group_value": 0.0,
            "article_match": "stable doc_id + article_number + optional version_id; complete source-boundary article only",
            "authorship": "declared source-authored does not independently prove human review or output blindness",
            "empty_group_rates": None,
            "undeclared_group": "undeclared",
            "pass_count": "retrieval gate only; not business acceptance",
        },
        "metrics": {name: value for name, value in summary.items()
                    if name not in {"denominator", "pass_count", "nonpass_count", "acceptance"}},
        "cases": [asdict(item) for item in case_results],
    }
    result["by_category"] = {
        category or "undeclared": _summary(
            [item for item in case_results if item.category == category], oracle_by_id,
        ) for category in ("system", "business", "user", None)
    }
    result["by_split"] = {
        split or "undeclared": _summary(
            [item for item in case_results if item.split == split], oracle_by_id,
        ) for split in ("train", "dev", "test", "challenge", None)
    }
    result["by_expected_status"] = {
        status: _summary(
            [item for item in case_results if oracle_by_id[item.id]["expected_status"] == status],
            oracle_by_id,
        ) for status in ("retrieved", "unresolved")
    }
    return result
