"""Offline, fail-closed evaluation contracts; gold remains in JSON/JSONL."""

from .contracts import ContractError, Suite, load_suite, validate_case
from .matchers import evaluate_case
from .runner import CaseResult, RunResult, SkipCase, run_suite, save_run

__all__ = [
    "ContractError", "Suite", "load_suite", "validate_case", "evaluate_case",
    "CaseResult", "RunResult", "SkipCase", "run_suite", "save_run",
]
