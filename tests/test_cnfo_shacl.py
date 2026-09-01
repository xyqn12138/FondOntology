"""CNFO V0.5 SHACL 数据质量校验验证。

覆盖验收标准：
- 至少完成 Fund、FundUnit、FundPosition、PortfolioPosition、NetAssetValueRecord 五类 SHACL 校验（另含 FundRoleAssignment）
- 一组“有效实例 + 无效实例”用于验证
"""

from __future__ import annotations

import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from fondontology.ontology_loader import load_ontology_graph

ROOT = Path(__file__).resolve().parents[1]
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFC = Namespace("https://ontology.example.cn/cnfo/code/")
ABOX = Namespace("https://ontology.example.cn/cnfo/abox/")


def load_shapes() -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontology" / "shacl" / "cnfo-fund-shapes.ttl", format="turtle")
    return graph


def load_sample_data() -> Graph:
    graph = load_ontology_graph(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
    graph.parse(ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-fund-sample-abox.ttl", format="turtle")
    return graph


class CnfoShaclTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shapes = load_shapes()

    def validate(self, data: Graph):
        return validate(
            data,
            shacl_graph=self.shapes,
            inference="none",
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
            meta_shacl=False,
        )

    # ---- 有效实例：示例 A-BOX 应整体通过 ----
    def test_sample_abox_conforms(self) -> None:
        conforms, _, text = self.validate(load_sample_data())
        self.assertTrue(conforms, text)

    # ---- 无效实例 1：基金代码不符合格式 ----
    def test_invalid_fund_code_format(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadFund, RDF.type, CNFO.Fund))
        g.add((ABOX.BadFund, CNFO.fundCode, Literal("ABC12")))
        g.add((ABOX.BadFund, CNFO.fundName, Literal("坏示例基金")))
        g.add((ABOX.BadFund, CNFO.inceptionDate, Literal("2020-01-01", datatype=XSD.date)))
        g.add((ABOX.BadFund, CNFO.hasFundOperationMode, CNFC.FundOperationModeOpenEnded))
        g.add((ABOX.BadFund, CNFO.hasFundManagerRole, ABOX.BadManagerRole))
        g.add((ABOX.BadFund, CNFO.hasFundDepositaryRole, ABOX.BadDepositaryRole))
        g.add((ABOX.BadFund, CNFO.hasFundUnit, ABOX.BadUnit))
        g.add((ABOX.BadManagerRole, CNFO.roleInFund, ABOX.BadFund))
        g.add((ABOX.BadDepositaryRole, CNFO.roleInFund, ABOX.BadFund))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("基金代码", text)

    # ---- 无效实例 2：终止日期早于成立日期（日期逻辑 SPARQL） ----
    def test_invalid_date_order(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadFund, RDF.type, CNFO.Fund))
        g.add((ABOX.BadFund, CNFO.fundCode, Literal("660002")))
        g.add((ABOX.BadFund, CNFO.fundName, Literal("坏日期基金")))
        g.add((ABOX.BadFund, CNFO.inceptionDate, Literal("2020-01-01", datatype=XSD.date)))
        g.add((ABOX.BadFund, CNFO.terminationDate, Literal("2019-01-01", datatype=XSD.date)))
        g.add((ABOX.BadFund, CNFO.hasFundOperationMode, CNFC.FundOperationModeOpenEnded))
        g.add((ABOX.BadFund, CNFO.hasFundManagerRole, ABOX.BadManagerRole))
        g.add((ABOX.BadFund, CNFO.hasFundDepositaryRole, ABOX.BadDepositaryRole))
        g.add((ABOX.BadFund, CNFO.hasFundUnit, ABOX.BadUnit))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("终止日期不得早于成立日期", text)

    # ---- 无效实例 3：运作方式与开放式标志不一致（代码一致性 SPARQL） ----
    def test_invalid_mode_flag_consistency(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadFund, RDF.type, CNFO.Fund))
        g.add((ABOX.BadFund, CNFO.fundCode, Literal("660003")))
        g.add((ABOX.BadFund, CNFO.fundName, Literal("坏标志基金")))
        g.add((ABOX.BadFund, CNFO.inceptionDate, Literal("2020-01-01", datatype=XSD.date)))
        g.add((ABOX.BadFund, CNFO.hasFundOperationMode, CNFC.FundOperationModeClosedEnded))
        g.add((ABOX.BadFund, CNFO.isOpenEnded, Literal(True)))
        g.add((ABOX.BadFund, CNFO.hasFundManagerRole, ABOX.BadManagerRole))
        g.add((ABOX.BadFund, CNFO.hasFundDepositaryRole, ABOX.BadDepositaryRole))
        g.add((ABOX.BadFund, CNFO.hasFundUnit, ABOX.BadUnit))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("开放式标志", text)

    # ---- 无效实例 4：份额币种格式错误 ----
    def test_invalid_unit_currency(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadUnit, RDF.type, CNFO.FundUnit))
        g.add((ABOX.BadUnit, CNFO.fundUnitCode, Literal("660002")))
        g.add((ABOX.BadUnit, CNFO.unitCurrency, Literal("CN")))
        g.add((ABOX.BadUnit, CNFO.issuedByFund, ABOX.BadFund))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("基金份额币种", text)

    # ---- 无效实例 5：持仓数量为负 ----
    def test_invalid_position_quantity(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadPosition, RDF.type, CNFO.FundPosition))
        g.add((ABOX.BadPosition, CNFO.positionQuantity, Literal(-5, datatype=XSD.decimal)))
        g.add((ABOX.BadPosition, CNFO.positionInFundUnit, ABOX.BadUnit))
        g.add((ABOX.BadPosition, CNFO.heldByInvestor, ABOX.BadInvestor))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("持仓数量", text)

    # ---- 无效实例 6：组合持仓缺少对应投资资产 ----
    def test_invalid_portfolio_position_missing_asset(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.add((ABOX.BadPortfolioPosition, RDF.type, CNFO.PortfolioPosition))
        g.add((ABOX.BadPortfolioPosition, CNFO.positionQuantity, Literal(100, datatype=XSD.decimal)))
        g.add((ABOX.BadPortfolioPosition, CNFO.positionAsOfDate, Literal("2026-08-26", datatype=XSD.date)))
        g.add((ABOX.BadPortfolioPosition, CNFO.positionCurrency, Literal("CNY")))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("持仓对应投资资产", text)

    # ---- 无效实例 7：基金份额持仓缺少币种 ----
    def test_invalid_fund_position_missing_currency(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.add((ABOX.BadFundPositionCurrency, RDF.type, CNFO.FundPosition))
        g.add((ABOX.BadFundPositionCurrency, CNFO.positionQuantity, Literal(100, datatype=XSD.decimal)))
        g.add((ABOX.BadFundPositionCurrency, CNFO.positionInFundUnit, ABOX.BadUnit))
        g.add((ABOX.BadFundPositionCurrency, CNFO.heldByInvestor, ABOX.BadInvestor))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("持仓币种", text)

    # ---- 无效实例 8：净值记录缺少份额净值与资产净值 ----
    def test_invalid_nav_missing_values(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadNav, RDF.type, CNFO.NetAssetValueRecord))
        g.add((ABOX.BadNav, CNFO.valuationDate, Literal("2026-08-26", datatype=XSD.date)))
        g.add((ABOX.BadNav, CNFO.valuationCurrency, Literal("CNY")))
        g.add((ABOX.BadNav, CNFO.recordForFund, ABOX.BadFund))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("份额净值或资产净值至少一个", text)

    # ---- 无效实例 9：任职记录日期倒挂 ----
    def test_invalid_role_assignment_period(self) -> None:
        g = Graph()
        g.bind("cnfo", CNFO)
        g.bind("cnfc", CNFC)
        g.add((ABOX.BadAssignment, RDF.type, CNFO.FundRoleAssignment))
        g.add((ABOX.BadAssignment, CNFO.assignmentForFund, ABOX.BadFund))
        g.add((ABOX.BadAssignment, CNFO.assignsFundRole, ABOX.BadRole))
        g.add((ABOX.BadAssignment, CNFO.assignmentPlayedBy, ABOX.BadParty))
        g.add((ABOX.BadAssignment, CNFO.effectiveFrom, Literal("2022-01-01", datatype=XSD.date)))
        g.add((ABOX.BadAssignment, CNFO.effectiveTo, Literal("2021-01-01", datatype=XSD.date)))
        conforms, _, text = self.validate(g)
        self.assertFalse(conforms)
        self.assertIn("任职结束日期不得早于开始日期", text)


if __name__ == "__main__":
    unittest.main()
