"""ABOX 实例查询与局部子图（M2）。

- execute_find：QueryPlan + DataStack → FindResult（含 explicit/inferred 类型证据、
  执行的 SPARQL 与行数——证据链由 M3 formalize，此处先产出原始证据对象）。
- local_subgraph：焦点实体 hop 邻域子图（nodes/edges），供后续 LLM 上下文（M3）与
  页面渲染使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from .graph import DataStack
from .query_planner import validate_plan
from .sparql_builder import build_select


@dataclass
class FindResult:
    plan: dict
    sparql: str
    count: int
    entities: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)   # entity IRI -> {"kind","via","chain"}
    errors: list[str] = field(default_factory=list)


def _local_name(uri: str) -> str:
    s = uri.rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def execute_find(stack: DataStack, plan: dict,
                 with_abox_inferred: bool = True) -> FindResult:
    """实例检索；默认在推理层启用的查询图上执行（定向物化：property chain +
    逆关系传播，产物可经 stack.inference_registry 归因）。"""
    errors = validate_plan(plan)
    if errors:
        return FindResult(plan, "", 0, errors=errors)

    graph = stack.query_graph(with_abox_inferred=with_abox_inferred)
    sparql = build_select(plan)
    rows = list(graph.query(sparql))
    entities = sorted({str(row[0]) for row in rows})

    target = plan.get("target", {}).get("concept", "")
    result = FindResult(plan=plan, sparql=sparql, count=len(entities),
                        entities=entities)
    for entity in entities:
        result.evidence[entity] = type_evidence(stack, URIRef(entity), URIRef(target))
    return result


def type_evidence(stack: DataStack, entity: URIRef, target: URIRef) -> dict:
    """实体属于 target 的显式/隐式证据。

    - declared：ABOX 中直接声明 rdf:type == target（或声明类型即 target 本身）
    - inference：经 TBOX 子类链到达（声明类型 X，X rdfs:subClassOf+ target）
    - chain：给出第一条可达链（边列表），供 M3 证据 ID 化
    """
    declared = stack.declared_types(entity)
    if target in declared:
        return {"kind": "declared", "via": str(target), "chain": []}
    for cls in sorted(declared, key=str):
        path = _chain_to(stack.tbox, cls, target)
        if path is not None:
            return {"kind": "inference", "via": str(cls),
                    "chain": [{"s": str(a), "p": str(b), "o": str(c)} for a, b, c in path]}
    return {"kind": "unknown_route", "via": "", "chain": []}


def _chain_to(graph: Graph, start: URIRef, end: URIRef) -> Optional[list]:
    """BFS 求 start → end 的 rdfs:subClassOf 链；不存在返回 None。"""
    if start == end:
        return []
    prev: dict[URIRef, tuple[URIRef, URIRef]] = {}
    seen = {start}
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for nxt in graph.objects(cur, RDFS.subClassOf):
            if not isinstance(nxt, URIRef) or nxt in seen:
                continue
            prev[nxt] = (cur, RDFS.subClassOf)
            if nxt == end:
                chain = []
                node = end
                while node in prev:
                    parent, pred = prev[node]
                    chain.append((parent, pred, node))
                    node = parent
                chain.reverse()
                return chain
            seen.add(nxt)
            queue.append(nxt)
    return None


def local_subgraph(graph: Graph, focus: list[URIRef], hop: int = 1,
                   include_literals: bool = True) -> dict:
    """焦点实体 hop 邻域的 nodes/edges（RDF 视图，供局部上下文/渲染）。

    与 Explorer 图 JSON 不同：此处保留完整 IRI 与 rdf:type 语义。
    nodes: {iri, label, types[]}；edges: {s,p,o}（URI-URI）；literal 边并入
    nodes[].properties（含中文 label 优先）。
    """
    focus_set = set(focus)
    boundary = set(focus_set)
    for _ in range(hop):
        boundary |= {
            o for s in boundary for o in graph.objects(URIRef(s) if isinstance(s, str) else s, None)
            if isinstance(o, URIRef)
        }
        # 入边（保证 hop=1 语义完整）
        for node in list(boundary):
            n = URIRef(node) if isinstance(node, str) else node
            boundary |= {s for s in graph.subjects(None, n) if isinstance(s, URIRef)}

    nodes: dict[str, dict] = {}
    for uri in sorted(str(u) for u in boundary):
        u = URIRef(uri)
        types = sorted({str(t) for t in graph.objects(u, RDF.type)})
        label = ""
        for o in graph.objects(u, RDFS.label):
            if getattr(o, "language", None) == "zh":
                label = str(o)
                break
        else:
            for o in graph.objects(u, RDFS.label):
                label = str(o)
                break
        node = {"iri": uri, "label": label or _local_name(uri), "types": types,
                "properties": {}}
        if include_literals and uri in {str(f) for f in focus_set}:
            for p, o in graph.predicate_objects(u):
                if isinstance(o, Literal):
                    node["properties"][_local_name(str(p))] = str(o)
        nodes[uri] = node

    edges = []
    for s in boundary:
        su = URIRef(s) if isinstance(s, str) else s
        for p, o in graph.predicate_objects(su):
            if p == RDF.type or not isinstance(o, URIRef):
                continue
            if str(o) in nodes:
                edges.append({"s": str(su), "p": str(p), "o": str(o)})
    return {"nodes": nodes, "edges": edges}