"""Cache ownership, inference reuse and read-only fixture isolation."""
import gc
import unittest
import weakref
from dataclasses import replace
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS

from fondontology.qa.engine import _get_index
from fondontology.qa.enforce import EnforcementResult, SemanticEnforcer
from fondontology.qa.graph import DataStack, GraphSnapshot, build_stack
from fondontology.qa.semantics import OntologyContext
from test_support import shared_index, shared_stack

F = Namespace("https://ontology.example.cn/cnfo/ontology/")


def tiny_stack():
    tbox = Graph()
    tbox.add((F.Fund, RDF.type, OWL.Class))
    snapshot = GraphSnapshot("test", "test", "test", "", "", "OWL-RL", "")
    return DataStack(tbox, Graph(), snapshot)


class RuntimeLifecycleTests(unittest.TestCase):
    def test_index_and_context_do_not_pin_stack_globally(self):
        stack = tiny_stack()
        index = _get_index(stack)
        context = OntologyContext.from_stack(stack)
        references = [weakref.ref(value) for value in (stack, index, context)]
        del stack, index, context
        gc.collect()
        self.assertTrue(all(ref() is None for ref in references))

    def test_cached_views_reuse_identity(self):
        stack = tiny_stack()
        self.assertIs(_get_index(stack), _get_index(stack))
        self.assertIs(OntologyContext.from_stack(stack), OntologyContext.from_stack(stack))

    def test_replaced_stack_has_fresh_views(self):
        stack = tiny_stack()
        _get_index(stack)
        OntologyContext.from_stack(stack)
        other = replace(stack, abox=Graph())
        self.assertIsNone(other._ontology_index)
        self.assertIsNone(other._ontology_context)
        self.assertIsNot(_get_index(stack), _get_index(other))

    def test_materialized_query_reuses_complete_graph(self):
        stack = tiny_stack()
        stack.abox.add((F.Sample, RDF.type, F.Fund))
        materialized = stack.require_abox_inferred()
        self.assertIs(materialized, stack.query_graph(with_abox_inferred=True))
        self.assertTrue(set(stack.tbox) | set(stack.abox) <= set(materialized))

    def test_merge_invalidates_index_and_inference(self):
        stack = tiny_stack()
        before = _get_index(stack)
        stack.query_graph(with_abox_inferred=True)
        graph = Graph()
        entity = Namespace("https://ontology.example.cn/cnfo/abox/").NewFund
        graph.add((entity, RDF.type, F.Fund))
        graph.add((entity, RDFS.label, Literal("New")))
        enforcer = SemanticEnforcer(stack)
        enforcer.merge_into_stack(EnforcementResult(graph=graph))
        self.assertIsNone(stack._ontology_index)
        self.assertIsNone(stack._combined_inferred)
        self.assertIsNot(before, _get_index(stack))
        self.assertIn(str(entity), _get_index(stack).entities)

    def test_suite_fixture_is_shared_but_real_builder_is_isolated(self):
        source = Path(__file__).resolve().parents[1] / "ontology/modules/cnfo-domain.ttl"
        shared = shared_stack(source)
        self.assertIs(shared, shared_stack(source))
        self.assertIs(shared_index(shared), shared_index(shared))
        isolated = build_stack(source)
        isolated.abox.add((F.New, RDF.type, F.Fund))
        self.assertNotIn((F.New, RDF.type, F.Fund), shared.abox)


if __name__ == "__main__":
    unittest.main()
