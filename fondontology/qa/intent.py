"""意图语义解析（Semantic Querying 第一阶段）：NL → SemanticParse。

三阶段生命周期之"Semantic Querying"：Ontology 不是替 LLM 推理，而是给 LLM
提供可以进行语义推理的世界模型——LLM 意图解析时注入 OntologyContext
（类层级 + 类间关系 + 属性 domain/range），使"同时管理多个基金"能映射为
target=FundManagerPerson + relation=^hasFundManager + COUNT(基金)>=2，
而不是退化成"找全部基金经理"。

输出协议（resolution 三态不变）：
  RESOLVED（唯一解释）/ AMBIGUOUS（多个可成立 → 需澄清）/ UNRESOLVED（无成立）。

SemanticParse（intent dict）在原有 find/verify 字段上扩展：
  select        entities | count      —— 返回实体集合还是计数
  related_class 聚合/排名涉及的另一类 IRI（如"管理多个基金"中的 Fund）
  relation_path [{"property","inverse"}]  —— target→related 的本体关系路径
  aggregation   {"func","operator","value"} —— COUNT/SUM/AVG/MAX/MIN + HAVING
  ordering      [{"by": "agg" | 属性IRI, "direction": "desc"|"asc"}]
  limit         int
LLM 输出须经本体白名单 + domain/range 约束校验才采纳；失败回落确定性规则。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .config import llm_config, llm_configured
from .index import Candidate, OntologyIndex
from .resolver import VocabularyResolver
from .semantics import OntologyContext
from .validator import WhitelistValidator

_INVALID = "INVALID"
_RESOLVED = "RESOLVED"
_AMBIGUOUS = "AMBIGUOUS"
_UNRESOLVED = "UNRESOLVED"

_AGG_FUNCS = ("count", "sum", "avg", "max", "min")
_CMP_OPS = (">=", "<=", ">", "<", "=")


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


def build_intent(question: str, index: OntologyIndex,
                 *, use_llm: Optional[bool] = None) -> IntentResult:
    """入口：模型语义解析为主、确定性规则兜底。

    use_llm：None=按 .env 配置；True=强制模型；False=强制规则（单测/确定性回归）。
    LLM 看到本体语义视图（类层级/关系/属性约束），输出 SemanticParse 后过
    白名单 + domain/range 校验；模型未配置/失败/输出非法 → 回落规则路径。
    """
    if use_llm is None:
        use_llm = llm_configured()
    # Phase 2 边界对 LLM/确定性两路径一致：compare/对比类直接拒答
    if any(k in question for k in ("区别", "比较", "对比")):
        return IntentResult(question, _UNRESOLVED, "find",
                            notes=["compare/对比 类问题属于 Phase 2，本版不支持"])
    if use_llm:
        result = _build_llm_intent(question, index)
        if result is not None and result.is_usable:
            return result
    fallback = _build_deterministic_intent(question, index)
    if use_llm and _LAST_LLM_ERROR:
        fallback.notes.insert(0, f"{_LAST_LLM_ERROR}，已回退确定性解析")
    return fallback


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
            traversals = [
                {"property": str(_prop_iri(index, p)), "inverse": inv}
                for p, inv in anchor_chain
            ]
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
    # 聚合/排名/计数句型（"同时管理多个基金的基金经理"等）：resolver 阈值可能
    # 过滤掉子串候选，故基于本体语义视图直接做类提及检测，不依赖 viable
    agg = _try_aggregation_intent(question, index, filters)
    if agg is not None:
        return agg

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


# ---------------------------------------------------------------------------
# 确定性聚合/排名/计数句型（规则兜底；LLM 路径覆盖任意表述）
# ---------------------------------------------------------------------------
# "同时管理多个/两只/3只以上" → COUNT(related) >= N
_MULTI_RE = re.compile(r"(?:同时|共|一共|累计)?.{0,8}?(多|两|几|(\d+))\s*(?:个|只|家|款)(?:以上|及以上)?")
# "最多/最高/前N/前 N 名" → ORDER BY agg DESC LIMIT N
_TOP_RE = re.compile(r"前\s*(\d+|[一二三四五六七八九十])\s*(?:个|只|家|名|位)?|最多|最高|最大|排名靠前")
_COUNT_RE = re.compile(r"多少")
_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _class_mentions(ctx: OntologyContext, question: str) -> list[tuple[int, int, object]]:
    """问题中提及的本体类：[(start, end, ClassInfo)]；同起点重叠取最长标签。"""
    mentions: list[tuple[int, int, object]] = []
    for info in ctx.classes.values():
        for token in {info.label, info.local}:
            if not token or len(token) < 2:
                continue
            start = 0
            while True:
                pos = question.find(token, start)
                if pos < 0:
                    break
                mentions.append((pos, pos + len(token), info))
                start = pos + 1
    mentions.sort(key=lambda m: (m[0], -(m[1] - m[0])))
    deduped: list[tuple[int, int, object]] = []
    for m in mentions:
        if deduped and m[0] == deduped[-1][0]:
            continue  # 同起点，先到者最长
        deduped.append(m)
    return deduped


def _try_aggregation_intent(question: str, index: OntologyIndex,
                            filters: list[dict]) -> Optional[IntentResult]:
    """"同时管理多个基金的基金经理"类句型 → 带 aggregation 的 SemanticParse。

    结构：target 类（问题焦点，取提及位置靠后的类）+ related 类（被聚合的
    另一类，经本体关系图发现路径）+ 触发词（多个/最多/多少）。
    类提及检测直接走 OntologyContext，不经过 resolver 阈值——聚合句型的
    类词（"基金经理""基金"）常因子串打分低于 0.6 被过滤掉。
    """
    has_multi = _MULTI_RE.search(question)
    has_top = _TOP_RE.search(question)
    has_count = _COUNT_RE.search(question)
    if not (has_multi or has_top or has_count):
        return None

    ctx = OntologyContext.from_stack(index.stack)
    mentions = _class_mentions(ctx, question)
    if not mentions:
        return None

    # target：问题焦点 = 提及结束位置最靠后的类（"…的X有"/"X有什么"）
    target_info = max(mentions, key=lambda m: m[1])[2]
    target_local = target_info.local
    target = Candidate(target_info.iri, "class", target_info.label, "contains", 0.9)

    # related：其余提及类中与 target 存在本体关系路径者
    related_local = None
    relation_path = None
    for _, _, info in sorted(mentions, key=lambda m: m[1], reverse=True):
        if info.local == target_local:
            continue
        path = ctx.find_relation_path(target_local, info.local, question=question)
        if path:
            related_local = info.local
            relation_path = path
            break
    if related_local is None and has_multi and target_local != "Fund":
        # "同时X多个Y"但 Y 未被类提及捕获（如"基金"被长词吞并）→ 默认 Fund
        path = ctx.find_relation_path(target_local, "Fund", question=question)
        if path:
            related_local = "Fund"
            relation_path = path

    if related_local is None and not has_count:
        return None  # 触发词命中但无法构成聚合语义 → 交回普通 find 流程

    intent: dict = {
        "operation": "find",
        "target_concept": question,
        "target_class": target_info.iri,
        "target_candidates": [_candidate_json(target)],
        "filters": filters,
        "resolution": {"status": _RESOLVED,
                       "method": "deterministic_aggregation",
                       "candidates": len(mentions)},
    }
    notes: list[str] = []

    if related_local is not None and relation_path:
        related_iri = next((iri for iri in index.class_iris
                            if iri.rsplit("/", 1)[-1] == related_local), None)
        intent["related_class"] = related_iri
        intent["relation_path"] = [
            {"property": h["property"], "inverse": h["inverse"]}
            for h in relation_path
        ]
        intent["aggregation"] = {"func": "count"}
        if has_multi:
            num = _cn_num(has_multi.group(2) or has_multi.group(1))
            threshold = max(num, 2)
            intent["aggregation"].update({"operator": ">=", "value": threshold})
            notes.append(f"聚合约束：COUNT({related_local}) >= {threshold}")
        if has_top:
            n = _top_n(has_top)
            intent["ordering"] = [{"by": "agg", "direction": "desc"}]
            intent["limit"] = n
            notes.append(f"排名：按 COUNT({related_local}) 降序，LIMIT {n}")
    elif has_count:
        intent["select"] = "count"
        notes.append("计数问题：返回结果数")

    if has_count and "select" not in intent:
        intent["select"] = "count"
    return IntentResult(question, _RESOLVED, "find", intent=intent,
                        candidates=intent["target_candidates"],
                        notes=notes or ["确定性聚合句型命中"])


def _cn_num(text: str) -> int:
    if not text:
        return 2
    if text.isdigit():
        return int(text)
    if text in ("多", "几"):
        return 2
    return _CN_NUM.get(text, 2)


def _top_n(match) -> int:
    raw = match.group(1)
    if raw is None:
        return 1                       # "最多/最高" → 取第 1
    if raw.isdigit():
        return max(1, int(raw))
    return _CN_NUM.get(raw, 1)


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


# 实体类型 → 到达基金的锚点遍历链（按本体属性路径设计；inverse=true 的跳依赖
# 推理层物化的快捷边，如 hasFundManager 由 propertyChainAxiom 推得）
_ANCHOR_PATHS: dict[str, tuple[tuple[str, bool], ...]] = {
    "Investor": (("holdsFundPosition", False), ("positionInFundUnit", False),
                 ("issuedByFund", False)),
    "FundManagerPerson": (("hasFundManager", True),),   # 推理边：hasFundManagerRole∘rolePlayedBy
}


def _anchor_chain_for(index: OntologyIndex, entity: Candidate) -> tuple[tuple[str, bool], ...] | None:
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
# LLM 语义解析（注入本体语义视图：类层级 + 类间关系 + 属性约束）
# ---------------------------------------------------------------------------
_LLM_SCHEMA = """{
  "operation": "find" 或 "verify",
  "target": "<类 local 名>" 或 null,
  "select": "entities" 或 "count",
  "related": "<类 local 名>" 或 null,
  "relation_path": [{"property": "<对象属性 local 名>", "inverse": true或false}] 或 null,
  "aggregation": {"func": "count|sum|avg|max|min", "operator": ">=|>|=|<=|<", "value": 数字} 或 null,
  "order_by": "agg" 或 "<数据属性 local 名>" 或 null,
  "order_direction": "desc" 或 "asc",
  "limit": 数字 或 null,
  "entity_label": "<问题中的具体人名/公司名/编号原文>" 或 null,
  "filters": [{"property": "<属性 local 名>", "operator": "eq|contains|>=|<=|>|<", "value": "<值原文>"}],
  "verify_subject": "<类 local 名>" 或 null,
  "verify_object": "<类 local 名>" 或 null,
  "verify_relation": "subClassOf|equivalentClass|disjointWith" 或 null
}"""

_LLM_EXAMPLES = """示例1：
问题：有哪些交易型开放式指数基金
输出：{"operation": "find", "target": "ExchangeTradedFund", "select": "entities",
  "related": null, "relation_path": null, "aggregation": null, "order_by": null,
  "order_direction": "desc", "limit": null, "entity_label": null, "filters": [],
  "verify_subject": null, "verify_object": null, "verify_relation": null}

示例2（聚合约束——"同时管理多个"是 COUNT(基金)>=2，不是普通列举）：
问题：同时管理多个基金的基金经理有什么？
输出：{"operation": "find", "target": "FundManagerPerson", "select": "entities",
  "related": "Fund", "relation_path": [{"property": "hasFundManager", "inverse": true}],
  "aggregation": {"func": "count", "operator": ">=", "value": 2},
  "order_by": null, "order_direction": "desc", "limit": null,
  "entity_label": null, "filters": [],
  "verify_subject": null, "verify_object": null, "verify_relation": null}

示例3（排名——"最多"是 ORDER BY COUNT DESC LIMIT 1）：
问题：在管基金最多的基金经理是谁？
输出：{"operation": "find", "target": "FundManagerPerson", "select": "entities",
  "related": "Fund", "relation_path": [{"property": "hasFundManager", "inverse": true}],
  "aggregation": {"func": "count"},
  "order_by": "agg", "order_direction": "desc", "limit": 1,
  "entity_label": null, "filters": [],
  "verify_subject": null, "verify_object": null, "verify_relation": null}

示例4（实体锚点——提到具体人名，target 是对方想查的类型）：
问题：魏辉管理的基金有哪些？
输出：{"operation": "find", "target": "Fund", "select": "entities",
  "related": null, "relation_path": null, "aggregation": null, "order_by": null,
  "order_direction": "desc", "limit": null, "entity_label": "魏辉", "filters": [],
  "verify_subject": null, "verify_object": null, "verify_relation": null}

示例5（问收益/表现——target 是基金类本身，业绩记录类永远不作 target）：
问题：货币基金收益怎么样？
输出：{"operation": "find", "target": "MoneyMarketFund", "select": "entities",
  "related": "FundPerformanceRecord",
  "relation_path": [{"property": "performanceForFund", "inverse": true}],
  "aggregation": null, "order_by": null, "order_direction": "desc", "limit": null,
  "entity_label": null, "filters": [],
  "verify_subject": null, "verify_object": null, "verify_relation": null}

示例6（行业主题基金——target 是 EquityFund，行业词用 investmentFocus contains 过滤，
该属性属于 FundInvestmentStrategy，需沿 usesInvestmentStrategy 关系到达）：
问题：医药基金有哪些？
输出：{"operation": "find", "target": "EquityFund", "select": "entities",
  "related": "FundInvestmentStrategy",
  "relation_path": [{"property": "usesInvestmentStrategy", "inverse": false}],
  "aggregation": null, "order_by": null, "order_direction": "desc", "limit": null,
  "entity_label": null,
  "filters": [{"property": "investmentFocus", "operator": "contains", "value": "医药"}],
  "verify_subject": null, "verify_object": null, "verify_relation": null}"""


def _build_llm_intent(question: str, index: OntologyIndex) -> Optional[IntentResult]:
    if not (question or "").strip():
        return None
    ctx = OntologyContext.from_stack(index.stack)
    semantic_view = ctx.render_for_llm()

    prompt = (
        "你是中国基金领域本体（CNFO）驱动的语义解析器。把用户问题解析为结构化 "
        "SemanticParse（JSON），供下游生成图查询。解析时必须利用下面的本体语义视图"
        "（类层级、类间关系、数据属性），不得把领域词当普通字符串处理。\n\n"
        f"{semantic_view}\n\n"
        "【解析要点】\n"
        "1. target 是用户想问的对象类型；related 是聚合/排名中涉及的另一类。\n"
        "2. relation_path 是 target→related 的本体关系路径（取自【类间关系】，"
        "   inverse=true 表示沿属性的反方向走，如 基金经理 ^hasFundManager 基金）。\n"
        "3. aggregation 表达\"同时管理多个/超过N只\"等数量约束"
        "   （func=count，operator/value 为阈值）；仅计数问题用 select=count。\n"
        "4. order_by=\"agg\" 表示按聚合值排序（需配合 aggregation）；"
        "   order_by=数据属性 local 名表示按该属性排序；limit 为返回条数。\n"
        "5. 问题提到具体人名/公司名/编号时填 entity_label（原文）；"
        "   判断题（是不是/是否/属于/互斥/等价）用 operation=verify。\n"
        "6. target/related/relation_path/filters 中的 local 名必须来自上面的语义视图；"
        "   不确定的字段填 null，不得编造。\n"
        "7. 问某类基金的收益/表现/净值'怎么样'时，target 永远是该基金类本身；"
        "   FundPerformanceRecord/NetAssetValueRecord 等记录类只能作 related。\n"
        "8. 行业/主题词（医药、消费、科技等）修饰'基金'时，target 用 EquityFund"
        "   （行业主题基金以股票型为主），主题词用 investmentFocus + contains 过滤，"
        "   该属性属于 FundInvestmentStrategy，须经 usesInvestmentStrategy 到达。\n"
        "9. 过滤文本型属性（描述性字符串）时用 contains；代码/枚举型属性用 eq。\n\n"
        f"【输出 Schema】只输出 JSON：\n{_LLM_SCHEMA}\n\n"
        f"{_LLM_EXAMPLES}\n\n"
        f"问题：{question}"
    )
    data = _call_deconstructor(prompt)
    if data is None:
        return None
    resolver = VocabularyResolver(index)
    validator = WhitelistValidator(index)
    return _parse_llm_intent(question, data, index, resolver, validator, ctx)


# 最近一次 LLM 调用失败原因（供回退路径写入 notes，避免静默降级）
_LAST_LLM_ERROR: Optional[str] = None


def _stream_chat_content(prompt: str, temperature: float = 0,
                         max_attempts: int = 2) -> Optional[str]:
    """OpenAI 兼容流式 chat 调用，返回 content 原文（失败返回 None）。

    必须用流式（stream=True）：非流式下服务端在生成完成前不下发任何字节，
    复杂问题的长推理（实测 145s）会触发读超时；流式首字节数秒即达，
    读超时只按"连续无字节"计。失败原因写入 _LAST_LLM_ERROR 供 notes 透传。
    """
    global _LAST_LLM_ERROR
    _LAST_LLM_ERROR = None
    import httpx
    cfg = llm_config()
    url = _chat_completions_url(cfg["OPENAI_BASE_URL"])
    headers = {"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}"}
    payload = {"model": cfg["OPENAI_MODEL"],
               "messages": [{"role": "user", "content": prompt}],
               "temperature": temperature, "stream": True}
    for attempt in range(1, max_attempts + 1):
        try:
            chunks: list[str] = []
            with httpx.stream("POST", url, headers=headers, json=payload,
                              timeout=httpx.Timeout(600.0, read=180.0)) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    try:
                        delta = json.loads(line[6:])["choices"][0].get("delta", {})
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta.get("content"):
                        chunks.append(delta["content"])
            content = "".join(chunks)
            if not content.strip():
                _LAST_LLM_ERROR = "LLM 输出为空"
                continue
            return content
        except httpx.TimeoutException:
            _LAST_LLM_ERROR = f"LLM 调用超时（第 {attempt}/{max_attempts} 次）"
        except httpx.HTTPStatusError as e:
            # 4xx（鉴权/限额）重试无意义，直接放弃；5xx 可重试
            _LAST_LLM_ERROR = f"LLM HTTP {e.response.status_code}"
            if e.response.status_code < 500:
                return None
        except Exception as e:  # 网络/解析等
            _LAST_LLM_ERROR = f"LLM 调用失败：{type(e).__name__}"
    return None


def _call_deconstructor(prompt: str, max_attempts: int = 2) -> Optional[dict]:
    """意图解析调用（抽出便于测试 mock）：流式取 content → 提取首个 JSON 对象。"""
    global _LAST_LLM_ERROR
    content = _stream_chat_content(prompt, temperature=0, max_attempts=max_attempts)
    if content is None:
        return None
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        _LAST_LLM_ERROR = "LLM 输出非 JSON"
        return None
    try:
        return json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        _LAST_LLM_ERROR = "LLM 输出 JSON 解析失败"
        return None


def _parse_llm_intent(question: str, data: dict, index: OntologyIndex,
                      resolver: VocabularyResolver,
                      validator: WhitelistValidator,
                      ctx: OntologyContext) -> Optional[IntentResult]:
    """LLM 输出 → 本体白名单 + domain/range 约束校验 → SemanticParse。"""
    operation = data.get("operation")

    def _resolve_class(term) -> Optional[str]:
        local = str(term or "").strip()
        if not local:
            return None
        if local in ctx.classes:
            return ctx.classes[local].iri
        # 容差：label 反向查找（LLM 给的可能是近似中文）
        hits = [c for c in resolver.resolve_concept(local) if c.kind == "class"]
        viable = [c for c in resolver.viable(hits) if validator.validate(c, "class")[0]]
        return viable[0].iri if viable else None

    if operation == "verify":
        relation = data.get("verify_relation") or "subClassOf"
        if relation not in {"subClassOf", "equivalentClass", "disjointWith",
                            "subPropertyOf", "domainOf", "rangeOf"}:
            return None
        # 规则兜底：问题中的关系词比模型输出更可信
        if any(k in question for k in ("互斥", "同时存在", "矛盾", "能同时")):
            relation = "disjointWith"
        elif "等价" in question:
            relation = "equivalentClass"
        sub = _resolve_class(data.get("verify_subject"))
        obj = _resolve_class(data.get("verify_object"))
        if sub is None or obj is None:
            return None
        intent = {
            "operation": "verify", "subject": sub, "relation": relation,
            "object": obj, "target_concept": question,
            "target_candidates": [],
            "resolution": {"status": _RESOLVED, "method": "llm_deconstruction"},
        }
        return IntentResult(question, _RESOLVED, "verify", intent=intent,
                            candidates=[], used_llm=True,
                            notes=["LLM 语义解析已过白名单校验"])

    target_iri = _resolve_class(data.get("target"))
    entity_label = str(data.get("entity_label") or "").strip()

    entity_anchor = None
    if entity_label:
        ents = resolver.viable(resolver.resolve_entity(entity_label))
        if ents:
            entity_anchor = ents[0]

    filters = _lexicon_filters(question, index)
    notes: list[str] = []

    # 既无类也无实体锚点 → 模型也未识别
    if target_iri is None and entity_anchor is None:
        return None

    # 实体锚点存在时目标语义由锚点链决定（如"魏辉管哪些基金"→Fund），
    # 模型输出的 target 不再覆盖
    anchor_chain = None
    if entity_anchor is not None:
        anchor_chain = _anchor_chain_for(index, entity_anchor)
        if anchor_chain is None:
            return None
        target_iri = _fund_iri(index)
        if anchor_chain is None:
            return None

    intent: dict = {
        "operation": "find",
        "target_concept": question,
        "target_class": target_iri,
        "target_candidates": ([_candidate_json(entity_anchor)] if entity_anchor else []),
        "filters": filters,
        "resolution": {"status": _RESOLVED, "method": "llm_deconstruction"},
    }
    if entity_anchor is not None:
        intent["source"] = entity_anchor.iri
        intent["traversals"] = [
            {"property": str(_prop_iri(index, p)), "inverse": inv}
            for p, inv in anchor_chain
        ]
        notes.append(f"实体锚点：{entity_anchor.label}")
    else:
        # ---- 聚合/排名/计数语义（仅非锚点路径）----
        target_local = target_iri.rsplit("/", 1)[-1]
        _apply_llm_query_semantics(data, intent, target_local, ctx, question, notes)

    # select 白名单
    if intent.get("select") not in (None, "entities", "count"):
        intent.pop("select", None)

    intent["notes"] = notes
    return IntentResult(question, _RESOLVED, "find", intent=intent,
                        candidates=intent["target_candidates"], used_llm=True,
                        notes=notes + ["LLM 语义解析已过白名单校验"])


def _apply_llm_query_semantics(data: dict, intent: dict, target_local: str,
                               ctx: OntologyContext, question: str,
                               notes: list[str]) -> None:
    """把 LLM 输出的 related/relation_path/aggregation/order/limit 校验后写进 intent。

    每步失败只降级（丢弃该语义并记录），不整体否决——LLM 的 target 已经过白名单。
    """
    # ---- related + relation_path ----
    related_term = str(data.get("related") or "").strip()
    related_local = related_term if related_term in ctx.classes else None
    if related_term and related_local is None:
        # 容差：按中文 label 反查
        for info in ctx.classes.values():
            if info.label == related_term:
                related_local = info.local
                break
    if related_local is None and data.get("aggregation"):
        notes.append(f"related 类无法解析（{related_term!r}），聚合语义已降级")

    path: Optional[list[dict]] = None
    raw_path = data.get("relation_path") or []
    if related_local and isinstance(raw_path, list) and raw_path:
        # 校验 LLM 给的路径：属性白名单 + inverse 布尔
        hops = []
        for h in raw_path:
            if not isinstance(h, dict):
                break
            prop_local = str(h.get("property") or "")
            prop = ctx.properties.get(prop_local)
            if prop is None or prop.kind != "object":
                hops = None
                break
            hops.append({"property": prop.iri, "inverse": bool(h.get("inverse"))})
        if hops:
            path = hops
        else:
            notes.append("LLM 关系路径未过属性白名单，改由本体关系图自动发现")
    if related_local and path is None:
        auto = ctx.find_relation_path(target_local, related_local, question=question)
        if auto:
            path = [{"property": h["property"], "inverse": h["inverse"]} for h in auto]
            notes.append(f"关系路径由本体关系图发现：{target_local}→{related_local} "
                         f"{[h['property'].rsplit('/', 1)[-1] for h in path]}")
    if related_local and path:
        intent["related_class"] = ctx.classes[related_local].iri
        intent["relation_path"] = path
    elif related_local:
        notes.append(f"target→{related_local} 无合法关系路径，关联语义已降级")

    # ---- aggregation（需要 relation_path 支撑）----
    agg = data.get("aggregation")
    if isinstance(agg, dict) and agg.get("func") in _AGG_FUNCS and "relation_path" in intent:
        out_agg: dict = {"func": agg["func"]}
        op, val = agg.get("operator"), agg.get("value")
        if op in _CMP_OPS and isinstance(val, (int, float)):
            out_agg.update({"operator": op, "value": val})
        intent["aggregation"] = out_agg
    elif isinstance(agg, dict) and agg.get("func"):
        notes.append("aggregation 缺少合法关系路径支撑，已丢弃")

    # ---- ordering ----
    order_by = data.get("order_by")
    direction = "desc" if data.get("order_direction") == "desc" else "asc"
    if order_by == "agg" and "aggregation" in intent:
        intent["ordering"] = [{"by": "agg", "direction": direction}]
    elif isinstance(order_by, str) and order_by in ctx.properties \
            and ctx.properties[order_by].kind == "datatype":
        ok, reason = ctx.check_property_domain(order_by, target_local)
        if ok:
            intent["ordering"] = [{"by": ctx.properties[order_by].iri,
                                   "direction": direction}]
        else:
            notes.append(f"排序属性被 domain 约束拒绝：{reason}")

    # ---- limit ----
    limit = data.get("limit")
    if isinstance(limit, int) and 1 <= limit <= 1000:
        intent["limit"] = limit
    elif isinstance(limit, float) and 1 <= int(limit) <= 1000:
        intent["limit"] = int(limit)

    # ---- select ----
    if data.get("select") == "count":
        intent["select"] = "count"

    # ---- LLM 提供的 filters（补充 lexicon 之外的显式过滤）----
    # 过滤可落在 target 上，也可落在 relation_path 终点类上（如"医药基金"的
    # investmentFocus 属于 FundInvestmentStrategy，须沿 usesInvestmentStrategy 到达）
    related_end_local = None
    if "related_class" in intent and "relation_path" in intent:
        related_end_local = intent["related_class"].rsplit("/", 1)[-1]
    for f in data.get("filters") or []:
        if not isinstance(f, dict):
            continue
        prop_local = str(f.get("property") or "")
        prop = ctx.properties.get(prop_local)
        if prop is None:
            continue
        on_related = False
        ok, _ = ctx.check_property_domain(prop_local, target_local)
        if not ok and related_end_local:
            ok, _ = ctx.check_property_domain(prop_local, related_end_local)
            on_related = ok
        if not ok:
            notes.append(f"过滤属性被 domain 约束拒绝：{prop_local}")
            continue
        operator = str(f.get("operator") or "eq")
        if operator not in ("eq", "contains", ">=", "<=", ">", "<"):
            operator = "eq"
        entry = {
            "property": prop.iri,
            "operator": operator,
            "value": str(f.get("value") or ""),
            "lexicon_source": "llm",
        }
        if on_related:
            entry["on"] = "related"
            notes.append(f"过滤落在关系路径终点 {related_end_local} 上：{prop_local}")
        intent.setdefault("filters", []).append(entry)


def _chat_completions_url(base_url: str) -> str:
    """兼容两种 .env 写法：base 已含 /chat/completions 端点则直接用，否则自动拼。"""
    base = (base_url or "").rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"
