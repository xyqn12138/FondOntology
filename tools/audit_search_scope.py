"""Diagnose benchmark source cues and independently audited recorded search scope."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.evaluation.artifact_audit import ArtifactAuditError
from fondontology.evaluation.legal_retrieval import LegalRetrievalError
from fondontology.evaluation.search_scope import (
    SearchScopeError, check_output_path, diagnose_search_scope,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--registry", type=Path,
                        default=Path("evaluation/corpora/official-laws-v1.sources.json"))
    parser.add_argument("--actual", type=Path)
    parser.add_argument("--corpus-db", type=Path)
    parser.add_argument("--require-unscoped", action="store_true",
                        help="require benchmark cases with only id/question/as_of and full available body scope")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if (args.actual is None) != (args.corpus_db is None):
            raise SearchScopeError("--actual and --corpus-db must be paired")
        inputs = [args.questions, args.registry]
        if args.actual is not None:
            inputs.extend([args.actual, args.corpus_db])
        check_output_path(args.output, inputs, args.actual)
        report = diagnose_search_scope(
            args.questions, args.registry, actual_path=args.actual, corpus_db=args.corpus_db,
            require_unscoped=args.require_unscoped)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2),
                               encoding="utf-8")
        print(json.dumps({
            "output": str(args.output.resolve()), "diagnostic_scope": report["diagnostic_scope"],
            "execution_checked": report["execution_checked"], "row_count": report["row_count"],
            "cue_case_count": report["cue_case_count"], "nonpass_count": report["nonpass_count"],
            "passed": report["passed"],
        }, ensure_ascii=False))
        return 0 if report["passed"] else 1
    except (ArtifactAuditError, LegalRetrievalError, SearchScopeError, OSError, ValueError,
            KeyError, TypeError) as exc:
        print(f"search-scope diagnostic unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
