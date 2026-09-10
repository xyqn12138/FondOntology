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
    """两级检索入口。entity_iri 非空走一级（锚定过滤），否则全局二级。

    R4 融合链：三路加权 RRF 粗排（锚定/dense/BM25）→ rerank 语义精排。
    精排让位规则（确定性信号优先于模型分数）：
    - section_hint 场景（"怎么看后市"→管理人报告）不 rerank；
    - 法规条文候选 ≤5 条时不 rerank（小集合精排收益低于一次网络往返）。
    降级：向量/rerank 任一不可用自动跳过，不阻断。
    """
    store = store or get_store()
    result = RetrievalResult()

    # 预取 dense 排名（两级共用）
    dense_rank: dict[str, int] = {}
    vidx = _vector_index_if_ready()
    if vidx is not None:
        from .embedder import embed_texts
        qv = embed_texts([question])
        if qv:
            for rank, (cid, _score) in enumerate(vidx.search(qv[0], k=20), 1):
                dense_rank[cid] = rank

    if entity_iri and query_graph is not None:
        codes = fund_codes_for_entity(ctx, query_graph, entity_iri)
        if codes:
            hits = store.bm25_search(question, k=top_k * 2, scope_fund_codes=codes)
            # 范围核查（冗余审计）：BM25 的 scope 过滤已保证，此处再断言一次
            checked = [(c, s) for c, s in hits if c.fund_code in codes]
            # 章节提示（"怎么看后市"→管理人报告）是确定性强信号：
            # 优先级高于 RRF/rerank，直接排序截断
            if section_hint:
                checked.sort(key=lambda cs: (0 if section_hint in cs[0].section else 1, -cs[1]))
                result.chunks = [c for c, _ in checked[:top_k]]
            else:
                # RRF 粗排（锚定/dense/BM25）→ rerank 精排
                coarse = _rrf_select(
                    anchor_ids=[c.chunk_id for c, _ in checked],
                    bm25_ranked=[(c.chunk_id, s) for c, s in checked],
                    dense_rank={cid: r for cid, r in dense_rank.items()
                                if any(cid == c.chunk_id for c, _ in checked)},
                    store=store, top_k=top_k * 2)
                result.chunks = _maybe_rerank(question, coarse, top_k)
            result.channels = {_channel_name(dense_rank):
                               [c.chunk_id for c in result.chunks]}
            result.scope_fund_codes = codes
            result.anchored = True
            return result

    # 二级：全局池（BM25 + dense RRF → rerank）
    hits = store.bm25_search(question, k=top_k * 2)
    if dense_rank:
        coarse = _rrf_select(anchor_ids=[],
                             bm25_ranked=[(c.chunk_id, s) for c, s in hits],
                             dense_rank=dense_rank, store=store, top_k=top_k * 2)
        result.chunks = _maybe_rerank(question, coarse, top_k)
    else:
        result.chunks = [c for c, _ in hits[:top_k]]
    result.channels = {_channel_name(dense_rank):
                       [c.chunk_id for c in result.chunks]}
    return result


def _channel_name(dense_rank: dict) -> str:
    name = "bm25" if not dense_rank else "bm25+dense"
    from ..config import rerank_configured
    if rerank_configured():
        name += "+rerank"
    return name


def _maybe_rerank(question: str, coarse: list, top_k: int) -> list:
    """rerank 精排；小集合/失败/未配置时保持 RRF 序。

    法规条文小集合（≤5）精排收益低于一次网络往返，跳过。
    """
    if len(coarse) <= 5:
        return coarse[:top_k]
    scored = _rerank_call(question, [c.text for c in coarse], top_k=top_k)
    if not scored:
        return coarse[:top_k]   # 失败/未配置：保持 RRF 序
    return [coarse[idx] for idx, _s in scored if idx < len(coarse)]


def _rerank_call(question: str, documents: list[str], top_k: int):
    """rerank 服务调用的可注入间接层（测试 mock 用）。"""
    from .reranker import rerank
    return rerank(question, documents, top_k=top_k)


def _vector_index_if_ready():
    """向量索引惰性加载（未配置/文件缺失返回 None，调用方 BM25-only）。"""
    try:
        from .embedder import get_vector_index
        return get_vector_index()
    except Exception:
        return None


def _rrf_select(anchor_ids: list[str], bm25_ranked: list[tuple[str, float]],
                dense_rank: dict[str, int], store: ChunkStore,
                top_k: int, k: int = 60) -> list[RagChunk]:
    """RRF 融合：score = Σ w·1/(k+rank)。

    权重：锚定 2.5（强先验——锚定命中范围是防串台的物理保证，任何
    词法/向量分数不得挤掉锚定 chunk）；dense 1.2（语义改写场景价值最高，
    实测「经理对未来市场怎么看」BM25 全错 dense 全对）；BM25 0.8（模拟
    语料章节文本同质化会系统性抬高词频分）。
    """
    scores: dict[str, float] = {}
    for cid in anchor_ids:
        scores[cid] = scores.get(cid, 0.0) + 2.5 / (k + 1)
    for rank, (cid, _s) in enumerate(bm25_ranked, 1):
        scores[cid] = scores.get(cid, 0.0) + 0.8 / (k + rank)
    for cid, rank in dense_rank.items():
        scores[cid] = scores.get(cid, 0.0) + 1.2 / (k + rank)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [store.by_id[cid] for cid, _ in ranked if cid in store.by_id]
