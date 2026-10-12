"""Offline adapters. Intent executes in a killable subprocess, without oracle."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .contracts import ContractError, canonical_json, object_fields, read_json


class ReplayAdapter:
    def __init__(self, actuals_path: Path, cases: tuple[dict, ...]):
        actuals = read_json(Path(actuals_path))
        if not isinstance(actuals, dict):
            raise ContractError("replay actuals: expected case_id -> actual object")
        expected_ids = {case["case_id"] for case in cases}
        if actuals.keys() != expected_ids:
            raise ContractError("replay actuals IDs must exactly match all manifest case IDs")
        self.actuals = actuals
        self.case_ids = {canonical_json(case["inputs"]): case["case_id"] for case in cases}
        if len(self.case_ids) != len(cases):
            raise ContractError("replay input collision: cases must have distinct inputs")

    def __call__(self, inputs: dict) -> dict:
        return self.actuals[self.case_ids[canonical_json(inputs)]]


class RulesIntentAdapter:
    def __init__(self, source: Path, abox: Path | None, *, timeout_seconds: float):
        self.source = Path(source).resolve()
        self.abox = Path(abox).resolve() if abox else None
        self.timeout_seconds = timeout_seconds

    def __call__(self, inputs: dict) -> dict:
        object_fields(inputs, {"question", "dataset_snapshot", "allowed_capabilities"}, set(), "rules inputs")
        if inputs["allowed_capabilities"] != ["intent"]:
            raise ContractError("rules_intent supports only allowed_capabilities=['intent']; no as_of/multiturn")
        command = [sys.executable, "-m", "fondontology.evaluation.adapters", str(self.source)]
        if self.abox:
            command.append(str(self.abox))
        try:
            completed = subprocess.run(
                command, input=canonical_json({"question": inputs["question"]}), text=True,
                encoding="utf-8", capture_output=True, timeout=self.timeout_seconds,
                cwd=Path(__file__).resolve().parents[2],
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"rules_intent child exceeded {self.timeout_seconds}s; terminated") from exc
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or f"worker exit {completed.returncode}")
        return json.loads(completed.stdout)


def _worker() -> None:
    from fondontology.qa.graph import build_stack
    from fondontology.qa.index import OntologyIndex
    from fondontology.qa.intent import build_intent

    inputs = json.loads(sys.stdin.read())
    object_fields(inputs, {"question"}, set(), "worker inputs")
    stack = build_stack(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    result = build_intent(inputs["question"], OntologyIndex(stack), use_llm=False)
    if result.used_llm:
        raise RuntimeError("offline rules contract violated: used_llm=True")
    actual = {
        "status": "intent_only", "intent_status": result.status,
        "slots": {"operation": result.operation, "intent": result.intent}, "used_llm": False,
    }
    print(canonical_json(actual))


if __name__ == "__main__":
    _worker()
