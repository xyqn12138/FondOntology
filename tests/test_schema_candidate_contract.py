"""Candidate necessity is independent of relevance rank and frozen task gold."""
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

from fondontology.qa.graph import DataStack, GraphSnapshot
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever

F = Namespace("https://ontology.example.cn/cnfo/ontology/")


class CandidateContractTests(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()
        for name, label in (("Sensor", "采样装置"), ("Reading", "测量记录")):
            self.graph.add((F[name], RDF.type, OWL.Class))
            self.graph.add((F[name], RDFS.label, Literal(label, lang="zh")))
        for name, label in (("primary", "温度读数"), ("support", "备用温度指标")):
            self.graph.add((F[name], RDF.type, OWL.DatatypeProperty))
            self.graph.add((F[name], RDFS.label, Literal(label, lang="zh")))
            self.graph.add((F[name], RDFS.domain, F.Sensor))
            self.graph.add((F[name], RDFS.range, XSD.decimal))

    def retriever(self, cap=10000):
        snapshot = GraphSnapshot("test", "test", "test", "", "", "OWL-RL", "")
        return SchemaRetriever(OntologyIndex(DataStack(self.graph, Graph(), snapshot)),
                               max_chars=cap)

    def test_explicit_field_has_source_span_and_requirement(self):
        result = self.retriever().retrieve("采样装置的温度读数")
        candidate = next(c for c in result.candidates if c["name"] == "primary")
        self.assertEqual(candidate["role"], "required")
        self.assertTrue(candidate["matched_span"])
        self.assertTrue(candidate["required_by"])
        self.assertIn("Sensor", candidate["anchor_classes"])
        self.assertFalse(result.required_missing)

    def test_optional_rejection_does_not_trigger_required_missing(self):
        retriever = self.retriever(100)
        real = retriever._refine_seeds

        def add_support(text, classes, properties):
            real(text, classes, properties)
            properties["support"] = 0.56

        with patch.object(retriever, "_refine_seeds", side_effect=add_support):
            result = retriever.retrieve("采样装置的温度读数")
        self.assertIn("primary", result.properties)
        self.assertIn("support", result.support_dropped)
        self.assertIn("support", result.candidate_budget_dropped)
        self.assertFalse(result.critical_missing)

    def test_insufficient_budget_still_reports_required_packet(self):
        result = self.retriever(1).retrieve("采样装置的温度读数")
        self.assertTrue(result.critical_missing)
        self.assertIn("primary", {r["name"] for r in result.required_missing})
        self.assertEqual(result.missing_reason, "budget_dropped")

    def test_final_packet_requires_route_not_just_property_name(self):
        requirements = [{"kind": "path", "name": "primary", "source": "Sensor",
                         "alternatives": [[{
            "property_local": "bridge", "via": "Reading", "inverse": False}]]}]
        self.assertTrue(SchemaRetriever._missing_requirements(
            requirements, {"Sensor", "Reading"}, {"primary", "bridge"}, []))
        self.assertFalse(SchemaRetriever._missing_requirements(
            requirements, {"Sensor", "Reading"}, {"primary", "bridge"},
            requirements[0]["alternatives"]))

    def test_regular_path_selection_is_not_search_cap(self):
        for name in ("aBridge", "bBridge"):
            self.graph.add((F[name], RDF.type, OWL.ObjectProperty))
            self.graph.add((F[name], RDFS.domain, F.Sensor))
            self.graph.add((F[name], RDFS.range, F.Reading))
        result = self.retriever().retrieve("采样装置的测量记录")
        self.assertTrue(result.selection_rejected)
        self.assertFalse(result.path_search_capped)


if __name__ == "__main__":
    unittest.main()
