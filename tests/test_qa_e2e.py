"""M3：确定性端到端回归（手工 Intent → QueryPlan → SPARQL → Evidence → 模板）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from fondontology.qa.context import SliceBudget
from fondontology.qa.engine import answer
from fondontology.qa.evidence import evidence_completeness, validate_citations
from fondontology.qa.graph import build_stack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


class DeterministicE2eTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)

    def ask(self, intent: dict):
        return answer(self.stack, intent, slice_budget=SliceBudget())

    def test_find_answer_and_evidence_contract(self) -> None:
        ans = self.ask({"operation": "find", "target": "ExchangeTradedFund"})
        self.assertEqual(ans.status, "ok")
        self.assertIn("共找到 4 个", ans.text)
        self.assertTrue(ans.report)
        ok, problems = evidence_completeness(ans.report)
        self.assertTrue(ok, problems)
        self.assertEqual(validate_citations(ans.report), [])

    def test_find_two_hop_traversal(self) -> None:
        ans = self.ask({"operation": "find", "target": "Fund",
                        "traversals": [
                            {"property": "hasFundManagerRole"},
                            {"property": "rolePlayedBy",
                             "filter": {"kind": "label", "value": "磐石基金管理有限公司"}}]})
        self.assertEqual(ans.status, "ok")
        self.assertIn("共找到 10 个", ans.text)

    def test_slice_truncated_with_tiny_budget(self) -> None:
        tiny = SliceBudget(max_classes=3, max_properties=8, max_triples=200, max_context_tokens=500)
        ans = answer(self.stack, {"operation": "find", "target": "Fund"}, slice_budget=tiny)
        self.assertEqual(ans.status, "ok")
        self.assertTrue(ans.local_context["ontology_slice"]["truncated"])
        self.assertIn("切片", ans.text)  # 模板显式标注简答

    def test_verify_entailed_and_unknown(self) -> None:
        a1 = self.ask({"operation": "verify", "subject": "ExchangeTradedFund",
                       "relation": "subClassOf", "object": "OpenEndedFund"})
        self.assertEqual((a1.status, a1.verdict), ("ok", "ENTAILED"))
        a2 = self.ask({"operation": "verify", "subject": "ExchangeTradedFund",
                       "relation": "subClassOf", "object": "MoneyMarketFund"})
        self.assertEqual((a2.status, a2.verdict), ("ok", "UNKNOWN"))
        self.assertIn("开放世界", a2.text)
        ok, problems = evidence_completeness(a2.report)
        self.assertTrue(ok, problems)

    def test_invalid_intents(self) -> None:
        self.assertEqual(self.ask({"operation": "find", "target": "NOPE"}).status, "invalid")
        self.assertEqual(self.ask({"operation": "verify", "subject": "Fund",
                                   "relation": "subClassOf", "object": "不存在"}).status, "invalid")
        self.assertEqual(self.ask({"operation": "bogus"}).status, "invalid")

    def test_verify_does_not_touch_abox(self) -> None:
        # verify 证据合同的 meta 明确 query_graph = TBOX（零 A-BOX 访问）
        ans = self.ask({"operation": "verify", "subject": "ExchangeTradedFund",
                        "relation": "subClassOf", "object": "Fund"})
        self.assertIn("TBOX", ans.report["meta"]["reasoning"]["query_graph"])
        self.assertNotIn("ABOX", ans.report["meta"]["reasoning"]["query_graph"])


if __name__ == "__main__":
    unittest.main()