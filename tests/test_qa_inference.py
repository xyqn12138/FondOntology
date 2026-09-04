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
        # 分类 claim 应引用推理证据（E5 类）
        c3 = [c for c in ans.report["claims"] if c.get("type") == "classification"][0]
        self.assertTrue(any(eid in c3["evidence"] for eid in {e["id"] for e in infer_ev}))


if __name__ == "__main__":
    unittest.main()