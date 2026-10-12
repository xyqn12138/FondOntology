"""Fixed-denominator accounting and an append-only-by-run result store."""
from __future__ import annotations

import copy
import math
import sqlite3
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .contracts import ContractError, Suite, canonical_json, content_hash, json_value, object_fields, text, validate_case
from .matchers import evaluate_case

OUTCOMES = {"pass", "fail", "error", "timeout", "skip", "not_run"}
MODES = {"replay", "rules_intent"}


class SkipCase(Exception):
    pass


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    case_hash: str
    eligible: bool
    outcome: str
    elapsed_seconds: float
    assertions: list
    actual: object
    error: str


@dataclass(frozen=True)
class RunResult:
    run_id: str
    started_at: str
    mode: str
    metadata: dict
    manifest_hash: str
    case_set_hash: str
    eligible_count: int
    results: tuple[CaseResult, ...]

    def summary(self) -> dict:
        counts = Counter(result.outcome for result in self.results if result.eligible)
        passed = counts["pass"]
        return {
            "run_id": self.run_id, "mode": self.mode, "eligible_count": self.eligible_count,
            "outcomes": {outcome: counts[outcome] for outcome in sorted(OUTCOMES)},
            "passed": passed, "success_rate": passed / self.eligible_count, "business_e2e": False,
            "scope": self.metadata["execution_config"]["scope"],
            "execution_origin": "recorded_unverified" if self.mode == "replay" else "offline_rules",
        }


def run_suite(
    suite: Suite, adapter: Callable[[dict], dict], *, mode: str, metadata: dict,
    timeout_seconds: float = 30.0, max_cases: int | None = None, stop_on_error: bool = False,
) -> RunResult:
    if mode not in MODES:
        raise ContractError("unsupported execution mode")
    if mode not in suite.manifest["allowed_modes"]:
        raise ContractError("mode not allowed by manifest")
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ContractError("timeout_seconds must be positive and finite")
    if max_cases is not None and (type(max_cases) is not int or max_cases < 0):
        raise ContractError("max_cases must be a nonnegative integer")
    object_fields(metadata, {"corpus", "ontology", "code", "model", "prompt", "execution_config"}, set(), "metadata")
    for field in ("corpus", "ontology", "code", "model", "prompt"):
        text(metadata[field], f"metadata.{field}")
    if not isinstance(metadata["execution_config"], dict):
        raise ContractError("metadata.execution_config: expected object")
    json_value(metadata, "metadata")
    if mode == "rules_intent" and (metadata["model"] != "none" or metadata["prompt"] != "none"):
        raise ContractError("rules_intent cannot claim model/prompt execution")
    frozen = copy.deepcopy(suite.cases)
    for case in frozen:
        validate_case(case)
    if not frozen or len({case["case_id"] for case in frozen}) != len(frozen):
        raise ContractError("empty or duplicate suite")
    eligible_count = sum(case["eligible"] for case in frozen)
    if not eligible_count:
        raise ContractError("suite: no eligible cases")
    if content_hash(list(frozen)) != suite.case_set_hash or content_hash(suite.manifest) != suite.manifest_hash:
        raise ContractError("suite mutated after validation")
    started_at = datetime.now(timezone.utc).isoformat()
    results = []
    attempted = 0
    stopped = False
    for case in frozen:
        actual = None
        assertions = []
        error = ""
        elapsed = 0.0
        if not case["eligible"]:
            outcome, error = "skip", "Declared ineligible before execution."
        elif stopped or (max_cases is not None and attempted >= max_cases):
            outcome, error = "not_run", "Execution stopped or max_cases reached."
        else:
            attempted += 1
            start = time.monotonic()
            try:
                if mode == "rules_intent" and case["kind"] != "intent":
                    raise ContractError("rules_intent does not execute answer cases")
                actual = adapter(copy.deepcopy(case["inputs"]))
                json_value(actual, "adapter output")
                if mode == "rules_intent" and (
                    not isinstance(actual, dict) or actual.get("used_llm") is not False
                ):
                    raise ContractError("rules_intent actual must explicitly report used_llm=False")
                elapsed = time.monotonic() - start
                if elapsed > timeout_seconds:
                    outcome, error = "timeout", "Adapter exceeded elapsed budget."
                else:
                    assertions = evaluate_case(case, actual)
                    outcome = "pass" if all(item["passed"] for item in assertions) else "fail"
            except TimeoutError as exc:
                outcome, error = "timeout", str(exc) or "Timeout"
            except SkipCase as exc:
                outcome, error = "skip", str(exc) or "Adapter declared unavailable."
            except Exception as exc:
                outcome, error = "error", f"{type(exc).__name__}: {exc}"
                actual = None
            elapsed = time.monotonic() - start
            if stop_on_error and outcome in {"error", "timeout"}:
                stopped = True
        results.append(CaseResult(case["case_id"], content_hash(case), case["eligible"], outcome,
                                  elapsed, assertions, actual, error))
    locked_metadata = copy.deepcopy(metadata)
    locked_metadata["execution_config"].update({
        "timeout_seconds": timeout_seconds, "max_cases": max_cases, "stop_on_error": stop_on_error,
        "timeout_enforcement": "hard deadline not enforced; elapsed check only",
        "scope": suite.manifest["scope"],
    })
    return RunResult(uuid.uuid4().hex, started_at, mode, locked_metadata, suite.manifest_hash,
                     suite.case_set_hash, eligible_count, tuple(results))


def save_run(database: Path, run: RunResult) -> None:
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                run_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                started_at TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('replay', 'rules_intent')),
                manifest_hash TEXT NOT NULL,
                case_set_hash TEXT NOT NULL,
                eligible_count INTEGER NOT NULL CHECK(eligible_count > 0),
                metadata_json TEXT NOT NULL,
                summary_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS case_results (
                run_id TEXT NOT NULL REFERENCES eval_runs(run_id),
                case_id TEXT NOT NULL,
                case_hash TEXT NOT NULL,
                eligible INTEGER NOT NULL CHECK(eligible IN (0, 1)),
                outcome TEXT NOT NULL CHECK(outcome IN ('pass','fail','error','timeout','skip','not_run')),
                elapsed_seconds REAL NOT NULL,
                assertions_json TEXT NOT NULL,
                actual_json TEXT,
                error TEXT NOT NULL,
                PRIMARY KEY(run_id, case_id)
            );
        """)
        connection.execute(
            "INSERT INTO eval_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run.run_id, "1.0", run.started_at, run.mode, run.manifest_hash, run.case_set_hash,
             run.eligible_count, canonical_json(run.metadata), canonical_json(run.summary())),
        )
        for result in run.results:
            connection.execute(
                "INSERT INTO case_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run.run_id, result.case_id, result.case_hash, int(result.eligible), result.outcome,
                 result.elapsed_seconds, canonical_json(result.assertions),
                 canonical_json(result.actual) if result.actual is not None else None, result.error),
            )
        connection.commit()
    finally:
        connection.close()
