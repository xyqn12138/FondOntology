"""Task-derived slicing contracts, independent of the production selector."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from fondontology.qa.context import SliceBudget, build_ontology_slice
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever, estimate_token_count


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/tbox_slice_contracts.ttl"
T = Namespace("https://example.org/slice-test/")
F = Namespace("https://ontology.example.cn/cnfo/ontology/")


class SliceContractTest(unittest.TestCase):
    def setUp(self):
        self.graph = Graph().parse(FIXTURE, format="turtle")

    def slice(self, budget=None, **fields):
        return build_ontology_slice(
            self.graph, {"target": {"concept": str(T.Target)}, **fields},
            budget or SliceBudget())

    def required(self, result):
        return {p["iri"] for p in result["properties"] if p.get("required")}

    def test_plan_dependencies(self):
        specifications = {
            "filter": {"filters": [{"property": str(T.zMeasure)}]},
            "traversal": {"traversals": [{"property": str(T.zLink)}]},
            "projection": {"projections": [str(T.zMeasure)]},
            "relation": {"relation_path": [{"property": str(T.zLink), "inverse": False}]},
            "ordering": {"ordering": [{"by": str(T.zMeasure), "direction": "desc"}]},
            "aggregation": {"aggregations": [{"func": "sum", "measure_property": str(T.zMeasure)}]},
            "date": {"date_ranges": [{"property": str(T.zTime), "from": "2024-01-01"}]},
            "latest": {"latest": {"date_property": str(T.zTime)}},
            "where": {"where": {"type": "and", "args": [
                {"type": "filter", "property": str(T.zMeasure), "value": 2}]}},
            "optional": {"optional": [{"path": [{"property": str(T.zLink)}],
                                       "where": {"property": str(T.zMeasure)}}]},
        }
        for name, fields in specifications.items():
            with self.subTest(source=name):
                expected = T.zTime if name in ("date", "latest") else (
                    T.zLink if name in ("traversal", "relation") else T.zMeasure)
                self.assertIn(str(expected), self.required(self.slice(**fields)))

    def test_required_precedes_optional_lexical_order(self):
        result = self.slice(SliceBudget(max_properties=1),
                            filters=[{"property": str(T.zMeasure)}])
        self.assertEqual(self.required(result), {str(T.zMeasure)})

    def test_required_endpoints_precede_children(self):
        result = self.slice(SliceBudget(max_classes=3, max_properties=1),
                            traversals=[{"property": str(T.zLink)}])
        self.assertIn(str(T.Other), {c["iri"] for c in result["classes"]})
        self.assertIn(str(T.zLink), self.required(result))

    def test_generic_namespace_optional_properties(self):
        self.assertIn(str(T.aOptional), {p["iri"] for p in self.slice()["properties"]})

    def test_no_dangling_property_endpoints(self):
        result = self.slice(SliceBudget(max_classes=1),
                            traversals=[{"property": str(T.zLink)}])
        classes = {c["iri"] for c in result["classes"]}
        for p in result["properties"]:
            for iri in p["domains"] + p["ranges"]:
                if (URIRef(iri), RDF.type, OWL.Class) in self.graph:
                    self.assertIn(iri, classes)
        self.assertTrue(result.get("dropped_required"))

    def test_inverse_path_retains_direction(self):
        path = [{"property": str(T.backLink), "inverse": True}]
        result = self.slice(relation_path=path)
        self.assertIn(path, result.get("required_paths", []))

    def test_missing_property_explicit(self):
        result = self.slice(filters=[{"property": str(T.notDeclared)}])
        self.assertTrue(result.get("dropped_required"))
        self.assertIn(str(T.notDeclared), json.dumps(result.get("dropped_items", {})))

    def test_aggregate_alias_is_not_property(self):
        result = self.slice(ordering=[{"by": "agg"}])
        self.assertNotIn("agg", result.get("required_properties", []))

    def test_anonymous_restriction_facets(self):
        result = self.slice()
        rows = result["restrictions"]
        for facet in ("some_values_from", "all_values_from", "has_value",
                      "min_cardinality", "max_cardinality", "cardinality",
                      "min_qualified_cardinality"):
            with self.subTest(facet=facet):
                self.assertTrue(any(facet in r and r[facet] not in ("", None) for r in rows))
        self.assertTrue(any(r.get("on_class") == str(T.Other) for r in rows))

    def test_equivalent_class_restriction(self):
        result = self.slice(related={"concept": str(T.Other)})
        self.assertTrue(any(r["class"] == str(T.Other)
                            and r["on_property"] == str(T.zTime)
                            for r in result["restrictions"]))

    def test_property_axiom_support(self):
        result = self.slice(projections=[str(T.chainLink), str(T.nextLink)])
        text = json.dumps(result, ensure_ascii=False)
        for term in ("property_chain", "sub_property_of", str(T.zLink), str(T.nextLink)):
            self.assertIn(term, text)

    def test_count_and_triple_budget(self):
        result = self.slice(SliceBudget(max_classes=1, max_properties=1, max_triples=1))
        self.assertLessEqual(len(result["classes"]), 1)
        self.assertLessEqual(len(result["properties"]), 1)
        triples = result.get("triples")
        self.assertIsNotNone(triples)
        self.assertLessEqual(len(triples), 1)
        self.assertTrue(result["truncated"])

    def test_token_budget_final_text(self):
        result = self.slice(SliceBudget(max_context_tokens=20),
                            traversals=[{"property": str(T.zLink)}])
        self.assertIn("render_text", result)
        self.assertLessEqual(estimate_token_count(result["render_text"])[0], 20)
        self.assertTrue(result.get("truncated"))

    def test_restriction_budget_reports_truncation(self):
        result = self.slice(SliceBudget(max_triples=4))
        self.assertTrue(result["truncated"])

    def test_zero_budgets(self):
        result = self.slice(SliceBudget(max_classes=0, max_properties=0,
                                        max_triples=0, max_context_tokens=0))
        self.assertEqual(result["classes"] + result["properties"] + result["restrictions"], [])
        self.assertTrue(result["truncated"])

    def test_repeatable_without_modifying_graph(self):
        before = set(self.graph)
        first = self.slice()
        self.assertEqual(first, self.slice())
        self.assertEqual(before, set(self.graph))


class SchemaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = build_stack(ROOT / "ontology/modules/cnfo-domain.ttl")
        cls.index = OntologyIndex(cls.stack)

    def result(self, cap=10000, question="医药主题的股票型基金有哪些？", **kwargs):
        return SchemaRetriever(self.index, max_chars=cap, **kwargs).retrieve(question)

    def test_low_budget_is_observable_and_metadata_matches(self):
        result = self.result(800)
        self.assertIsInstance(getattr(result, "truncated", None), bool)
        for prop in result.properties:
            self.assertRegex(result.render_text, rf"(?m)^{prop}\(")
        for cls in result.classes:
            self.assertRegex(result.render_text, rf"(?m)^{cls}\(")

    def test_low_budget_paths_closed(self):
        result = self.result(800)
        for path in result.paths:
            for hop in path:
                self.assertIn(hop["property_local"], result.properties)
                self.assertIn(hop["via"], result.classes)
        for name in result.properties:
            prop = SchemaRetriever(self.index).ctx.properties[name]
            for cls in prop.domains + prop.ranges:
                if cls in SchemaRetriever(self.index).ctx.classes:
                    self.assertIn(cls, result.classes)

    def test_tiny_budget_and_long_question(self):
        for cap in (0, 1, 24, 100):
            with self.subTest(cap=cap):
                result = self.result(cap, "基金" * 1000)
                self.assertLessEqual(len(result.render_text), cap)
                self.assertTrue(getattr(result, "critical_missing", False))

    def test_token_budget(self):
        result = self.result(max_tokens=100)
        self.assertLessEqual(estimate_token_count(result.render_text)[0], 100)
        self.assertTrue(result.truncated)

    def test_empty_query_has_no_concepts(self):
        result = self.result(question="")
        self.assertEqual(result.classes + result.properties + result.paths, [])

    def test_repeatable(self):
        self.assertEqual(self.result().__dict__, self.result().__dict__)

    def test_new_alias_and_definition_without_python_rules(self):
        graph = Graph()
        graph.add((F.Sensor, RDF.type, OWL.Class))
        graph.add((F.measure42, RDF.type, OWL.DatatypeProperty))
        graph.add((F.measure42, RDFS.domain, F.Sensor))
        graph.add((F.measure42, RDFS.range, URIRef("http://www.w3.org/2001/XMLSchema#decimal")))
        graph.add((F.measure42, SKOS.altLabel, Literal("传感器读数", lang="zh")))
        graph.add((F.measure42, SKOS.definition, Literal("采样得到的温度测量结果。", lang="zh")))
        stack = replace(self.stack, tbox=graph, _combined=None)
        index = OntologyIndex(stack)
        for question in ("传感器读数是多少？", "温度测量结果大于十的有哪些？"):
            with self.subTest(question=question):
                result = SchemaRetriever(index).retrieve(question)
                self.assertIn("measure42(", result.render_text)


if __name__ == "__main__":
    unittest.main()
