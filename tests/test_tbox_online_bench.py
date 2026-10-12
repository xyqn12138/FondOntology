"""No network: reject vocabulary/path errors before considering LLM judgments."""
import unittest

from tools.tbox_online_bench import parse_object, validate_plan
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever
from pathlib import Path


class OnlineBenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.ctx = SchemaRetriever(OntologyIndex(build_stack(
            root / "ontology/modules/cnfo-domain.ttl"))).ctx
        cls.view = cls.ctx.render_for_llm()
        cls.case = {"classes": ["Fund", "NetAssetValueRecord"],
                    "properties": ["valuationDate"],
                    "connections": [["hasNetAssetValueRecord", "recordForFund"]]}

    def plan(self):
        return {"status": "resolved", "operation": "query", "target": "Fund",
                "classes": ["Fund", "NetAssetValueRecord"],
                "projections": [{"property": "valuationDate", "on": "NetAssetValueRecord"}],
                "paths": [{"from": "Fund", "to": "NetAssetValueRecord",
                           "hops": [{"property": "hasNetAssetValueRecord", "inverse": False}]}]}

    def test_valid_forward(self):
        result = validate_plan(self.plan(), self.case, self.ctx, self.view)
        self.assertTrue(result["valid"], result)
        self.assertTrue(result["gold_covered"])

    def test_reverse_must_connect(self):
        plan = self.plan()
        plan["paths"][0]["hops"][0]["inverse"] = True
        self.assertFalse(validate_plan(plan, self.case, self.ctx, self.view)["valid"])

    def test_wrong_domain(self):
        plan = self.plan()
        plan["projections"][0]["on"] = "Fund"
        self.assertFalse(validate_plan(plan, self.case, self.ctx, self.view)["valid"])

    def test_unsupported_property(self):
        plan = self.plan()
        plan["projections"].append({"property": "bloodType", "on": "Fund"})
        self.assertFalse(validate_plan(plan, self.case, self.ctx, self.view)["valid"])

    def test_out_of_view(self):
        self.assertFalse(validate_plan(self.plan(), self.case, self.ctx, "")["valid"])

    def test_self_claim_is_not_coverage(self):
        plan = {"status": "resolved", "operation": "query", "target": "Fund",
                "unsupported": ["valuationDate hasNetAssetValueRecord NetAssetValueRecord"]}
        self.assertFalse(validate_plan(plan, self.case, self.ctx, self.view)["gold_covered"])

    def test_bad_json_and_protocol(self):
        with self.assertRaises(ValueError):
            parse_object('{"ok":true} trailing prose')
        with self.assertRaises(ValueError):
            parse_object('[]')
        self.assertFalse(validate_plan({"classes": "Fund"}, self.case, self.ctx, self.view)["valid"])
