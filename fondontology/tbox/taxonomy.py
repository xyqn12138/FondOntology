"""T-BOX 分类学层：子类/子属性闭包与判链（确定性，不做 OWL 推理）。

全部操作基于 rdfs:subClassOf / rdfs:subPropertyOf 的传递闭包（SPARQL 属性路径
语义）。本层不处理 domain/range/restriction/disjoint（见 constraints.py），
不处理 propertyChainAxiom 的物化（见 inference.py）。
"""
from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDFS

Edge = tuple[URIRef, URIRef, URIRef]  # (s, p, o)


def descendants(graph: Graph, cls: URIRef, include_self: bool = False) -> set[URIRef]:
    """rdfs:subClassOf+ 后代（若 include_self 则含自身）。"""
    result: set[URIRef] = {cls} if include_self else set()
    result.update(o for o in graph.transitive_objects(cls, RDFS.subClassOf)
                  if isinstance(o, URIRef))
    return result


def ancestors(graph: Graph, cls: URIRef) -> set[URIRef]:
    """rdfs:subClassOf+ 祖先。"""
    return {s for s in graph.transitive_subjects(RDFS.subClassOf, cls)
            if isinstance(s, URIRef)}


def subproperty_path(graph: Graph, sub: URIRef, sup: URIRef) -> bool:
    """strict 子属性链：sub rdfs:subPropertyOf+ sup"""
    return sup in {o for o in graph.transitive_objects(sub, RDFS.subPropertyOf)
                   if isinstance(o, URIRef)}


def find_subclass_path(graph: Graph, sub: URIRef, sup: URIRef) -> list[Edge] | None:
    """BFS 求一条 sub → sup 的子类链（边列表）；不存在返回 None。

    与 rdfs:subClassOf+ 语义一致（严格链，不含自身）。
    """
    if sub == sup:
        return None
    prev: dict[URIRef, tuple[URIRef, URIRef]] = {}
    seen = {sub}
    queue = [sub]
    while queue:
        cur = queue.pop(0)
        for nxt in graph.objects(cur, RDFS.subClassOf):
            if not isinstance(nxt, URIRef) or nxt in seen:
                continue
            prev[nxt] = (cur, RDFS.subClassOf)
            if nxt == sup:
                # 回溯构造链
                chain: list[Edge] = []
                node: URIRef = sup
                while node in prev:
                    parent, pred = prev[node]
                    chain.append((parent, pred, node))
                    node = parent
                chain.reverse()
                return chain
            seen.add(nxt)
            queue.append(nxt)
    return None


def find_subproperty_path(graph: Graph, sub: URIRef, sup: URIRef) -> list[Edge] | None:
    """BFS 求一条 sub → sup 的子属性链；不存在返回 None。"""
    if sub == sup:
        return None
    prev: dict[URIRef, tuple[URIRef, URIRef]] = {}
    seen = {sub}
    queue = [sub]
    while queue:
        cur = queue.pop(0)
        for nxt in graph.objects(cur, RDFS.subPropertyOf):
            if not isinstance(nxt, URIRef) or nxt in seen:
                continue
            prev[nxt] = (cur, RDFS.subPropertyOf)
            if nxt == sup:
                chain: list[Edge] = []
                node: URIRef = sup
                while node in prev:
                    parent, pred = prev[node]
                    chain.append((parent, pred, node))
                    node = parent
                chain.reverse()
                return chain
            seen.add(nxt)
            queue.append(nxt)
    return None


def equivalents(graph: Graph, cls: URIRef) -> set[URIRef]:
    """owl:equivalentClass 双向声明（仅声明，不做推理）。"""
    result = {o for o in graph.objects(cls, OWL.equivalentClass) if isinstance(o, URIRef)}
    result |= {s for s in graph.subjects(OWL.equivalentClass, cls) if isinstance(s, URIRef)}
    return result