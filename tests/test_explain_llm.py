# -*- coding: utf-8 -*-
"""M7-R3b/c：explain LLM 表达层回归（mock，CI 无网络）。

覆盖：
- 闸门：好引用过（llm_validated）、未知 claim_id 拒绝、空输出拒绝；
- 数组 claim_id：一句多 claim 支撑，证据并集；
- 短语核查：R/C 代码越权拒绝；
- 归属断言核查：claims 原文支持放行 / 图级判定放行 / 均无拒绝；
- 回退：重试耗尽 → template_fallback，文本=模板原文；
- use_llm=False：模板直通（无 LLM 调用）。
"""
from __future__ import annotations

import unittest
from unittest import mock

from fondontology.qa.rag.answer import ExplainAnswer
from fondontology.qa.rag import explain_llm
from fondontology.qa.rag.explain_llm import express_explain


def _template(claims: list[dict], evidence: list[dict], text: str) -> ExplainAnswer:
    return ExplainAnswer(status="ok", text=text,
                         report={"claims": claims, "evidence": evidence})


CLAIMS = [
    {"claim_id": "C1", "type": "fact",
     "claim": "（第八条）基金产品风险等级按风险由低到高至少划分为 R1、R2、R3、R4、R5 五个等级。",
     "evidence": ["R1"]},
    {"claim_id": "C2", "type": "fact",
     "claim": "R4（中高风险）是第四档风险等级。",
     "evidence": ["R1"]},
]
EVIDENCE = [{"id": "R1", "kind": "document", "text": "适当性指引第八条…"}]


class GateTest(unittest.TestCase):
    def _run(self, llm_out, **kw):
        with mock.patch.object(explain_llm, "_explain_chat", return_value=llm_out):
            return express_explain("R4是什么意思", _template(CLAIMS, EVIDENCE, "模板"),
                                   use_llm=True, **kw)

    def test_valid_sentences_pass_gate(self) -> None:
        out = {"answer_sentences": [
            {"text": "R4 是基金产品风险等级中的第四档（中高风险）。", "claim_id": ["C1", "C2"]}]}
        exp = self._run(out)
        self.assertEqual(exp.report["explanation"]["gate"], "llm_validated")
        self.assertIn("[R1]", exp.text)

    def test_unknown_claim_id_rejected(self) -> None:
        out = {"answer_sentences": [
            {"text": "R4 是第四档。", "claim_id": "C999"}]}
        exp = self._run(out)
        self.assertEqual(exp.report["explanation"]["gate"], "template_fallback")
        self.assertEqual(exp.text, "模板")

    def test_none_output_rejected(self) -> None:
        exp = self._run(None)
        self.assertEqual(exp.report["explanation"]["gate"], "template_fallback")

    def test_no_llm_passthrough(self) -> None:
        with mock.patch.object(explain_llm, "_explain_chat") as chat:
            exp = express_explain("R4是什么意思", _template(CLAIMS, EVIDENCE, "模板"),
                                  use_llm=False)
            chat.assert_not_called()
        self.assertEqual(exp.text, "模板")


class PhraseCheckTest(unittest.TestCase):
    def _run(self, llm_out, **kw):
        with mock.patch.object(explain_llm, "_explain_chat", return_value=llm_out):
            return express_explain("R4是什么意思", _template(CLAIMS, EVIDENCE, "模板"),
                                   use_llm=True, **kw)

    def test_foreign_code_rejected(self) -> None:
        out = {"answer_sentences": [
            {"text": "该等级对应投资者评级 C4，风险较高。", "claim_id": "C1"}]}
        exp = self._run(out)
        # C4 不在 claims 原文 → 短语核查拒绝 → 回退模板
        self.assertEqual(exp.report["explanation"]["gate"], "template_fallback")

    def test_known_code_passes(self) -> None:
        out = {"answer_sentences": [
            {"text": "等级划分为 R1 到 R5 五档。", "claim_id": "C1"}]}
        exp = self._run(out)
        self.assertEqual(exp.report["explanation"]["gate"], "llm_validated")


class SubjectCheckTest(unittest.TestCase):
    """归属断言核查：图判定优先，正则兜底；仅图级证伪才硬拒绝。"""

    CLAIMS_SUBJ = [
        {"claim_id": "C1", "type": "fact",
         "claim": "（第三十二条）基金管理人运用基金财产进行证券投资，不得超过比例限制。",
         "evidence": ["R1"]},
    ]

    def _run(self, sentence, probe=None):
        out = {"answer_sentences": [{"text": sentence, "claim_id": "C1"}]}
        tmpl = _template(self.CLAIMS_SUBJ, EVIDENCE, "模板")
        with mock.patch.object(explain_llm, "_explain_chat", return_value=out):
            return express_explain("有什么限制", tmpl, use_llm=True,
                                   subclass_probe=probe)

    def test_graph_falsified_subclass_rejected(self) -> None:
        # 图上明确证伪（货币基金 ∉ 私募基金）→ 硬拒绝
        probe = lambda s, o: False if (s, o) == ("货币基金", "私募基金") else None
        exp = self._run("货币基金作为私募基金的一种，需向合格投资者募集。", probe)
        self.assertEqual(exp.report["explanation"]["gate"], "template_fallback")

    def test_graph_verified_subclass_passes(self) -> None:
        probe = lambda s, o: True if (s, o) == ("交易型开放式指数基金", "开放式基金") else None
        exp = self._run("交易型开放式指数基金是开放式基金的一种，受比例限制约束。", probe)
        self.assertEqual(exp.report["explanation"]["gate"], "llm_validated")

    def test_unverifiable_subclass_passes(self) -> None:
        # 图判不了（None）且 claims 无原文 → 放行（正则不作为拒绝依据）
        probe = lambda s, o: None
        exp = self._run("货币基金作为高流动性产品的一种，需遵守久期限制。", probe)
        self.assertEqual(exp.report["explanation"]["gate"], "llm_validated")

    def test_claims_supported_passes(self) -> None:
        exp = self._run("基金管理人运用基金财产投资，作为基金管理人的一种职责须受约束。")
        self.assertEqual(exp.report["explanation"]["gate"], "llm_validated")


if __name__ == "__main__":
    unittest.main()
