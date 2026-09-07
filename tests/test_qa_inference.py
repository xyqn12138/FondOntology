"""推理层回归：定向物化（property chain / inverse 传播）、查询图生效、证据归因。"""
from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Namespace, URIRef

from fondontology.qa.engine import answer_question
from fondontology.qa.graph import build_stack
from fondontology.qa.query_planner import plan_find
from fondontology.qa.sparql_builder import build_select

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")


class InferenceLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.stack.query_graph(with_abox_inferred=True)  # 触生物化

    def test_chain_fact_materialized_with_rule_and_premises(self) -> None:
        fact = (URIRef(str(CNFOA) + "F005377"),
                URIRef(str(CNFO) + "hasFundManager"),
                URIRef(str(CNFOA) + "Manager005377"))
        reg = self.stack.inference_registry
        self.assertIn(fact, reg)
        self.assertEqual(reg[fact]["rule"],
                         "property_chain:hasFundManagerRole∘rolePlayedBy")
        self.assertEqual(len(reg[fact]["premises"]), 2)

    def test_inverse_propagation(self) -> None:
        # 40 位绑定经理经 playsFundRole 逆传播进入角色承担者
        inverse_facts = {f for f, v in self.stack.inference_registry.items()
                         if v["rule"] == "inverse:playsFundRole"}
        self.assertEqual(len(inverse_facts), 40)

    def test_inferred_graph_contains_facts(self) -> None:
        g = self.stack.query_graph(with_abox_inferred=True)
        self.assertIn((URIRef(str(CNFOA) + "F005377"),
                       URIRef(str(CNFO) + "hasFundManager"),
                       URIRef(str(CNFOA) + "Manager005377")), g)

    def test_planner_preserves_inverse(self) -> None:
        plan = plan_find(target="Fund", tbox=self.stack.tbox, abox=self.stack.abox,
                         source="Manager005377",
                         traversals=[{"property": "hasFundManager", "inverse": True}])
        self.assertEqual(plan["traversals"][0]["inverse"], True)
        sparql = build_select(plan)
        self.assertIn("^<https://ontology.example.cn/cnfo/ontology/hasFundManager>", sparql)

    def test_anchor_query_uses_inference_edge(self) -> None:
        # 魏辉：意图解析出经理锚点 → 推理边 hasFundManager（反向）→ 1 只基金
        from fondontology.qa.engine import _get_index
        from fondontology.qa.intent import build_intent
        index = _get_index(self.stack)
        r = build_intent("魏辉的基金有什么？", index)
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual([t.get("inverse") for t in r.intent["traversals"]], [True])

    def test_evidence_contains_inference_attribution(self) -> None:
        ans = answer_question("魏辉的基金有什么？", self.stack, use_llm=False)
        self.assertEqual(ans.status, "ok")
        infer_ev = [e for e in ans.report["evidence"] if e["kind"] == "inference"
                    and e.get("rule", "").startswith("property_chain")]
        self.assertTrue(infer_ev)
        # 推理证据必须带前提证据 id，且前提证据也在集合中
        eids = {e["id"] for e in ans.report["evidence"]}
        for e in infer_ev:
            self.assertTrue(e["premises"])
            self.assertTrue(set(e["premises"]) <= eids)
        # 锚点查询的关系 claim（「基金」具有基金管理人「魏辉」）应引用推理证据
        rel = [c for c in ans.report["claims"]
               if c.get("type") == "fact" and "魏辉" in c.get("claim", "")]
        self.assertTrue(rel, "缺锚点关系 claim")
        self.assertTrue(any(eid in rel[0]["evidence"] for eid in {e["id"] for e in infer_ev}))
        # 锚点查询不再产出"属于 Fund"式同义反复的分类 claim
        self.assertFalse([c for c in ans.report["claims"]
                          if c.get("type") == "classification"])

    def test_fund_anchor_compound_e2e(self) -> None:
        # 基金锚点复合链：恒信货币（F005659）→ 经理陶凯 → 其管理的其他基金；
        # pivot claim 须给出经理名（表达层只消费 claims），锚点自身被排除
        ans = answer_question(
            "恒信货币货币市场基金的基金经理是谁，他除了这个基金还有管理别的基金吗",
            self.stack, use_llm=False)
        self.assertEqual(ans.status, "ok")
        claim_texts = [c["claim"] for c in ans.report["claims"]]
        self.assertTrue(any("陶凯" in t for t in claim_texts),
                        f"pivot claim 未给出经理名：{claim_texts}")
        self.assertTrue(any("恒信流动性管理货币市场基金" in t for t in claim_texts),
                        f"结果未含陶凯管理的另一只货币基金：{claim_texts}")
        rows = ans.report["evidence"][0]["rows"]
        self.assertNotIn(str(CNFOA) + "F005659", rows)  # 锚点自身被 exclusions 排除
        # 管理公司不得混入 pivot（FundParty range 被 to=FundManagerPerson 收窄）
        self.assertFalse(any("恒信基金管理有限公司" in t for t in claim_texts),
                         f"管理公司混入结果：{claim_texts}")


if __name__ == "__main__":
    unittest.main()