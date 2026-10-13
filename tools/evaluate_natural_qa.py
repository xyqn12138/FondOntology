"""Audit natural QA release and recorded full-corpus retrieval evidence."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.evaluation.artifact_audit import audit_artifact, read_only_connection
from fondontology.evaluation.natural_qa import load_sources, read_json, score_spans, validate_release
from fondontology.evaluation.search_scope import check_output_path, diagnose_search_scope


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("evaluation/cases/real_user_qa_v1"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--corpus-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        inputs = [args.actual, args.corpus_db, *args.directory.glob("*.json"),
                  args.data_root / "source_catalog.json", args.data_root / "rag_source_lock.json"]
        check_output_path(args.output, inputs, args.actual)
        validation = validate_release(args.directory, args.data_root)
        questions = read_json(args.directory / "questions.json")["cases"]
        audit = audit_artifact(args.actual, args.corpus_db, questions=questions)
        _lock, sources, _registry = load_sources(args.data_root)
        with closing(read_only_connection(args.corpus_db)) as connection:
            members = connection.execute(
                "SELECT v.document_id,v.sha256 FROM document_versions v "
                "JOIN snapshot_members m ON m.version_id=v.version_id WHERE m.snapshot_id=?",
                (audit["snapshot_id"],),
            ).fetchall()
        expected = {(identifier, document["markdown_sha256"]) for identifier, document in sources.items()}
        if len(members) != len(expected) or {(row["document_id"], row["sha256"]) for row in members} != expected:
            raise ValueError("Snapshot must contain exactly the frozen 43 source bodies")
        scope = diagnose_search_scope(
            args.directory / "questions.json", args.directory / "sources.json",
            actual_path=args.actual, corpus_db=args.corpus_db, require_unscoped=True)
        score = score_spans(read_json(args.directory / "oracle.json")["rows"], audit["rows"])
        output = {
            "schema_version": "1.0", "source_version": validation["source_version"],
            "validation": validation, "scope": scope, "retrieval": score,
            "answer_correctness": "not_scored",
            "audit": {key: value for key, value in audit.items() if key != "rows"},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output), "cases": score["denominator"],
                          "complete_evidence_count": score["complete_evidence_count"],
                          "scope_passed": scope["passed"], "answer_correctness": "not_scored"},
                         ensure_ascii=False))
        return 0 if scope["passed"] and not score["execution_error_count"] else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Natural QA evaluation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
