"""GraphQueryIR 和 SPARQL 算子测试。"""
from __future__ import annotations

import unittest
from pathlib import Path

from fondontology.qa.query_ir import (
    Aggregate,
    GraphQueryIR,
    OrderExpr,
    PathJoin,
    TypeScan,
    literal,
)
from fondontology.qa.abox_query import execute_find
from test_support import shared_stack as build_stack
from fondontology.qa.query_planner import plan_find, validate_plan
from fondontology.qa.semantics import OntologyContext
from fondontology.qa.sparql_builder import build_ir, build_select, render_ir


CNFO = "https://ontology.example.cn/cnfo/ontology/"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


class QueryIROperatorTest(unittest.TestCase):
    def test_literal_escaping_and_scalar_types(self) -> None:
        self.assertEqual(literal("O'Reilly\\基金"), "'O\\'Reilly\\\\基金'")
        self.assertEqual(literal(12), "12")
        self.assertEqual(literal(1.5), "1.5")
        self.assertEqual(literal(True), "true")
        self.assertEqual(
            literal("2026-01-01",
                    "http://www.w3.org/2001/XMLSchema#date"),
            '"2026-01-01"^^<http://www.w3.org/2001/XMLSchema#date>')

    def test_type_and_inverse_path_render(self) -> None:
        ir = GraphQueryIR(select_vars=["?entity"])
        ir.patterns.extend([
            TypeScan("?entity", CNFO + "Fund"),
            PathJoin("?entity", CNFO + "hasFundManager",
                     "?manager", inverse=True),
        ])
        sparql = render_ir(ir)
        self.assertIn("^<" + CNFO + "hasFundManager>", sparql)
        self.assertIn("rdf-syntax-ns#type>/<http://www.w3.org/2000/01/"
                      "rdf-schema#subClassOf>*", sparql)

    def test_aggregate_select_is_parseable_shape(self) -> None:
        plan = {
            "target": {"concept": CNFO + "FundManagerPerson"},
            "related": {"concept": CNFO + "Fund"},
            "relation_path": [{
                "property": CNFO + "hasFundManager",
                "inverse": True,
            }],
            "aggregations": [{
                "func": "count",
                "having": {"operator": ">=", "value": 2},
            }],
            "ordering": [{"by": "agg", "direction": "desc"}],
            "pagination": {"limit": 1, "offset": 0},
        }
        sparql = build_select(plan)
        self.assertIn("(COUNT(DISTINCT ?a1) AS ?agg)", sparql)
        self.assertIn("HAVING (COUNT(DISTINCT ?a1) >= 2)", sparql)
        self.assertIn("ORDER BY DESC(?agg)", sparql)

    def test_count_mode_counts_result_variable(self) -> None:
        plan = {
            "select": "count",
            "target": {"concept": CNFO + "Fund"},
            "source": {"entity": "https://ontology.example.cn/cnfo/abox/U001113"},
            "traversals": [{
                "property": CNFO + "hasFundManager",
                "inverse": False,
            }],
            "pagination": {"limit": None, "offset": 0},
        }
        sparql = build_select(plan)
        self.assertIn("COUNT(DISTINCT ?h1)", sparql)

    def test_order_property_auto_binds_optional(self) -> None:
        plan = {
            "target": {"concept": CNFO + "Fund"},
            "projections": [],
            "ordering": [{
                "by": CNFO + "fundName",
                "direction": "desc",
            }],
            "pagination": {"limit": 5, "offset": 0},
        }
        sparql = build_select(plan)
        self.assertIn("OPTIONAL", sparql)
        self.assertIn("ORDER BY DESC(?p0)", sparql)
        self.assertIn("LIMIT 5", sparql)

    def test_ir_aggregate_dataclass(self) -> None:
        ir = GraphQueryIR(
            mode="aggregate",
            select_vars=["?entity"],
            aggregates=[Aggregate("COUNT", "?fund", "?agg")],
            group_by=["?entity"],
            order_by=[OrderExpr("?agg", "desc")],
        )
        self.assertIn("(COUNT(DISTINCT ?fund) AS ?agg)", render_ir(ir))

    def test_where_or_compiles_as_exists_expression(self) -> None:
        plan = {
            "target": {"concept": CNFO + "Fund"},
            "where": {
                "op": "or",
                "args": [
                    {"op": "filter", "property": CNFO + "fundTypeCode",
                     "operator": "eq", "value": "ETF"},
                    {"op": "filter", "property": CNFO + "fundTypeCode",
                     "operator": "eq", "value": "LOF"},
                ],
            },
            "pagination": {"limit": None, "offset": 0},
        }
        sparql = build_select(plan)
        self.assertIn("FILTER((EXISTS", sparql)
        self.assertIn("||", sparql)
        self.assertIn("'ETF'", sparql)
        self.assertIn("'LOF'", sparql)

    def test_exists_and_not_exists_compile(self) -> None:
        plan = {
            "target": {"concept": CNFO + "Fund"},
            "where": {
                "op": "not_exists",
                "path": [{"property": CNFO + "hasFundManagerRole"}],
                "target": CNFO + "FundManagerRole",
            },
            "pagination": {"limit": None, "offset": 0},
        }
        sparql = build_select(plan)
        self.assertIn("FILTER(NOT EXISTS", sparql)
        self.assertIn("hasFundManagerRole", sparql)
        self.assertIn("FundManagerRole", sparql)

    def test_optional_path_does_not_filter_results(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        plan = plan_find(
            target="Fund",
            tbox=stack.tbox,
            abox=stack.abox,
            ctx=OntologyContext.from_stack(stack),
            optional=[{"path": [{"property": "fundName"}]}],
        )
        self.assertEqual(validate_plan(plan), [])
        result = execute_find(stack, plan)
        self.assertEqual(result.count, 40)
        self.assertIn("OPTIONAL", result.sparql)

    def test_where_planner_rejects_unknown_property(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        plan = plan_find(
            target="Fund",
            tbox=stack.tbox,
            abox=stack.abox,
            where={"op": "filter", "property": "NOPE",
                   "operator": "eq", "value": "x"},
        )
        self.assertTrue(validate_plan(plan))

    def test_numeric_aggregate_and_date_range_are_typed(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        plan = plan_find(
            target="Fund",
            tbox=stack.tbox,
            abox=stack.abox,
            related_class="NetAssetValueRecord",
            relation_path=[{"property": "hasNetAssetValueRecord"}],
            aggregation={
                "func": "avg",
                "measure_property": "fundUnitNetAssetValue",
                "operator": ">",
                "value": 1,
            },
            date_ranges=[{
                "property": "valuationDate",
                "on": "related",
                "from": "2025-04-01",
                "to": "2025-04-30",
            }],
            ctx=OntologyContext.from_stack(stack),
        )
        self.assertEqual(validate_plan(plan), [])
        sparql = build_select(plan)
        self.assertIn("(AVG(?measure) AS ?agg)", sparql)
        self.assertIn("HAVING (AVG(?measure) > 1)", sparql)
        self.assertIn(
            '"2025-04-01"^^<http://www.w3.org/2001/XMLSchema#date>',
            sparql,
        )

    def test_latest_record_uses_grouped_max_subquery(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        plan = plan_find(
            target="Fund",
            tbox=stack.tbox,
            abox=stack.abox,
            related_class="NetAssetValueRecord",
            relation_path=[{"property": "hasNetAssetValueRecord"}],
            latest={"date_property": "valuationDate"},
            ctx=OntologyContext.from_stack(stack),
        )
        self.assertEqual(validate_plan(plan), [])
        sparql = build_select(plan)
        self.assertIn("SELECT ?entity (MAX(?latestDateValue) AS ?latestDate)", sparql)
        self.assertIn("?a1 <", sparql)
        self.assertIn("?a1 <" + CNFO + "valuationDate> ?latestDate", sparql)

    def test_latest_subquery_applies_related_date_window(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        plan = plan_find(
            target="Fund",
            tbox=stack.tbox,
            abox=stack.abox,
            related_class="NetAssetValueRecord",
            relation_path=[{"property": "hasNetAssetValueRecord"}],
            date_ranges=[{
                "property": "valuationDate",
                "on": "related",
                "from": "2025-04-01",
                "to": "2025-04-30",
            }],
            latest={"date_property": "valuationDate"},
            ctx=OntologyContext.from_stack(stack),
        )
        self.assertEqual(validate_plan(plan), [])
        sparql = build_select(plan)
        self.assertGreaterEqual(sparql.count(
            '"2025-04-01"^^<http://www.w3.org/2001/XMLSchema#date>'), 2)

    def test_numeric_aggregate_requires_related_class(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        plan = plan_find(
            target="Fund",
            tbox=stack.tbox,
            abox=stack.abox,
            relation_path=[{"property": "hasNetAssetValueRecord"}],
            aggregation={
                "func": "avg",
                "measure_property": "fundUnitNetAssetValue",
            },
            ctx=OntologyContext.from_stack(stack),
        )
        self.assertTrue(any("related_class" in error for error in plan["errors"]))


if __name__ == "__main__":
    unittest.main()
