"""Semantic Enforcement 回归：数据导入时本体作为语义控制/Schema 层。

覆盖：
- 类型约束：松散记录 → Fund/类型子类 + 继承闭环
- 属性约束：字段必须命中 CNFO/CNFC 词表；未知字段拒绝
- 关系约束：range 非法端点（Fund managedBy Fund）拒绝
- aum → NetAssetValueRecord 映射
- merge 后推理物化 hasFundManager（经理人与管理公司），问数链路可答
"""
from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF

from fondontology.qa.engine import answer_question
from fondontology.qa.enforce import SemanticEnforcer
from fondontology.qa.graph import build_stack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")

RECORD = {
    "person": "张三",
    "fund_code": "110011",
    "fund_name": "星河成长混合型证券投资基金",
    "fund_type": "混合型",
    "operation_mode": "开放式",
    "organization_form": "契约型",
    "risk_level": "R3",
    "management_company": "星河基金管理有限公司",
    "aum": "32.5亿",
}


class SemanticEnforcementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # 共享数据栈仅供"不合并"的约束用例；merge 用例使用独立栈避免污染
        cls.stack = build_stack(SOURCE, ABOX)

    def make_enforcer(self, stack=None):
        return SemanticEnforcer(stack or self.stack)

    def run_clean(self):
        r = self.make_enforcer().enforce(RECORD)
        self.assertTrue(r.ok, r.errors)
        return r

    def test_type_constraint_and_inheritance_closure(self) -> None:
        r = self.run_clean()
        fund = URIRef(r.resolved["fund"])
        self.assertIn((fund, RDF.type, URIRef(str(CNFO) + "HybridFund")), r.graph)
        # 继承闭环：HybridFund → Fund → FundBusinessObject 被显式断言
        self.assertIn((fund, RDF.type, URIRef(str(CNFO) + "Fund")), r.graph)
        self.assertIn((fund, RDF.type, URIRef(str(CNFO) + "FundBusinessObject")), r.graph)

    def test_attribute_and_code_mapping(self) -> None:
        r = self.run_clean()
        fund = URIRef(r.resolved["fund"])
        self.assertIn((fund, URIRef(str(CNFO) + "fundCode"), Literal("110011")), r.graph)
        self.assertIn((fund, URIRef(str(CNFO) + "hasFundOperationMode"),
                       URIRef("https://ontology.example.cn/cnfo/code/FundOperationModeOpenEnded")), r.graph)
        self.assertIn((fund, URIRef(str(CNFO) + "hasFundRiskLevel"),
                       URIRef("https://ontology.example.cn/cnfo/code/FundRiskLevelR3")), r.graph)

    def test_aum_maps_to_nav_record(self) -> None:
        r = self.run_clean()
        fund = URIRef(r.resolved["fund"])
        navs = [o for o in r.graph.objects(fund, URIRef(str(CNFO) + "hasNetAssetValueRecord"))]
        self.assertEqual(len(navs), 1)
        vals = [str(o) for o in r.graph.objects(navs[0], URIRef(str(CNFO) + "fundNetAssetValue"))]
        self.assertEqual(vals, ["3250000000"])

    def test_unknown_field_rejected(self) -> None:
        r = self.make_enforcer().enforce(dict(RECORD, net_cube="red"))
        self.assertFalse(r.ok)
        self.assertTrue(any("未知字段" in e for e in r.errors))

    def test_illegal_relation_endpoint_rejected(self) -> None:
        # 管理公司字段指向一个基金（Fund 类型，非 FundParty 闭包）→ 关系被拒
        r = self.make_enforcer().enforce(dict(RECORD, management_company="磐石货币货币市场基金"))
        self.assertFalse(r.ok)
        self.assertTrue(any("关系被拒" in e for e in r.errors), r.errors)

    def test_invalid_merge_rejected(self) -> None:
        r = self.make_enforcer().enforce(dict(RECORD, fund_type="钻石型"))
        self.assertFalse(r.ok)
        enforcer = self.make_enforcer()
        with self.assertRaises(ValueError):
            enforcer.merge_into_stack(r)

    def test_merge_then_question_answers_new_fund(self) -> None:
        # 独立数据栈：并入约束产物 → 推理物化 → 问数链路即刻可答
        stack2 = build_stack(SOURCE, ABOX)
        r = self.make_enforcer(stack2).enforce(RECORD)
        self.assertTrue(r.ok, r.errors)
        self.make_enforcer(stack2).merge_into_stack(r)
        ans = answer_question("张三管理的基金有哪些？", stack2, use_llm=False)
        self.assertEqual(ans.status, "ok", ans.text)
        self.assertIn("共找到 1 个", ans.text)
        self.assertIn("星河成长", ans.text)
        # 证据含推理归因：hasFundManager 由属性链物化
        rules = {e.get("rule") for e in ans.report["evidence"] if e["kind"] == "inference"}
        self.assertTrue(any("property_chain" in (x or "") for x in rules), rules)


class BatchImportTest(unittest.TestCase):
    """批量导入生产路径（import_records）：失败跳过、同人同公司实体复用、导入即可问。"""

    def test_batch_import_and_query(self) -> None:
        from fondontology.qa.enforce import import_records
        stack = build_stack(SOURCE, ABOX)
        record2 = dict(RECORD, fund_code="110012",
                       fund_name="星河稳健债券型证券投资基金",
                       fund_type="债券型", risk_level="R2", aum="18亿")
        bad = {"fund_code": "110013", "fund_type": "不存在型"}
        r = import_records([RECORD, record2, bad], stack)
        self.assertEqual(r["imported"], 2)
        self.assertEqual(len(r["failed"]), 1)
        self.assertIn("类型词表", r["failed"][0]["errors"][0])
        # 同一"张三"关联两只基金 → 聚合问法即刻可答（实体索引同步生效）
        ans = answer_question("张三管理的基金有哪些？", stack, use_llm=False)
        self.assertEqual(ans.status, "ok", ans.text)
        self.assertIn("共找到 2 个", ans.text)


if __name__ == "__main__":
    unittest.main()