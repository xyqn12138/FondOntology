"""Ontology Slice Policy：局部本体切片（对查询语义闭合，带硬上限；P2 语义优先级预留）。

设计文档 v0.4 §11：切片不是"空间邻居"而是"对当前查询语义闭合"；
截断不是随便砍，而是按 required concepts → required properties →
required constraints → optional neighborhood 的语义优先级取舍。
本模块提供确定性的 prioritize（P2 概念的可用基础）：先必需后可选，超预算即截断并标记。
"""
from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from ..tbox.taxonomy import ancestors

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")


@dataclass(frozen=True)
class SliceBudget:
    max_classes: int = 32
    max_properties: int = 64
    max_triples: int = 2_000
    max_context_tokens: int = 6_000


def _local(uri: str) -> str:
    s = uri.rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _zh(graph: Graph, uri: URIRef, pred) -> str:
    for o in graph.objects(uri, pred):
        if getattr(o, "language", None) == "zh":
            return str(o)
    return ""


def _label(graph: Graph, uri: URIRef) -> str:
    return (_zh(graph, uri, SKOS.prefLabel) or _zh(graph, uri, RDFS.label)
            or _local(str(uri)))


def _definition(graph: Graph, uri: URIRef) -> str:
    return _zh(graph, uri, SKOS.definition)


def build_ontology_slice(graph: Graph, plan: dict, budget: SliceBudget = SliceBudget()) -> dict:
    """按计划构建 L0-L4 自适应切片（确定性）。

    优先级（§11）：ancestors + target + 计划用属性（required）→ 直接子类与
    domain/range 类（constraints）→ 邻域（optional）。超预算即截断并标记。
    """
    target_uri = URIRef(plan.get("target", {}).get("concept", ""))
    if (target_uri, RDF.type, OWL.Class) not in graph:
        return {"classes": [], "properties": [], "restrictions": [],
                "truncated": True, "levels": 0, "counts": {}}

    used_props: list[URIRef] = []
    for f in plan.get("filters") or []:
        p = URIRef(f.get("property", ""))
        if (p, None, None) in graph:
            used_props.append(p)
    for t in plan.get("traversals") or []:
        p = URIRef(t.get("property", ""))
        if (p, None, None) in graph:
            used_props.append(p)
    for p in plan.get("projections") or []:
        p_uri = URIRef(p)
        if (p_uri, None, None) in graph:
            used_props.append(p_uri)

    # tier0: target + 祖先链（必需）
    tier0 = [target_uri] + sorted(ancestors(graph, target_uri), key=str)
    # tier1: 直接子类（必要宽度）
    direct_children = sorted(
        (s for s in graph.subjects(RDFS.subClassOf, target_uri) if isinstance(s, URIRef)),
        key=str)
    # tier2: 属性 domain/range 类（约束闭合）
    tier2_classes: set[URIRef] = set()
    for p in used_props:
        for d in graph.objects(p, RDFS.domain):
            if isinstance(d, URIRef) and (d, RDF.type, OWL.Class) in graph:
                tier2_classes.add(d)
        for r in graph.objects(p, RDFS.range):
            if isinstance(r, URIRef) and (r, RDF.type, OWL.Class) in graph:
                tier2_classes.add(r)

    classes_ordered: list[tuple[URIRef, int]] = (
        [(u, 0) for u in tier0] + [(u, 1) for u in direct_children]
        + [(u, 2) for u in sorted(tier2_classes, key=str)]
    )
    seen: set[URIRef] = set()
    classes: list[dict] = []
    truncated_classes = False
    for uri, tier in classes_ordered:
        if uri in seen:
            continue
        seen.add(uri)
        if len(classes) >= budget.max_classes:
            truncated_classes = True
            break
        classes.append({
            "iri": str(uri), "local_name": _local(str(uri)),
            "label_zh": _label(graph, uri),
            "definition_zh": _definition(graph, uri),
            "tier": tier,
        })

    # 属性：必需(计划用) + 类上直接声明的对象/数据属性
    used_set = set(used_props)
    for cls in seen:
        for p in set(graph.subjects(RDFS.domain, cls)) | set(graph.subjects(RDFS.range, cls)):
            if isinstance(p, URIRef) and str(p).startswith(str(CNFO)):
                used_set.add(p)
    properties: list[dict] = []
    truncated_props = False
    for p in sorted(used_set, key=str):
        if len(properties) >= budget.max_properties:
            truncated_props = True
            break
        properties.append({
            "iri": str(p), "local_name": _local(str(p)),
            "label_zh": _label(graph, p),
            "domains": [str(d) for d in graph.objects(p, RDFS.domain) if isinstance(d, URIRef)],
            "ranges": [str(r) for r in graph.objects(p, RDFS.range) if isinstance(r, URIRef)],
            "required": p in set(used_props),
        })

    # 约束：类切片上的 OWL restriction 简表（cap 计入总三元组预算）
    restrictions: list[dict] = []
    remaining = budget.max_triples - (len(classes) + len(properties))
    for cls in seen:
        if remaining <= 0:
            break
        for r in graph.objects(cls, RDFS.subClassOf):
            if not isinstance(r, URIRef) or (r, RDF.type, OWL.Restriction) not in graph:
                continue
            if remaining <= 0:
                break
            prop = graph.value(r, OWL.onProperty)
            restrictions.append({
                "class": str(cls),
                "restriction": str(r),
                "on_property": str(prop) if prop else "",
                "some_values_from": str(graph.value(r, OWL.someValuesFrom) or ""),
            })
            remaining -= 1

    return {
        "classes": classes,
        "properties": properties,
        "restrictions": restrictions,
        "truncated": truncated_classes or truncated_props,
        "levels": 4 if any(t["tier"] >= 2 for t in classes) else (1 if any(t["tier"] == 1 for t in classes) else 0),
        "counts": {"classes": len(classes), "properties": len(properties),
                   "restrictions": len(restrictions), "used_props": len(used_props)},
    }


def assemble_local_context(report: dict, slice_: dict) -> dict:
    """局部上下文 = 本体切片 + 证据摘要 + 子图（供模板/M4-LLM）。"""
    return {
        "ontology_slice": slice_,
        "evidence_summary": {
            "total": len(report.get("evidence", [])),
            "query": [e for e in report.get("evidence", []) if e.get("kind") == "query"][:1],
            "claims": report.get("claims", []),
        },
        "subgraph": report.get("subgraph", {}),
        "meta": report.get("meta", {}),
    }