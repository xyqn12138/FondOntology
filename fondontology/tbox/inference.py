"""T-BOX 推理层：OWL-RL 闭包与推理产物登记（"能推出什么"）。

- compute_closure：对给定图做 owlrl OWLRL_Semantics 闭包
- inferred_triples：inferred = closure − explicit（天然标出"哪些是推出来的"）
- property_chain_axioms：列出 ontology 中声明的 propertyChainAxiom（物化规则用，
  与 Query Path（布路查询）无关，见设计文档 v0.4 §4）
"""
from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF
from owlrl import DeductiveClosure, OWLRL_Semantics


def compute_closure(graph: Graph, *, datatype_axioms: bool = False) -> Graph:
    """对 graph 的副本做 OWL-RL 闭包，返回闭包图（不修改入参）。"""
    closed = Graph()
    for triple in graph:
        closed.add(triple)
    DeductiveClosure(
        OWLRL_Semantics,
        axiomatic_triples=False,
        datatype_axioms=datatype_axioms,
    ).expand(closed)
    return closed


def inferred_triples(graph: Graph, closed: Graph | None = None) -> set[tuple]:
    """推理产物 = closure − explicit（集合差），供 Evidence 标 kind=inference。"""
    if closed is None:
        closed = compute_closure(graph)
    explicit = set(graph)
    return {t for t in closed if t not in explicit}


def property_chain_axioms(graph: Graph) -> list[tuple[URIRef, list[URIRef]]]:
    """propertyChainAxiom：(头属性, [链上属性…])。"""
    chains: list[tuple[URIRef, list[URIRef]]] = []
    for prop in graph.subjects(OWL.propertyChainAxiom, None):
        if not isinstance(prop, URIRef):
            continue
        lst = graph.value(prop, OWL.propertyChainAxiom)
        parts: list[URIRef] = []
        seen = set()
        while lst and lst != RDF.nil and lst not in seen:
            seen.add(lst)
            member = graph.value(lst, RDF.first)
            if isinstance(member, URIRef):
                parts.append(member)
            lst = graph.value(lst, RDF.rest)
        if parts:
            chains.append((prop, parts))
    return chains