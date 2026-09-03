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
    "citation": ROOT / "artifacts" / "qa" / "benchmarks" / "citation.json",
}
QUERY_PLAN_SCHEMA = ROOT / "artifacts" / "qa" / "query_plan.schema.json"


def run_verify_benchmark(graph, cqs_path: Path) -> int:
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    passed = 0
    failures: list[str] = []
    for case in cases:
        result = verify(graph, case["subject"], case["relation"], case["object"])
        ok = result.answer == case["expected"]
        if ok:
            passed += 1
        else:
            failures.append(
                f"{case['id']} [{case.get('question', '')}] expected={case['expected']} "
                f"actual={result.answer} basis={result.basis or '-'} "
                f"reason={result.reason or result.note or '-'}"
            )
    total = len(cases)
    print(f"verify benchmark: {passed}/{total} 通过（{passed / total:.1%}）")
    if failures:
        print("---- 失败明细 ----")
        for line in failures:
            print(" -", line)
        return 1
    print("全部通过（确定性语义，对照 T-BOX 声明）。")
    return 0


def run_find_benchmark(stack, cqs_path: Path) -> int:
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    passed = 0
    failures: list[str] = []
    evidence_checked = 0
    for case in cases:
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
        ok = result.count == case["expected"]["count"] and not result.errors
        if ok:
            passed += 1
            for ent, ev in result.evidence.items():
                evidence_checked += 1
                if ev["kind"] not in ("declared", "inference"):
                    failures.append(f"{case['id']}: 证据类型异常 {ent} -> {ev['kind']}")
        else:
            failures.append(
                f"{case['id']} target={case['target']} expected={case['expected']['count']} "
                f"actual={result.count} errors={result.errors}"
            )
    total = len(cases)
    print(f"find benchmark: {passed}/{total} 通过（{passed / total:.1%}）；证据断言 {evidence_checked} 条")
    if failures:
        print("---- 失败明细 ----")
        for line in failures[:20]:
            print(" -", line)
        return 1
    print("全部通过（显式+推断类型证据区分正常）。")
    return 0


def run_e2e_benchmark(stack, cqs_path: Path) -> int:
    """M3 确定性端到端：状态/计数/判定 + 证据完整度 + 引用校验 + 切片预算。"""
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    passed = 0
    failures: list[str] = []
    completeness_checked = 0
    citation_checked = 0
    for case in cases:
        ans = answer(stack, case["intent"], slice_budget=SliceBudget())
        status_ok = ans.status == case["expected"].get("status")
        detail = []
        if case["expected"].get("count") is not None:
            if case["expected"]["count"] != _int_in_text(ans.text):
                detail.append(f"count expected={case['expected']['count']} text={ans.text!r}")
        if case["expected"].get("verdict") is not None and ans.verdict != case["expected"]["verdict"]:
            detail.append(f"verdict expected={case['expected']['verdict']} actual={ans.verdict}")
        # 证据合同（find/verify ok 时必须完整且引用零越权）
        if status_ok and ans.report:
            ok_c, problems = evidence_completeness(ans.report)
            unknown = validate_citations(ans.report)
            completeness_checked += 1
            citation_checked += 1
            if not ok_c:
                detail.append(f"证据不完整: {problems}")
            if unknown:
                detail.append(f"引用越权: {unknown}")
        if status_ok and not detail:
            passed += 1
        else:
            failures.append(f"{case['id']} intent={case['intent']}: " + ("; ".join(detail) or "状态不符"))
    total = len(cases)
    print(f"e2e (确定性) benchmark: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"证据完整度断言 {completeness_checked} 条，引用校验 {citation_checked} 条")
    if failures:
        print("---- 失败明细（前 20）----")
        for line in failures[:20]:
            print(" -", line)
        return 1
    print("全部通过：状态/计数/判定 OK；Evidence Completeness 100%；引用零越权。")
    return 0


def _int_in_text(text: str) -> int | None:
    """从“共找到 N 个…”文本提取 N；非 find 模板返回 None。"""
    import re
    m = re.search(r"共找到 (\d+) 个", text)
    return int(m.group(1)) if m else None


def run_citation_benchmark(stack, cqs_path: Path) -> int:
    """M5：NL → 答案 全链路；UCR/引用/证据断言 +（LLM 配置时）gate 分布。"""
    from fondontology.qa.config import llm_configured
    from fondontology.qa.engine import answer_question
    from fondontology.qa.evidence import evidence_completeness, validate_citations

    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    passed = 0
    failures: list[str] = []
    gates: dict[str, int] = {}
    max_ucr = 0.0
    for case in cases:
        ans = answer_question(case["question"], stack)
        exp = case["expected"]
        status_ok = ans.status == exp.get("status")
        detail = []
        if exp.get("verdict") is not None and ans.verdict != exp["verdict"]:
            detail.append(f"verdict expected={exp['verdict']} actual={ans.verdict}")
        if ans.status == "ok":
            # 表达层引用闸门
            expl = ans.explanation or {}
            gates[expl.get("gate", "?")] = gates.get(expl.get("gate", "?"), 0) + 1
            max_ucr = max(max_ucr, expl.get("ucr", 1.0))
            if expl.get("ucr", 1.0) > 0:
                detail.append(f"UCR={expl.get('ucr')}（必须为 0）")
            # 证据合同
            ok_c, problems = evidence_completeness(ans.report)
            if not ok_c:
                detail.append(f"证据不完整: {problems}")
            if validate_citations(ans.report):
                detail.append(f"证据引用越权: {validate_citations(ans.report)}")
        if status_ok and not detail:
            passed += 1
        else:
            failures.append(f"{case['id']} [{case['question']}]: " + ("; ".join(detail) or "状态不符"))
    total = len(cases)
    llm_used = sum(v for k, v in gates.items() if k.startswith("llm_") or k == "template_fallback")
    print(f"citation benchmark: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"表达 gate 分布 {gates}；经闸门后最大 UCR={max_ucr}；"
          f"LLM 表达启用 {llm_used} 条" + ("" if llm_configured() else "（未配置 LLM，全部模板）"))
    if failures:
        print("---- 失败明细（前 20）----")
        for line in failures[:20]:
            print(" -", line)
        return 1
    print("全部通过：Unsupported Claim Rate = 0；引用全部 ∈ claims；证据完整度 100%。")
    return 0


def run_intent_benchmark(stack, cqs_path: Path) -> int:
    """M4：NL → Intent。无 key 走确定性路径；有 key 时打印 LLM 路径的 Semantic Accuracy
    （LLM 输出经白名单校验后与确定性真相比对）。"""
    index = OntologyIndex(stack)
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    passed = 0
    resolved = 0
    semantic_ok = 0
    failures: list[str] = []
    distributions: dict[str, int] = {}
    for case in cases:
        result = build_intent(case["question"], index)
        distributions[result.status] = distributions.get(result.status, 0) + 1
        exp = case["expected"]
        status_ok = result.status == exp.get("status")
        op_ok = (not exp.get("operation")) or result.operation == exp.get("operation")
        target_ok = True
        if exp.get("target"):
            intent = result.intent
            target_local = (intent.get("target_class") or "").rsplit("/", 1)[-1]
            target_ok = target_local == exp["target"]
        rel_ok = True
        if exp.get("relation"):
            rel_ok = result.intent.get("relation") == exp["relation"]
        lex_ok = True
        if exp.get("lexicon_filters"):
            lex_ok = len(result.intent.get("filters") or []) >= exp["lexicon_filters"]
        src_ok = True
        if exp.get("source"):
            src_ok = bool(result.intent.get("source"))
        ok = status_ok and op_ok and target_ok and rel_ok and lex_ok and src_ok
        if ok:
            passed += 1
            if result.status == "RESOLVED":
                resolved += 1
                if target_ok:
                    semantic_ok += 1
        else:
            failures.append(
                f"{case['id']} [{case['question']}] expected={exp} "
                f"actual=status={result.status} op={result.operation} "
                f"intent={result.intent} notes={result.notes[:2]}")
    total = len(cases)
    semantic_acc = (semantic_ok / resolved) if resolved else None
    print(f"intent benchmark: {passed}/{total} 通过（{passed / total:.1%}）；"
          f"resolution 分布 {distributions}")
    if semantic_acc is not None:
        print(f"Semantic Accuracy（RESOLVED 目标类命中）: {semantic_ok}/{resolved} = {semantic_acc:.1%}")
    if failures:
        print("---- 失败明细（前 20）----")
        for line in failures[:20]:
            print(" -", line)
        return 1
    print("全部通过（确定性路径；LLM 路径启用后同批跑 Semantic Accuracy）")
    return 0


def run_intent_llm_spot(stack, cqs_path: Path) -> None:
    """LLM 配置存在时给出对比报告（不作为 pass/fail）。"""
    from fondontology.qa.config import llm_configured
    if not llm_configured():
        return
    index = OntologyIndex(stack)
    data = json.loads(cqs_path.read_text(encoding="utf-8"))
    used = matched = 0
    for case in data["cases"]:
        result = build_intent(case["question"], index)
        if not result.used_llm:
            continue
        used += 1
        exp_target = case["expected"].get("target")
        if exp_target:
            target_local = (result.intent.get("target_class") or "").rsplit("/", 1)[-1]
            if target_local == exp_target:
                matched += 1
    print(f"[LLM 路径] 启用 {used} 条；Semantic Accuracy（LLM，对照确定性真值）: "
          f"{matched}/{used} = {matched / used:.1%}" if used else "[LLM 路径] 未配置，跳过")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CNFO QA benchmark 跑批")
    ap.add_argument("--stage", choices=["verify", "find", "e2e", "intent", "citation"],
                    default="verify")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--abox", type=Path, default=DEFAULT_ABOX)
    ap.add_argument("--cqs", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.stage == "verify":
        print(f"加载 T-BOX: {args.source}")
        graph = load_ontology_graph(args.source)
        print(f"三元组: {len(graph)}")
        return run_verify_benchmark(graph, args.cqs or DEFAULT_CQS["verify"])

    print(f"加载数据栈（T-BOX: {args.source}；ABOX: {args.abox}）")
    stack = build_stack(args.source, args.abox)
    print(f"T-BOX {len(stack.tbox)} / ABOX {len(stack.abox)} 三元组；"
          f"本体版本 {stack.snapshot.ontology_version}")

    if args.stage == "find":
        return run_find_benchmark(stack, args.cqs or DEFAULT_CQS["find"])
    if args.stage == "intent":
        code = run_intent_benchmark(stack, args.cqs or DEFAULT_CQS["intent"])
        run_intent_llm_spot(stack, args.cqs or DEFAULT_CQS["intent"])
        return code
    if args.stage == "citation":
        return run_citation_benchmark(stack, args.cqs or DEFAULT_CQS["citation"])

    # ---- M3 冻结点：QueryPlan v1.0 schema 落盘 ----
    from fondontology.qa.query_planner import write_plan_schema
    write_plan_schema(QUERY_PLAN_SCHEMA)
    print(f"[M3 冻结点] Query Plan schema 已冻结: {QUERY_PLAN_SCHEMA}")
    return run_e2e_benchmark(stack, args.cqs or DEFAULT_CQS["e2e"])


if __name__ == "__main__":
    raise SystemExit(main())