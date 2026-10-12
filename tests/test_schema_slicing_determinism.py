"""Regression: bounded path candidates are independent of RDF insertion order."""
import unittest
from dataclasses import replace
from pathlib import Path

from rdflib import Graph

from fondontology.qa.graph import build_stack
from fondontology.qa.semantics import OntologyContext


class RelationOrderTest(unittest.TestCase):
    def test_graph_reinsertion_keeps_relation_and_path_order(self):
        root = Path(__file__).resolve().parents[1]
        stack = build_stack(root / "ontology/modules/cnfo-domain.ttl")
        reversed_graph = Graph()
        for triple in sorted(stack.tbox, key=lambda t: tuple(map(str, t)), reverse=True):
            reversed_graph.add(triple)
        first = OntologyContext(stack)
        second = OntologyContext(replace(stack, tbox=reversed_graph))
        self.assertEqual(first.relations, second.relations)
        self.assertEqual(first.find_relation_paths("FundUnit", "Investor", limit=4),
                         second.find_relation_paths("FundUnit", "Investor", limit=4))
