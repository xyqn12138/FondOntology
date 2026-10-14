"""Build or validate a source-bound draft QA release without executing RAG."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.evaluation.natural_qa import (
    NaturalQAError, load_sources, read_json, sha, validate_cases, validate_release,
)


def encoded(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors", type=Path, action="append")
    parser.add_argument("--directory", type=Path,
                        default=Path("evaluation/cases/real_user_qa_v1"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--review", type=Path, help="bind an independent model review of exact author inputs")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.validate:
            if args.authors:
                raise NaturalQAError("--validate does not accept author inputs")
            report = validate_release(args.directory, args.data_root)
        else:
            if not args.authors:
                raise NaturalQAError("Build requires explicit author inputs")
            cases = [case for path in args.authors for case in read_json(path)["cases"]]
            rows, report = validate_cases(cases, args.data_root)
            lock, _sources, registry = load_sources(args.data_root)
            author_hashes = {path.name: sha(path) for path in args.authors}
            review = read_json(args.review) if args.review else None
            if review is not None:
                if (review.get("full_batch_approved") is not True
                        or review.get("human_reviewed") is not False
                        or review.get("author_input_sha256") != author_hashes
                        or review.get("source_version") != lock["source_version"]
                        or review.get("catalog_sha256") != lock["catalog_sha256"]):
                    raise NaturalQAError("Model review must approve exact author files and frozen sources")
                reviewed = review.get("cases", [])
                if (len(reviewed) != len(rows)
                        or {case["id"] for case in reviewed} != {row["id"] for row in rows}
                        or any(case.get("decision") != "accept" for case in reviewed)):
                    raise NaturalQAError("Every published question requires an explicit model-review acceptance")
            questions = [{"id": row["id"], "question": row["question"], "as_of": "2026-10-13"}
                         for row in rows]
            oracle_rows = [{**row, "split": "challenge" if row["difficulty"] == "multi"
                            or row["expected_behavior"] != "answer" else "dev"} for row in rows]
            payloads = {
                "sources.json": {"schema_version": "1.0", "sources": registry},
                "questions.json": {"schema_version": "1.0", "cases": questions},
                "oracle.json": {
                    "schema_version": "2.0",
                    "authorship": {"kind": "source_authored_model_draft",
                                   "created_without_actuals": True,
                                   "independent_human_review": False},
                    "source_version": lock["source_version"], "rows": oracle_rows,
                },
                "references.json": {"schema_version": "1.0", "rows": [
                    {"id": row["id"], "reference": row["reference"],
                     "reference_contexts": [target["quote"] for target in row["evidence"]],
                     "review_status": "draft"} for row in rows]},
                "protocol.json": {
                    "schema_version": "1.0", "dataset_id": "real_user_qa_v1",
                    "source_version": lock["source_version"],
                    "catalog_sha256": lock["catalog_sha256"],
                    "baseline_snapshot": lock["snapshot_id"],
                    "baseline_members_sha256": lock["snapshot_members_sha256"],
                    "as_of": "2026-10-13", "require_unscoped": True,
                    "runtime_fields": ["id", "question", "as_of"],
                    "gold_policy": "Oracle and references never enter retrieval or generation; merge after execution.",
                    "retrieval_budget": {"top_k": [5, 10], "primary": 5, "candidate_k": 40,
                                         "per_case_gold_budget_adjustment": False},
                    "metrics": ["complete_evidence_span_rate", "execution_errors",
                                "recorded_full_corpus_scope_equality", "answer_point_coverage",
                                "unsupported_claims", "clarification_behavior", "abstention_behavior",
                                "ragas_faithfulness", "ragas_response_relevancy",
                                "latency", "context_characters"],
                    "behavior_policy": "Expected behavior is the primary action, not mutually exclusive wording. Partial safe answers, clarification and data-boundary disclosure may coexist. Do not score these from retrieval status.",
                    "review_policy": "AI-authored draft; independent model review is not human certification.",
                    "exposure_policy": "Development/challenge set, not a blind holdout; first execution makes it exposed regression.",
                    "date_policy": "as_of filters available documents; does not certify current legal validity.",
                    "baseline_execution": "not_executed_by_release_builder",
                },
            }
            outputs = {name: encoded(payload) for name, payload in payloads.items()}
            if args.review:
                outputs["domain-review.json"] = args.review.read_bytes()
            freeze = {
                "schema_version": "1.0", "dataset_id": "real_user_qa_v1",
                "frozen_date": "2026-10-14", "as_of": "2026-10-13",
                "case_count": len(rows), "source_version": lock["source_version"],
                "catalog_sha256": lock["catalog_sha256"],
                "review_status": "draft", "independent_human_review": False,
                "author_input_sha256": author_hashes,
                "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in outputs.items()},
                "validation": report,
                "post_freeze_policy": "Corrections require a new explicit revision; never fit gold to actuals.",
            }
            outputs["freeze.json"] = encoded(freeze)
            for name, raw in outputs.items():
                target = args.directory / name
                if target.exists() and target.read_bytes() != raw:
                    raise NaturalQAError(f"Existing release is immutable: {target}")
            args.directory.mkdir(parents=True, exist_ok=True)
            for name, raw in outputs.items():
                (args.directory / name).write_bytes(raw)
            report = validate_release(args.directory, args.data_root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (NaturalQAError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Natural QA validation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
