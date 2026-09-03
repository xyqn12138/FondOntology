"""M4：意图层回归（Index / Resolver / Validator / Lexicon / Intent 三态）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex, _normalize_name
from fondontology.qa.intent import build_intent
from fondontology.qa.lexicon import apply
from fondontology.qa.resolver import VocabularyResolver
from fondontology.qa.validator import WhitelistValidator

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


class VocabularyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)
        cls.resolver = VocabularyResolver(cls.index)
        cls.validator = WhitelistValidator(cls.index)

    def test_index_counts(self) -> None:
        self.assertEqual(len(self.index.classes), 143)
        self.assertEqual(len(self.index.object_properties), 143)
        self.assertEqual(len(self.index.datatype_properties), 61)
        self.assertGreaterEqual(len(self.index.codes), 27)
        self.assertGreaterEqual(len(self.index.entities), 3000)

    def test_resolve_concept_label_exact_and_contains(self) -> None:
        hit = self.resolver.resolve_concept("交易型开放式指数基金")[0]
        self.assertEqual(hit.kind, "class")
        self.assertEqual(hit.match_type, "label")
        self.assertEqual(hit.score, 1.0)
        # 子串命中给加分，避免“基金”吞并“基金中基金”
        fof = [c for c in self.resolver.resolve_concept("有哪些基金中基金") if c.label == "基金中基金"]
        fund = [c for c in self.resolver.resolve_concept("有哪些基金中基金") if c.label == "基金"]
        self.assertTrue(fof and fund)
        self.assertGreater(fof[0].score, fund[0].score)

    def test_resolve_entity_by_code(self) -> None:
        hit = self.resolver.resolve_entity("001113")[0]
        self.assertEqual(hit.kind, "entity")
        self.assertEqual(hit.match_type, "code")
        self.assertEqual(hit.score, 1.0)

    def test_validator_rejects_unknown(self) -> None:
        from fondontology.qa.index import Candidate
        ok, reason = self.validator.validate(
            Candidate("https://example.com/bogus", "class", "假类", "label", 1.0), "class")
        self.assertFalse(ok)
        ok, reason = self.validator.validate_iris(
            "https://ontology.example.cn/cnfo/ontology/Fund", "class")
        self.assertTrue(ok)

    def test_normalize_name_guardrail(self) -> None:
        # 家族名不得被归一化合并：A证券投资基金 vs A证券投资基金C
        a = _normalize_name("A证券投资基金")
        a_c = _normalize_name("A证券投资基金C")
        self.assertNotEqual(a, a_c)

    def test_lexicon_risk_range(self) -> None:
        specs = apply("R4以上的基金")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].operator, "in")
        self.assertEqual(len(specs[0].value), 2)  # R4, R5
        specs2 = apply("国内交易型基金")
        self.assertTrue(any(s.lexicon_source == "国内" for s in specs2))


class IntentDeterministicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stack = build_stack(SOURCE, ABOX)
        cls.index = OntologyIndex(cls.stack)

    def intent(self, q: str):
        return build_intent(q, self.index)

    def test_find_resolved(self) -> None:
        r = self.intent("有哪些交易型开放式指数基金")
        self.assertEqual((r.status, r.operation), ("RESOLVED", "find"))
        self.assertIn("ExchangeTradedFund", r.intent["target_class"])

    def test_find_longest_match_priority(self) -> None:
        r = self.intent("有哪些基金中基金")
        self.assertEqual(r.status, "RESOLVED")
        self.assertIn("FundOfFunds", r.intent["target_class"])

    def test_ambiguous(self) -> None:
        r = self.intent("混合基金股票基金")
        self.assertEqual(r.status, "AMBIGUOUS")

    def test_unresolved(self) -> None:
        self.assertEqual(self.intent("电磁炉").status, "UNRESOLVED")
        # compare 类问题显式拒绝（Phase 2）
        self.assertEqual(self.intent("公募基金和私募基金有什么区别").status, "UNRESOLVED")
        # 实体锚点识别（source 查询待后续版本）
        self.assertEqual(self.intent("基金001113的管理人是谁").status, "UNRESOLVED")

    def test_verify_subclass(self) -> None:
        r = self.intent("交易型开放式指数基金是不是开放式基金")
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual(r.intent.get("relation"), "subClassOf")
        self.assertIn("ExchangeTradedFund", r.intent["subject"])
        self.assertIn("OpenEndedFund", r.intent["object"])

    def test_verify_disjoint(self) -> None:
        r = self.intent("开放式基金与封闭式基金是否互斥")
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual(r.intent.get("relation"), "disjointWith")

    def test_lexicon_filter_driven_default_fund(self) -> None:
        r = self.intent("R4以上的基金有哪些")
        self.assertEqual(r.status, "RESOLVED")
        self.assertIn("Fund", r.intent["target_class"])
        self.assertGreaterEqual(len(r.intent.get("filters") or []), 1)
        self.assertEqual(r.intent["filters"][0]["operator"], "in")

    def test_filters_carry_lexicon_source(self) -> None:
        r = self.intent("R5风险等级的基金")
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual(r.intent["filters"][0]["lexicon_source"], "R5")

    def test_investor_anchor_source_path(self) -> None:
        r = self.intent("钱强的基金有什么？")
        self.assertEqual(r.status, "RESOLVED")
        self.assertEqual(r.operation, "find")
        src = r.intent.get("source")
        self.assertTrue(src)
        # 锚点实体确实是投资者（类型在实体的 types 元数据中）
        meta = self.index.entities.get(src, {})
        self.assertTrue(any(t.rsplit("/", 1)[-1] == "Investor" for t in meta.get("types", [])),
                        f"{src} 非投资者实体")
        self.assertEqual(len(r.intent.get("traversals") or []), 3)

    def test_manager_person_anchor_funds_chain(self) -> None:
        # 魏辉是基金经理（FundManagerPerson），数据修复后经 playsFundRole→roleInFund 链可查
        r = self.intent("魏辉的基金有什么？")
        self.assertEqual(r.status, "RESOLVED")
        src = r.intent.get("source")
        meta = self.index.entities.get(src, {})
        self.assertTrue(any(t.rsplit("/", 1)[-1] == "FundManagerPerson"
                            for t in meta.get("types", [])), f"{src} 非基金经理实体")
        self.assertEqual([t["property"].rsplit("/", 1)[-1] for t in r.intent["traversals"]],
                         ["playsFundRole", "roleInFund"])


if __name__ == "__main__":
    unittest.main()