# -*- coding: utf-8 -*-
"""M7：classify 语义（T-BOX 层 schema 枚举）回归。

「基金有哪些分类」类问题的答案是类清单（读 T-BOX 类层级），
不是实例清单（A-BOX 查询）——这是本体问答的一等能力，不依赖 RAG 开关。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from fondontology.qa import intent as intent_mod
from fondontology.qa.engine import answer_question
from fondontology.qa.evidence import evidence_completeness, validate_citations
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.intent import build_intent

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"

FUND_CHILDREN = 12   # Fund 的直接子类数（v0.6.0 口径）


class ClassifyIntentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    def _intent(self, q: str):
        return build_intent(q, self.index, use_llm=False)

    def test_classify_rule_hits(self) -> None:
        for q in ("基金有哪些分类", "基金有哪些分类概念", "基金分几种",
                  "基金分为哪几类", "基金分了哪几种类型"):
            res = self._intent(q)
            self.assertEqual(res.status, "RESOLVED", q)
            self.assertEqual(res.intent["operation"], "classify", q)
            self.assertTrue(res.intent["topic"].endswith("/Fund"), q)

    def test_find_not_hijacked(self) -> None:
        """实例列举问法不得被 classify 劫持（「有哪些」是弱标记）。"""
        for q in ("基金有哪些", "货币市场基金有哪些", "有哪些交易型开放式指数基金",
                  "基金有多少只"):
            res = self._intent(q)
            self.assertNotEqual(res.intent.get("operation"), "classify", q)
            if res.status == "RESOLVED":
                self.assertEqual(res.intent.get("operation"), "find", q)

    def test_leaf_class_classify_answers_honestly(self) -> None:
        """叶类（货币市场基金）无子类：可命中但答案如实说明，不编造。"""
        res = self._intent("货币基金有哪些类型")
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["operation"], "classify")
        self.assertTrue(res.intent["topic"].endswith("/MoneyMarketFund"))

    def test_llm_classification_scheme_redirected(self) -> None:
        """LLM 把目录类解为 find target 时自动改路由 classify。"""
        with mock.patch.object(intent_mod, "_call_deconstructor", return_value={
                "operation": "find", "target": "FundClassification",
                "select": "entities"}):
            res = build_intent("基金有哪些分类", self.index, use_llm=True)
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["operation"], "classify")
        self.assertTrue(res.intent["topic"].endswith("/Fund"))
        self.assertTrue(any("目录类" in n for n in res.notes))

    def test_llm_classify_operation_accepted(self) -> None:
        with mock.patch.object(intent_mod, "_call_deconstructor", return_value={
                "operation": "classify", "target": "Fund"}):
            res = build_intent("基金有哪些分类", self.index, use_llm=True)
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["operation"], "classify")


class ClassifyAnswerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)

    def test_fund_classification_answer(self) -> None:
        ans = answer_question("基金有哪些分类", self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("classify", "ok"))
        # 12 个分类维度（公募/私募/开放/封闭/股/债/混/货/FOF/跨境/政府/证券）
        self.assertIn("12 个直接子类", ans.text)
        for dim in ("公募基金", "私募基金", "开放式基金", "封闭式基金", "货币市场基金"):
            self.assertIn(dim, ans.text)
        # 证据合同：每条 claim 有 T-BOX 定义卡证据，引用零越权
        ok, problems = evidence_completeness(ans.report)
        self.assertTrue(ok, str(problems))
        self.assertEqual(validate_citations(ans.report), [])
        self.assertEqual(len(ans.report["evidence"]), FUND_CHILDREN)

    def test_leaf_class_honest_answer(self) -> None:
        ans = answer_question("货币基金有哪些类型", self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("classify", "ok"))
        self.assertIn("未声明直接子类", ans.text)

    def test_delta_stream_contract(self) -> None:
        """classify 答案同样走 on_text_delta（SSE 流式契约）。"""
        chunks: list[str] = []
        ans = answer_question("基金有哪些分类", self.stack, use_llm=False,
                              on_text_delta=chunks.append)
        self.assertEqual("".join(chunks), ans.text)


class DefineIntentTest(unittest.TestCase):
    """define 一等能力：定义问法不依赖 RAG 开关，含口语容差。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    def _intent(self, q: str):
        return build_intent(q, self.index, use_llm=False)

    def test_define_rule_hits_variants(self) -> None:
        for q, topic in (
            ("什么是ETF", "ExchangeTradedFund"),
            ("ETF指什么", "ExchangeTradedFund"),
            ("开放式基金是什么意思", "OpenEndedFund"),
            ("货币市场基金的定义", "MoneyMarketFund"),
            ("何为基金中基金", "FundOfFunds"),
        ):
            res = self._intent(q)
            self.assertEqual(res.status, "RESOLVED", q)
            self.assertEqual(res.intent["operation"], "explain", q)
            self.assertEqual(res.intent["explain_type"], "define", q)
            self.assertTrue(res.intent["topic"].endswith(f"/{topic}"), q)

    def test_define_colloquial_tolerance(self) -> None:
        """口语形近变体归一：「开放型基金」→「开放式基金」。"""
        for q, topic in (("开放型基金指什么", "OpenEndedFund"),
                         ("封闭型基金是什么", "ClosedEndedFund")):
            res = self._intent(q)
            self.assertEqual(res.status, "RESOLVED", q)
            self.assertTrue(res.intent["topic"].endswith(f"/{topic}"),
                            f"{q} 应锚定 {topic}，实际 {res.intent['topic']}")

    def test_define_answer_reads_tbox(self) -> None:
        ans = answer_question("ETF指什么", self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("explain", "ok"))
        self.assertIn("交易型开放式指数基金", ans.text)
        self.assertIn("指数", ans.text)
        ok, problems = evidence_completeness(ans.report)
        self.assertTrue(ok, str(problems))

    def test_llm_define_operation_accepted(self) -> None:
        with mock.patch.object(intent_mod, "_call_deconstructor", return_value={
                "operation": "explain", "target": "ExchangeTradedFund",
                "explain_type": "define"}):
            res = build_intent("ETF指什么", self.index, use_llm=True)
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["operation"], "explain")
        self.assertEqual(res.intent["explain_type"], "define")

    def test_find_questions_still_go_find(self) -> None:
        """定义问法放开后，实例列举不受影响。"""
        ans = answer_question("交易型开放式指数基金有哪些",
                              self.stack, use_llm=False)
        self.assertEqual(ans.kind, "find")
        self.assertIn("共找到", ans.text)


if __name__ == "__main__":
    unittest.main()
