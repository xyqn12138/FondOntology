"""聚合/排名/计数问法回归：Ontology 驱动的 Semantic Querying（Stage 3）。

覆盖用户设计的核心边界——"Ontology 不可能预计算所有答案，Query 阶段
Ontology 给 LLM/规则提供可以进行语义推理的世界模型"：
- 意图：聚合句型（"同时管理多个"）→ target + relation_path + COUNT>=N
- 规划：domain/range 关系约束（非法属性/路径拒绝）
- 执行：GROUP BY/HAVING/ORDER BY/LIMIT 端到端，期望值动态计算（不锁数据）
"""
from __future__ import annotations

import unittest
from pathlib import Path

from fondontology.qa.abox_query import execute_find
from fondontology.qa.engine import answer_question
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.intent import build_intent
from fondontology.qa.query_planner import plan_find
from fondontology.qa.semantics import OntologyContext

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
CNFO = "https://ontology.example.cn/cnfo/ontology/"


def _manager_fund_counts(stack) -> dict:
    """ground truth：经理 → 在管基金数（推理图直接 SPARQL，与被测链路独立）。"""
    g = stack.query_graph(with_abox_inferred=True)
    rows = g.query(
        "SELECT ?m (COUNT(DISTINCT ?f) AS ?n) WHERE {"
        f"  ?f <{CNFO}hasFundManager> ?m ."
        f"  ?m <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{CNFO}FundManagerPerson> ."
        "} GROUP BY ?m")
    return {str(r[0]): int(r[1]) for r in rows}


class AggregateIntentTest(unittest.TestCase):
    """确定性意图：聚合/排名/计数句型（LLM 路径的兜底等价物）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    def intent(self, q: str):
        return build_intent(q, self.index, use_llm=False)

    def test_multi_management_aggregation(self) -> None:
        r = self.intent("同时管理多个基金的基金经理有什么？")
        self.assertEqual(r.status, "RESOLVED")
        self.assertIn("FundManagerPerson", r.intent["target_class"])
        self.assertEqual(r.intent["aggregation"],
                         {"func": "count", "operator": ">=", "value": 2})
        self.assertIn("Fund", r.intent["related_class"])
        hops = [(p["property"].rsplit("/", 1)[-1], p["inverse"])
                for p in r.intent["relation_path"]]
        self.assertEqual(hops, [("hasFundManager", True)])

    def test_rank_top1(self) -> None:
        r = self.intent("在管基金最多的基金经理是谁？")
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual(r.intent["aggregation"], {"func": "count"})
        self.assertEqual(r.intent["ordering"], [{"by": "agg", "direction": "desc"}])
        self.assertEqual(r.intent["limit"], 1)

    def test_count_select(self) -> None:
        r = self.intent("有多少位基金经理")
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual(r.intent.get("select"), "count")

    def test_plain_find_not_hijacked(self) -> None:
        # 无触发词的普通问法不进入聚合语义
        r = self.intent("有哪些交易型开放式指数基金")
        self.assertEqual(r.status, "RESOLVED")
        self.assertNotIn("aggregation", r.intent)
        self.assertNotIn("relation_path", r.intent)


class AggregatePlannerTest(unittest.TestCase):
    """约束感知规划：domain/range 关系约束进入计划层。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.ctx = OntologyContext.from_stack(cls.stack)

    def test_filter_domain_conflict_rejected(self) -> None:
        # fundTypeCode 的 domain 是 Fund，用在 FundManagerPerson 上属语义非法
        plan = plan_find(target="FundManagerPerson", tbox=self.stack.tbox,
                         abox=self.stack.abox,
                         filters=[{"property": "fundTypeCode", "operator": "eq",
                                   "value": "ETF"}],
                         ctx=self.ctx)
        self.assertTrue(plan["errors"])
        self.assertIn("关系约束", plan["errors"][0])

    def test_relation_path_valid(self) -> None:
        plan = plan_find(target="FundManagerPerson", tbox=self.stack.tbox,
                         abox=self.stack.abox,
                         related_class="Fund",
                         relation_path=[{"property": "hasFundManager", "inverse": True}],
                         aggregation={"func": "count", "operator": ">=", "value": 2},
                         ctx=self.ctx)
        self.assertEqual(plan["errors"], [])
        self.assertEqual(plan["aggregations"][0]["having"],
                         {"operator": ">=", "value": 2})

    def test_relation_path_domain_conflict_rejected(self) -> None:
        # 正向 hasFundManager 的 domain 是 Fund；从 FundManagerPerson 正向走非法
        plan = plan_find(target="FundManagerPerson", tbox=self.stack.tbox,
                         abox=self.stack.abox,
                         related_class="Fund",
                         relation_path=[{"property": "hasFundManager", "inverse": False}],
                         aggregation={"func": "count"},
                         ctx=self.ctx)
        self.assertTrue(plan["errors"])

    def test_aggregation_requires_path(self) -> None:
        plan = plan_find(target="FundManagerPerson", tbox=self.stack.tbox,
                         abox=self.stack.abox,
                         aggregation={"func": "count"}, ctx=self.ctx)
        self.assertTrue(any("relation_path" in e for e in plan["errors"]))


class AggregateE2ETest(unittest.TestCase):
    """端到端：期望值由独立 SPARQL 动态计算（不锁仿真数据规模）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.truth = _manager_fund_counts(cls.stack)

    def test_multi_management_answer(self) -> None:
        expected = {m for m, n in self.truth.items() if n >= 2}
        self.assertTrue(expected, "仿真数据应包含多管经理（生成器四分之一区段共享）")
        ans = answer_question("同时管理多个基金的基金经理有什么？",
                              self.stack, use_llm=False)
        self.assertEqual(ans.status, "ok")
        self.assertEqual(ans.report["unresolved"], [])
        rows = set(ans.report["evidence"][0]["rows"])
        self.assertEqual(rows, expected)
        # measures 全部 >= 2，且 C1 claim 带聚合约束描述
        measures = ans.report["evidence"][0].get("measures", {})
        self.assertTrue(all(v >= 2 for v in measures.values()))
        c1 = ans.report["claims"][0]
        self.assertIn(">= 2", c1["claim"])

    def test_rank_top1_answer(self) -> None:
        top_n = max(self.truth.values())
        top_set = {m for m, n in self.truth.items() if n == top_n}
        ans = answer_question("在管基金最多的基金经理是谁？",
                              self.stack, use_llm=False)
        self.assertEqual(ans.status, "ok")
        rows = ans.report["evidence"][0]["rows"]
        # LIMIT 1：并列第一时任取其一，但必须是真第一且度量值正确
        self.assertEqual(len(rows), 1)
        self.assertIn(rows[0], top_set)
        self.assertEqual(ans.report["evidence"][0]["measures"][rows[0]],
                         float(top_n))

    def test_count_answer(self) -> None:
        ans = answer_question("有多少位基金经理", self.stack, use_llm=False)
        self.assertEqual(ans.status, "ok")
        # 经理总数 = 有在管基金的经理 + 有意保留的在职未分派经理
        total = ans.report["evidence"][0]["row_count"]
        self.assertGreaterEqual(total, len(self.truth))


class LLMSemanticParseTest(unittest.TestCase):
    """LLM 语义解析（mock 传输层，不依赖外部 API）。

    验证三阶段设计的关键闭环：本体语义视图注入 prompt → LLM 输出 SemanticParse
    → 本体白名单 + domain/range 校验 → 可用的聚合查询计划。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    @staticmethod
    def _payload(**over) -> dict:
        base = {
            "operation": "find", "target": "FundManagerPerson", "select": "entities",
            "related": "Fund",
            "relation_path": [{"property": "hasFundManager", "inverse": True}],
            "aggregation": {"func": "count", "operator": ">=", "value": 2},
            "order_by": None, "order_direction": "desc", "limit": None,
            "entity_label": None, "filters": [],
            "verify_subject": None, "verify_object": None, "verify_relation": None,
        }
        base.update(over)
        return base

    def test_prompt_contains_semantic_view(self) -> None:
        # prompt 必须注入类层级 + 类间关系（LLM 的 world model），而非裸类名表
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        captured: dict = {}

        def fake_call(prompt: str):
            captured["prompt"] = prompt
            return self._payload()

        with mock.patch.object(intent_mod, "_call_deconstructor", side_effect=fake_call):
            r = intent_mod.build_intent("同时管理多个基金的基金经理有什么？",
                                        self.index, use_llm=True)
        self.assertTrue(r.used_llm)
        p = captured["prompt"]
        self.assertIn("类间关系", p)
        self.assertIn("FundManagerPerson", p)
        self.assertIn("hasFundManager", p)
        self.assertIn("FundManagerPerson(基金经理)", p)

    def test_llm_multi_management_parse(self) -> None:
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        with mock.patch.object(intent_mod, "_call_deconstructor",
                               return_value=self._payload()):
            r = intent_mod.build_intent("同时管理多个基金的基金经理有什么？",
                                        self.index, use_llm=True)
        self.assertEqual(r.status, "RESOLVED")
        self.assertTrue(r.used_llm)
        self.assertIn("FundManagerPerson", r.intent["target_class"])
        self.assertEqual(r.intent["aggregation"],
                         {"func": "count", "operator": ">=", "value": 2})
        self.assertEqual([(p["property"].rsplit("/", 1)[-1], p["inverse"])
                          for p in r.intent["relation_path"]],
                         [("hasFundManager", True)])

    def test_llm_path_auto_discovery(self) -> None:
        # LLM 只给 related 不给 relation_path → 本体关系图自动发现路径
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        payload = self._payload(related="Fund", relation_path=None)
        with mock.patch.object(intent_mod, "_call_deconstructor", return_value=payload):
            r = intent_mod.build_intent("同时管理多个基金的基金经理有什么？",
                                        self.index, use_llm=True)
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual([(p["property"].rsplit("/", 1)[-1], p["inverse"])
                          for p in r.intent["relation_path"]],
                         [("hasFundManager", True)])

    def test_llm_bogus_property_whitelist_rejects(self) -> None:
        # LLM 编造属性 → 白名单拒绝该路径，改由本体关系图发现正确路径
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        payload = self._payload(
            relation_path=[{"property": "managesLotsOfFunds", "inverse": False}])
        with mock.patch.object(intent_mod, "_call_deconstructor", return_value=payload):
            r = intent_mod.build_intent("同时管理多个基金的基金经理有什么？",
                                        self.index, use_llm=True)
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual([(p["property"].rsplit("/", 1)[-1], p["inverse"])
                          for p in r.intent["relation_path"]],
                         [("hasFundManager", True)])

    def test_llm_e2e_answer(self) -> None:
        # mock 意图层 + 真实规划/执行/证据：全链路出正确答案
        #（表达层在无可用 API 时自动模板回退，不影响判定）
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        with mock.patch.object(intent_mod, "_call_deconstructor",
                               return_value=self._payload()), \
             mock.patch.object(intent_mod, "llm_configured", return_value=True):
            ans = answer_question("同时管理多个基金的基金经理有什么？",
                                  self.stack)
        self.assertEqual(ans.status, "ok")
        self.assertIn(">= 2", ans.report["claims"][0]["claim"])


class RelatedFilterTest(unittest.TestCase):
    """关系路径终点类上的属性过滤（"医药基金"句型）。

    investmentFocus 属于 FundInvestmentStrategy 而非 Fund——过滤须沿
    usesInvestmentStrategy 关系落在路径终点，而不是被 domain 约束拒绝。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    @staticmethod
    def _sector_payload(**over) -> dict:
        base = {
            "operation": "find", "target": "EquityFund", "select": "entities",
            "related": "FundInvestmentStrategy",
            "relation_path": [{"property": "usesInvestmentStrategy", "inverse": False}],
            "aggregation": None, "order_by": None, "order_direction": "desc",
            "limit": None, "entity_label": None,
            "filters": [{"property": "investmentFocus",
                         "operator": "contains", "value": "医药"}],
            "verify_subject": None, "verify_object": None, "verify_relation": None,
        }
        base.update(over)
        return base

    def test_related_class_filter_parse(self) -> None:
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        with mock.patch.object(intent_mod, "_call_deconstructor",
                               return_value=self._sector_payload()):
            r = intent_mod.build_intent("医药基金有哪些", self.index, use_llm=True)
        self.assertEqual(r.status, "RESOLVED")
        self.assertIn("EquityFund", r.intent["target_class"])
        self.assertIn("FundInvestmentStrategy", r.intent["related_class"])
        rel_filters = [f for f in r.intent["filters"] if f.get("on") == "related"]
        self.assertEqual(len(rel_filters), 1)
        self.assertIn("investmentFocus", rel_filters[0]["property"])
        self.assertEqual(rel_filters[0]["operator"], "contains")

    def test_related_filter_sparql(self) -> None:
        from fondontology.qa.query_planner import plan_find
        from fondontology.qa.sparql_builder import build_select
        from fondontology.qa.semantics import OntologyContext
        ctx = OntologyContext.from_stack(self.stack)
        plan = plan_find(
            target="EquityFund", tbox=self.stack.tbox, abox=self.stack.abox,
            related_class="FundInvestmentStrategy",
            relation_path=[{"property": "usesInvestmentStrategy", "inverse": False}],
            filters=[{"property": "investmentFocus", "operator": "contains",
                      "value": "医药", "on": "related"}],
            ctx=ctx)
        self.assertEqual(plan.get("errors"), [])
        sparql = build_select(plan)
        self.assertIn("usesInvestmentStrategy", sparql)
        self.assertIn("CONTAINS", sparql)
        self.assertIn("医药", sparql)

    def test_related_filter_e2e(self) -> None:
        # 端到端：医药主题过滤落在策略上，命中仿真数据中的生物医药股票基金
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        with mock.patch.object(intent_mod, "_call_deconstructor",
                               return_value=self._sector_payload()), \
             mock.patch.object(intent_mod, "llm_configured", return_value=True):
            ans = answer_question("医药基金有哪些", self.stack)
        self.assertEqual(ans.status, "ok")
        self.assertEqual(ans.report["evidence"][0]["row_count"], 1)
        self.assertEqual(ans.report["evidence"][0]["rows"],
                         ["https://ontology.example.cn/cnfo/abox/F001288"])

    def test_record_class_not_target(self) -> None:
        # "X的收益怎么样"：target 是基金类本身，业绩记录类只能作 related
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        payload = self._sector_payload(
            target="MoneyMarketFund", related="FundPerformanceRecord",
            relation_path=[{"property": "performanceForFund", "inverse": True}],
            filters=[])
        with mock.patch.object(intent_mod, "_call_deconstructor",
                               return_value=payload):
            r = intent_mod.build_intent("货币基金收益怎么样", self.index, use_llm=True)
        self.assertEqual(r.status, "RESOLVED")
        self.assertIn("MoneyMarketFund", r.intent["target_class"])
        self.assertIn("FundPerformanceRecord", r.intent["related_class"])

    def test_compare_rejected_before_llm(self) -> None:
        # Phase 2 边界两路径一致：对比类问题不进入 LLM 解析
        from unittest import mock
        from fondontology.qa import intent as intent_mod
        with mock.patch.object(intent_mod, "_call_deconstructor") as m:
            r = intent_mod.build_intent("公募基金和私募基金有什么区别",
                                        self.index, use_llm=True)
        self.assertEqual(r.status, "UNRESOLVED")
        self.assertFalse(r.used_llm)
        m.assert_not_called()


if __name__ == "__main__":
    unittest.main()
