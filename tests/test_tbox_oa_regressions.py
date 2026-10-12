"""OA regressions use synthetic, non-domain-specific OWL structures."""
import json
import io
from contextlib import redirect_stdout
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from rdflib import Graph, Namespace

from fondontology.qa.context import SliceBudget, build_ontology_slice, explanation_schema
from fondontology.qa.intent import IntentResult, _build_llm_intent
from fondontology.qa.schema_retriever import SchemaContext

T = Namespace("https://example.org/oa/")
PREFIX = """@prefix : <https://example.org/oa/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


class SemanticClosureTests(unittest.TestCase):
    def slice(self, ttl, budget=SliceBudget(), prop="zRequired"):
        return build_ontology_slice(
            Graph().parse(data=PREFIX + ttl, format="turtle"),
            {"target": {"concept": str(T.Target)},
             "projections": [str(T[prop])]}, budget)

    def test_required_restriction_precedes_optional(self):
        result = self.slice("""
        :Target a owl:Class ;
          rdfs:subClassOf [ a owl:Restriction; owl:onProperty :aOptional; owl:hasValue 1 ],
                         [ a owl:Restriction; owl:onProperty :zRequired; owl:hasValue 2 ] .
        :aOptional a owl:DatatypeProperty .
        :zRequired a owl:DatatypeProperty .
        """, SliceBudget(max_triples=8))
        self.assertEqual([r["on_property"] for r in result["restrictions"]],
                         [str(T.zRequired)])
        self.assertFalse(result["dropped_required"])

    def test_nested_expression_is_required_atomic_and_rendered(self):
        ttl = """
        :Target a owl:Class; owl:equivalentClass [
          owl:intersectionOf (:Base [ a owl:Restriction; owl:onProperty :zRequired;
                                      owl:someValuesFrom :Other ]) ] .
        :Base a owl:Class . :Other a owl:Class .
        :zRequired a owl:ObjectProperty .
        """
        result = self.slice(ttl)
        self.assertIn("intersection", result["render_text"])
        self.assertEqual(result["restrictions"][0]["some_values_from"], str(T.Other))
        small = self.slice(ttl, SliceBudget(max_triples=7))
        self.assertTrue(small["dropped_required"])
        self.assertEqual(small["expressions"], [])

    def test_fixed_point_reverse_and_chain_axioms(self):
        result = self.slice("""
        :Target a owl:Class .
        :zRequired a owl:ObjectProperty .
        :q a owl:ObjectProperty; owl:inverseOf :zRequired; rdfs:subPropertyOf :r .
        :r a owl:ObjectProperty; owl:propertyChainAxiom (:s :t) .
        :s a owl:ObjectProperty . :t a owl:ObjectProperty .
        """)
        self.assertTrue({str(T[n]) for n in ("zRequired", "q", "r", "s", "t")}
                        <= {p["iri"] for p in result["properties"]})
        self.assertEqual({a["kind"] for a in result["axioms"]},
                         {"inverse_of", "sub_property_of", "property_chain"})

    def test_boolean_and_cardinality_ast(self):
        result = self.slice("""
        :Target a owl:Class; owl:equivalentClass [ owl:unionOf (
          [ owl:complementOf :Other ]
          [ a owl:Restriction; owl:onProperty :zRequired;
            owl:minQualifiedCardinality 1; owl:onClass :Other ]) ] .
        :Other a owl:Class . :zRequired a owl:ObjectProperty .
        """)
        text = json.dumps(result["expressions"])
        for word in ("union", "complement", "minQualifiedCardinality", "onClass"):
            self.assertIn(word, text)

    def test_cross_load_and_process_determinism(self):
        ttl = PREFIX + """
        :Target a owl:Class; rdfs:subClassOf [
          a owl:Restriction; owl:onProperty :zRequired; owl:allValuesFrom :Target ] .
        :zRequired a owl:ObjectProperty .
        """
        plan = {"target": {"concept": str(T.Target)}, "projections": [str(T.zRequired)]}
        first = build_ontology_slice(Graph().parse(data=ttl, format="turtle"), plan)
        second_graph = Graph().parse(data=ttl, format="turtle")
        reversed_graph = Graph()
        for triple in reversed(list(second_graph)):
            reversed_graph.add(triple)
        self.assertEqual(first, build_ontology_slice(reversed_graph, plan))
        code = (
            "import json; from rdflib import Graph; "
            "from fondontology.qa.context import build_ontology_slice; "
            f"print(json.dumps(build_ontology_slice(Graph().parse(data={ttl!r}, "
            f"format='turtle'), {plan!r}), sort_keys=True))")
        output = subprocess.check_output(
            [sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
            text=True, encoding="utf-8")
        self.assertEqual(first, json.loads(output))
        self.assertEqual(json.loads(explanation_schema(first))["dropped_required"], False)

    def test_not_found_is_not_budget_loss(self):
        result = self.slice(":Target a owl:Class .")
        self.assertEqual(result["degradation"], "not_found")
        self.assertEqual(result["missing_reasons"]["budget_dropped"], [])

    def test_anonymous_domain_is_not_silently_discarded(self):
        result = self.slice("""
        :Target a owl:Class . :Other a owl:Class .
        :zRequired a owl:ObjectProperty;
          rdfs:domain [ owl:unionOf (:Target :Other) ]; rdfs:range :Other .
        """)
        prop = next(p for p in result["properties"] if p["iri"] == str(T.zRequired))
        self.assertIn("union", prop["domains"][0])
        self.assertIn(str(T.Other), {c["iri"] for c in result["classes"]})

    def test_production_aggregation_and_related_slots(self):
        result = build_ontology_slice(Graph().parse(data=PREFIX + """
        :Target a owl:Class . :Other a owl:Class . :zRequired a owl:DatatypeProperty .
        """, format="turtle"), {
            "target": {"concept": str(T.Target)}, "related_class": str(T.Other),
            "aggregation": {"measure_property": str(T.zRequired)}})
        self.assertIn(str(T.zRequired), result["required_properties"])
        self.assertIn(str(T.Other), {c["iri"] for c in result["classes"]})


class ProductionBudgetTests(unittest.TestCase):
    def context(self, missing=False, reason="none"):
        return SchemaContext(critical_missing=missing, missing_reason=reason,
                             degradation="budget_insufficient" if missing else "none")

    def invoke(self, contexts):
        retriever = SimpleNamespace(max_chars=100, max_tokens=100)
        with patch("fondontology.qa.intent.SchemaRetriever", return_value=retriever), \
             patch("fondontology.qa.intent.OntologyContext.from_stack"), \
             patch("fondontology.qa.intent.VocabularyResolver"), \
             patch("fondontology.qa.intent.WhitelistValidator"), \
             patch("fondontology.qa.intent._call_deconstructor", return_value={}) as call, \
             patch("fondontology.qa.intent._parse_llm_intent",
                   return_value=IntentResult("question", "RESOLVED", "find")):
            retriever.retrieve = unittest.mock.Mock(side_effect=contexts)
            result = _build_llm_intent("question", SimpleNamespace(stack=None))
            return result, retriever.retrieve.call_count, call.call_count

    def test_budget_expands_once(self):
        result, retrieves, calls = self.invoke([
            self.context(True, "budget_dropped"), self.context()])
        self.assertEqual((retrieves, calls), (2, 1))
        self.assertTrue(result.schema_trace["expansion_attempted"])

    def test_still_missing_skips_model(self):
        result, retrieves, calls = self.invoke([
            self.context(True, "budget_dropped"), self.context(True, "budget_dropped")])
        self.assertEqual((retrieves, calls), (2, 0))
        self.assertEqual(result.status, "UNRESOLVED")

    def test_rejected_recall_does_not_expand(self):
        for reason in ("not_found", "retrieval_rejected", "path_search_capped"):
            with self.subTest(reason=reason):
                result, retrieves, calls = self.invoke([self.context(False, reason)])
                self.assertEqual((retrieves, calls), (1, 1))
                self.assertFalse(result.schema_trace["expansion_attempted"])

    def test_explainer_receives_complete_structured_schema(self):
        from fondontology.qa.explainer import _llm_chat
        summary = json.dumps({"classes": ["X" * 1800], "dropped_required": True})
        with patch("fondontology.qa.intent._stream_chat_content",
                   return_value='{"answer_sentences": []}') as call:
            _llm_chat("question", [], summary)
        prompt = call.call_args.args[0]
        self.assertIn(summary, prompt)
        self.assertIn("不是实例事实证据", prompt)


class EvaluationTests(unittest.TestCase):
    def test_wrong_resolved_target_stays_in_denominator(self):
        from tools.qa_bench import run_intent_benchmark
        cases = {"cases": [
            {"id": "one", "question": "one", "expected": {
                "status": "RESOLVED", "operation": "find", "target": "Right"}},
            {"id": "two", "question": "two", "expected": {
                "status": "RESOLVED", "operation": "find", "target": "Right"}},
        ]}
        results = [IntentResult("one", "RESOLVED", "find",
                                intent={"target_class": "https://example.org/Right"}),
                   IntentResult("two", "RESOLVED", "find",
                                intent={"target_class": "https://example.org/Wrong"})]
        output = io.StringIO()
        with patch("tools.qa_bench.OntologyIndex"), \
             patch("tools.qa_bench.build_intent", side_effect=results), \
             patch.object(Path, "read_text", return_value=json.dumps(cases)), \
             redirect_stdout(output):
            self.assertEqual(run_intent_benchmark(None, Path("unused")), 1)
        self.assertIn("1/2 = 50.0%", output.getvalue())

    def test_alternative_connection_is_one_gold_unit(self):
        from tools.tbox_slice_bench import connection_coverage
        case = {"connections": [["direct"], ["first", "second"]], "connection_mode": "any"}
        self.assertEqual(connection_coverage(case, {"direct"})[1], 1.0)
        self.assertEqual(connection_coverage(case, {"first"})[1], 0.0)


if __name__ == "__main__":
    unittest.main()
