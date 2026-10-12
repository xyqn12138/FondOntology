"""Regression coverage for the eight post-OA semantic and evaluation findings."""
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import XSD

from fondontology.qa.context import SliceBudget, build_ontology_slice, explanation_schema
from fondontology.qa.intent import IntentResult, build_intent
from fondontology.qa.owl_expression import expression_ast
from fondontology.qa.semantics import OntologyContext
from tools.qa_bench import run_intent_benchmark
from tools.tbox_slice_bench import evaluate_case

T = Namespace("https://ontology.example.cn/cnfo/ontology/")
PREFIX = f"""@prefix : <{T}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


def graph(ttl):
    return Graph().parse(data=PREFIX + ttl, format="turtle")


def slice_graph(ttl, budget=SliceBudget()):
    return build_ontology_slice(graph(ttl), {
        "target": {"concept": str(T.Target)}, "projections": [str(T.required)]}, budget)


class RemainingSemanticTests(unittest.TestCase):
    def test_axiom_endpoint_class_constraints_are_discovered(self):
        result = slice_graph("""
        :Target a owl:Class . :Other a owl:Class;
          rdfs:subClassOf [a owl:Restriction; owl:onProperty :required; owl:hasValue 7] .
        :required a owl:ObjectProperty; owl:inverseOf :inverse .
        :inverse a owl:ObjectProperty; rdfs:domain :Other .
        """)
        self.assertIn(str(T.Other), {r["class"] for r in result["restrictions"]})
        self.assertFalse(result["dropped_required"])

    def test_constraint_class_discovery_reaches_fixed_point(self):
        result = slice_graph("""
        :Target a owl:Class; owl:equivalentClass :Other .
        :Other a owl:Class; owl:equivalentClass :Third .
        :Third a owl:Class; rdfs:subClassOf [
          a owl:Restriction; owl:onProperty :required; owl:hasValue 7] .
        :required a owl:DatatypeProperty .
        """)
        self.assertIn(str(T.Third), {r["class"] for r in result["restrictions"]})

    def test_named_restriction_is_rendered_and_sent_to_explainer(self):
        result = slice_graph("""
        :Target a owl:Class; rdfs:subClassOf :Rule .
        :Rule a owl:Restriction; owl:onProperty :required; owl:hasValue "tag"@en .
        :required a owl:DatatypeProperty .
        """)
        self.assertEqual(result["restrictions"][0]["restriction"], str(T.Rule))
        ast = json.loads(explanation_schema(result))["expressions"][0]["expression"]
        self.assertEqual(ast["kind"], "restriction")
        self.assertEqual(ast["hasValue"]["language"], "en")
        self.assertIn("restriction", result["render_text"])

    def test_named_restriction_within_nested_expression(self):
        result = slice_graph("""
        :Target a owl:Class; owl:equivalentClass [owl:intersectionOf (:Rule :Other)] .
        :Other a owl:Class .
        :Rule a owl:Restriction; owl:onProperty :required; owl:someValuesFrom :Other .
        :required a owl:ObjectProperty .
        """)
        self.assertEqual(result["restrictions"][0]["on_property"], str(T.required))
        self.assertIn("restriction", json.dumps(result["expressions"]))

    def test_named_union_expression_is_not_silently_dropped(self):
        result = slice_graph("""
        :Target a owl:Class; owl:equivalentClass [
            owl:intersectionOf (:NamedUnion [a owl:Restriction;
                owl:onProperty :required; owl:someValuesFrom :A])] .
        :NamedUnion owl:unionOf (:A :B) .
        :A a owl:Class . :B a owl:Class .
        :required a owl:DatatypeProperty .
        """)
        self.assertIn("union", result["render_text"])
        self.assertIn(str(T.A), json.dumps(result["expressions"]))
        small = slice_graph("""
        :Target a owl:Class; owl:equivalentClass [
            owl:intersectionOf (:NamedUnion [a owl:Restriction;
                owl:onProperty :required; owl:someValuesFrom :A])] .
        :NamedUnion owl:unionOf (:A :B) .
        :A a owl:Class . :B a owl:Class .
        :required a owl:DatatypeProperty .
        """, SliceBudget(max_triples=4))
        self.assertTrue(small["truncated"])
        self.assertTrue(small["dropped_required"])
        self.assertNotEqual(small["degradation"], "none")
        self.assertTrue(small["missing_reasons"]["budget_dropped"])
        self.assertNotIn("union", small["render_text"])
        for definition, kind in (("owl:unionOf (:A :B)", "union"),
                                 ("owl:intersectionOf (:A :B)", "intersection"),
                                 ("owl:complementOf :A", "complement")):
            with self.subTest(kind=kind):
                direct = slice_graph(f"""
                :Target a owl:Class; owl:equivalentClass :Named .
                :Named {definition} .
                :A a owl:Class . :B a owl:Class .
                :required a owl:DatatypeProperty .
                """)
                self.assertIn(kind, direct["render_text"])
                self.assertEqual(direct["expressions"][0]["expression"]["kind"], kind)

    def test_explanation_json_retains_inheritance(self):
        result = slice_graph("""
        :Target a owl:Class; rdfs:subClassOf :Parent .
        :Parent a owl:Class; rdfs:subClassOf :Root . :Root a owl:Class .
        :required a owl:DatatypeProperty .
        """)
        classes = {c["iri"]: c for c in json.loads(explanation_schema(result))["classes"]}
        self.assertEqual(classes[str(T.Target)]["parents"], [str(T.Parent)])
        self.assertEqual(classes[str(T.Parent)]["parents"], [str(T.Root)])

    def test_ast_distinguishes_typed_plain_and_language_literals(self):
        values = [Literal("1"), Literal("1", datatype=XSD.integer),
                  Literal("1", lang="zh"), Literal("1", lang="en")]
        asts = [expression_ast(Graph(), value) for value in values]
        self.assertEqual(len({json.dumps(a, sort_keys=True) for a in asts}), 4)
        self.assertEqual(asts[1]["datatype"], str(XSD.integer))

    def test_last_frontier_can_still_overflow_path_limit(self):
        ctx = OntologyContext(SimpleNamespace(tbox=graph("""
        :Target a owl:Class . :Other a owl:Class .
        :a a owl:ObjectProperty; rdfs:domain :Target; rdfs:range :Other .
        :b a owl:ObjectProperty; rdfs:domain :Target; rdfs:range :Other .
        """)))
        diagnostics = {}
        self.assertEqual(len(ctx.find_relation_paths("Target", "Other", limit=1,
                                                     diagnostics=diagnostics)), 1)
        self.assertTrue(diagnostics["capped"])
        self.assertEqual((diagnostics["candidates"], diagnostics["retained"]), (2, 1))
        diagnostics = {}
        ctx.find_relation_paths("Target", "Other", limit=2, diagnostics=diagnostics)
        self.assertFalse(diagnostics["capped"])


class RemainingEvaluationTests(unittest.TestCase):
    def evaluate_missing_connection(self, reported, mode=None, connections=None):
        case = {"id": "test", "split": "development", "category": "synthetic",
                "question": "q", "classes": [], "properties": [],
                "connections": connections or [["link"]]}
        if mode:
            case["connection_mode"] = mode
        result = SimpleNamespace(render_text="", paths=[], classes=[], properties=[],
                                 dropped_items={"properties": reported, "classes": []},
                                 critical_missing=True, token_count=0)
        retriever = SimpleNamespace(ctx=SimpleNamespace(classes={}, properties={}),
                                    retrieve=lambda question: result)
        return evaluate_case(case, 800, retriever)

    def test_unrelated_missing_alarm_does_not_hide_missing_connection(self):
        row = self.evaluate_missing_connection(["unrelated"])
        self.assertEqual(row["silent_missing_count"], 1)
        self.assertEqual(row["silent_missing_rate"], 1.0)

    def test_matching_missing_edge_is_not_silent(self):
        self.assertEqual(self.evaluate_missing_connection(["link"])["silent_missing_count"], 0)

    def test_alternative_chains_need_specific_missing_reports(self):
        groups = [["direct"], ["first", "second"]]
        self.assertEqual(self.evaluate_missing_connection(
            ["direct"], "any", groups)["silent_missing_count"], 1)
        self.assertEqual(self.evaluate_missing_connection(
            ["direct", "second"], "any", groups)["silent_missing_count"], 0)

    def run_intent(self, expected, intent, trace=None, use_llm=False):
        cases = {"cases": [{"id": "test", "question": "q", "expected": {
            "status": "RESOLVED", "operation": "find", "target": "Target", **expected}}]}
        result = IntentResult("q", "RESOLVED", "find",
                              intent={"target_class": str(T.Target), **intent},
                              schema_trace=trace or {})
        output = io.StringIO()
        with patch("tools.qa_bench.OntologyIndex"), \
             patch("tools.qa_bench.build_intent", return_value=result) as build, \
             patch.object(Path, "read_text", return_value=json.dumps(cases)), \
             patch("fondontology.qa.config.llm_configured", return_value=True), \
             redirect_stdout(output):
            code = run_intent_benchmark(None, Path("unused"), use_llm=use_llm)
        return code, output.getvalue(), build.call_args.kwargs["use_llm"]

    def test_related_and_traversal_slots_affect_exact_score(self):
        for slot in ("related", "related_class", "traversals"):
            with self.subTest(slot=slot):
                expected = [{"property": str(T.required)}] if slot == "traversals" else str(T.Other)
                code, output, _ = self.run_intent({slot: expected}, {})
                self.assertEqual(code, 1)
                self.assertIn("0/1 = 0.0%", output)
                self.assertEqual(self.run_intent({slot: expected}, {slot: expected})[0], 0)

    def test_auto_llm_mode_counts_structured_fallback(self):
        code, output, effective_llm = self.run_intent(
            {}, {}, trace={"fallback": True}, use_llm=None)
        self.assertEqual(code, 0)
        self.assertTrue(effective_llm)
        self.assertIn("fallback rate=100.0%", output)

    def test_model_none_result_also_sets_fallback_flag(self):
        deterministic = IntentResult("q", "RESOLVED", "find")
        with patch("fondontology.qa.intent.VocabularyResolver"), \
             patch("fondontology.qa.intent.WhitelistValidator"), \
             patch("fondontology.qa.intent._try_compare_intent", return_value=None), \
             patch("fondontology.qa.intent._try_anchor_fast_path", return_value=None), \
             patch("fondontology.qa.intent._build_llm_intent", return_value=None), \
             patch("fondontology.qa.intent._build_deterministic_intent",
                   return_value=deterministic):
            result = build_intent("q", None, use_llm=True)
        self.assertTrue(result.schema_trace["fallback"])

    def test_exclusions_are_part_of_intent_score(self):
        cases = {"cases": [{"id": "test", "question": "q", "expected": {
            "status": "RESOLVED", "operation": "find", "target": "Target",
            "exclusions": [str(T.Excluded)]}}]}
        result = IntentResult("q", "RESOLVED", "find",
                              intent={"target_class": str(T.Target),
                                      "exclusions": [str(T.Excluded)]})
        output = io.StringIO()
        with patch("tools.qa_bench.OntologyIndex"), \
             patch("tools.qa_bench.build_intent", return_value=result), \
             patch.object(Path, "read_text", return_value=json.dumps(cases)), \
             redirect_stdout(output):
            self.assertEqual(run_intent_benchmark(None, Path("unused")), 0)
        for actual in (None, [], [str(T.Wrong)],
                       ["https://other.example.org/Excluded"]):
            with self.subTest(actual=actual):
                if actual is None:
                    result.intent.pop("exclusions", None)
                else:
                    result.intent["exclusions"] = actual
                output = io.StringIO()
                with patch("tools.qa_bench.OntologyIndex"), \
                     patch("tools.qa_bench.build_intent", return_value=result), \
                     patch.object(Path, "read_text", return_value=json.dumps(cases)), \
                     redirect_stdout(output):
                    self.assertEqual(run_intent_benchmark(None, Path("unused")), 1)
                self.assertIn("0/1 = 0.0%", output.getvalue())


if __name__ == "__main__":
    unittest.main()
