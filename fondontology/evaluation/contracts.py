"""Strict, standard-library validation of the deliberately small v1 contract."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
ANSWER_STATUSES = {"answered", "empty", "clarification", "insufficient", "refused", "invalid"}
INTENT_STATUSES = {"RESOLVED", "AMBIGUOUS", "UNRESOLVED", "INVALID"}
MATCHERS = {"status", "intent_status", "entity_set", "slots", "evidence_groups"}


class ContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def object_fields(value: Any, required: set[str], optional: set[str], where: str) -> None:
    if not isinstance(value, dict):
        raise ContractError(f"{where}: expected object")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise ContractError(f"{where}: missing={sorted(missing)}, unknown={sorted(unknown)}")


def text(value: Any, where: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{where}: expected nonblank string")


def identifier(value: Any, where: str) -> None:
    text(value, where)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
        raise ContractError(f"{where}: invalid identifier")


def json_value(value: Any, where: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ContractError(f"{where}: nonfinite number")
        return
    if isinstance(value, list):
        for item in value:
            json_value(item, where)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            json_value(item, where)
        return
    raise ContractError(f"{where}: not a JSON value")


def unique_strings(value: Any, where: str, *, nonempty: bool = False) -> None:
    if not isinstance(value, list) or (nonempty and not value):
        raise ContractError(f"{where}: expected {'nonempty ' if nonempty else ''}array")
    for item in value:
        text(item, where)
    if len(set(value)) != len(value):
        raise ContractError(f"{where}: duplicate values")


def evidence_ref(value: Any, where: str) -> None:
    object_fields(value, {"source_version", "locator"}, set(), where)
    text(value["source_version"], where)
    text(value["locator"], where)


def validate_slots(value: Any, where: str) -> None:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{where}: expected nonempty array")
    paths = set()
    for slot in value:
        object_fields(slot, {"path", "value", "type"}, set(), where)
        if not isinstance(slot["path"], list) or not slot["path"]:
            raise ContractError(f"{where}: path must be a nonempty array")
        for component in slot["path"]:
            if isinstance(component, bool) or not isinstance(component, (str, int)):
                raise ContractError(f"{where}: invalid path component")
            if isinstance(component, str):
                text(component, where)
            elif component < 0:
                raise ContractError(f"{where}: negative index")
        path = canonical_json(slot["path"])
        if path in paths:
            raise ContractError(f"{where}: duplicate slot path")
        paths.add(path)
        expected = slot["value"]
        kind = slot["type"]
        if not isinstance(kind, str) or kind not in {"string", "number", "boolean", "date", "json", "ordered_ids"}:
            raise ContractError(f"{where}: unknown slot type")
        json_value(expected, where)
        if kind in {"string", "date"}:
            text(expected, where)
        if kind == "date":
            try:
                if date.fromisoformat(expected).isoformat() != expected:
                    raise ValueError()
            except ValueError as exc:
                raise ContractError(f"{where}: expected ISO YYYY-MM-DD") from exc
        if kind == "number" and (isinstance(expected, bool) or not isinstance(expected, (int, float))):
            raise ContractError(f"{where}: expected number")
        if kind == "boolean" and not isinstance(expected, bool):
            raise ContractError(f"{where}: expected boolean")
        if kind == "ordered_ids":
            unique_strings(expected, where)


def validate_case(case: Any) -> dict:
    required = {"schema_version", "case_id", "suite", "split", "task_family", "scenario_group",
                "provenance", "eligible", "kind", "inputs", "oracle"}
    object_fields(case, required, set(), "case")
    if case["schema_version"] != SCHEMA_VERSION:
        raise ContractError("case: unsupported schema_version")
    for field in ("case_id", "suite", "scenario_group"):
        identifier(case[field], field)
    for field in ("split", "task_family"):
        text(case[field], field)
    if type(case["eligible"]) is not bool:
        raise ContractError("case.eligible: expected boolean")
    if not isinstance(case["kind"], str) or case["kind"] not in {"answer", "intent"}:
        raise ContractError("case.kind: unsupported")
    provenance = case["provenance"]
    object_fields(provenance, {"independence", "source", "annotator", "review_status"}, set(), "provenance")
    if provenance["independence"] not in ("synthetic_contract", "independently_reviewed"):
        raise ContractError("provenance.independence: unsupported")
    for field in ("source", "annotator", "review_status"):
        text(provenance[field], f"provenance.{field}")
    inputs = case["inputs"]
    object_fields(inputs, {"question", "dataset_snapshot", "allowed_capabilities"}, {"as_of"}, "inputs")
    for field in ("question", "dataset_snapshot"):
        text(inputs[field], f"inputs.{field}")
    unique_strings(inputs["allowed_capabilities"], "inputs.allowed_capabilities", nonempty=True)
    if "as_of" in inputs:
        validate_slots([{"path": ["as_of"], "type": "date", "value": inputs["as_of"]}], "inputs")
    oracle = case["oracle"]
    object_fields(oracle, {"matchers"}, set(), "oracle")
    matchers = oracle["matchers"]
    if not isinstance(matchers, list) or not matchers:
        raise ContractError("oracle.matchers: expected nonempty array")
    names = set()
    expected_status = None
    for matcher in matchers:
        object_fields(matcher, {"matcher", "expected"}, set(), "matcher")
        name = matcher["matcher"]
        if not isinstance(name, str) or name not in MATCHERS or name in names:
            raise ContractError(f"matcher: unknown or duplicate matcher {name!r}")
        names.add(name)
        expected = matcher["expected"]
        if name == "status":
            if not isinstance(expected, str) or expected not in ANSWER_STATUSES | {"intent_only"}:
                raise ContractError("status: unsupported")
            expected_status = expected
        elif name == "intent_status":
            if not isinstance(expected, str) or expected not in INTENT_STATUSES:
                raise ContractError("intent_status: unsupported")
        elif name == "entity_set":
            unique_strings(expected, "entity_set")
        elif name == "slots":
            validate_slots(expected, "slots")
        else:
            if not isinstance(expected, list) or not expected:
                raise ContractError("evidence_groups: expected nonempty alternatives")
            for group in expected:
                if not isinstance(group, list) or not group:
                    raise ContractError("evidence_groups: empty evidence group")
                for reference in group:
                    evidence_ref(reference, "evidence_groups")
                if len({canonical_json(reference) for reference in group}) != len(group):
                    raise ContractError("evidence_groups: duplicate reference")
    if "status" not in names:
        raise ContractError("oracle: status is mandatory")
    if case["kind"] == "intent":
        if expected_status != "intent_only" or "intent_status" not in names:
            raise ContractError("intent oracle: requires intent_only and intent_status")
        if names & {"entity_set", "evidence_groups"}:
            raise ContractError("intent oracle: business results/evidence unsupported")
        resolved = next(m["expected"] for m in matchers if m["matcher"] == "intent_status") == "RESOLVED"
        if resolved and "slots" not in names:
            raise ContractError("resolved intent oracle: structured slots required")
    else:
        if expected_status == "intent_only" or "intent_status" in names:
            raise ContractError("answer oracle: intent-only assertions unsupported")
        if expected_status == "answered" and (
            "evidence_groups" not in names or not names & {"entity_set", "slots"}
        ):
            raise ContractError("answered oracle: result and evidence required")
        if expected_status == "empty" and not any(
            m["matcher"] == "entity_set" and m["expected"] == [] for m in matchers
        ):
            raise ContractError("empty oracle: explicit empty entity set required")
    return case


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ContractError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ContractError(f"nonfinite JSON constant {value}")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"{path}: {exc}") from exc


@dataclass(frozen=True)
class Suite:
    manifest: dict
    cases: tuple[dict, ...]
    case_set_hash: str
    manifest_hash: str


def load_suite(manifest_path: Path) -> Suite:
    manifest_path = Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    object_fields(manifest, {"schema_version", "suite", "case_files", "dataset_snapshot",
                             "corpus", "ontology", "description", "scope", "allowed_modes"},
                  {"allow_external_case_files"}, "manifest")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ContractError("manifest: unsupported schema_version")
    identifier(manifest["suite"], "manifest.suite")
    for field in ("dataset_snapshot", "corpus", "ontology", "description"):
        text(manifest[field], f"manifest.{field}")
    unique_strings(manifest["case_files"], "manifest.case_files", nonempty=True)
    allow_external = manifest.get("allow_external_case_files", False)
    if type(allow_external) is not bool:
        raise ContractError("manifest.allow_external_case_files: expected boolean")
    if manifest["scope"] not in ("synthetic_contract", "intent_only"):
        raise ContractError("manifest.scope: unsupported")
    unique_strings(manifest["allowed_modes"], "manifest.allowed_modes", nonempty=True)
    if any(mode not in {"replay", "rules_intent"} for mode in manifest["allowed_modes"]):
        raise ContractError("manifest.allowed_modes: unsupported")
    if manifest["scope"] == "synthetic_contract" and "rules_intent" in manifest["allowed_modes"]:
        raise ContractError("manifest: synthetic answer/scorer scope cannot allow rules_intent")
    cases = []
    seen = set()
    for relative in manifest["case_files"]:
        relative_path = Path(relative)
        if relative_path.anchor:
            raise ContractError("manifest.case_files: absolute or drive-rooted paths prohibited")
        try:
            path = (manifest_path.parent / relative_path).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ContractError(f"manifest.case_files: cannot resolve {relative!r}") from exc
        if not allow_external and not path.is_relative_to(manifest_path.parent):
            raise ContractError(
                "manifest.case_files: resolved path escapes manifest directory; "
                "external files require allow_external_case_files=true"
            )
        if path.suffix == ".json":
            batch = read_json(path)
            if not isinstance(batch, list):
                raise ContractError(f"{path}: cases must be an array")
        elif path.suffix == ".jsonl":
            batch = []
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    raise ContractError(f"{path}:{number}: blank JSONL line")
                try:
                    item = json.loads(line, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
                except json.JSONDecodeError as exc:
                    raise ContractError(f"{path}:{number}: invalid JSON") from exc
                batch.append(item)
        else:
            raise ContractError("manifest.case_files: only JSON/JSONL supported")
        if not batch:
            raise ContractError(f"{path}: empty case file")
        for case in batch:
            validate_case(case)
            if case["suite"] != manifest["suite"]:
                raise ContractError("case suite differs from manifest")
            if case["inputs"]["dataset_snapshot"] != manifest["dataset_snapshot"]:
                raise ContractError("case dataset_snapshot differs from manifest")
            if manifest["scope"] == "intent_only" and case["kind"] != "intent":
                raise ContractError("intent_only manifest cannot contain answer cases")
            if case["case_id"] in seen:
                raise ContractError(f"duplicate case_id: {case['case_id']}")
            seen.add(case["case_id"])
            cases.append(case)
    if not any(case["eligible"] for case in cases):
        raise ContractError("suite: no eligible cases")
    return Suite(manifest, tuple(cases), content_hash(cases), content_hash(manifest))
