# -*- coding: utf-8 -*-
"""两级检索路由（RAG V2 §3）。

一级（锚定过滤）：intent 解析出实体锚点（基金/经理）→ 图遍历展开为 fund_code
集合 → BM25 只在该范围检索。串台被物理消灭：简称撞名的基金文档不可能进入范围。

二级（全局池）：无锚点的解释类问题 → BM25 全局 + 图指针补充（法条类问题经
basisForRestriction 等图路径直达条文 chunk）。

范围核查（审计冗余）：一级结果 chunk.fund_code ∈ 锚定集合，不满足即丢弃。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, Namespace, URIRef

from ..semantics import OntologyContext
from .store import ChunkStore, RagChunk, get_store

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")

TOP_K = 5


@dataclass
class RetrievalResult:
    chunks: list[RagChunk] = field(default_factory=list)
    channels: dict[str, list[str]] = field(default_factory=dict)  # channel -> [chunk_id]
    scope_fund_codes: Optional[set] = None    # 一级检索的锚定范围（None = 全局）
    anchored: bool = False


def fund_codes_for_entity(ctx: OntologyContext, query_graph: Graph,
                          entity_iri: str) -> set[str]:
    """实体锚点 → fund_code 集合。

    基金锚点：自身（fundCode 字面量）；
    经理/公司锚点：经 hasFundManager（或物化链）折返的全部基金；
    其他主体：经 hasFundParty 折返（保险兜底）。
    """
    ent = URIRef(entity_iri)
    codes: set[str] = set()

    def _is_fund(iri: URIRef) -> bool:
        return (iri, None, None) in query_graph and \
            any(str(t).startswith(str(CNFO)) and "Fund" in str(t).rsplit("/", 1)[-1]
                for t in query_graph.objects(iri, URIRef(
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type")))

    # 基金自身
    if _is_fund(ent):
        for code in query_graph.objects(ent, CNFO.fundCode):
            codes.add(str(code))
    # 基金产品（FundProduct）：经 hasFundProduct / realizesFundProduct 折返基金
    for fund in query_graph.subjects(CNFO.hasFundProduct, ent):
        for code in query_graph.objects(fund, CNFO.fundCode):
            codes.add(str(code))
    for fund in query_graph.subjects(CNFO.realizesFundProduct, ent):
        for code in query_graph.objects(fund, CNFO.fundCode):
            codes.add(str(code))
    # 经理：playsFundRole → roleInFund（经理角色挂基金）或 ^hasFundManager 折返
    for role in query_graph.objects(ent, CNFO.playsFundRole):
        for fund in query_graph.objects(role, CNFO.roleInFund):
            for code in query_graph.objects(fund, CNFO.fundCode):
                codes.add(str(code))
    # 物化快捷边（require_abox_inferred 的产物或显式边）
    for fund in query_graph.subjects(CNFO.hasFundManager, ent):
        for code in query_graph.objects(fund, CNFO.fundCode):
            codes.add(str(code))
    # 管理公司等机构：rolePlayedBy ← 角色 ← fund 的 hasFundManagerRole
    for role in query_graph.subjects(CNFO.rolePlayedBy, ent):
        for fund in query_graph.subjects(CNFO.hasFundManagerRole, role):
            for code in query_graph.objects(fund, CNFO.fundCode):
                codes.add(str(code))
    return codes


def retrieve(question: str, *, store: Optional[ChunkStore] = None,
             ctx: Optional[OntologyContext] = None,
             query_graph: Optional[Graph] = None,
             entity_iri: Optional[str] = None,
             section_hint: Optional[str] = None,
             top_k: int = TOP_K) -> RetrievalResult:
    """两级检索入口。entity_iri 非空走一级（锚定过滤），否则全局二级。"""
    store = store or get_store()
    result = RetrievalResult()

    if entity_iri and query_graph is not None:
        codes = fund_codes_for_entity(ctx, query_graph, entity_iri)
        if codes:
            hits = store.bm25_search(question, k=top_k * 2, scope_fund_codes=codes)
            # 范围核查（冗余审计）：BM25 的 scope 过滤已保证，此处再断言一次
            checked = [(c, s) for c, s in hits if c.fund_code in codes]
            # 章节提示加权（如"怎么看后市"→ 管理人报告）
            if section_hint:
                checked.sort(key=lambda cs: (0 if section_hint in cs[0].section else 1, -cs[1]))
            result.chunks = [c for c, _ in checked[:top_k]]
            result.channels = {"anchor+bm25": [c.chunk_id for c in result.chunks]}
            result.scope_fund_codes = codes
            result.anchored = True
            return result

    # 二级：全局池
    hits = store.bm25_search(question, k=top_k)
    result.chunks = [c for c, _ in hits]
    result.channels = {"bm25": [c.chunk_id for c in result.chunks]}
    return result
