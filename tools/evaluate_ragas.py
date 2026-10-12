"""Validate or explicitly execute Ragas metrics on recorded JSON/JSONL rows."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.evaluation.ragas_runner import (  # noqa: E402
    METRICS, RagasInputError, evaluate, load_input, merge_references, save_results,
    resolve_judge_config,
)


def validate_paths(input_path: Path, references: Path | None,
                   output: Path, database: Path | None) -> None:
    sources = {input_path.resolve()}
    if references is not None:
        sources.add(references.resolve())
    destinations = [output.resolve()]
    if database is not None:
        destinations.append(database.resolve())
    if len(set(destinations)) != len(destinations) or set(destinations) & sources:
        raise RagasInputError("output/database must not overwrite input/references or each other")
    for source in sources:
        for destination in destinations:
            if source.exists() and destination.exists() and source.samefile(destination):
                raise RagasInputError("output/database must not alias input/references")
    if len(destinations) == 2 and all(path.exists() for path in destinations):
        if destinations[0].samefile(destinations[1]):
            raise RagasInputError("output/database must not alias each other")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evaluation/ragas.json")
    parser.add_argument("--execute", action="store_true", help="allow RAGAS judge/embedding calls")
    parser.add_argument("--reuse-project-model", action="store_true",
                        help="explicitly reuse project judge key/base in this process only")
    parser.add_argument("--judge-model", help="override only this evaluation's judge model")
    parser.add_argument("--judge-thinking", choices=("default", "disabled"), default="default",
                        help="explicit judge-only thinking policy; never inherit production settings")
    parser.add_argument("--judge-thinking-param", choices=("enable_thinking", "thinking"),
                        help="explicit provider request parameter required with disabled thinking")
    parser.add_argument("--references", type=Path, help="external reference envelope, merged after production execution")
    parser.add_argument("--metrics", default=",".join(METRICS), help="comma-separated requested metrics")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--max-judge-calls", type=int, default=18)
    parser.add_argument("--max-rows", type=int, default=3)
    parser.add_argument("--database", type=Path, help="also save the run to SQLite")
    parser.add_argument("--corpus-db", type=Path, help="read-only corpus for independent artifact verification")
    parser.add_argument("--verify-trace", action="store_true",
                        help="verify trace/envelope/evidence against --corpus-db before evaluation")
    args = parser.parse_args(argv)
    try:
        validate_paths(args.input, args.references, args.output, args.database)
        if args.timeout <= 0:
            raise RagasInputError("--timeout must be positive")
        if args.execute and (not args.verify_trace or args.timeout > 90
                             or not 1 <= args.max_judge_calls <= 18
                             or not 1 <= args.max_rows <= 3):
            raise RagasInputError("execution requires trace verification and limits: 3 rows, 90 seconds, 18 calls")
        provenance, rows = load_input(args.input)
        protected_paths = [args.corpus_db] if args.corpus_db else []
        if args.verify_trace and "trace_path" in provenance:
            trace_path = Path(provenance["trace_path"])
            protected_paths.append(trace_path if trace_path.is_absolute() else args.input.resolve().parent / trace_path)
        for protected_path in protected_paths:
            validate_paths(protected_path, args.references, args.output, args.database)
        artifact_verification = None
        if args.verify_trace:
            if not args.corpus_db:
                raise RagasInputError("--verify-trace requires --corpus-db")
            from fondontology.evaluation.artifact_audit import audit_artifact
            artifact_verification = audit_artifact(args.input, args.corpus_db)
        elif args.corpus_db:
            raise RagasInputError("--corpus-db requires --verify-trace")
        review = {}
        if args.references:
            rows, review = merge_references(rows, args.references)
        if args.execute and len(rows) > args.max_rows:
            raise RagasInputError("input exceeds execution sample limit")
        judge_config = resolve_judge_config(
            reuse_project_model=args.reuse_project_model, judge_model=args.judge_model,
            judge_thinking=args.judge_thinking, judge_thinking_param=args.judge_thinking_param)
        payload = evaluate(
            provenance, rows, execute=args.execute, timeout=args.timeout,
            metrics=tuple(args.metrics.split(",")), max_tokens=args.max_tokens,
            max_calls=args.max_judge_calls, max_rows=args.max_rows,
            reference_review=review,
            judge_config=judge_config,
        )
        if artifact_verification:
            payload["execution"]["artifact_verification"] = {
                key: value for key, value in artifact_verification.items() if key != "rows"
            }
        save_results(args.output, payload)
        if args.database:
            save_results(args.database, payload)
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True, allow_nan=False))
        if not args.execute:
            return 0
        return 0 if all(item["status"] == "ok" for item in payload["results"]) else 1
    except (RagasInputError, OSError, ValueError) as exc:
        print(f"ragas evaluation unavailable: {type(exc).__name__}; details withheld", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
