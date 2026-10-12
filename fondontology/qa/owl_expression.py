"""Stable OWL expression rendering and content fingerprints."""
from __future__ import annotations

import hashlib
import json

from rdflib import BNode, Graph, Literal
from rdflib.compare import to_canonical_graph
from rdflib.namespace import OWL, RDF


_EXPRESSION_PREDICATES = (OWL.intersectionOf, OWL.unionOf, OWL.complementOf)


def is_expression_node(graph: Graph, node) -> bool:
    """Return whether node carries an OWL class-expression structure."""
    return ((node, RDF.type, OWL.Restriction) in graph
            or any((node, predicate, None) in graph
                   for predicate in _EXPRESSION_PREDICATES))


def canonical_graph(graph: Graph) -> Graph:
    return to_canonical_graph(graph)


def graph_hash(graph: Graph) -> str:
    triples = sorted(" ".join(term.n3() for term in triple) for triple in graph)
    return hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest()


def expression_ast(graph: Graph, node, seen=None):
    """Represent nested OWL expressions without leaking parser BNode IDs."""
    if isinstance(node, Literal):
        return {"kind": "literal", "value": str(node),
                "datatype": str(node.datatype) if node.datatype else None,
                "language": node.language}
    if not isinstance(node, BNode) and not is_expression_node(graph, node):
        return str(node)
    seen = set() if seen is None else seen
    if node in seen:
        return {"ref": str(node)}
    seen = seen | {node}
    for predicate, kind in ((OWL.intersectionOf, "intersection"),
                            (OWL.unionOf, "union")):
        head = graph.value(node, predicate)
        if head is not None:
            return {"kind": kind, "members": [
                expression_ast(graph, member, seen) for member in graph.items(head)]}
    complement = graph.value(node, OWL.complementOf)
    if complement is not None:
        return {"kind": "complement", "operand": expression_ast(graph, complement, seen)}
    fields = {}
    for predicate, obj in sorted(graph.predicate_objects(node),
                                 key=lambda pair: tuple(map(str, pair))):
        if predicate == RDF.type:
            continue
        key = str(predicate).rsplit("#", 1)[-1]
        fields.setdefault(key, []).append(expression_ast(graph, obj, seen))
    return {"kind": "restriction" if (node, RDF.type, OWL.Restriction) in graph
            else "expression",
            **{key: values[0] if len(values) == 1 else values
               for key, values in fields.items()}}


def expression_text(graph: Graph, node) -> str:
    value = expression_ast(graph, node)
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, dict) else value
