"""确定性端到端（M3）+ NL 全链路入口（M4/M5）。

- answer()：手工 Intent → QueryPlan → SPARQL → Evidence → 模板/LLM 表达
- answer_question()：自然语言 → intent（Candidate Selection 三态）→ 同链条 →
  explainer（LLM 表达 + citation 闸门，无 key 自动模板）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import explainer, templates
from .abox_query import execute_find
from .context import SliceBudget, assemble_local_context, build_ontology_slice
from .evidence import EvidenceBuilder
from .graph import DataStack
from .query_planner import plan_find
from .verify import verify as tbox_verify

FIND_INTENT_KEYS = ("target", "source", "filters", "exclusions", "traversals",
                    "projections", "ordering", "limit", "offset")

# 索引缓存（answer_question 复用，key 按 stack 对象身份）
_INDEX_CACHE: dict[int, object] = {}


def _get_index(stack: DataStack):
    key = id(stack)
    if key not in _INDEX_CACHE:
        from .index import OntologyIndex
        _INDEX_CACHE[key] = OntologyIndex(stack)
    return _INDEX_CACHE[key]


@dataclass
class QaAnswer:
    kind: str                       # find | verify | intent
    status: str                     # ok | invalid | unresolved | ambiguous
    text: str
    claims: list = field(default_factory=list)
    cited_evidence: list = field(default_factory=list)
    report: Optional[dict] = None   # 证据合同（find/verify）
    local_context: Optional[dict] = None
    verdict: Optional[str] = None   # verify 四状态
    explanation: Optional[dict] = None   # M5：{gate, used_llm, ucr, claims_used}
    intent_status: Optional[str] = None


def _cand_label(c) -> str:
    """候选（dict 或 Candidate 对象）取展示名，异常兜底。"""
    try:
        if isinstance(c, dict):
            return str(c.get("label", ""))
        return str(getattr(c, "label", ""))
    except Exception:
        return ""


def answer_question(question: str, stack: DataStack, *,
                    slice_budget: SliceBudget = SliceBudget(),
                    max_subgraph_entities: int = 8,
                    use_llm: Optional[bool] = None) -> QaAnswer:
    """自然语言 → 答案（M4 意图三态 + M3/M5 链条）。

    无 LLM key：intent 走确定性，表达走模板（gate=template_nokey，UCR=0）；
    有 key：intent/表达走 LLM（候选选择过白名单；表达越权引用→重试→模板回退）。
    """
    from .intent import build_intent

    intent_res = build_intent(question, _get_index(stack))
    if intent_res.status != "RESOLVED":
        cand_text = "、".join(_cand_label(c) for c in intent_res.candidates)
        text_map = {
            "AMBIGUOUS": "问题存在多个可成立的解释，请澄清（候选：" + cand_text + "）",
            "UNRESOLVED": "未能将问题映射到本体语义"
                          + (f"（{intent_res.notes[0]}）" if intent_res.notes else ""),
            "INVALID": "问题为空或格式非法",
        }
        return QaAnswer(kind="intent", status=intent_res.status.lower(),
                        text=text_map.get(intent_res.status, "无法处理"),
                        intent_status=intent_res.status)

    intent = intent_res.intent
    if intent["operation"] == "verify":
        base = answer(stack, {
            "operation": "verify",
            "subject": intent["subject"],
            "relation": intent["relation"],
            "object": intent["object"],
        }, slice_budget=slice_budget)
        if base.status == "ok" and base.report:
            exp = explainer.verify_explanation(
                tbox_verify(stack.query_graph(), intent["subject"],
                            intent["relation"], intent["object"]),
                base.report)
        else:
            exp = explainer.Explanation(text=base.text)
        base.text = exp.text
        base.explanation = {
            "gate": exp.gate, "used_llm": exp.used_llm, "ucr": exp.ucr,
            "claims_used": exp.claims_used,
        }
        return base

    # find：intent 过滤条件（lexicon_source）直接进计划；投资者锚点经 source+traversals
    filters = [dict(f) for f in intent.get("filters") or []]
    plan = plan_find(
        target=intent["target_class"], tbox=stack.tbox, abox=stack.abox,
        source=intent.get("source"),
        traversals=intent.get("traversals"),
        filters=filters,
    )
    if plan.get("errors"):
        return QaAnswer(kind="find", status="invalid",
                        text=templates.render_invalid(plan["errors"]))
    result = execute_find(stack, plan)
    if result.errors:
        return QaAnswer(kind="find", status="invalid",
                        text=templates.render_invalid(result.errors))
    builder = EvidenceBuilder(stack)
    report = builder.build_for_find(plan, result, max_subgraph_entities=max_subgraph_entities)
    slice_ = build_ontology_slice(stack.tbox, plan, slice_budget)
    local_context = assemble_local_context(report, slice_)
    exp = explainer.explain(question, report,
                            context_summary=f"{len(slice_['classes'])} 类切片",
                            use_llm=use_llm)
    return QaAnswer(
        kind="find", status="ok", text=exp.text,
        claims=(report or {}).get("claims", []),
        cited_evidence=[e["id"] for e in (report or {}).get("evidence", [])],
        report=report, local_context=local_context,
        explanation={"gate": exp.gate, "used_llm": exp.used_llm, "ucr": exp.ucr,
                     "claims_used": exp.claims_used},
    )


def answer(stack: DataStack, intent: dict, *,
           slice_budget: SliceBudget = SliceBudget(),
           max_subgraph_entities: int = 8,
           with_evidence: bool = True) -> QaAnswer:
    """确定性端到端回答。

    intent 形态：
      {"operation": "find", "target": "...", "filters": [...], ...}
      {"operation": "verify", "subject": "...", "relation": "subClassOf", "object": "..."}
    """
    operation = (intent or {}).get("operation")
    builder = EvidenceBuilder(stack) if with_evidence else None

    if operation == "verify":
        result = tbox_verify(stack.query_graph(),
                             intent.get("subject", ""),
                             intent.get("relation", ""),
                             intent.get("object", ""))
        report = builder.build_for_verify(operation, result) if builder else None
        return QaAnswer(
            kind="verify",
            status="ok" if result.answer != "INVALID_REQUEST" else "invalid",
            text=templates.render_verify(result),
            claims=(report or {}).get("claims", []),
            cited_evidence=[e["id"] for e in (report or {}).get("evidence", [])],
            report=report,
            verdict=result.answer,
        )

    if operation == "find":
        kwargs = {k: intent[k] for k in FIND_INTENT_KEYS if k in intent}
        plan = plan_find(tbox=stack.tbox, abox=stack.abox, **kwargs)
        if plan.get("errors"):
            return QaAnswer(kind="find", status="invalid",
                            text=templates.render_invalid(plan["errors"]))
        result = execute_find(stack, plan)
        if result.errors:
            return QaAnswer(kind="find", status="invalid",
                            text=templates.render_invalid(result.errors))
        report = builder.build_for_find(plan, result,
                                        max_subgraph_entities=max_subgraph_entities) if builder else None
        slice_ = build_ontology_slice(stack.tbox, plan, slice_budget)
        text = templates.render_find(report or {}, slice_)
        local = assemble_local_context(report or {}, slice_) if report else None
        return QaAnswer(
            kind="find", status="ok", text=text,
            claims=(report or {}).get("claims", []),
            cited_evidence=[e["id"] for e in (report or {}).get("evidence", [])],
            report=report, local_context=local,
        )

    return QaAnswer(kind="unknown", status="invalid",
                    text=templates.render_invalid(["intent.operation 缺失或非法（支持 find/verify）"]))