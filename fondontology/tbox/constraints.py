"""T-BOX schema 约束层：domain/range/disjoint/restriction 查询（只查声明，不推理）。"""
from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS


def domains(graph: Graph, prop: URIRef) -> set[URIRef]:
    return {d for d in graph.objects(prop, RDFS.domain) if isinstance(d, URIRef)}


def ranges(graph: Graph, prop: URIRef) -> set[URIRef]:
    return {r for r in graph.objects(prop, RDFS.range) if isinstance(r, URIRef)}


def all_disjoint_group_members(graph: Graph) -> list[list[URIRef]]:
    """所有 owl:AllDisjointClasses 组的成员列表。"""
    groups: list[list[URIRef]] = []
    for group in graph.subjects(RDF.type, OWL.AllDisjointClasses):
        members: list[URIRef] = []
        head = graph.value(group, OWL.members)
        seen = set()
        while head and head != RDF.nil and head not in seen:
            seen.add(head)
            member = graph.value(head, RDF.first)
            if isinstance(member, URIRef):
                members.append(member)
            head = graph.value(head, RDF.rest)
        if members:
            groups.append(members)
    return groups


def declared_disjoint(graph: Graph, a: URIRef, b: URIRef) -> bool:
    """是否声明互斥：直接 owl:disjointWith（任一方向）或在同一 AllDisjointClasses 组。

    仅查 T-BOX 声明；不做 OWL 推理（如经由 domain/range 导出的不相交一律不算）。
    """
    if (a, OWL.disjointWith, b) in graph or (b, OWL.disjointWith, a) in graph:
        return True
    for members in all_disjoint_group_members(graph):
        if a in members and b in members:
            return True
    return False


def restrictions(graph: Graph, cls: URIRef) -> list[tuple[URIRef, URIRef, URIRef]]:
    """类上的 OWL restriction 声明（subClassOf 指向 restriction 的三元组）。"""
    return [
        (cls, RDFS.subClassOf, r)
        for r in graph.objects(cls, RDFS.subClassOf)
        if isinstance(r, URIRef) and (r, RDF.type, OWL.Restriction) in graph
    ]