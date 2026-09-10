# -*- coding: utf-8 -*-
"""M7-R4.5b：指代消解 v2（LLM 改写器，无规则词典）回归。

架构：语义理解全交 LLM（任意代词/省略/指代形态），确定性代码只留
保真护栏。测试全部 mock LLM 输出锁契约。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from fondontology.qa import coref as coref_mod
from fondontology.qa.coref import _faithful, resolve_coreference
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"

CTX = {"last_question": "魏辉管理的基金有什么",
       "last_answer": "魏辉管理的基金有：磐石现金管理货币市场基金，"
                      "管理人为磐石基金管理有限公司。",
       "last_entities": ["魏辉"]}


class LlmRewriteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    def _resolve(self, q, llm_out, ctx=CTX):
        with mock.patch.object(coref_mod, "_llm_rewrite", return_value=llm_out):
            return resolve_coreference(q, self.index, ctx, use_llm=True)

    def test_pronoun_resolved(self) -> None:
        res = self._resolve("他是哪家公司的",
                            ("魏辉是哪家基金公司的", "魏辉"))
        self.assertTrue(res.resolved)
        self.assertEqual(res.method, "llm")
        self.assertEqual(res.entity, "魏辉")

    def test_company_reference_resolved(self) -> None:
        """复杂指代（这家公司）：LLM 理解为上文答案里的磐石基金公司。"""
        res = self._resolve("这家公司还有别的基金管理人吗",
                            ("磐石基金管理有限公司还有别的基金管理人吗",
                             "磐石基金管理有限公司"))
        self.assertTrue(res.resolved)
        self.assertIn("磐石基金管理有限公司", res.question)

    def test_self_contained_unchanged(self) -> None:
        """自包含问题：LLM 返回原句 → 不算消解。"""
        res = self._resolve("有哪些货币市场基金",
                            ("有哪些货币市场基金", ""))
        self.assertFalse(res.resolved)

    def test_unfaithful_rewrite_rejected(self) -> None:
        """改写偷换主干（持仓→业绩）：保真护栏拦截。"""
        res = self._resolve("它的持仓是什么",
                            ("云帆中证500的业绩表现怎么样", "云帆中证500"))
        self.assertFalse(res.resolved)
        self.assertEqual(res.question, "它的持仓是什么")

    def test_llm_failure_passthrough(self) -> None:
        res = self._resolve("他是哪家公司的", (None, ""))
        self.assertFalse(res.resolved)


class GuardTest(unittest.TestCase):
    def test_no_context_or_no_llm(self) -> None:
        stack = build_stack(SOURCE, ABOX)
        index = OntologyIndex(stack)
        # 无上文 → 直通（不调 LLM）
        with mock.patch.object(coref_mod, "_llm_rewrite") as rw:
            res = resolve_coreference("他是谁", index, None, use_llm=True)
            rw.assert_not_called()
            self.assertFalse(res.resolved)
        # use_llm=False → 直通
        res2 = resolve_coreference("他是谁", index, CTX, use_llm=False)
        self.assertFalse(res2.resolved)

    def test_faithful_2gram(self) -> None:
        self.assertTrue(_faithful("它的持仓是什么",
                                  "云帆中证500的持仓是什么"))
        self.assertFalse(_faithful("它的持仓是什么",
                                   "云帆中证500的业绩表现怎么样"))
        # 代词本身剔除后无实词 → 视为保真（如"它呢"这类纯代词问句）
        self.assertTrue(_faithful("它呢", "云帆中证500怎么样"))


class EngineIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)

    def test_engine_context_flow(self) -> None:
        """engine 带上文 → coref 被调用；改写成功时问题被替换。"""
        from fondontology.qa.engine import answer_question
        with mock.patch.object(
                coref_mod, "resolve_coreference",
                return_value=coref_mod.CorefResult(
                    question="魏辉管理的基金是什么类型",
                    resolved=True, method="llm", entity="魏辉")) as rc:
            ans = answer_question("他管理的基金是什么类型", self.stack,
                                  use_llm=False, context=CTX)
            rc.assert_called_once()
        self.assertEqual(ans.status, "ok")


if __name__ == "__main__":
    unittest.main()
