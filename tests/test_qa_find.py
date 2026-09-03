"""M2：find 查询链回归（QueryPlan → SPARQL → ABOX 检索 + 显式/推断类型证据）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Graph, Namespace, URIRef

from fondontology.qa.abox_query import execute_find, local_subgraph, type_evidence
from fondontology.qa.graph import build_stack
from fondontology.qa.query_planner import plan_find, validate_plan
from fondontology.qa.sparql_builder import build_select

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")


class FindQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)

    def execute(self, **plan_kwargs):
        plan = plan_find(tbox=self.stack.tbox, abox=self.stack.abox, **plan_kwargs)
        self.assertEqual(validate_plan(plan), [])
        return execute_find(self.stack, plan)

    def test_find_funds_type_closure(self) -> None:
        result = self.execute(target="Fund")
        self.assertEqual(result.count, 40)
        # builder 用完整 IRI 属性路径（rdf-schema#subClassOf>*）
        self.assertIn("rdf-schema#subClassOf>*", result.sparql)

    def test_find_etf_with_filter_and_exclusion(self) -> None:
        result = self.execute(
            target="Fund",
            filters=[{"property": "fundTypeCode", "value": "ETF"}],
            exclusions=["F051143"],
        )
        self.assertEqual(result.count, 3)

    def test_find_private_funds(self) -> None:
        self.assertEqual(self.execute(target="PrivateFund").count, 8)

    def test_find_units_inherit_via_subclass(self) -> None:
        # FundUnitClass ⊑ FundUnit：类型闭包必须经子类继承
        result = self.execute(target="FundUnit")
        self.assertEqual(result.count, 59)

    def test_find_risk_filter_object_iri(self) -> None:
        result = self.execute(
            target="Fund",
            filters=[{"property": "hasFundRiskLevel",
                      "value": "https://ontology.example.cn/cnfo/code/FundRiskLevelR4"}],
        )
        self.assertEqual(result.count, 16)

    def test_find_two_hop_traversal_label_filter(self) -> None:
        result = self.execute(
            target="Fund",
            traversals=[
                {"property": "hasFundManagerRole"},
                {"property": "rolePlayedBy",
                 "filter": {"kind": "label", "value": "华曦基金管理有限公司"}},
            ],
        )
        self.assertEqual(result.count, 10)

    def test_pagination_limit(self) -> None:
        self.assertEqual(self.execute(target="Fund", limit=5).count, 5)

    def test_invalid_plan_rejected(self) -> None:
        plan = plan_find(target="NON_EXISTENT_KLASS", tbox=self.stack.tbox)
        self.assertTrue(validate_plan(plan))

    def test_type_evidence_declared_vs_inferred(self) -> None:
        # ETF 基金在 ABOX 中直接声明 ExchangeTradedFund 类型 → declared
        ent = URIRef("https://ontology.example.cn/cnfo/abox/F051143")
        ev = type_evidence(self.stack, ent, CNFO.ExchangeTradedFund)
        self.assertIn(ev["kind"], ("declared", "inference"))
        # Fund 目标：类型声明于 ABOX → declared；若类仅经链到达则 inference
        if ev["kind"] == "inference":
            self.assertTrue(ev["chain"])

    def test_local_subgraph(self) -> None:
        graph = self.stack.query_graph()
        sub = local_subgraph(graph, [URIRef("https://ontology.example.cn/cnfo/abox/F051143")], hop=1)
        fund_node = sub["nodes"].get("https://ontology.example.cn/cnfo/abox/F051143")
        self.assertIsNotNone(fund_node)
        self.assertTrue(any(t.endswith("/Fund") for t in fund_node["types"]))
        self.assertTrue(sub["edges"])


class SparqlBuilderTest(unittest.TestCase):
    def test_builder_emits_expected_patterns(self) -> None:
        plan = {
            "target": {"concept": "https://ontology.example.cn/cnfo/ontology/Fund"},
            "exclusions": ["https://ontology.example.cn/cnfo/abox/F051143"],
            "filters": [{"property": "https://ontology.example.cn/cnfo/ontology/fundTypeCode",
                         "operator": "eq", "value": "ETF"}],
            "traversals": [{"property": "https://ontology.example.cn/cnfo/ontology/hasFundManagerRole",
                            "filter": None}],
            "projections": [],
            "ordering": [],
            "pagination": {"limit": None, "offset": 0},
        }
        sparql = build_select(plan)
        # builder 使用完整 IRI（不依赖前缀绑定）
        self.assertIn("http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
                      "/<http://www.w3.org/2000/01/rdf-schema#subClassOf>*", sparql)
        self.assertIn("FILTER(?entity != <https://ontology.example.cn/cnfo/abox/F051143>)", sparql)
        self.assertIn("FILTER(?v0 = 'ETF')", sparql)
        self.assertIn("?entity <https://ontology.example.cn/cnfo/ontology/hasFundManagerRole> ?h1 .", sparql)


if __name__ == "__main__":
    unittest.main()