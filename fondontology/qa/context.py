"""Ontology Slice Policy：局部本体切片（对查询语义闭合，带硬上限；P2 语义优先级预留）。

设计文档 v0.4 §11：切片不是"空间邻居"而是"对当前查询语义闭合"；
截断不是随便砍，而是按 required concepts → required properties →
required constraints → optional neighborhood 的语义优先级取舍。
本模块提供确定性的 prioritize（P2 概念的可用基础）：先必需后可选，超预算即截断并标记。
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from ..tbox.taxonomy import ancestors
from .schema_retriever import estimate_token_count
from .owl_expression import (canonical_graph, expression_ast, expression_text,
                             is_expression_node)


@dataclass(frozen=True)
class SliceBudget:
    max_classes: int = 32
    max_properties: int = 64
    max_triples: int = 2_000
    max_context_tokens: int = 6_000


@dataclass(frozen=True)
class SemanticPacket:
    triples: frozenset
    kind: str
    name: str
    required: bool = False


def _local(uri: str) -> str:
    s = uri.rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _zh(graph: Graph, uri: URIRef, pred) -> str:
    values = sorted(str(o) for o in graph.objects(uri, pred)
                    if getattr(o, "language", None) == "zh")
    return values[0] if values else ""


def _label(graph: Graph, uri: URIRef) -> str:
    return (_zh(graph, uri, SKOS.prefLabel) or _zh(graph, uri, RDFS.label)
            or _local(str(uri)))


def _definition(graph: Graph, uri: URIRef) -> str:
    return _zh(graph, uri, SKOS.definition)


def build_ontology_slice(graph: Graph, plan: dict, budget: SliceBudget = SliceBudget()) -> dict:
    """Select dependency-closed packets; never exceed a configured output budget."""
    graph = canonical_graph(graph)
    required, sources, paths, explicit_classes = _plan_dependencies(plan)
    target = URIRef((plan.get("target") or {}).get("concept", ""))
    selected = Graph()
    dropped = {"classes": [], "properties": [], "restrictions": [], "axioms": []}
    missing = []
    not_found = []
    facets = {
        OWL.someValuesFrom: "some_values_from", OWL.allValuesFrom: "all_values_from",
        OWL.hasValue: "has_value", OWL.cardinality: "cardinality",
        OWL.minCardinality: "min_cardinality", OWL.maxCardinality: "max_cardinality",
        OWL.qualifiedCardinality: "qualified_cardinality",
        OWL.minQualifiedCardinality: "min_qualified_cardinality",
        OWL.maxQualifiedCardinality: "max_qualified_cardinality",
        OWL.onClass: "on_class", OWL.onDataRange: "on_data_range",
    }

    def is_class(uri):
        return isinstance(uri, URIRef) and (uri, RDF.type, OWL.Class) in graph

    def is_property(uri):
        return any((uri, RDF.type, t) in graph
                   for t in (OWL.ObjectProperty, OWL.DatatypeProperty))

    def describe(g):
        classes = [{
            "iri": str(u), "local_name": _local(str(u)), "label_zh": _label(g, u),
            "definition_zh": _definition(g, u), "tier": 0 if u == target else 2,
            "parents": sorted(str(p) for p in g.objects(u, RDFS.subClassOf)
                              if isinstance(p, URIRef)
                              and (p, RDF.type, OWL.Restriction) not in g),
        } for u in sorted(set(g.subjects(RDF.type, OWL.Class)), key=str)
            if isinstance(u, URIRef)]
        properties = [{
            "iri": str(u), "local_name": _local(str(u)), "label_zh": _label(g, u),
            "domains": sorted(expression_text(g, d) for d in g.objects(u, RDFS.domain)),
            "ranges": sorted(expression_text(g, r) for r in g.objects(u, RDFS.range)),
            "required": str(u) in required,
            "dependency_sources": sorted(sources.get(str(u), [])),
        } for u in sorted(set(g.subjects(RDF.type, OWL.ObjectProperty)) |
                          set(g.subjects(RDF.type, OWL.DatatypeProperty)), key=str)]
        restrictions = []
        expressions = []
        for cls in sorted(set(g.subjects(RDF.type, OWL.Class)), key=str):
            for predicate in (RDFS.subClassOf, OWL.equivalentClass):
                for root in sorted(g.objects(cls, predicate), key=str):
                    if not is_expression_node(g, root):
                        continue
                    expressions.append({"class": str(cls), "predicate": str(predicate),
                                        "expression": expression_ast(g, root)})
                    pending, visited = [root], set()
                    while pending:
                        r = pending.pop()
                        if r in visited:
                            continue
                        visited.add(r)
                        pending.extend(o for o in g.objects(r)
                                       if isinstance(o, BNode) or is_expression_node(g, o))
                        if not ((r, RDF.type, OWL.Restriction) in g):
                            continue
                        row = {"class": str(cls), "restriction": str(r),
                               "on_property": str(g.value(r, OWL.onProperty) or ""),
                               "source": "declared", "class_predicate": str(predicate)}
                        for pred, key in facets.items():
                            value = g.value(r, pred)
                            if value is not None:
                                row[key] = expression_text(g, value)
                        restrictions.append(row)
        for root in sorted({s for s in g.subjects() if isinstance(s, URIRef)
                            and is_expression_node(g, s)}, key=str):
            ast = expression_ast(g, root)
            if not any(item["expression"] == ast for item in expressions):
                expressions.append({"class": str(root), "predicate": "owl:expression",
                                    "expression": ast})
        axioms = []
        for predicate, kind in ((OWL.inverseOf, "inverse_of"),
                                (RDFS.subPropertyOf, "sub_property_of"),
                                (OWL.propertyChainAxiom, "property_chain"),
                                (OWL.disjointWith, "disjoint_with"),
                                (OWL.equivalentClass, "equivalent_class")):
            for s, o in sorted(g.subject_objects(predicate), key=lambda t: tuple(map(str, t))):
                row = {"subject": str(s), "kind": kind, "object": expression_text(g, o),
                       "source": "declared"}
                if predicate == OWL.propertyChainAxiom:
                    row["members"] = [str(v) for v in g.items(o)]
                axioms.append(row)
        lines = [f"{c['local_name']}({c['label_zh']})" for c in classes]
        lines += [f"{p['local_name']}({p['label_zh']})："
                  f"{','.join(_local(u) for u in p['domains'])} -> "
                  f"{','.join(_local(u) for u in p['ranges'])}" for p in properties]
        lines += [f"{_local(r['class'])} restriction "
                  + " ".join(f"{k}={v}" for k, v in r.items()
                             if k not in ("class", "restriction", "source", "class_predicate"))
                  for r in restrictions]
        lines += [f"{_local(a['subject'])} {a['kind']} "
                  + (" -> ".join(_local(v) for v in a["members"]) if "members" in a
                     else _local(a["object"])) for a in axioms]
        # Composite expression structure is meaningful beyond its restriction leaves.
        lines += [f"{_local(e['class'])} expression "
                  + json.dumps(e["expression"], ensure_ascii=False, sort_keys=True)
                  for e in expressions if e["expression"].get("kind") != "restriction"]
        return classes, properties, restrictions, axioms, "\n".join(lines), expressions

    def class_packet(uri):
        packet = set()
        if not is_class(uri):
            return packet
        family = {uri} | {a for a in ancestors(graph, uri) if is_class(a)}
        for u in family:
            packet.add((u, RDF.type, OWL.Class))
            for pred in (RDFS.label, SKOS.prefLabel, SKOS.definition):
                packet.update(graph.triples((u, pred, None)))
            packet.update((u, RDFS.subClassOf, p) for p in graph.objects(u, RDFS.subClassOf)
                          if p in family)
        return packet

    def property_packet(uri, visited=None):
        packet = set()
        visited = set() if visited is None else visited
        if uri in visited or not is_property(uri):
            return packet
        visited = visited | {uri}
        for pred in (RDF.type, RDFS.label, SKOS.prefLabel, RDFS.domain, RDFS.range):
            for triple in graph.triples((uri, pred, None)):
                if isinstance(triple[2], BNode) or is_expression_node(graph, triple[2]):
                    packet.add(triple)
                    packet.update(expression_packet(triple[2], visited))
                    continue
                packet.add(triple)
                if pred in (RDFS.domain, RDFS.range):
                    packet.update(class_packet(triple[2]))
        return packet

    def accept(packet, kind, name, mandatory=False):
        packet = SemanticPacket(frozenset(packet), kind, str(name), mandatory)
        candidate = Graph()
        for triple in set(selected) | packet.triples:
            candidate.add(triple)
        cls, props, _, _, text, _ = describe(candidate)
        fits = (len(cls) <= max(0, budget.max_classes)
                and len(props) <= max(0, budget.max_properties)
                and len(candidate) <= max(0, budget.max_triples)
                and estimate_token_count(text)[0] <= max(0, budget.max_context_tokens))
        if packet.triples and fits:
            for triple in packet.triples:
                selected.add(triple)
            return True
        dropped[packet.kind].append(packet.name)
        if packet.required:
            missing.append(packet.name)
            if not packet.triples:
                not_found.append(packet.name)
        return False

    def expression_packet(node, visited=None):
        visited = set() if visited is None else visited
        if node in visited:
            return set()
        visited.add(node)
        packet = set(graph.triples((node, None, None)))
        for _, predicate, obj in list(packet):
            if isinstance(obj, BNode) or is_expression_node(graph, obj):
                packet.update(expression_packet(obj, visited))
            elif predicate == OWL.onProperty:
                packet.update(property_packet(obj, visited))
            elif is_class(obj):
                packet.update(class_packet(obj))
        return packet

    accept(class_packet(target), "classes", target, True)
    for uri in sorted(explicit_classes - {str(target)}):
        accept(class_packet(URIRef(uri)), "classes", uri, True)

    def property_closure(uri):
        packet, queue, visited = set(), [uri], set()
        while queue:
            prop = queue.pop()
            if prop in visited:
                continue
            visited.add(prop)
            packet.update(property_packet(prop))
            for pred in (OWL.inverseOf, RDFS.subPropertyOf, OWL.propertyChainAxiom):
                links = set(graph.triples((prop, pred, None)))
                if pred != OWL.propertyChainAxiom:
                    links.update(graph.triples((None, pred, prop)))
                for triple in links:
                    packet.add(triple)
                    for endpoint in (triple[0], triple[2]):
                        if isinstance(endpoint, BNode):
                            packet.update(expression_packet(endpoint))
                            queue.extend(graph.items(endpoint))
                        elif is_property(endpoint):
                            queue.append(endpoint)
        return packet

    for uri in sorted(required):
        accept(property_packet(URIRef(uri)), "properties", uri, True)
    core_classes = set(selected.subjects(RDF.type, OWL.Class))

    # Discover constraints on classes introduced by property axioms and expressions,
    # before budget selection so required constraints still precede optional ones.
    dependency_classes = set(selected.subjects(RDF.type, OWL.Class))
    for uri in sorted(required):
        dependency_classes.update(s for s, p, o in property_closure(URIRef(uri))
                                  if p == RDF.type and o == OWL.Class)
    constraints = []
    pending_classes = sorted(dependency_classes, key=str)
    visited_classes = set()
    while pending_classes:
        cls = pending_classes.pop(0)
        if cls in visited_classes:
            continue
        visited_classes.add(cls)
        if is_expression_node(graph, cls):
            constraints.append(SemanticPacket(
                frozenset(class_packet(cls) | expression_packet(cls)),
                "restrictions", str(cls), cls in dependency_classes))
        for pred in (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith):
            for obj in sorted(graph.objects(cls, pred), key=str):
                if isinstance(obj, BNode) or is_expression_node(graph, obj):
                    packet = class_packet(cls) | {(cls, pred, obj)} | expression_packet(obj)
                    relevant = any(p == OWL.onProperty and str(o) in required
                                   for _, p, o in packet)
                    for _, p, o in list(packet):
                        if p == OWL.onProperty:
                            packet.update(property_closure(o))
                    constraints.append(SemanticPacket(frozenset(packet), "restrictions",
                                                      str(obj), relevant))
                elif pred != RDFS.subClassOf and is_class(obj):
                    constraints.append(SemanticPacket(
                        frozenset(class_packet(cls) | {(cls, pred, obj)} | class_packet(obj)), "axioms",
                        str(obj), str(cls) in explicit_classes and str(obj) in explicit_classes))
        discovered = {s for packet in constraints for s, p, o in packet.triples
                      if p == RDF.type and o == OWL.Class}
        pending_classes.extend(sorted(discovered - visited_classes - set(pending_classes),
                                      key=str))
    for packet in sorted((p for p in constraints if p.required),
                         key=lambda p: (p.kind, p.name)):
        accept(packet.triples, packet.kind, packet.name, packet.required)
    for uri in sorted(required):
        if is_property(URIRef(uri)):
            accept(property_closure(URIRef(uri)), "axioms", uri, True)
    for packet in sorted((p for p in constraints if not p.required),
                         key=lambda p: (p.kind, p.name)):
        accept(packet.triples, packet.kind, packet.name)

    # Required constraints precede optional descendants and neighbors.
    for child in sorted(set(graph.subjects(RDFS.subClassOf, target)), key=str):
        if is_class(child):
            accept(class_packet(child), "classes", child)
    neighbors = set()
    for cls in core_classes:
        neighbors.update(graph.subjects(RDFS.domain, cls))
        neighbors.update(graph.subjects(RDFS.range, cls))
    for prop in sorted(neighbors - {URIRef(u) for u in required}, key=str):
        if is_property(prop):
            accept(property_closure(prop), "properties", prop)

    classes, properties, restrictions, axioms, text, expressions = describe(selected)
    kept_props = {p["iri"] for p in properties}
    kept_paths = [path for path in paths if all(h["property"] in kept_props for h in path)]
    return {
        "classes": classes, "properties": properties, "restrictions": restrictions,
        "axioms": axioms, "expressions": expressions,
        "triples": [list(map(str, t)) for t in sorted(selected, key=lambda t: tuple(map(str, t)))],
        "render_text": text, "truncated": any(dropped.values()),
        "dropped_required": bool(missing), "dropped_items": dropped,
        "required_properties": sorted(required), "required_paths": paths,
        "paths": kept_paths, "levels": 4 if properties or restrictions else 0,
        "budget_used": {"triples": len(selected), "tokens": estimate_token_count(text)[0],
                        "tokenizer": estimate_token_count(text)[1]},
        "missing_reasons": {"not_found": sorted(not_found),
                            "budget_dropped": sorted(set(missing) - set(not_found))},
        "degradation": "not_found" if not_found else "budget_insufficient" if missing else (
            "optional_context_dropped" if any(dropped.values()) else "none"),
        "counts": {"classes": len(classes), "properties": len(properties),
                   "restrictions": len(restrictions), "used_props": len(required)},
    }


def _plan_dependencies(plan: dict) -> tuple[set, dict, list, set]:
    """Walk only schema-bearing slots; values and aggregate aliases are not IRIs."""
    properties, classes, paths, sources = set(), set(), [], {}
    property_slots = {"property", "measure_property", "date_property", "by"}
    child_slots = {"filters", "traversals", "projections", "relation_path", "ordering",
                   "aggregation", "aggregations", "date_ranges", "latest", "where", "optional",
                   "path", "args", "arg", "conditions", "children", "not", "filter"}

    def walk(node, source):
        if isinstance(node, list):
            for value in node:
                if source == "projections" and isinstance(value, str):
                    properties.add(value)
                    sources.setdefault(value, set()).add(source)
                else:
                    walk(value, source)
            if node and all(isinstance(h, dict) and "property" in h for h in node):
                if source in ("path", "relation_path", "traversals"):
                    paths.append([{"property": h["property"], "inverse": bool(h.get("inverse"))}
                                  for h in node])
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in property_slots and isinstance(value, str) and "://" in value:
                    properties.add(value)
                    sources.setdefault(value, set()).add(source)
                elif key in ("concept", "related_class") and isinstance(value, str):
                    classes.add(value)
                elif key in ("from", "to") and isinstance(value, str) and "://" in value:
                    classes.add(value)
                elif key in child_slots:
                    walk(value, key if source == "plan" else source)
                    if key == "path" and isinstance(value, list) and value:
                        paths.append([{"property": h["property"],
                                       "inverse": bool(h.get("inverse"))}
                                      for h in value if isinstance(h, dict) and "property" in h])
                elif key in ("target", "related"):
                    if isinstance(value, str) and "://" in value:
                        classes.add(value)
                    else:
                        walk(value, key)

    walk(plan, "plan")
    return properties, sources, paths, classes


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


def explanation_schema(slice_: dict) -> str:
    """Serialize the already budgeted semantic slice, never instance evidence."""
    return json.dumps({
        key: slice_.get(key) for key in
        ("classes", "properties", "expressions", "restrictions", "axioms",
         "paths", "dropped_required", "degradation")
    }, ensure_ascii=False, sort_keys=True)
