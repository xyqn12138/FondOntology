"""Structured comparisons; evidence identity is not semantic entailment."""
from __future__ import annotations

from typing import Any

from .contracts import (
    ANSWER_STATUSES, INTENT_STATUSES, ContractError, canonical_json, evidence_ref,
    json_value, object_fields, unique_strings, validate_case,
)


def typed_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return actual == expected
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            typed_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            typed_equal(actual_item, expected_item) for actual_item, expected_item in zip(actual, expected)
        )
    return actual == expected


def validate_actual(actual: Any) -> None:
    object_fields(actual, {"status"}, {"intent_status", "entities", "slots", "evidence", "used_llm"}, "actual")
    status = actual["status"]
    if not isinstance(status, str) or status not in ANSWER_STATUSES | {"intent_only"}:
        raise ContractError("actual.status: unsupported")
    if "used_llm" in actual and type(actual["used_llm"]) is not bool:
        raise ContractError("actual.used_llm: expected boolean")
    if status == "intent_only":
        if not isinstance(actual.get("intent_status"), str) or actual["intent_status"] not in INTENT_STATUSES:
            raise ContractError("actual.intent_status: missing or unsupported")
        if "entities" in actual or "evidence" in actual:
            raise ContractError("actual: intent_only cannot claim business results/evidence")
    elif "intent_status" in actual:
        raise ContractError("actual: answer status cannot carry intent-only result")
    if status in {"clarification", "insufficient", "refused", "invalid"} and (
        actual.get("entities") or actual.get("slots") or actual.get("evidence")
    ):
        raise ContractError("actual: non-answer status cannot carry answer entities, facts, or evidence")
    if status == "empty" and actual.get("entities") != []:
        raise ContractError("actual: empty status requires explicit entities=[]")
    if status == "empty" and (actual.get("slots") or actual.get("evidence")):
        raise ContractError("actual: empty status cannot carry answer facts or evidence")
    if "entities" in actual:
        unique_strings(actual["entities"], "actual.entities")
    if "slots" in actual:
        if not isinstance(actual["slots"], dict):
            raise ContractError("actual.slots: expected object")
        json_value(actual["slots"], "actual.slots")
    if "evidence" in actual:
        if not isinstance(actual["evidence"], list):
            raise ContractError("actual.evidence: expected array")
        for reference in actual["evidence"]:
            evidence_ref(reference, "actual.evidence")
        if len({canonical_json(reference) for reference in actual["evidence"]}) != len(actual["evidence"]):
            raise ContractError("actual.evidence: duplicate references")


def _lookup(slots: dict, path: list):
    current = slots
    for component in path:
        if isinstance(current, dict) and isinstance(component, str) and component in current:
            current = current[component]
        elif isinstance(current, list) and type(component) is int and component < len(current):
            current = current[component]
        else:
            raise KeyError(canonical_json(path))
    return current


def evaluate_case(case: dict, actual: dict) -> list[dict]:
    validate_case(case)
    try:
        validate_actual(actual)
    except ContractError as exc:
        return [{"matcher": "actual_contract", "passed": False, "detail": str(exc)}]
    assertions = []
    for matcher in case["oracle"]["matchers"]:
        name = matcher["matcher"]
        expected = matcher["expected"]
        detail = ""
        if name in {"status", "intent_status"}:
            passed = actual.get(name) == expected
        elif name == "entity_set":
            passed = "entities" in actual and set(actual["entities"]) == set(expected)
        elif name == "slots":
            failures = []
            for slot in expected:
                try:
                    value = _lookup(actual.get("slots", {}), slot["path"])
                    if not typed_equal(value, slot["value"]):
                        failures.append(f"mismatch at {canonical_json(slot['path'])}")
                except KeyError:
                    failures.append(f"missing {canonical_json(slot['path'])}")
            passed = not failures
            detail = "; ".join(failures)
        else:
            references = {canonical_json(reference) for reference in actual.get("evidence", [])}
            passed = any(
                all(canonical_json(reference) in references for reference in group) for group in expected
            )
            detail = "Locator/version identity only; semantic support is not measured."
        assertions.append({"matcher": name, "passed": passed, "detail": detail})
    return assertions
