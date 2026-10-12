# -*- coding: utf-8 -*-
"""QA benchmark 跑批工具（M1 verify / M2 find 阶段）。

用法：
    .venv\\Scripts\\python.exe tools\\qa_bench.py --stage verify
    .venv\\Scripts\\python.exe tools\\qa_bench.py --stage find
    .venv\\Scripts\\python.exe tools\\qa_bench.py --stage find --cqs artifacts/qa/benchmarks/find.json

输出：通过率 + 失败明细。全部通过 exit=0。
"""
from __future__ import annotations

import argparse
from functools import wraps
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.ontology_loader import load_ontology_graph
from fondontology.qa.abox_query import execute_find
from fondontology.qa.context import SliceBudget
from fondontology.qa.engine import answer
from fondontology.qa.evidence import evidence_completeness, validate_citations
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.intent import build_intent
from fondontology.qa.query_planner import plan_find
from fondontology.qa.verify import verify

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
DEFAULT_ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
DEFAULT_CQS = {
    "verify": ROOT / "artifacts" / "qa" / "benchmarks" / "verify.json",
    "find": ROOT / "artifacts" / "qa" / "benchmarks" / "find.json",
    "e2e": ROOT / "artifacts" / "qa" / "benchmarks" / "e2e.json",
    "intent": ROOT / "artifacts" / "qa" / "benchmarks" / "intent.json",
    "intent-real": ROOT / "artifacts" / "qa" / "benchmarks" / "intent_real.json",
    "citation": ROOT / "artifacts" / "qa" / "benchmarks" / "citation.json",
    "explain": ROOT / "artifacts" / "qa" / "benchmarks" / "explain.json",
    "explain-real": ROOT / "artifacts" / "qa" / "benchmarks" / "explain_real.json",
}
QUERY_PLAN_SCHEMA = ROOT / "artifacts" / "qa" / "query_plan.schema.json"

INTENT_SLOTS = {
    "status", "operation", "target", "relation", "lexicon_filters", "source",
    "related_class", "related", "traversals", "exclusions", "relation_path",
    "filters", "date_ranges", "latest", "aggregation", "ordering", "limit", "select",
    "subject", "object",
}
EXPECTED_FIELDS = {
    "find": {"count", "entities"},
    "e2e": {"status", "count", "verdict"},
    "intent": INTENT_SLOTS,
    "citation": {"status", "verdict"},
    "explain": {"status", "kind", "contains", "contains_any", "not_contains",
                "not_contains_head"},
}


def _benchmark_guard(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            print(f"[ERROR] {function.__name__}: {type(error).__name__}: {error}")
            return 1
    return guarded


def _strict_equal(actual, expected) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _strict_equal(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_equal(actual_value, expected_value)
            for actual_value, expected_value in zip(actual, expected))
    return actual == expected


def _validate_expected(case_id: str, stage: str, expected: dict) -> None:
    string_fields = {
        "status", "operation", "target", "relation", "related_class", "select",
        "verdict", "kind", "not_contains_head", "subject", "object",
    }
    list_fields = {
        "traversals", "filters", "date_ranges",
        "ordering",
    }
    for field, value in expected.items():
        if field in string_fields and (
                not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{case_id}: expected.{field} must be a nonempty string")
        if field in list_fields and (
                not isinstance(value, list) or any(
                    not isinstance(item, dict) for item in value)):
            raise ValueError(f"{case_id}: expected.{field} must be an object list")
        if field in {"exclusions", "relation_path"} and (
                not isinstance(value, list) or any(
                    not isinstance(item, (str, dict)) or not item for item in value)):
            raise ValueError(f"{case_id}: expected.{field} must be an ID/object list")
        if field == "related" and not isinstance(value, (str, dict)):
            raise ValueError(f"{case_id}: expected.related must be an entity ID or object")
        if field == "aggregation" and not isinstance(value, dict):
            raise ValueError(f"{case_id}: expected.{field} must be an object")
        if field in {"count", "limit", "lexicon_filters"} and (
                type(value) is not int or value < 0):
            raise ValueError(f"{case_id}: expected.{field} must be a nonnegative integer")
        if field == "source" and not (
                type(value) is bool or isinstance(value, dict) or
                isinstance(value, str) and bool(value.strip())):
            raise ValueError(f"{case_id}: expected.source must be a boolean, entity ID or object")
        if field == "latest" and not isinstance(value, (bool, dict, list)):
            raise ValueError(f"{case_id}: expected.latest must be a boolean, object or object list")
        if field == "latest" and isinstance(value, list) and any(
                not isinstance(item, dict) for item in value):
            raise ValueError(f"{case_id}: expected.latest must contain objects")
        if field in {"contains", "contains_any", "not_contains", "entities"} and (
                not isinstance(value, list) or any(
                    not isinstance(item, str) or not item.strip() for item in value)):
            raise ValueError(f"{case_id}: expected.{field} must be a nonempty-string list")
    statuses = {
        "intent": {"RESOLVED", "AMBIGUOUS", "UNRESOLVED", "INVALID"},
        "e2e": {"ok", "invalid", "unresolved", "ambiguous"},
        "citation": {"ok", "invalid", "unresolved", "ambiguous"},
        "explain": {"ok", "invalid", "unresolved", "ambiguous"},
    }
    if stage in statuses and expected["status"] not in statuses[stage]:
        raise ValueError(f"{case_id}: unsupported expected.status")
    if "verdict" in expected and expected["verdict"] not in {
            "ENTAILED", "CONTRADICTED", "UNKNOWN", "INVALID_REQUEST"}:
        raise ValueError(f"{case_id}: unsupported expected.verdict")


def _load_cases(cqs_path: Path, stage: str, acceptance: bool = False) -> list[dict]:
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("case file must be an object with a cases list")
    cases = data["cases"]
    if not cases:
        raise ValueError("empty case set is not a successful benchmark")
    if acceptance and stage in {"e2e", "citation", "explain"}:
        raise ValueError(
            f"{stage}: business acceptance unavailable: manual Intent integration "
            "or keyword/citation projections lack a structured business oracle")
    seen_ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case id must be a nonempty string")
        if case_id.strip() in seen_ids:
            raise ValueError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id.strip())
        required = {
            "verify": ("subject", "relation", "object"),
            "find": ("target",), "e2e": ("intent",),
            "intent": ("question",), "citation": ("question",), "explain": ("question",),
        }[stage]
        for field in required:
            value = case.get(field)
            if field == "intent":
                valid = isinstance(value, dict) and bool(value)
            else:
                valid = isinstance(value, str) and bool(value.strip())
            if not valid:
                raise ValueError(f"{case_id}: missing or invalid {field}")
        expected = case.get("expected")
        if stage == "verify":
            if expected not in ("ENTAILED", "CONTRADICTED", "UNKNOWN"):
                raise ValueError(f"{case_id}: verify expected must be a supported verdict")
            continue
        if not isinstance(expected, dict) or not expected:
            raise ValueError(f"{case_id}: expected must be a nonempty object")
        unknown = set(expected) - EXPECTED_FIELDS[stage]
        if unknown:
            raise ValueError(f"{case_id}: unknown expected fields: {sorted(unknown)}")
        required_expected = "count" if stage == "find" else "status"
        if required_expected not in expected:
            raise ValueError(f"{case_id}: missing expected.{required_expected}")
        _validate_expected(case_id, stage, expected)
        if "status" in expected and (
                not isinstance(expected["status"], str) or not expected["status"].strip()):
            raise ValueError(f"{case_id}: expected.status must be a nonempty string")
        if "count" in expected and (
                type(expected["count"]) is not int or expected["count"] < 0):
            raise ValueError(f"{case_id}: expected.count must be a nonnegative integer")
        if "entities" in expected:
            entities = expected["entities"]
            if not isinstance(entities, list) or any(
                    not isinstance(entity, str) or not entity.strip() for entity in entities):
                raise ValueError(f"{case_id}: expected.entities must be an entity ID list")
            if len(set(entities)) != len(entities):
                raise ValueError(f"{case_id}: duplicate expected.entities")
            if expected["count"] != len(entities):
                raise ValueError(f"{case_id}: expected count/entities length mismatch")
        for field in ("contains", "contains_any", "not_contains"):
            if field in expected and (
                    not isinstance(expected[field], list) or any(
                        not isinstance(keyword, str) for keyword in expected[field])):
                raise ValueError(f"{case_id}: expected.{field} must be a string list")
        if acceptance and stage == "find" and "entities" not in expected:
            raise ValueError(f"{case_id}: acceptance requires expected.entities; count-only oracle incomplete")
        if acceptance and stage == "intent" and expected["status"] == "RESOLVED":
            contract = case.get("semantic_contract")
            if not isinstance(contract, dict) or contract.get("reviewed") is not True:
                raise ValueError(f"{case_id}: acceptance requires semantic_contract.reviewed=true")
            slots = contract.get("required_slots")
            if not isinstance(slots, list) or not slots or any(
                    not isinstance(slot, str) for slot in slots):
                raise ValueError(f"{case_id}: semantic_contract.required_slots must be a nonempty list")
            if len(set(slots)) != len(slots) or set(slots) - INTENT_SLOTS:
                raise ValueError(f"{case_id}: duplicate or unsupported required_slots")
            base_slots = {"status", "operation"}
            if expected.get("operation") == "find":
                base_slots.add("target")
            elif expected.get("operation") == "verify":
                base_slots.update({"subject", "relation", "object"})
            else:
                raise ValueError(f"{case_id}: acceptance supports find/verify Intent contracts only")
            if not base_slots.issubset(slots):
                raise ValueError(f"{case_id}: required_slots missing base semantic slots {sorted(base_slots)}")
            if expected.get("source") is True or "lexicon_filters" in expected:
                raise ValueError(f"{case_id}: acceptance requires exact source/filters gold, not presence/count")
            for slot in slots:
                if slot not in expected or expected[slot] is None or expected[slot] == "" or (
                        isinstance(expected[slot], (list, dict)) and not expected[slot]):
                    raise ValueError(f"{case_id}: required slot {slot} lacks nonempty gold")
    return cases


def _online_mode(use_llm: bool | None) -> bool:
    if use_llm is False:
        return False
    from fondontology.qa.config import llm_configured
    if not llm_configured():
        raise ValueError("online benchmark unavailable: explicitly requires configured API key, base URL and model")
    return True


def _online_answer_problems(ans) -> list[str]:
    explanation = ans.explanation or {}
    if not explanation.get("used_llm") or explanation.get("gate") == "template_fallback":
        return ["online case did not complete with an explicitly recorded LLM result (fallback/unavailable)"]
    if getattr(ans, "schema_trace", {}).get("fallback"):
        return ["online Intent fell back to deterministic parsing"]
    return []


def _score_cases(cases: list[dict], evaluate) -> tuple[int, list[str]]:
    passed = 0
    failures = []
    for case in cases:
        try:
            details = evaluate(case)
            if details:
                failures.append(f"[FAIL] {case['id']}: " + "; ".join(details))
            else:
                passed += 1
        except Exception as error:
            failures.append(f"[ERROR] {case['id']}: {type(error).__name__}: {error}")
    return passed, failures


def _finish(failures: list[str]) -> int:
    if failures:
        print("---- 失败明细（前 20）----")
        for failure in failures[:20]:
            print(" -", failure)
        return 1
    print("全部已声明断言通过；未标注的业务语义不计为通过。")
    return 0


def _scope(acceptance: bool, description: str) -> None:
    if acceptance:
        print(f"[ACCEPTANCE] {description}; reviewed=true is an explicit label, not proof of independent review.")
    else:
        print(f"[LEGACY] {description}; partial regression only, NOT business acceptance; oracle may be incomplete.")


@_benchmark_guard
def run_verify_benchmark(graph, cqs_path: Path, acceptance: bool = False) -> int:
    cases = _load_cases(cqs_path, "verify", acceptance)
    _scope(acceptance, "T-BOX declared verdict contract")

    def evaluate(case):
        result = verify(graph, case["subject"], case["relation"], case["object"])
        if result.answer != case["expected"]:
            return [
                f"[{case.get('question', '')}] expected={case['expected']} "
                f"actual={result.answer} basis={result.basis or '-'} "
                f"reason={result.reason or result.note or '-'}"]
        return []

    passed, failures = _score_cases(cases, evaluate)
    total = len(cases)
    print(f"verify benchmark: {passed}/{total} 通过（{passed / total:.1%}）")
    return _finish(failures)


def _entity_evidence_problems(entity: str, evidence, target: str) -> list[str]:
    if not isinstance(evidence, dict) or evidence.get("kind") not in ("declared", "inference"):
        return [f"{entity}: missing or invalid entity evidence kind"]
    via = evidence.get("via")
    chain = evidence.get("chain")
    if not isinstance(via, str) or not via or not isinstance(chain, list):
        return [f"{entity}: evidence requires nonempty via and chain list"]
    if evidence["kind"] == "declared":
        return [] if via == target and not chain else [f"{entity}: declared evidence target/chain mismatch"]
    if not chain:
        return [f"{entity}: inference evidence requires a nonempty chain"]
    current = via
    for edge in chain:
        if not isinstance(edge, dict) or any(
                not isinstance(edge.get(field), str) or not edge[field] for field in ("s", "p", "o")):
            return [f"{entity}: malformed inference edge"]
        if edge["s"] != current or edge["p"] != "http://www.w3.org/2000/01/rdf-schema#subClassOf":
            return [f"{entity}: invalid inference chain"]
        current = edge["o"]
    return [] if current == target else [f"{entity}: inference chain does not reach target"]


@_benchmark_guard
def run_find_benchmark(stack, cqs_path: Path, acceptance: bool = False) -> int:
    cases = _load_cases(cqs_path, "find", acceptance)
    count_only = sum("entities" not in case["expected"] for case in cases)
    _scope(acceptance, f"find entity-set contract; count-only projection {count_only}/{len(cases)} (oracle incomplete)")
    evidence_checked = 0

    def evaluate(case):
        nonlocal evidence_checked
        plan = plan_find(
            target=case["target"],
            tbox=stack.tbox,
            abox=stack.abox,
            filters=case.get("filters"),
            exclusions=case.get("exclusions"),
            traversals=case.get("traversals"),
            limit=case.get("limit"),
        )
        result = execute_find(stack, plan)
        details = []
        if result.errors:
            details.append(f"execution errors={result.errors}")
        if not _strict_equal(result.count, case["expected"]["count"]):
            details.append(f"count expected={case['expected']['count']} actual={result.count}")
        entities = result.entities
        if not isinstance(entities, list) or any(
                not isinstance(entity, str) or not entity.strip() for entity in entities):
            return details + ["actual entities must be an entity ID list"]
        if result.count != len(entities):
            details.append(f"actual count/entities length mismatch: {result.count}/{len(entities)}")
        if len(set(entities)) != len(entities):
            details.append("duplicate actual entities")
        if "entities" in case["expected"] and set(entities) != set(case["expected"]["entities"]):
            details.append(f"entities expected={case['expected']['entities']} actual={entities}")
        if not isinstance(result.evidence, dict):
            return details + ["actual evidence must be an object"]
        target = (plan.get("target") or {}).get("concept", "")
        for entity in entities:
            evidence_checked += 1
            details.extend(_entity_evidence_problems(entity, result.evidence.get(entity), target))
        return details

    passed, failures = _score_cases(cases, evaluate)
    total = len(cases)
    print(f"find benchmark: {passed}/{total} 通过（{passed / total:.1%}）；证据断言 {evidence_checked} 条")
    return _finish(failures)


def _report_problems(report) -> list[str]:
    if not isinstance(report, dict) or not isinstance(report.get("claims"), list) or not report["claims"] or (
            not isinstance(report.get("evidence"), list) or not report["evidence"]):
        return ["successful answer requires a nonempty report with claims and evidence"]
    for claim in report["claims"]:
        if not isinstance(claim, dict) or any(
                not isinstance(claim.get(field), str) or not claim[field].strip()
                for field in ("claim_id", "type", "claim")) or (
                    not isinstance(claim.get("evidence"), list) or not claim["evidence"] or any(
                        not isinstance(reference, str) or not reference.strip()
                        for reference in claim["evidence"])):
            return ["malformed report claim/evidence links"]
    claim_keys = [claim["claim_id"] for claim in report["claims"]]
    if len(set(claim_keys)) != len(claim_keys):
        return ["duplicate report claim IDs"]
    for evidence in report["evidence"]:
        if not isinstance(evidence, dict) or not isinstance(evidence.get("id"), str) or not evidence["id"]:
            return ["malformed report evidence ID"]
        kind = evidence.get("kind")
        if kind not in {"declared", "inference", "query", "definition", "document"}:
            return ["malformed report evidence kind"]
        if kind == "query":
            if not evidence.get("source") and not evidence.get("sparql"):
                return ["query evidence lacks source or executed query"]
        elif not isinstance(evidence.get("source"), list) or not evidence["source"]:
            return ["report evidence lacks source"]
        if kind in {"document", "definition"} and (
                not isinstance(evidence.get("text"), str) or not evidence["text"].strip() or
                not isinstance(evidence.get("locator"), dict) or not evidence["locator"]):
            return ["document/definition evidence lacks text or locator"]
    evidence_keys = [evidence["id"] for evidence in report["evidence"]]
    if len(set(evidence_keys)) != len(evidence_keys):
        return ["duplicate report evidence IDs"]
    complete, problems = evidence_completeness(report)
    unknown = validate_citations(report)
    details = [] if complete else [f"证据不完整: {problems}"]
    if unknown:
        details.append(f"引用越权: {unknown}")
    return details


@_benchmark_guard
def run_e2e_benchmark(stack, cqs_path: Path, acceptance: bool = False) -> int:
    """手工 Intent integration 回归，不是用户自然语言 E2E。"""
    cases = _load_cases(cqs_path, "e2e", acceptance)
    _scope(acceptance, "manual Intent integration regression, NOT user NL E2E")
    completeness_checked = 0
    citation_checked = 0

    def evaluate(case):
        nonlocal completeness_checked, citation_checked
        ans = answer(stack, case["intent"], slice_budget=SliceBudget())
        status_ok = ans.status == case["expected"].get("status")
        detail = []
        if not status_ok:
            detail.append(f"status expected={case['expected']['status']} actual={ans.status}")
        if "count" in case["expected"]:
            if case["expected"]["count"] != _int_in_text(ans.text):
                detail.append(f"count expected={case['expected']['count']} text={ans.text!r}")
        if "verdict" in case["expected"] and not _strict_equal(ans.verdict, case["expected"]["verdict"]):
            detail.append(f"verdict expected={case['expected']['verdict']} actual={ans.verdict}")
        if ans.status == "ok":
            completeness_checked += 1
            citation_checked += 1
            detail.extend(_report_problems(ans.report))
        return detail

    passed, failures = _score_cases(cases, evaluate)
    total = len(cases)
    print(f"integration (manual Intent) benchmark: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"证据完整度断言 {completeness_checked} 条，引用校验 {citation_checked} 条")
    return _finish(failures)


def _int_in_text(text: str) -> int | None:
    """从“共找到 N 个…”文本提取 N；非 find 模板返回 None。"""
    import re
    match = re.search(r"共找到 (\d+) 个", text)
    return int(match.group(1)) if match else None


@_benchmark_guard
def run_citation_benchmark(stack, cqs_path: Path, acceptance: bool = False,
                           use_llm: bool = False) -> int:
    """M5：NL → 答案 全链路；UCR/引用/证据断言 +（LLM 配置时）gate 分布。"""
    from fondontology.qa.config import llm_configured
    from fondontology.qa.engine import answer_question
    from fondontology.qa.evidence import evidence_completeness, validate_citations

    cases = _load_cases(cqs_path, "citation", acceptance)
    use_llm = _online_mode(use_llm)
    _scope(acceptance, "citation whitelist and claim-link projection; not factual support accuracy")
    gates: dict[str, int] = {}
    max_ucr = 0.0

    def evaluate(case):
        nonlocal max_ucr
        ans = answer_question(case["question"], stack, use_llm=use_llm)
        exp = case["expected"]
        status_ok = ans.status == exp.get("status")
        detail = []
        if use_llm:
            detail.extend(_online_answer_problems(ans))
        if not status_ok:
            detail.append(f"status expected={exp['status']} actual={ans.status}")
        if "verdict" in exp and not _strict_equal(ans.verdict, exp["verdict"]):
            detail.append(f"verdict expected={exp['verdict']} actual={ans.verdict}")
        if ans.status == "ok":
            expl = ans.explanation or {}
            gates[expl.get("gate", "?")] = gates.get(expl.get("gate", "?"), 0) + 1
            max_ucr = max(max_ucr, expl.get("ucr", 1.0))
            if expl.get("ucr", 1.0) > 0:
                detail.append(f"UCR={expl.get('ucr')}（必须为 0）")
            detail.extend(_report_problems(ans.report))
        return detail

    passed, failures = _score_cases(cases, evaluate)
    total = len(cases)
    llm_used = sum(count for gate, count in gates.items()
                   if gate.startswith("llm_") or gate == "template_fallback")
    print(f"citation benchmark: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"表达 gate 分布 {gates}；经闸门后最大 UCR={max_ucr}；"
          f"LLM 表达启用 {llm_used} 条" + ("" if llm_configured() else "（未配置 LLM，全部模板）"))
    return _finish(failures)


@_benchmark_guard
def run_intent_benchmark(stack, cqs_path: Path, use_llm: bool | None = False,
                         acceptance: bool = False, require_online: bool = False) -> int:
    """M4：NL → Intent（use_llm=False 走确定性回归；True 走模型路径对照）。"""
    cases = _load_cases(cqs_path, "intent", acceptance)
    if require_online:
        use_llm = _online_mode(use_llm)
    elif use_llm is None:
        from fondontology.qa.config import llm_configured
        use_llm = llm_configured()
    _scope(acceptance, "Intent declared-slot contract only; NOT executed business-answer accuracy")
    index = OntologyIndex(stack)
    resolved = 0
    semantic_ok = 0
    fallback_count = 0
    distributions: dict[str, int] = {}

    def evaluate(case):
        nonlocal resolved, semantic_ok, fallback_count
        result = build_intent(case["question"], index, use_llm=use_llm)
        fallback = bool(use_llm and (
            not result.used_llm or result.schema_trace.get("fallback") or
            any("回退" in note for note in result.notes)))
        fallback_count += fallback
        distributions[result.status] = distributions.get(result.status, 0) + 1
        exp = case["expected"]
        details = []
        for slot, expected_value in exp.items():
            if slot == "status":
                actual_value = result.status
            elif slot == "operation":
                actual_value = result.operation
            elif slot == "target":
                actual_value = (result.intent.get("target_class") or "").rstrip("/#").rsplit(
                    "/", 1)[-1].rsplit("#", 1)[-1]
                if expected_value.startswith(("http://", "https://")):
                    actual_value = result.intent.get("target_class")
            elif slot == "lexicon_filters":
                actual_value = len(result.intent.get("filters") or [])
                if actual_value >= expected_value:
                    continue
            elif slot == "source" and type(expected_value) is bool:
                actual_value = bool(result.intent.get("source"))
            else:
                actual_value = result.intent.get(slot)
            if not _strict_equal(actual_value, expected_value):
                details.append(f"{slot} expected={expected_value!r} actual={actual_value!r}")
        if fallback and require_online:
            details.append("online Intent did not complete with an LLM result (fallback/unavailable)")
        if result.status == "RESOLVED" and exp.get("status") == "RESOLVED":
            resolved += 1
            semantic_ok += not details
        return details

    passed, failures = _score_cases(cases, evaluate)
    total = len(cases)
    semantic_acc = (semantic_ok / resolved) if resolved else None
    print(f"intent benchmark: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"resolution 分布 {distributions}")
    if semantic_acc is not None:
        print(f"Declared-slot projection（RESOLVED; not full business success）: "
              f"{semantic_ok}/{resolved} = {semantic_acc:.1%}")
    labeled = sum(case["expected"]["status"] == "RESOLVED" for case in cases)
    print(f"unconditional declared-slot accuracy={semantic_ok / labeled if labeled else 0:.1%}; "
          f"unresolved rate={sum(v for k, v in distributions.items() if k != 'RESOLVED') / total if total else 0:.1%}; "
          f"wrong-resolved rate={(resolved - semantic_ok) / resolved if resolved else 0:.1%}; "
          f"fallback rate={fallback_count / total if total else 0:.1%}")
    return _finish(failures)


def run_intent_llm_spot(stack, cqs_path: Path) -> None:
    """LLM 配置存在时给出对比报告（不作为 pass/fail）。"""
    from fondontology.qa.config import llm_configured
    if not llm_configured():
        return
    index = OntologyIndex(stack)
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    used = checked = matched = 0
    for case in data["cases"]:
        result = build_intent(case["question"], index, use_llm=True)
        if not result.used_llm:
            continue
        used += 1
        exp_target = case["expected"].get("target")
        if exp_target:
            checked += 1
            target_local = (result.intent.get("target_class") or "").rsplit("/", 1)[-1]
            if target_local == exp_target:
                matched += 1
    accuracy = f"{matched}/{checked} = {matched / checked:.1%}" if checked else "无目标类断言"
    print(f"[LLM 路径] 启用 {used} 条；目标类断言 {checked} 条；"
          f"Semantic Accuracy（LLM，对照确定性真值）: {accuracy}")


def run_intent_llm_spot_real(stack, cqs_path: Path) -> None:
    """真实口语问法的 LLM 路径报告（这些问法规则兜底约半数能解，模型承担其余）。"""
    from fondontology.qa.config import llm_configured
    if not llm_configured():
        return
    index = OntologyIndex(stack)
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    used = checked = matched = 0
    for case in data["cases"]:
        result = build_intent(case["question"], index, use_llm=True)
        if not result.used_llm:
            continue
        used += 1
        exp_target = case["expected"].get("target")
        if exp_target:
            checked += 1
            target_local = (result.intent.get("target_class") or "").rsplit("/", 1)[-1]
            if target_local == exp_target:
                matched += 1
    accuracy = f"{matched}/{checked} = {matched / checked:.1%}" if checked else "无目标类断言"
    print(f"[LLM 路径·真实问法] 启用 {used} 条；目标类断言 {checked} 条；"
          f"Semantic Accuracy: {accuracy}")


@_benchmark_guard
def run_explain_benchmark(stack, cqs_path: Path, use_llm: bool | None = False,
                          acceptance: bool = False, require_online: bool = False) -> int:
    """M7-R3c：explain 类问题基准（describe/regulation/code/compare）。

    use_llm=False（explain 档）：规则兜底路径，CI 确定性跑批；
    use_llm=None（explain-real 档）：LLM 主判+表达全链路，需 key。
    断言 kind/status/文本关键词（含防串台 not_contains）+ 证据合同。
    """
    from fondontology.qa.engine import answer_question

    cases = _load_cases(cqs_path, "explain", acceptance)
    if require_online:
        use_llm = _online_mode(use_llm)
    elif use_llm is None:
        from fondontology.qa.config import llm_configured
        use_llm = llm_configured()
    _scope(acceptance, "explain keyword projection and evidence contract; not factual support accuracy")
    failures: list[str] = []
    contract_checked = 0
    gates: dict[str, int] = {}

    def evaluate(case):
        nonlocal contract_checked
        ans = answer_question(case["question"], stack, use_llm=use_llm)
        exp = case["expected"]
        detail = []
        if exp.get("kind") and ans.kind != exp["kind"]:
            detail.append(f"kind expected={exp['kind']} actual={ans.kind}")
        if ans.status != exp.get("status"):
            detail.append(f"status expected={exp.get('status')} actual={ans.status}")
        for kw in exp.get("contains", []):
            if kw not in (ans.text or ""):
                detail.append(f"缺关键词「{kw}」")
        if exp.get("contains_any") and not any(
                kw in (ans.text or "") for kw in exp["contains_any"]):
            detail.append(f"关键词组「{exp['contains_any']}」全部缺失")
        for kw in exp.get("not_contains", []):
            if kw in (ans.text or ""):
                detail.append(f"串台关键词「{kw}」出现")
        if exp.get("not_contains_head"):
            head = (ans.text or "").split("\n")[0]
            if exp["not_contains_head"] in head:
                detail.append(f"首条命中越权条文「{exp['not_contains_head']}」")
        if ans.status == "ok":
            if require_online:
                detail.extend(_online_answer_problems(ans))
            contract_checked += 1
            detail.extend(_report_problems(ans.report))
        if ans.status == "ok":
            gate = (ans.explanation or {}).get("gate", "-")
            gates[gate] = gates.get(gate, 0) + 1
        return detail

    passed, failures = _score_cases(cases, evaluate)
    total = len(cases)
    mode = "规则兜底" if use_llm is False else "LLM 主判"
    print(f"explain benchmark（{mode}）: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"证据合同断言 {contract_checked} 条；gate 分布 {gates or '{}'}")
    return _finish(failures)


@_benchmark_guard
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CNFO QA benchmark 跑批")
    ap.add_argument("--stage", choices=["verify", "find", "e2e", "intent",
                                        "citation", "intent-real", "explain", "explain-real"],
                    default="verify")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--abox", type=Path, default=DEFAULT_ABOX)
    ap.add_argument("--cqs", type=Path, default=None)
    ap.add_argument("--acceptance", action="store_true",
                    help="启用显式业务验收合同；默认仅运行 legacy 回归")
    args = ap.parse_args(argv)
    stage_contract = {
        "intent-real": "intent", "explain-real": "explain",
    }.get(args.stage, args.stage)
    _load_cases(args.cqs or DEFAULT_CQS[args.stage], stage_contract, args.acceptance)
    if args.stage in {"intent-real", "explain-real"}:
        _online_mode(True)

    if args.stage == "verify":
        print(f"加载 T-BOX: {args.source}")
        graph = load_ontology_graph(args.source)
        print(f"三元组: {len(graph)}")
        return run_verify_benchmark(graph, args.cqs or DEFAULT_CQS["verify"], args.acceptance)

    print(f"加载数据栈（T-BOX: {args.source}；ABOX: {args.abox}）")
    stack = build_stack(args.source, args.abox)
    print(f"T-BOX {len(stack.tbox)} / ABOX {len(stack.abox)} 三元组；"
          f"本体版本 {stack.snapshot.ontology_version}")

    if args.stage == "find":
        return run_find_benchmark(stack, args.cqs or DEFAULT_CQS["find"], args.acceptance)
    if args.stage == "intent":
        code = run_intent_benchmark(stack, args.cqs or DEFAULT_CQS["intent"],
                                    use_llm=False, acceptance=args.acceptance)
        return code
    if args.stage == "intent-real":
        code = run_intent_benchmark(stack, args.cqs or DEFAULT_CQS.get("intent-real", args.cqs),
                                    use_llm=True, acceptance=args.acceptance,
                                    require_online=True)
        return code
    if args.stage == "citation":
        return run_citation_benchmark(stack, args.cqs or DEFAULT_CQS["citation"],
                                      acceptance=args.acceptance, use_llm=False)
    if args.stage == "explain":
        return run_explain_benchmark(stack, args.cqs or DEFAULT_CQS["explain"],
                                     use_llm=False, acceptance=args.acceptance)
    if args.stage == "explain-real":
        return run_explain_benchmark(stack,
                                     args.cqs or DEFAULT_CQS["explain-real"],
                                     use_llm=True, acceptance=args.acceptance,
                                     require_online=True)

    # ---- QueryPlan v1.1 schema 落盘 ----
    from fondontology.qa.query_planner import write_plan_schema
    write_plan_schema(QUERY_PLAN_SCHEMA)
    print(f"[P3] Query Plan schema 已生成（版本 1.1）: {QUERY_PLAN_SCHEMA}")
    return run_e2e_benchmark(stack, args.cqs or DEFAULT_CQS["e2e"], args.acceptance)


if __name__ == "__main__":
    raise SystemExit(main())
