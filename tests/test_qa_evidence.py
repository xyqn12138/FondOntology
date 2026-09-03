"""M3：证据合同回归（Claim-Evidence Map / provenance chain / 引用校验）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import URIRef

from fondontology.qa.abox_query import execute_find
from fondontology.qa.evidence import (
    EvidenceBuilder, evidence_completeness, validate_citations,
)
from fondontology.qa.graph import build_stack
from fondontology.qa.query_planner import plan_find
from fondontology.qa.verify import verify

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


class EvidenceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.builder = EvidenceBuilder(cls.stack)

    def test_find_report_complete_and_cited(self) -> None:
        plan = plan_find(target="ExchangeTradedFund", tbox=self.stack.tbox, abox=self.stack.abox)
        result = execute_find(self.stack, plan)
        report = self.builder.build_for_find(plan, result, max_subgraph_entities=8)
        self.assertEqual(result.count, 4)
        # 证据完整度：每条 claim 有证据且 id 存在
        ok, problems = evidence_completeness(report)
        self.assertTrue(ok, problems)
        # 引用校验零越权
        self.assertEqual(validate_citations(report), [])
        # 至少包含 query 证据与实体分类证据
        kinds = {e["kind"] for e in report["evidence"]}
        self.assertIn("query", kinds)
        self.assertTrue({"declared", "inference"} & kinds)
        # 推理证据必须带 premises/derived（provenance chain）
        for e in report["evidence"]:
            if e["kind"] == "inference":
                self.assertTrue(e.get("premises"))
            self.assertIn("premises", e)
            self.assertIn("derived", e)
        # meta 携带本体/数据版本哈希
        meta = report["meta"]
        self.assertEqual(meta["ontology"]["version"], "0.5.3")
        self.assertTrue(meta["abox"]["hash"])

    def test_inference_evidence_has_rule_and_chain_source(self) -> None:
        # FundPositionRecord：ABOX 只声明 FundPosition/PortfolioPosition（均 ⊑
        # FundPositionRecord），成员资格只能经 TBOX 子类链到达 → inference 证据
        plan = plan_find(target="FundPositionRecord", tbox=self.stack.tbox, abox=self.stack.abox)
        result = execute_find(self.stack, plan)
        self.assertEqual(result.count, 941)  # 706 投资者持仓 + 235 组合持仓
        report = self.builder.build_for_find(plan, result, max_subgraph_entities=3)
        inference_ev = [e for e in report["evidence"] if e["kind"] == "inference"]
        self.assertTrue(inference_ev)
        self.assertEqual(inference_ev[0].get("rule"), "rdfs:subClassOf")
        self.assertTrue(inference_ev[0].get("source"))  # 链边
        self.assertTrue(inference_ev[0].get("premises"))  # 声明类型证据前置

    def test_citation_validation_rejects_unknown_id(self) -> None:
        plan = plan_find(target="Fund", tbox=self.stack.tbox, abox=self.stack.abox, limit=5)
        result = execute_find(self.stack, plan)
        report = self.builder.build_for_find(plan, result)
        self.assertEqual(validate_citations(report, ["E99", "NOPE"]), ["E99", "NOPE"])

    def test_verify_unknown_has_open_world_evidence(self) -> None:
        graph = self.stack.query_graph()
        result = verify(graph, "ExchangeTradedFund", "subClassOf", "MoneyMarketFund")
        self.assertEqual(result.answer, "UNKNOWN")
        report = self.builder.build_for_verify("verify", result)
        ok, problems = evidence_completeness(report)
        self.assertTrue(ok, problems)
        self.assertEqual(validate_citations(report), [])
        # UNKNOWN 也有查询证据（ASK 未发现链）
        self.assertTrue(any(e["kind"] == "query" and "ASK" in e.get("sparql", "")
                            for e in report["evidence"]))

    def test_verify_entailed_claim_backed_by_chain(self) -> None:
        graph = self.stack.query_graph()
        result = verify(graph, "ExchangeTradedFund", "subClassOf", "Fund")
        report = self.builder.build_for_verify("verify", result)
        ok, problems = evidence_completeness(report)
        self.assertTrue(ok, problems)
        self.assertEqual(validate_citations(report), [])
        self.assertTrue(any(e["kind"] == "declared" for e in report["evidence"]))


if __name__ == "__main__":
    unittest.main()