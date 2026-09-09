# -*- coding: utf-8 -*-
"""explain 问题生成（R2：确定性模板，LLM 表达接入是 R3）。

三种 explain_type：
- define   「什么是X」→ T-BOX 定义卡（类 label + skos:definition + 层级）
- describe 「介绍一下X」「X怎么看后市」→ 实体档案（一级检索的章节 chunk）
- compare  「X和Y的区别」→ 两侧定义卡 + 图上互斥判定（无声明时明确说明）

证据合同扩展：kind=document 的证据带 text 与 locator（E# 之外的 R# 系列）；
claim 句级引用 R#，复用现有 validate_citations / evidence_completeness 校验器。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from ..semantics import OntologyContext
from .retrieve import RetrievalResult, retrieve
from .store import ChunkStore, get_store

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")


@dataclass
class ExplainAnswer:
    status: str                        # ok | unresolved
    text: str
    report: Optional[dict] = None      # 与 find/verify 同构的证据合同


def _zh_label(graph: Graph, uri: URIRef) -> str:
    for pred in (SKOS.prefLabel, RDFS.label):
        for o in graph.objects(uri, pred):
            if getattr(o, "language", None) == "zh":
                return str(o)
    for o in graph.objects(uri, RDFS.label):
        return str(o)
    return str(uri).rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _definition_card(tbox: Graph, class_iri: URIRef) -> dict:
    """T-BOX 定义卡：label/定义/直接父类（中文）——define/compare 的语料。"""
    card = {"iri": str(class_iri), "label": _zh_label(tbox, class_iri),
            "definition": "", "parents": [], "children": []}
    for o in tbox.objects(class_iri, SKOS.definition):
        card["definition"] = str(o)
        break
    if not card["definition"]:
        for o in tbox.objects(class_iri, RDFS.comment):
            card["definition"] = str(o)
            break
    for p in tbox.objects(class_iri, RDFS.subClassOf):
        if isinstance(p, URIRef):
            card["parents"].append(_zh_label(tbox, p))
    for c in tbox.subjects(RDFS.subClassOf, class_iri):
        if isinstance(c, URIRef):
            card["children"].append(_zh_label(tbox, c))
    return card


def _document_evidence(seq: int, chunk) -> dict:
    return {
        "id": f"R{seq}", "kind": "document",
        "source": [chunk.doc_id, chunk.section],
        "note": f"{chunk.doc_id} · {chunk.section}",
        "text": chunk.text,
        "locator": chunk.locator,
        "premises": [], "derived": [],
    }


def _class_evidence(seq: int, card: dict) -> dict:
    return {
        "id": f"R{seq}", "kind": "definition",
        "source": ["cnfo-fund-tbox.ttl", card["iri"].rsplit("/", 1)[-1], "definition"],
        "note": f"本体定义卡：{card['label']}",
        "text": card["definition"] or "（本类暂无中文定义）",
        "locator": {"iri": card["iri"]},
        "premises": [], "derived": [],
    }


def answer_explain(question: str, intent: dict, ctx: OntologyContext,
                   query_graph: Graph, *,
                   store: Optional[ChunkStore] = None) -> ExplainAnswer:
    """explain 语义 → 答案（模板路径）。

    intent 形态：{"operation": "explain", "explain_type": "define|describe|compare",
                 "topic": <类IRI>，"compare_topic": <类IRI>，"entity_iri": <实体IRI>}
    """
    store = store or get_store()
    tbox = ctx._g   # OntologyContext 持有的 T-BOX 图（类层级/定义/互斥公理）
    explain_type = intent.get("explain_type") or "define"
    lines: list[str] = []
    evidence: list[dict] = []
    claims: list[dict] = []
    seq = 1          # evidence R# 序号
    claim_seq = 1    # claim C# 序号（与 R# 各自独立计数）

    def emit_claim(text: str, eids: list[str]) -> None:
        nonlocal claim_seq
        cid = f"C{claim_seq}"
        claim_seq += 1
        claims.append({"claim_id": cid, "type": "definition" if explain_type == "define"
                       else "fact", "claim": text, "evidence": eids})
        lines.append(f"{text} [{' '.join(eids)}]")

    if explain_type == "define":
        topic = intent.get("topic")
        if not topic:
            return _unresolved(question, "define 未指定主题类")
        card = _definition_card(tbox, URIRef(topic))
        eid = f"R{seq}"; seq += 1
        evidence.append(_class_evidence(int(eid[1:]), card))
        emit_claim(f"「{card['label']}」的定义：{card['definition'] or '本体未收录定义'}", [eid])
        if card["parents"]:
            parents = "、".join(card["parents"])
            emit_claim(f"其直接父类为：{parents}。", [eid])
        if card["children"]:
            children = "、".join(card["children"][:8])
            emit_claim(f"其直接子类包括：{children}。", [eid])
        # 补充：该类的实例若有季报文本，追加提示（不做事实性陈述）
        return _assemble(question, lines, evidence, claims)

    if explain_type == "compare":
        t1, t2 = intent.get("topic"), intent.get("compare_topic")
        if not (t1 and t2):
            return _unresolved(question, "compare 未指定两个比较类")
        c1, c2 = _definition_card(tbox, URIRef(t1)), _definition_card(tbox, URIRef(t2))
        for card in (c1, c2):
            eid = f"R{seq}"; seq += 1
            evidence.append(_class_evidence(int(eid[1:]), card))
            emit_claim(f"「{card['label']}」的定义：{card['definition'] or '本体未收录定义'}", [eid])
        # 图上互斥判定（verify 复用；无声明时如实说明，禁止推断性对比）
        a, b = URIRef(t1), URIRef(t2)
        disjoint = False
        for s, p, o in tbox.triples((None, OWL.AllDisjointClasses, None)):
            members = list(tbox.objects(o, URIRef(
                "http://www.w3.org/2002/07/owl#members")))
            for m in members:
                items = {str(x) for x in tbox.items(m)}
                if str(a) in items and str(b) in items:
                    disjoint = True
        if disjoint:
            emit_claim(f"本体声明「{c1['label']}」与「{c2['label']}」互斥"
                       "（AllDisjointClasses），二者不能同时成立。", [evidence[0]["id"], evidence[1]["id"]])
        else:
            lines.append("（本体未声明两者互斥；以上为各自定义，差异见定义内容。）")
        return _assemble(question, lines, evidence, claims)

    # describe：实体档案（一级检索）或全局池（二级）
    entity_iri = intent.get("entity_iri")
    retrieval: RetrievalResult = retrieve(
        question, store=store, ctx=ctx, query_graph=query_graph,
        entity_iri=entity_iri,
        section_hint=intent.get("section_hint"))
    if not retrieval.chunks:
        return _unresolved(
            question,
            "文档索引未构建或无相关文本" if not store.chunks else "未找到相关文档")
    for chunk in retrieval.chunks[:TOP_K_LOCAL]:
        eid = f"R{seq}"; seq += 1
        evidence.append(_document_evidence(int(eid[1:]), chunk))
        # 每个 chunk 一条 claim：引用章节名 + 正文首句（正文可全文展开于证据面板）
        first_sentence = chunk.text.split("。")[0] + ("。" if "。" in chunk.text else "")
        emit_claim(f"（{chunk.section}）{first_sentence}", [eid])
    return _assemble(question, lines, evidence, claims)


TOP_K_LOCAL = 3


def answer_classify(question: str, intent: dict, ctx: OntologyContext) -> ExplainAnswer:
    """classify 语义 → 枚举类层级（schema 级问题，答案是类清单）。

    「基金有哪些分类」→ Fund 的直接子类，每个子类一条定义 claim（T-BOX 定义卡）。
    与 RAG 开关无关：T-BOX 是图的固定部分，classify 是本体问答的一等能力。
    """
    tbox = ctx._g
    topic = intent.get("topic")
    if not topic:
        return _unresolved(question, "classify 未指定主题类")
    topic_local = topic.rsplit("/", 1)[-1]
    info = ctx.classes.get(topic_local)
    if info is None:
        return _unresolved(question, f"未知类 {topic_local}")
    children = [ctx.classes[c] for c in info.children if c in ctx.classes]
    if not children:
        return ExplainAnswer(
            status="ok",
            text=f"本体中「{info.label}」未声明直接子类，暂无分类维度可枚举。")

    lines: list[str] = []
    evidence: list[dict] = []
    claims: list[dict] = []
    lines.append(f"本体将「{info.label}」划分为 {len(children)} 个直接子类（分类维度）：")
    for i, child in enumerate(children, 1):
        eid = f"R{i}"
        card = _definition_card(tbox, URIRef(child.iri))
        evidence.append(_class_evidence(i, card))
        claims.append({"claim_id": f"C{i}", "type": "classification",
                       "claim": f"{card['label']}：{card['definition'] or '（本类暂无中文定义）'}",
                       "evidence": [eid]})
        lines.append(f"{i}. {card['label']}——{card['definition'] or '（本类暂无中文定义）'} [{eid}]")
    report = {
        "meta": {"reasoning": {"profile": "tbox_hierarchy", "inference_enabled": False,
                               "query_graph": "T-BOX 类层级（rdfs:subClassOf 直接子类）"}},
        "evidence": evidence,
        "claims": claims,
        "unresolved": [],
    }
    return ExplainAnswer(status="ok", text="\n".join(lines), report=report)


def _unresolved(question: str, note: str) -> ExplainAnswer:
    return ExplainAnswer(status="unresolved",
                         text=f"未能回答该解释类问题（{note}）。")


def _assemble(question: str, lines: list[str], evidence: list[dict],
              claims: list[dict]) -> ExplainAnswer:
    report = {
        "meta": {"reasoning": {"profile": "template", "inference_enabled": False,
                               "query_graph": "T-BOX 定义卡 + 文本 chunk 池"}},
        "evidence": evidence,
        "claims": claims,
        "unresolved": [],
    }
    return ExplainAnswer(status="ok", text="\n".join(lines), report=report)
