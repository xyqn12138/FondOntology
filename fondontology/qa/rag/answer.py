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


def answer_regulation(question: str, intent: dict, ctx: OntologyContext,
                      query_graph: Graph, *,
                      store: Optional[ChunkStore] = None) -> ExplainAnswer:
    """regulation 语义 → 检索法规条文（答案=条文原文+引用）。

    相关度两步走（R3c）：
    1) 图边缩小范围：主题类的实例经 governedByRegulation 关联的法规集合
       （货币基金→JL-001/002/005），条文 chunk 只在该集合内检索——
       排除与主题无关的条文（如私募办法对公募货币基金不适用）；
    2) 范围内 BM25 排序。
    图边缺失时退化为全量条文检索（不阻断）。
    """
    store = store or get_store()
    topic = intent.get("topic")
    topic_label = ""
    scope_reg_uris: set[str] | None = None
    if topic:
        topic_local = topic.rsplit("/", 1)[-1]
        info = ctx.classes.get(topic_local)
        topic_label = info.label if info else topic_local
        # 图边缩小：该类任一实例 governedByRegulation 的法规集合
        reg_uris: set[str] = set()
        from rdflib import RDF as _RDF
        for fund in query_graph.subjects(_RDF.type, URIRef(topic)):
            for reg in query_graph.objects(fund, CNFO.governedByRegulation):
                reg_uris.add(str(reg))
        if reg_uris:
            scope_reg_uris = reg_uris

    articles = store.chunks_by_doc_type("regulation_article")
    if not articles:
        return _unresolved(question, "法规条文索引未构建")

    # 条文 chunk → 法规 IRI 映射（cnfo-sim-reports.ttl 的 articleOf 边）
    reg_by_article: dict[str, str] = {}
    if scope_reg_uris is not None:
        from pathlib import Path as _P
        reports_g = Graph()
        rp = _P("artifacts/cnfo/abox/cnfo-sim-reports.ttl")
        if rp.is_file():
            reports_g.parse(str(rp), format="turtle")
            for art in reports_g.subjects(CNFO.articleOf, None):
                reg = reports_g.value(art, CNFO.articleOf)
                if reg is not None:
                    reg_by_article[str(art).rsplit("/", 1)[-1]] = str(reg)
        scoped = [c for c in articles
                  if reg_by_article.get(c.locator.get("entity", ""), None) in scope_reg_uris]
        articles = scoped or articles   # 范围空命中时退化为全量（不静默空白）

    # 范围内 BM25：主题词 + 监管语义词联合查询。
    # 注意不用问句原文——问句里的泛化词（"基金"）会让所有条文同分
    # （模拟数据中每只基金 governedByRegulation 全部法规，图边当前无
    # 区分度；真实数据中该边分化后图过滤自然生效）
    query_text = f"{topic_label} 投资 运作 限制 比例"
    hits = store.bm25_search(query_text, k=10)
    article_ids = {c.chunk_id for c in articles}
    ranked = [c for c, _ in hits if c.chunk_id in article_ids]
    if not ranked:
        ranked = articles[:3]   # 查询词零命中时按 chunk 序兜底
    if not ranked:
        return _unresolved(question, f"未找到与「{topic_label}」相关的法规条文")

    lines: list[str] = []
    evidence: list[dict] = []
    claims: list[dict] = []
    for i, chunk in enumerate(ranked[:3], 1):
        eid = f"R{i}"
        evidence.append(_document_evidence(i, chunk))
        claims.append({"claim_id": f"C{i}", "type": "fact",
                       "claim": f"（{chunk.section}）{chunk.text}",
                       "evidence": [eid]})
        lines.append(f"（{chunk.section}）{chunk.text} [{eid}]")
    report = {
        "meta": {"reasoning": {"profile": "regulation_retrieval",
                               "inference_enabled": False,
                               "query_graph": "法规条文 chunk 池（BM25）"}},
        "evidence": evidence, "claims": claims, "unresolved": [],
    }
    return ExplainAnswer(status="ok", text="\n".join(lines), report=report)


def answer_code(question: str, intent: dict, ctx: OntologyContext,
                query_graph: Graph, *,
                store: Optional[ChunkStore] = None) -> ExplainAnswer:
    """code 语义 → 代码概念解释（图指针优先：articleCitesCode → 条文正文）。

    「R4是什么意思」：R4 是 cnfc 代码概念；适当性指引第八条 articleCitesCode
    指向 R1-R5 → 答案=条文原文。无指针条文时降级代码表 label。
    """
    from rdflib import Namespace
    CNFC = Namespace("https://ontology.example.cn/cnfo/code/")
    code_local = intent.get("code") or ""
    # 裸代码（R4/C3）按代码表前缀族扩展（cnfc 概念本地名带 scheme 前缀）
    _CODE_FAMILY = (("R", "FundRiskLevel"), ("C", "InvRating"))
    code_iri = None
    if code_local:
        candidates = [code_local]
        for prefix, family in _CODE_FAMILY:
            if code_local.startswith(prefix) and code_local[1:].isdigit():
                candidates.insert(0, family + code_local)
        for local in candidates:
            iri = URIRef(str(CNFC) + local)
            if (iri, None, None) in ctx._g or (iri, None, None) in query_graph:
                code_iri = iri
                break

    lines: list[str] = []
    evidence: list[dict] = []
    claims: list[dict] = []

    # 1) 图指针：条文 articleCitesCode → 代码
    if code_iri is not None:
        # articleCitesCode 在 reports A-BOX；query_graph 若未含 reports 则查 tbox+abox 需外部图
        # 此处经 query_graph 查（engine 传入 stack.query_graph()，含主 A-BOX；
        # reports 图单独加载——指针边在 cnfo-sim-reports.ttl）
        from pathlib import Path as _P
        reports_g = Graph()
        rp = _P("artifacts/cnfo/abox/cnfo-sim-reports.ttl")
        if rp.is_file():
            reports_g.parse(str(rp), format="turtle")
        from rdflib.namespace import RDF as _RDF, RDFS as _RDFS, SKOS as _SKOS
        citing = [a for a in reports_g.subjects(CNFO.articleCitesCode, code_iri)]
        if citing:
            # 取第一条引用条文（模拟数据中 R 系代码仅适当性条文引用）
            art = citing[0]
            number = reports_g.value(art, CNFO.articleNumber)
            text = reports_g.value(art, CNFO.articleText)
            reg = reports_g.value(art, CNFO.articleOf)
            reg_title = query_graph.value(reg, CNFO.regulationTitle) if reg else None
            src = str(reg_title or reg or "")
            evidence.append({
                "id": "R1", "kind": "document",
                "source": [src, str(number or "")], "note": f"{src} {number}",
                "text": str(text or ""), "locator": {"entity": str(art).rsplit("/", 1)[-1]},
                "premises": [], "derived": [],
            })
            claims.append({"claim_id": "C1", "type": "fact",
                           "claim": f"{code_local} 的规范出处（{src} {number}）：{text}",
                           "evidence": ["R1"]})
            label = _code_label(query_graph, code_iri)
            head = f"{label}：" if label else f"{code_local}："
            return ExplainAnswer(
                status="ok",
                text=f"{head}{text} [R1]",
                report={"meta": {"reasoning": {"profile": "code_pointer",
                                               "inference_enabled": False,
                                               "query_graph": "articleCitesCode 图指针 → 条文"}},
                        "evidence": evidence, "claims": claims, "unresolved": []})

    # 2) 降级：代码表 label（cnfc 概念的中文标签，在 T-BOX）
    label = _code_label(ctx._g, code_iri) if code_iri is not None else None
    if label:
        return ExplainAnswer(
            status="ok", text=f"{code_local} 的代码含义：{label}。",
            report={"meta": {"reasoning": {"profile": "code_label",
                                           "inference_enabled": False,
                                           "query_graph": "cnfc 代码表 label"}},
                    "evidence": [{"id": "R1", "kind": "definition",
                                  "source": ["cnfo-fund-codes.ttl", code_local, "prefLabel"],
                                  "note": f"代码概念 {code_local}",
                                  "text": label,
                                  "locator": {"iri": str(code_iri)},
                                  "premises": [], "derived": []}],
                    "claims": [{"claim_id": "C1", "type": "definition",
                                "claim": f"{code_local} 的代码含义：{label}",
                                "evidence": ["R1"]}],
                    "unresolved": []})
    return _unresolved(question, f"代码概念 {code_local} 不在本体代码表中")


def _code_label(graph: Graph, code_iri: URIRef) -> str:
    from rdflib.namespace import RDFS, SKOS
    for pred in (SKOS.prefLabel, RDFS.label):
        for o in graph.objects(code_iri, pred):
            return str(o)
    return ""


def answer_compare_entities(question: str, intent: dict, ctx: OntologyContext,
                            query_graph: Graph, *,
                            store: Optional[ChunkStore] = None) -> ExplainAnswer:
    """compare_entities 语义 → 多实体档案对比（每实体独立锚定检索，合并 report）。

    「云帆中证500和华曦消费升级哪个更推荐买」：
    - 每个实体独立走一级检索（锚定防串台机制复用，各自 scope 隔离）；
    - 每实体取其基金产品概况章节（档案事实：经理/类型/风险等级）；
    - claims 带实体来源标记（「云帆中证500：…」），LLM 表达据此组织对比；
    - factual-only：对比结论只能基于可溯源事实（风险等级/类型差异），
      不做投资建议（系统原则：LLM 不是事实来源，建议含不可溯源的未来判断）。
    """
    store = store or get_store()
    anchors = intent.get("entity_anchors") or []
    if len(anchors) < 2:
        return _unresolved(question, "compare_entities 需要至少两个对象锚点")

    lines: list[str] = []
    evidence: list[dict] = []
    claims: list[dict] = []
    seq = 1
    claim_seq = 1
    for anchor in anchors:
        r = retrieve(question, store=store, ctx=ctx, query_graph=query_graph,
                     entity_iri=anchor["iri"])
        # 档案事实优先取"基金产品概况"章节；无命中退而取首条
        profile = [c for c in r.chunks if c.section == "基金产品概况"] or r.chunks[:1]
        if not profile:
            lines.append(f"（{anchor['label']}）未找到相关文档。")
            continue
        chunk = profile[0]
        eid = f"R{seq}"; seq += 1
        evidence.append(_document_evidence(int(eid[1:]), chunk))
        # claim 带实体来源前缀：表达层与证据面板都能对上"谁的事实"
        sentences = [s for s in chunk.text.split("。") if s.strip()]
        facts = "；".join(sentences[:3])
        cid = f"C{claim_seq}"; claim_seq += 1
        claims.append({"claim_id": cid, "type": "fact",
                       "claim": f"{anchor['label']}：{facts}。",
                       "evidence": [eid]})
        lines.append(f"{anchor['label']}：{facts}。 [{eid}]")

    if not claims:
        return _unresolved(question, "未找到任何对象的档案文本")
    lines.append("（以上为两只基金的可溯源档案事实；投资决策需结合自身风险承受能力，"
                 "本系统不提供投资建议。）")
    report = {
        "meta": {"reasoning": {"profile": "multi_entity_compare",
                               "inference_enabled": False,
                               "query_graph": "多锚点独立检索（scope 隔离）+ 合并证据"}},
        "evidence": evidence, "claims": claims, "unresolved": [],
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
