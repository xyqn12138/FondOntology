"""External gold runner: replay or real offline intent, never online E2E."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.evaluation import ContractError, load_suite, run_suite, save_run
from fondontology.evaluation.adapters import ReplayAdapter, RulesIntentAdapter
from fondontology.evaluation.contracts import canonical_json


def code_identity() -> str:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
    ).decode("utf-8").split("\0")
    digest = hashlib.sha256()
    for relative in sorted(set(paths) - {""}):
        path = ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"<missing>")
        digest.update(b"\0")
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    return f"commit={commit};dirty={bool(dirty)};workspace_sha256={digest.hexdigest()}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("replay", "rules_intent"), required=True)
    parser.add_argument("--actuals", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--abox", type=Path)
    parser.add_argument("--database", type=Path, default=ROOT / "artifacts/evaluation/evaluation.sqlite")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args(argv)
    try:
        suite = load_suite(args.manifest)
        config = {"use_llm": False, "online_execution": False, "business_e2e": False}
        ontology = suite.manifest["ontology"]
        if args.mode == "replay":
            if args.actuals is None or args.source is not None or args.abox is not None:
                raise ContractError("replay requires --actuals and forbids --source/--abox")
            adapter = ReplayAdapter(args.actuals, suite.cases)
            config.update({"actuals_sha256": hashlib.sha256(args.actuals.read_bytes()).hexdigest(),
                           "execution": "recorded actuals; no system execution"})
        else:
            if args.source is None or args.actuals is not None:
                raise ContractError("rules_intent requires --source and forbids --actuals")
            from fondontology.qa.graph import build_stack
            snapshot = build_stack(args.source, args.abox).snapshot
            ontology = f"declared={ontology};graph_sha256={snapshot.ontology_hash}"
            config.update({"source": str(args.source.resolve()), "abox": snapshot.abox_file,
                           "abox_sha256": snapshot.abox_hash, "execution": "build_intent(use_llm=False)"})
            adapter = RulesIntentAdapter(args.source, args.abox, timeout_seconds=args.timeout)
        metadata = {
            "corpus": f"declared={suite.manifest['corpus']};snapshot={suite.manifest['dataset_snapshot']}",
            "ontology": ontology, "code": code_identity(), "model": "none", "prompt": "none",
            "execution_config": config,
        }
        run = run_suite(suite, adapter, mode=args.mode, metadata=metadata, timeout_seconds=args.timeout,
                        max_cases=args.max_cases, stop_on_error=args.stop_on_error)
        save_run(args.database, run)
        print(canonical_json({"summary": run.summary(), "results": [asdict(result) for result in run.results]}))
        return 0 if run.summary()["passed"] == run.eligible_count else 1
    except (ContractError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"evaluation unavailable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
