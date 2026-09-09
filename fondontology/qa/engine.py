"""确定性端到端（M3）+ NL 全链路入口（M4/M5）。

- answer()：手工 Intent → QueryPlan → SPARQL → Evidence → 模板/LLM 表达
- answer_question()：自然语言 → intent（Candidate Selection 三态）→ 同链条 →
  explainer（LLM 表达 + citation 闸门，无 key 自动模板）；支持 on_phase 阶段
  回调与 on_text_delta 终稿增量回调（Web UI SSE 流式）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional
from weakref import WeakKeyDictionary

from . import explainer, templates
from .abox_query import execute_find
from .context import SliceBudget, assemble_local_context, build_ontology_slice
from .evidence import EvidenceBuilder
from .graph import DataStack
from .query_planner import plan_find
from .verify import verify as tbox_verify

FIND_INTENT_KEYS = ("target", "source", "filters", "exclusions", "traversals",
                    "projections", "ordering", "limit", "offset",
                    "related_class", "relation_path", "aggregation", "select")

# 索引缓存：弱引用键（DataStack 被回收即失效）。禁止使用 id() 作键——
# 同一进程中 id 会被复用，全量测试/长生命周期下会命中陈旧索引。
_INDEX_CACHE: WeakKeyDictionary = WeakKeyDictionary()


def _get_index(stack: DataStack):
    index = _INDEX_CACHE.get(stack)
    if index is None:
        from .index import OntologyIndex
        index = OntologyIndex(stack)
        _INDEX_CACHE[stack] = index
    return index


def _get_ctx(stack: DataStack):
    """本体语义视图（planner 关系约束校验用；OntologyContext 自带弱引用缓存）。"""
    from .semantics import OntologyContext
    return OntologyContext.from_stack(stack)


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


def _emit(on_phase: Optional[Callable[[str, str], None]], code: str, message: str) -> None:
    """可选的阶段回调（Web UI SSE 进度用）；默认 None 时为空操作。"""
    if on_phase is not None:
        try:
            on_phase(code, message)
        except Exception:
            pass  # 阶段回调异常不得影响问数链路


def _emit_text_deltas(text: str, on_text_delta: Optional[Callable[[str], None]]) -> None:
    """终稿答案文本切块后经 on_text_delta 增量下发（Web UI 流式渲染用）。

    只在表达层（LLM 过闸终稿/模板）产出完整文本后调用：表达层输出是结构化
    JSON 且须整句过 citation 闸门，无法做 LLM 原始 token 级直通，故按行切块、
    单块上限 64 字符，由前端打字机平滑输出。下发异常不影响问数链路。
    """
    if on_text_delta is None or not text:
        return
    lines = text.split("\n")
    for i, line in enumerate(lines):
        chunk = line + ("\n" if i < len(lines) - 1 else "")
        for j in range(0, len(chunk), 64):
            try:
                on_text_delta(chunk[j:j + 64])
            except Exception:
                return


def answer_question(question: str, stack: DataStack, *,
                    slice_budget: SliceBudget = SliceBudget(),
                    max_subgraph_entities: int = 8,
                    use_llm: Optional[bool] = None,
                    on_phase: Optional[Callable[[str, str], None]] = None,
                    on_text_delta: Optional[Callable[[str], None]] = None) -> QaAnswer:
    """自然语言 → 答案（M4 意图三态 + M3/M5 链条）。

    无 LLM key：intent 走确定性，表达走模板（gate=template_nokey，UCR=0）；
    有 key：intent/表达走 LLM（候选选择过白名单；表达越权引用→重试→模板回退）。
    on_phase(code, message)：可选阶段进度回调（intent/plan/query/evidence/explain）。
    on_text_delta(chunk)：可选文本增量回调，answer 终稿按行/块流出（先于返回值）。
    """
    ans = _answer_question_impl(question, stack, slice_budget=slice_budget,
                                max_subgraph_entities=max_subgraph_entities,
                                use_llm=use_llm, on_phase=on_phase)
    _emit_text_deltas(ans.text, on_text_delta)
    return ans


def _answer_question_impl(question: str, stack: DataStack, *,
                          slice_budget: SliceBudget = SliceBudget(),
                          max_subgraph_entities: int = 8,
                          use_llm: Optional[bool] = None,
                          on_phase: Optional[Callable[[str, str], None]] = None) -> QaAnswer:
    """answer_question 的同步实现（不含文本增量下发）。"""
    from .intent import build_intent

    _emit(on_phase, "intent", "语义解析中")
    intent_res = build_intent(question, _get_index(stack),
                              use_llm=(False if use_llm is False else None))
    if intent_res.status != "RESOLVED":
        _emit(on_phase, "intent", "意图未解析")
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
    if intent["operation"] == "classify":
        # T-BOX 层问题（schema 枚举）：答案是类清单，读类层级即可，不依赖 RAG 开关
        from .rag.answer import answer_classify
        _emit(on_phase, "retrieve", "读取本体类层级")
        ctx = _get_ctx(stack)
        exp = answer_classify(question, intent, ctx)
        if exp.status != "ok":
            return QaAnswer(kind="classify", status="unresolved", text=exp.text,
                            intent_status="UNRESOLVED")
        return QaAnswer(
            kind="classify", status="ok", text=exp.text,
            claims=(exp.report or {}).get("claims", []),
            cited_evidence=[e["id"] for e in (exp.report or {}).get("evidence", [])],
            report=exp.report,
            explanation={"gate": "tbox_hierarchy", "used_llm": intent_res.used_llm,
                         "ucr": 0.0,
                         "claims_used": [c["claim_id"] for c in (exp.report or {}).get("claims", [])]},
        )

    if intent["operation"] == "explain":
        from .config import rag_enabled
        # define/compare 读 T-BOX（一等能力，不受 RAG 开关限制）；
        # describe 依赖 chunk 池（RAG 扩展数据面），受开关控制
        if intent.get("explain_type") == "describe" and not rag_enabled():
            return QaAnswer(kind="intent", status="unresolved",
                            text="解释类问答（RAG）当前未启用",
                            intent_status="UNRESOLVED")
        _emit(on_phase, "retrieve", "检索文本与定义")
        from .rag import answer_explain
        ctx = _get_ctx(stack)
        exp = answer_explain(question, intent, ctx, stack.query_graph())
        if exp.status != "ok":
            return QaAnswer(kind="explain", status="unresolved", text=exp.text,
                            intent_status="UNRESOLVED")
        _emit(on_phase, "explain", "组织解释性回答")
        return QaAnswer(
            kind="explain", status="ok", text=exp.text,
            claims=(exp.report or {}).get("claims", []),
            cited_evidence=[e["id"] for e in (exp.report or {}).get("evidence", [])],
            report=exp.report,
            explanation={"gate": "template_rag", "used_llm": False,
                         "ucr": 0.0, "claims_used":
                         [c["claim_id"] for c in (exp.report or {}).get("claims", [])]},
        )

    if intent["operation"] == "verify":
        _emit(on_phase, "verify", "T-BOX 判链")
        base = answer(stack, {
            "operation": "verify",
            "subject": intent["subject"],
            "relation": intent["relation"],
            "object": intent["object"],
        }, slice_budget=slice_budget)
        if base.status == "ok" and base.report:
            result = tbox_verify(stack.query_graph(), intent["subject"],
                                 intent["relation"], intent["object"])
            # 表达层与 find 一致走 LLM+闸门；未启用 LLM 时保留模板+证据链渲染
            exp = explainer.explain(question, base.report, use_llm=use_llm)
            if not exp.used_llm:
                exp = explainer.verify_explanation(result, base.report)
        else:
            exp = explainer.Explanation(text=base.text)
        base.text = exp.text
        base.explanation = {
            "gate": exp.gate, "used_llm": exp.used_llm, "ucr": exp.ucr,
            "claims_used": exp.claims_used,
        }
        return base

    # find：intent 过滤条件（lexicon_source）直接进计划；投资者锚点经 source+traversals；
    # 聚合/排名语义（related_class/relation_path/aggregation/ordering/limit）进计划，
    # planner 经本体语义视图做 domain/range 关系约束校验
    filters = [dict(f) for f in intent.get("filters") or []]
    _emit(on_phase, "plan", "编译查询计划")
    plan = plan_find(
        target=intent["target_class"], tbox=stack.tbox, abox=stack.abox,
        source=intent.get("source"),
        traversals=intent.get("traversals"),
        filters=filters,
        exclusions=intent.get("exclusions"),
        related_class=intent.get("related_class"),
        relation_path=intent.get("relation_path"),
        aggregation=intent.get("aggregation"),
        select=intent.get("select"),
        ordering=intent.get("ordering"),
        limit=intent.get("limit"),
        ctx=_get_ctx(stack),
    )
    if plan.get("errors"):
        return QaAnswer(kind="find", status="invalid",
                        text=templates.render_invalid(plan["errors"]))
    _emit(on_phase, "query", "执行本体检索")
    result = execute_find(stack, plan)
    if result.errors:
        return QaAnswer(kind="find", status="invalid",
                        text=templates.render_invalid(result.errors))
    builder = EvidenceBuilder(stack)
    _emit(on_phase, "evidence", "构建证据与溯源")
    report = builder.build_for_find(plan, result, max_subgraph_entities=max_subgraph_entities)
    slice_ = build_ontology_slice(stack.tbox, plan, slice_budget)
    local_context = assemble_local_context(report, slice_)
    _emit(on_phase, "explain", "生成自然语言表达")
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
        plan = plan_find(tbox=stack.tbox, abox=stack.abox, ctx=_get_ctx(stack), **kwargs)
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