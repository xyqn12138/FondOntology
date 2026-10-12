"""Audit recorded retrieval artifacts and score source-authored article retrieval."""
from __future__ import annotations

import argparse
import json
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.evaluation.artifact_audit import ArtifactAuditError, audit_artifact
from fondontology.evaluation.legal_retrieval import LegalRetrievalError, load_oracle, load_questions, score_retrieval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--corpus-db", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-trace", action="store_true",
                        help="perform read-only trace/database verification before scoring")
    args = parser.parse_args(argv)
    try:
        for source in (args.actual, args.corpus_db, args.questions, args.oracle):
            if args.output.resolve() == source.resolve() or (
                args.output.exists() and source.exists() and args.output.samefile(source)
            ):
                raise ArtifactAuditError("output must not overwrite an input")
        if not args.verify_trace:
            raise ArtifactAuditError("--verify-trace is required; scoring never accepts self-declared hashes")
        questions = load_questions(args.questions)
        authorship, oracle = load_oracle(args.oracle)
        audit = audit_artifact(args.actual, args.corpus_db, questions=questions)
        from fondontology.evaluation.ragas_runner import load_input
        provenance, _rows = load_input(args.actual)
        trace_path = Path(provenance["trace_path"])
        if not trace_path.is_absolute():
            trace_path = args.actual.resolve().parent / trace_path
        if args.output.resolve() == trace_path.resolve() or (
            args.output.exists() and trace_path.exists() and args.output.samefile(trace_path)
        ):
            raise ArtifactAuditError("output must not overwrite trace")
        scored = score_retrieval(questions, oracle, audit)
        scored["oracle_authorship"] = authorship
        scored["audit"] = {key: value for key, value in audit.items() if key != "rows"}
        scored["questions_file_sha256"] = hashlib.sha256(args.questions.read_bytes()).hexdigest()
        scored["oracle_file_sha256"] = hashlib.sha256(args.oracle.read_bytes()).hexdigest()
        scored["scorer_implementation_sha256"] = hashlib.sha256(
            (ROOT / "fondontology/evaluation/legal_retrieval.py").read_bytes()).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(scored, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
        print(json.dumps({
            "output": str(args.output.resolve()), "verified": True,
            "row_count": scored["denominator"], "scoring_scope": scored["scoring_scope"],
            "nonpass_count": scored["nonpass_count"], "acceptance": False,
        }, ensure_ascii=False))
        return 1 if scored["nonpass_count"] > 0 else 0
    except (ArtifactAuditError, LegalRetrievalError, OSError, ValueError) as exc:
        print(f"legal retrieval evaluation unavailable: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
