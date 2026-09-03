"""LLM 意图解构（M4）：NL → Intent（Candidate Selection 协议 + resolution 三态）。

设计文档 v0.4 §1/§12：
- 无 LLM key 时走确定性意图构建（先验证系统能力），LLM 只是可选增强；
- LLM 只看到"局部候选词汇"（schema enum 由 resolver 结果生成），不接触全量 TBOX；
- confidence 仅展示，不参与正确性判定；resolution 由确定性规则给出：
  RESOLVED（唯一解释）/ AMBIGUOUS（多个可成立 → 需澄清）/ UNRESOLVED（无成立）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from .config import llm_config, llm_configured
from .index import Candidate, OntologyIndex
from .resolver import VocabularyResolver
from .validator import WhitelistValidator

_INVALID = "INVALID"
_RESOLVED = "RESOLVED"
_AMBIGUOUS = "AMBIGUOUS"
_UNRESOLVED = "UNRESOLVED"


@dataclass
class IntentResult:
    question: str
    status: str                  # RESOLVED | AMBIGUOUS | UNRESOLVED | INVALID
    operation: str               # find | verify
    intent: dict = field(default_factory=dict)
    candidates: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    used_llm: bool = False

    @property
    def is_usable(self) -> bool:
        return self.status == _RESOLVED


def _candidate_json(c: Candidate) -> dict:
    return {"class": c.iri, "label": c.label, "kind": c.kind,
            "score": round(c.score, 4), "confidence": round(c.score, 4),
            "match_type": c.match_type}


def build_intent(question: str, index: OntologyIndex) -> IntentResult:
    """入口：优先 LLM（已配置时），否则/失败时确定性构建。"""
    if llm_configured():
        result = _build_llm_intent(question, index)
        if result is not None and result.is_usable:
            return result
    return _build_deterministic_intent(question, index)


# ---------------------------------------------------------------------------
# 确定性意图（无 key / 兜底）
# ---------------------------------------------------------------------------
def _build_deterministic_intent(question: str, index: OntologyIndex) -> IntentResult:
    if not (question or "").strip():
        return IntentResult(question, _INVALID, "find", notes=["问题为空"])
    resolver = VocabularyResolver(index)
    validator = WhitelistValidator(index)
    notes: list[str] = []

    # verify 语义：优先匹配更具体的标记（"是否互斥/是否等价" 不能被 "是否" 抢先）
    if "互斥" in question:
        return _build_verify(question, "与", resolver, validator, notes, "disjointWith")
    if "等价" in question:
        return _build_verify(question, "与", resolver, validator, notes, "equivalentClass")
    for marker in ("是不是", "是否"):
        if marker in question:
            return _build_verify(question, marker, resolver, validator, notes, "subClassOf")
    if "属于" in question or "子类" in question:
        return _build_verify(question, "属于", resolver, validator, notes, "subClassOf")
    if any(k in question for k in ("区别", "比较", "对比")):
        return IntentResult(question, _UNRESOLVED, "find",
                            notes=["compare/对比 类问题属于 Phase 2，本版不支持"])

    # find：整句解析类候选
    classes = [c for c in resolver.resolve_concept(question) if c.kind == "class"]
    viable = [c for c in resolver.viable(classes) if validator.validate(c, "class")[0]]
    filters = _lexicon_filters(question, index)

    # 实体锚点（投资者/基金经理等个体）：来源锚定查询（entity → traversals → Fund）
    entity_anchor = _find_entity_mention(index, question)
    if entity_anchor is not None and not viable:
        anchor_chain = _anchor_chain_for(index, entity_anchor)
        if anchor_chain is not None:
            traversals = [{"property": str(_prop_iri(index, p))} for p in anchor_chain]
            if all(t["property"] != "None" for t in traversals):
                intent = {
                    "operation": "find",
                    "target_concept": question,
                    "target_class": str(_fund_iri(index)),
                    "source": entity_anchor.iri,
                    "traversals": traversals,
                    "target_candidates": [_candidate_json(entity_anchor)],
                    "filters": filters,
                    "resolution": {"status": _RESOLVED,
                                   "method": "deterministic_candidate_selection(entity_anchor)",
                                   "candidates": 1},
                }
                return IntentResult(question, _RESOLVED, "find", intent=intent,
                                    candidates=intent["target_candidates"],
                                    notes=[f"实体锚点：{entity_anchor.label}（{entity_anchor.kind}）"])
        anchor_types = index.entities.get(entity_anchor.iri, {}).get("types", [])
        type_names = [_t.rsplit("/", 1)[-1] for _t in anchor_types
                      if _t.startswith("https://ontology.example.cn/cnfo/ontology/")]
        return IntentResult(
            question, _UNRESOLVED, "find",
            candidates=[_candidate_json(entity_anchor)],
            notes=[f"已识别实体锚点「{entity_anchor.label}」（{'/'.join(type_names[:3]) or '未知类型'}），"
                   "但该类别的锚点查询链尚未覆盖（当前支持：投资者→持仓→基金、"
                   "基金经理→管理角色→基金）"])
    if not viable:
        if filters and "基金" in question:
            # 词法过滤驱动（如“R4以上的基金”）且上下文为基金 → 默认目标 Fund
            fund = next((c for c in resolver.resolve_concept("基金") if c.kind == "class"), None)
            if fund is not None and validator.validate(fund, "class")[0]:
                intent = {
                    "operation": "find",
                    "target_concept": question,
                    "target_class": fund.iri,
                    "target_candidates": [_candidate_json(fund)],
                    "filters": filters,
                    "resolution": {"status": _RESOLVED,
                                   "method": "deterministic_candidate_selection(default_fund+lexicon)",
                                   "candidates": 1},
                }
                return IntentResult(question, _RESOLVED, "find", intent=intent,
                                    candidates=intent["target_candidates"],
                                    notes=["无类候选，由词法过滤+基金上下文推导目标 Fund"])
        return IntentResult(question, _UNRESOLVED, "find",
                            candidates=[_candidate_json(c) for c in classes],
                            notes=["未找到可成立的类候选"])
    top = viable[0].score
    top_group = [c for c in viable if abs(c.score - top) < 0.05]
    if len(top_group) > 1:
        return IntentResult(question, _AMBIGUOUS, "find",
                            candidates=[_candidate_json(c) for c in top_group],
                            notes=[f"多个候选均可成立：{ [c.label for c in top_group] }"])

    target = viable[0]
    intent = {
        "operation": "find",
        "target_concept": question,
        "target_class": target.iri,
        "target_candidates": [_candidate_json(c) for c in viable[:5]],
        "filters": filters,
        "resolution": {"status": _RESOLVED, "method": "deterministic_candidate_selection",
                       "candidates": len(viable)},
    }
    return IntentResult(question, _RESOLVED, "find", intent=intent,
                        candidates=intent["target_candidates"], notes=notes)


def _build_verify(question: str, marker: str, resolver, validator,
                  notes: list[str], relation: str) -> IntentResult:
    """按关键词把问题切成左右两段，各自解析类候选。"""
    split_at = question.find(marker)
    if split_at <= 0:
        return IntentResult(question, _UNRESOLVED, "verify",
                            notes=[f"无法按 {marker!r} 切分"])
    left = question[:split_at]
    right = question[split_at + len(marker):]
    if not left.strip() or not right.strip():
        return IntentResult(question, _UNRESOLVED, "verify",
                            notes=["切分后一侧为空"])

    def pick(side: str) -> Optional[Candidate]:
        cands = [c for c in resolver.resolve_concept(side) if c.kind == "class"]
        viable = [c for c in resolver.viable(cands) if validator.validate(c, "class")[0]]
        return viable[0] if viable else None

    sub = pick(left)
    obj = pick(right)
    if sub is None or obj is None:
        return IntentResult(question, _UNRESOLVED, "verify",
                            candidates=[_candidate_json(sub)] if sub else [],
                            notes=[f"左侧解析: {'ok' if sub else '失败'}；"
                                   f"右侧解析: {'ok' if obj else '失败'}"])
    intent = {
        "operation": "verify",
        "subject": sub.iri,
        "relation": relation,
        "object": obj.iri,
        "target_concept": question,
        "target_candidates": [_candidate_json(sub), _candidate_json(obj)],
        "resolution": {"status": _RESOLVED, "method": "deterministic_candidate_selection",
                       "candidates": 2},
    }
    return IntentResult(question, _RESOLVED, "verify", intent=intent,
                        candidates=intent["target_candidates"], notes=notes)


def _lexicon_filters(question: str, index: OntologyIndex) -> list[dict]:
    from . import lexicon
    filters: list[dict] = []
    for spec in lexicon.apply(question):
        if not lexicon.resolve(spec.property_iri, index.graph()):
            continue
        filters.append({
            "property": spec.property_iri,
            "operator": spec.operator,
            "value": spec.value,
            "lexicon_source": spec.lexicon_source,
        })
    return filters


# ---------------------------------------------------------------------------
# 实体锚点（投资者等个体提及）——来源锚定的确定性检测
# ---------------------------------------------------------------------------
def _find_entity_mention(index: OntologyIndex, question: str,
                         min_label_len: int = 2) -> Optional[Candidate]:
    """在问题文本中定位实体提及：实体标签（或代码）作为问题子串出现时，
    取最长标签命中（专名优先，避免短词误中）。"""
    best: Optional[Candidate] = None
    for iri, meta in index.entities.items():
        label = meta.get("label", "")
        if len(label) < min_label_len or label not in question:
            continue
        score = round(0.95 + 0.01 * len(label), 4)   # 更长标签得分更高
        cand = Candidate(iri, "entity", label, "label", score)
        if best is None or cand.score > best.score:
            best = cand
    for code, iris in index._entity_codes.items():
        if code and len(code) >= 4 and code in question:
            for iri in iris:
                score = 1.0 + 0.001 * len(code)
                cand = Candidate(iri, "entity", index.entities[iri]["label"], "code", score)
                if best is None or cand.score > best.score:
                    best = cand
    return best


def _entity_has_type(index: OntologyIndex, entity_iri: str, local_name: str) -> bool:
    meta = index.entities.get(entity_iri, {})
    return any(t.rsplit("/", 1)[-1] == local_name for t in meta.get("types", []))


# 实体类型 → 到达基金的锚点遍历链（按本体属性路径设计）
_ANCHOR_PATHS: dict[str, tuple[str, ...]] = {
    "Investor": ("holdsFundPosition", "positionInFundUnit", "issuedByFund"),
    "FundManagerPerson": ("playsFundRole", "roleInFund"),
}


def _anchor_chain_for(index: OntologyIndex, entity: Candidate) -> tuple[str, ...] | None:
    """按实体类型返回锚点遍历链；未覆盖的类型返回 None。"""
    meta = index.entities.get(entity.iri, {})
    for local_name, chain in _ANCHOR_PATHS.items():
        if any(t.rsplit("/", 1)[-1] == local_name for t in meta.get("types", [])):
            return chain
    return None


def _fund_iri(index: OntologyIndex) -> Optional[str]:
    for iri in index.class_iris:
        if iri.rsplit("/", 1)[-1] == "Fund":
            return iri
    return None


def _prop_iri(index: OntologyIndex, local_name: str) -> Optional[str]:
    for iri in index.property_iris:
        if iri.rsplit("/", 1)[-1] == local_name:
            return iri
    return None


# ---------------------------------------------------------------------------
# LLM 意图（局部候选 schema + OpenAI 兼容接口；失败即回退确定性）
# ---------------------------------------------------------------------------
def _build_llm_intent(question: str, index: OntologyIndex) -> Optional[IntentResult]:
    resolver = VocabularyResolver(index)
    validator = WhitelistValidator(index)
    candidates = resolver.search(question, limit=12)
    viable = resolver.viable(candidates)
    if not viable:
        return None
    schema = {
        "operation": {"type": "string", "enum": ["find", "verify"]},
        "target_class": {"type": "string",
                         "enum": [c.iri for c in viable if c.kind in ("class", "entity")][:8]},
        "verify_relation": {"type": "string",
                            "enum": ["subClassOf", "equivalentClass", "disjointWith",
                                     "subPropertyOf", "domainOf", "rangeOf"]},
        "verify_object": {"type": "string", "enum": [c.iri for c in viable if c.kind == "class"][:8]},
    }
    prompt = (
        "你是基金领域本体的语义解构器。只允许从候选词汇中选择，输出 JSON：\n"
        f"候选词汇（局部，非全量）：{json.dumps(candidates[:8], ensure_ascii=False)}\n"
        f"JSON schema：{json.dumps(schema, ensure_ascii=False)}\n"
        f"问题：{question}\n"
        "输出格式：{\"operation\": ..., \"target_class\": ...}（verify 时另含 "
        "subject/relation/object 三字段）。不得编造候选之外的 IRI。"
    )
    try:
        import httpx
        cfg = llm_config()
        resp = httpx.post(
            f"{cfg['OPENAI_BASE_URL'].rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}"},
            json={"model": cfg["OPENAI_MODEL"],
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0},
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_llm_intent(question, content, viable, validator)
    except Exception:
        return None


def _parse_llm_intent(question: str, content: str, viable: list[Candidate],
                      validator: WhitelistValidator) -> Optional[IntentResult]:
    try:
        data = json.loads(content[content.find("{"): content.rfind("}") + 1])
    except Exception:
        return None
    operation = data.get("operation")
    if operation not in ("find", "verify"):
        return None
    by_iri = {c.iri: c for c in viable}
    if operation == "find":
        target = data.get("target_class")
        cand = by_iri.get(target)
        if cand is None or not validator.validate(cand, "class")[0]:
            return None
        intent = {
            "operation": "find", "target_concept": question, "target_class": target,
            "target_candidates": [_candidate_json(c) for c in viable[:5]],
            "filters": _lexicon_filters(question, validator.index),
            "resolution": {"status": _RESOLVED, "method": "llm_candidate_selection",
                           "candidates": len(viable)},
        }
        return IntentResult(question, _RESOLVED, "find", intent=intent,
                            candidates=intent["target_candidates"], used_llm=True,
                            notes=["LLM 候选选择已过白名单校验"])
    # verify
    sub = by_iri.get(data.get("subject"))
    obj = by_iri.get(data.get("object") or data.get("verify_object"))
    relation = data.get("relation") or data.get("verify_relation")
    if (sub is None or obj is None or relation not in
            {"subClassOf", "equivalentClass", "disjointWith", "subPropertyOf",
             "domainOf", "rangeOf"}):
        return None
    intent = {
        "operation": "verify", "subject": sub.iri, "relation": relation,
        "object": obj.iri, "target_concept": question,
        "target_candidates": [_candidate_json(sub), _candidate_json(obj)],
        "resolution": {"status": _RESOLVED, "method": "llm_candidate_selection",
                       "candidates": 2},
    }
    return IntentResult(question, _RESOLVED, "verify", intent=intent,
                        candidates=intent["target_candidates"], used_llm=True,
                        notes=["LLM 候选选择已过白名单校验"])