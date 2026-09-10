# -*- coding: utf-8 -*-
"""M7-R2：explain 语义（RAG 路径）回归。

覆盖：
- 意图规则：define / compare / describe(entity) 的命中与解释形态；
- 检索契约：一级（锚定过滤）scope 不泄漏、防串台断言；
- 证据合同：kind=document/definition 证据、claim 引用 ⊆ evidence（复用校验器）；
- 端到端：engine 路由 explain 分支，模板答案可回归。

全部 use_llm=False（确定性路径；LLM 表达接入是 R3）。
"""
from __future__ import annotations

import unittest
from pathlib import Path

from fondontology.qa.engine import answer_question
from fondontology.qa.evidence import evidence_completeness, validate_citations
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.intent import build_intent
from fondontology.qa.rag import get_store, retrieve
from fondontology.qa.semantics import OntologyContext

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


def _set_rag(on: bool) -> None:
    """切换 RAG 总开关（进程内共享，测试结束必须还原，避免污染其他测试）。"""
    import os
    os.environ["RAG_ENABLED"] = "1" if on else ""
FUND_A_CODE = "006494"     # 云帆中证500
FUND_A_LABEL = "云帆中证500指数型证券投资基金"
RIVAL_FUND = "006798"       # 华曦中证500（同简称前缀，防串台探针）


@unittest.skipUnless((ROOT / "artifacts/cnfo/rag/chunks.jsonl").is_file(),
                     "文本资产未生成（先运行 tools/gen_text_assets.py）")
class ExplainIntentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _set_rag(True)
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    @classmethod
    def tearDownClass(cls) -> None:
        _set_rag(False)

    def _intent(self, q: str):
        return build_intent(q, self.index, use_llm=False)

    def test_define_rule_hits(self) -> None:
        res = self._intent("什么是货币市场基金？")
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["operation"], "explain")
        self.assertEqual(res.intent["explain_type"], "define")
        self.assertTrue(res.intent["topic"].endswith("MoneyMarketFund"))

    def test_define_via_suffix(self) -> None:
        res = self._intent("货币市场基金的定义是什么")
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["explain_type"], "define")

    def test_compare_rule_hits(self) -> None:
        res = self._intent("货币市场基金和债券基金有什么区别？")
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["operation"], "explain")
        self.assertEqual(res.intent["explain_type"], "compare")
        self.assertTrue(res.intent["topic"].endswith("MoneyMarketFund"))
        self.assertTrue(res.intent["compare_topic"].endswith("BondFund"))

    def test_describe_entity_rule_hits(self) -> None:
        res = self._intent("介绍一下云帆中证500指数基金")
        self.assertEqual(res.status, "RESOLVED")
        self.assertEqual(res.intent["explain_type"], "describe")
        self.assertTrue(res.intent["entity_iri"])

    def test_describe_outlook_gets_section_hint(self) -> None:
        res = self._intent("杨洋怎么看后市？")
        self.assertEqual(res.intent["explain_type"], "describe")
        self.assertEqual(res.intent["section_hint"], "管理人报告")

    def test_find_questions_not_hijacked_by_explain(self) -> None:
        """列举/聚合类问法不得被 explain 抢路由（回归保护）。"""
        for q in ("货币市场基金有哪些？", "杨洋管理的基金有什么？",
                  "同时管理多个基金的基金经理是谁？"):
            res = self._intent(q)
            self.assertNotEqual(res.intent.get("operation"), "explain",
                                f"{q} 被误路由到 explain")


class RagSwitchTest(unittest.TestCase):
    """RAG 总开关：R3b 起默认开启；关闭时 describe 不可用，
    define/compare 一等能力始终可用。"""

    def test_enabled_by_default(self) -> None:
        import os
        from fondontology.qa.config import rag_enabled
        prev = os.environ.get("RAG_ENABLED")
        try:
            os.environ.pop("RAG_ENABLED", None)
            self.assertTrue(rag_enabled())   # R3b 默认开启
        finally:
            if prev is not None:
                os.environ["RAG_ENABLED"] = prev

    def test_disabled_blocks_describe_only(self) -> None:
        import os
        from fondontology.qa.config import rag_enabled
        stack = build_stack(SOURCE, ABOX)
        index = OntologyIndex(stack)
        prev = os.environ.get("RAG_ENABLED")
        try:
            os.environ["RAG_ENABLED"] = "0"
            self.assertFalse(rag_enabled())
            import fondontology.qa.intent as intent_mod
            # define/compare 读 T-BOX，不受开关限制（一等能力）
            res = intent_mod.build_intent("什么是货币市场基金？", index, use_llm=False)
            self.assertEqual(res.intent.get("explain_type"), "define")
            res_cmp = intent_mod.build_intent(
                "公募基金和私募基金有什么区别", index, use_llm=False)
            self.assertEqual(res_cmp.intent.get("explain_type"), "compare")
            # describe 依赖 chunk 池，受开关控制：关闭时不路由
            res2 = intent_mod.build_intent("介绍一下云帆中证500指数基金", index, use_llm=False)
            self.assertNotEqual(res2.intent.get("explain_type"), "describe")
        finally:
            if prev is None:
                os.environ.pop("RAG_ENABLED", None)
            else:
                os.environ["RAG_ENABLED"] = prev


class RetrieveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _set_rag(True)   # retrieve 本身不读开关，但保持文件内一致
        cls.stack = build_stack(SOURCE, ABOX)
        cls.ctx = OntologyContext.from_stack(cls.stack)
        cls.qg = cls.stack.query_graph()
        cls.store = get_store()

    @classmethod
    def tearDownClass(cls) -> None:
        _set_rag(False)

    def test_anchor_scope_no_leakage(self) -> None:
        """一级检索：基金产品实体锚点 → scope 只含该基金，不混入同简称基金。"""
        entity = f"https://ontology.example.cn/cnfo/abox/Prod{FUND_A_CODE}"
        r = retrieve("介绍一下云帆中证500指数基金", ctx=self.ctx,
                     query_graph=self.qg, entity_iri=entity)
        self.assertTrue(r.anchored)
        self.assertEqual(r.scope_fund_codes, {FUND_A_CODE})
        for c in r.chunks:
            self.assertEqual(c.fund_code, FUND_A_CODE,
                             f"串台：{c.chunk_id}（{c.fund_code}）不在锚定范围")
            self.assertNotEqual(c.fund_code, RIVAL_FUND)

    def test_manager_anchor_expands_to_funds(self) -> None:
        """人物锚点：经理 → 他管的基金集合（图遍历展开）。"""
        # 杨洋管理华曦两只基金（生成器多管分布）
        r = retrieve("杨洋怎么看后市", ctx=self.ctx, query_graph=self.qg,
                     entity_iri=None)   # 无锚点走全局
        self.assertFalse(r.anchored)
        # 经理实体 IRI 需从图上取：Manager006798（华曦经理）
        r2 = retrieve("杨洋怎么看后市", ctx=self.ctx, query_graph=self.qg,
                      entity_iri="https://ontology.example.cn/cnfo/abox/Manager006798",
                      section_hint="管理人报告")
        self.assertTrue(r2.anchored)
        self.assertTrue(r2.scope_fund_codes)
        for c in r2.chunks:
            self.assertIn(c.fund_code, r2.scope_fund_codes)
            if r2.scope_fund_codes == {"006798", "006797"}:
                self.assertEqual(c.section, "管理人报告",
                                 "section_hint 应把管理人报告排到最前")

    def test_bm25_hits_regulation_article(self) -> None:
        """全局二级：R 系代码问题命中适当性条文。"""
        r = retrieve("基金风险等级 R1 到 R5 是什么意思", ctx=self.ctx,
                     query_graph=self.qg)
        self.assertTrue(r.chunks)
        self.assertTrue(any(c.doc_type == "regulation_article" for c in r.chunks),
                        "应命中法规条文 chunk")


@unittest.skipUnless((ROOT / "artifacts/cnfo/rag/chunks.jsonl").is_file(),
                     "文本资产未生成（先运行 tools/gen_text_assets.py）")
class ExplainAnswerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _set_rag(True)
        cls.stack = build_stack(SOURCE, ABOX)

    @classmethod
    def tearDownClass(cls) -> None:
        _set_rag(False)

    def test_define_answer_with_evidence_contract(self) -> None:
        ans = answer_question("什么是货币市场基金？", self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("explain", "ok"))
        self.assertIn("货币市场基金", ans.text)
        self.assertIn("定义", ans.text)
        # 证据合同：claim 引用 ⊆ evidence 集合；每条 claim 有证据
        ok, problems = evidence_completeness(ans.report)
        self.assertTrue(ok, str(problems))
        self.assertEqual(validate_citations(ans.report), [])
        # 定义证据带 locator（可回溯到 T-BOX）
        self.assertTrue(all(e.get("locator") for e in ans.report["evidence"]))

    def test_compare_answer_states_no_disjoint_claim(self) -> None:
        ans = answer_question("货币市场基金和债券基金有什么区别？",
                              self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("explain", "ok"))
        # 本体声明了互斥（AllDisjointClasses 四基金组）→ 应出现互斥判定
        self.assertIn("互斥", ans.text)
        ok, problems = evidence_completeness(ans.report)
        self.assertTrue(ok, str(problems))

    def test_describe_answer_scoped_to_anchor(self) -> None:
        ans = answer_question("介绍一下云帆中证500指数基金", self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("explain", "ok"))
        # 防串台硬断言：答案不得提及同简称前缀的华曦
        self.assertNotIn("华曦", ans.text)
        # 证据 chunk 全部属于锚定基金
        for e in ans.report["evidence"]:
            doc = e["source"][0]
            self.assertIn(FUND_A_CODE, doc, f"证据 {e['id']} 不属于锚定基金")
        ok, problems = evidence_completeness(ans.report)
        self.assertTrue(ok, str(problems))

    def test_describe_outlook_answer(self) -> None:
        ans = answer_question("杨洋怎么看后市？", self.stack, use_llm=False)
        self.assertEqual((ans.kind, ans.status), ("explain", "ok"))
        self.assertIn("管理人报告", ans.text)

    def test_claim_ids_sequential(self) -> None:
        ans = answer_question("什么是货币市场基金？", self.stack, use_llm=False)
        ids = [c["claim_id"] for c in ans.report["claims"]]
        self.assertEqual(ids, [f"C{i}" for i in range(1, len(ids) + 1)],
                         "claim 序号应连续无跳号")


if __name__ == "__main__":
    unittest.main()
