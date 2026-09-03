"""M5：表达层回归（LLM 引用闸门 / 模板回退 / NL 全链路入口）。"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from fondontology.qa import explainer
from fondontology.qa.engine import answer_question
from fondontology.qa.evidence import EvidenceBuilder
from fondontology.qa.graph import build_stack
from fondontology.qa.query_planner import plan_find

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


class _StubVerifyResult:
    def __init__(self, answer="ENTAILED", chain=None, note=None, reason=None):
        self.answer = answer
        self.chain = chain or [{"s": "A", "p": "rdfs:subClassOf", "o": "B"}]
        self.subject = "ExchangeTradedFund"
        self.relation = "subClassOf"
        self.object = "OpenEndedFund"
        self.basis = "taxonomy"
        self.note = note
        self.reason = reason


class ExplainerGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.builder = EvidenceBuilder(cls.stack)
        plan = plan_find(target="ExchangeTradedFund", tbox=cls.stack.tbox, abox=cls.stack.abox)
        from fondontology.qa.abox_query import execute_find
        cls.report = cls.builder.build_for_find(
            plan, execute_find(cls.stack, plan), max_subgraph_entities=4)

    def test_no_key_uses_template_and_zero_ucr(self) -> None:
        exp = explainer.explain("有哪些ETF", self.report, use_llm=False)
        self.assertEqual(exp.gate, "template_nokey")
        self.assertEqual(exp.ucr, 0.0)
        self.assertTrue(exp.text)
        self.assertTrue(exp.claims_used)

    def test_valid_llm_sentences_pass_gate(self) -> None:
        with mock.patch.object(explainer, "_llm_chat", return_value={
            "answer_sentences": [
                {"text": "共有4只交易型开放式指数基金。", "claim_id": "C1"},
                {"text": "包括磐石创业板指ETF等。", "claim_id": "C2"},
            ]}):
            exp = explainer.explain("有哪些ETF", self.report, use_llm=True)
        self.assertEqual(exp.gate, "llm_validated")
        self.assertEqual(exp.ucr, 0.0)
        self.assertTrue(exp.used_llm)

    def test_invalid_citations_retry_then_fallback(self) -> None:
        # 第一次越权（E99），第二次仍越权（C999）→ 重试耗尽 → 模板回退；
        # 终态 UCR=0（全部句子有 claim 支撑），越权数记于 violations_before_gate
        calls = iter([
            {"answer_sentences": [{"text": "胡说", "claim_id": "E99"}]},
            {"answer_sentences": [{"text": "乱讲", "claim_id": "C999"}]},
        ])
        with mock.patch.object(explainer, "_llm_chat", side_effect=lambda *a, **k: next(calls)):
            exp = explainer.explain("有哪些ETF", self.report, use_llm=True, retries=1)
        self.assertEqual(exp.gate, "template_fallback")
        self.assertEqual(exp.ucr, 0.0)
        self.assertEqual(exp.violations_before_gate, 2)
        self.assertTrue(exp.claims_used)

    def test_unparsable_llm_output_falls_back(self) -> None:
        with mock.patch.object(explainer, "_llm_chat", return_value=None):
            exp = explainer.explain("有哪些ETF", self.report, use_llm=True)
        self.assertEqual(exp.gate, "template_fallback")
        self.assertEqual(exp.ucr, 0.0)

    def test_verify_explanation(self) -> None:
        report = self.builder.build_for_verify(
            "verify", _StubVerifyResult())
        exp = explainer.verify_explanation(_StubVerifyResult(), report)
        self.assertTrue(exp.text)
        self.assertEqual(exp.ucr, 0.0)


class AnswerQuestionNlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)

    def test_find_question(self) -> None:
        ans = answer_question("有哪些交易型开放式指数基金", self.stack, use_llm=False)
        self.assertEqual(ans.status, "ok")
        self.assertEqual(ans.explanation["gate"], "template_nokey")
        self.assertEqual(ans.explanation["ucr"], 0.0)
        self.assertIn("共找到 4", ans.text)

    def test_verify_question(self) -> None:
        ans = answer_question("交易型开放式指数基金是不是开放式基金", self.stack, use_llm=False)
        self.assertEqual((ans.status, ans.verdict), ("ok", "ENTAILED"))
        self.assertEqual(ans.explanation["ucr"], 0.0)

    def test_unresolved_question(self) -> None:
        ans = answer_question("电磁炉", self.stack, use_llm=False)
        self.assertEqual(ans.status, "unresolved")
        self.assertIn("未能", ans.text)

    def test_ambiguous_question(self) -> None:
        ans = answer_question("混合基金股票基金", self.stack, use_llm=False)
        self.assertEqual(ans.status, "ambiguous")
        self.assertIn("澄清", ans.text)


if __name__ == "__main__":
    unittest.main()