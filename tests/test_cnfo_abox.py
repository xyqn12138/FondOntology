"""CNFO V0.5 核心业务闭环验证：A-BOX 业务查询与 OWL 推理一致性。

覆盖验收标准：
- 完成 5～6 个基金业务查询问题的验证
- OWL 推理不产生意外的类归属或关系
"""

from __future__ import annotations

import unittest
from pathlib import Path

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Literal, Namespace, term
from rdflib.namespace import RDF, RDFS, SKOS

from fondontology.ontology_loader import load_ontology_graph

ROOT = Path(__file__).resolve().parents[1]
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFC = Namespace("https://ontology.example.cn/cnfo/code/")
ABOX = Namespace("https://ontology.example.cn/cnfo/abox/")


def load_abox_graph() -> Graph:
    graph = load_ontology_graph(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
    graph.parse(ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-fund-sample-abox.ttl", format="turtle")
    DeductiveClosure(
        OWLRL_Semantics,
        axiomatic_triples=False,
        datatype_axioms=False,
    ).expand(graph)
    return graph


def labels(graph: Graph, iri) -> list[str]:
    return [
        str(o)
        for o in graph.objects(iri, RDFS.label)
        if getattr(o, "language", None) == "zh"
    ]


class CnfoAboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.g = load_abox_graph()

    # ---- 查询 1：基金基本信息 ----
    def test_query_fund_basic_info(self) -> None:
        rows = list(self.g.query(
            "SELECT ?code ?name ?short ?inc WHERE {"
            "  ?f a cnfo:Fund ; cnfo:fundCode ?code ; cnfo:fundName ?name ;"
            "     cnfo:fundShortName ?short ; cnfo:inceptionDate ?inc ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        code, name, short, inc = rows[0]
        self.assertEqual(str(code), "660001")
        self.assertIn("均衡成长", str(name))
        self.assertEqual(str(inc), "2018-05-16")

    # ---- 查询 2：管理人与托管人 ----
    def test_query_manager_and_depositary(self) -> None:
        rows = list(self.g.query(
            "SELECT ?mgrLabel ?depLabel WHERE {"
            "  cnfo-a:SampleFund cnfo:hasFundManagerRole ?mgrRole ."
            "  cnfo-a:SampleFund cnfo:hasFundDepositaryRole ?depRole ."
            "  ?mgrRole cnfo:rolePlayedBy ?mgr . ?depRole cnfo:rolePlayedBy ?dep ."
            "  ?mgr rdfs:label ?mgrLabel . ?dep rdfs:label ?depLabel ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        mgr_label, dep_label = rows[0]
        self.assertIn("基金管理有限公司", str(mgr_label))
        self.assertIn("托管银行", str(dep_label))

    # ---- 角色链派生的管理人与托管人快捷关系 ----
    def test_query_derived_manager_and_depositary(self) -> None:
        rows = list(self.g.query(
            "SELECT ?mgrLabel ?depLabel WHERE {"
            "  cnfo-a:SampleFund cnfo:hasFundManager ?mgr ;"
            "     cnfo:hasFundDepositary ?dep ."
            "  ?mgr rdfs:label ?mgrLabel . ?dep rdfs:label ?depLabel ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        mgr_label, dep_label = rows[0]
        self.assertIn("基金管理有限公司", str(mgr_label))
        self.assertIn("托管银行", str(dep_label))

    # ---- 查询 3：最新份额净值 ----
    def test_query_latest_nav(self) -> None:
        rows = list(self.g.query(
            "SELECT ?d ?nav WHERE {"
            "  cnfo-a:SampleFund cnfo:hasNetAssetValueRecord ?r ."
            "  ?r cnfo:valuationDate ?d ; cnfo:fundUnitNetAssetValue ?nav ."
            "} ORDER BY DESC(?d) LIMIT 1"
        ))
        self.assertEqual(len(rows), 1)
        d, nav = rows[0]
        self.assertEqual(str(d), "2026-08-26")
        self.assertAlmostEqual(float(nav), 1.2345, places=6)

    # ---- 查询 4：投资组合持仓构成 ----
    def test_query_portfolio_positions(self) -> None:
        rows = list(self.g.query(
            "SELECT ?assetLabel ?qty WHERE {"
            "  cnfo-a:SamplePortfolio cnfo:hasFundPortfolioPosition ?p ."
            "  ?p cnfo:positionInAsset ?a ; cnfo:positionQuantity ?qty ."
            "  ?a rdfs:label ?assetLabel ."
            "} ORDER BY ?qty"
        ))
        self.assertEqual(len(rows), 2)
        types = {str(a) for a, _ in rows}
        self.assertEqual(types, {"示例股票资产", "示例债券资产"})
        quantities = sorted(float(q) for _, q in rows)
        self.assertEqual(quantities, [50000.0, 100000.0])

    # ---- 查询 5：投资者持有的基金份额 ----
    def test_query_investor_holdings(self) -> None:
        rows = list(self.g.query(
            "SELECT ?code ?qty WHERE {"
            "  cnfo-a:SampleInvestor cnfo:holdsFundPosition ?pf ."
            "  ?pf cnfo:positionQuantity ?qty ; cnfo:positionInFundUnit ?u ."
            "  ?u cnfo:fundUnitCode ?code ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        code, qty = rows[0]
        self.assertEqual(str(code), "660001")
        self.assertEqual(float(qty), 50000.0)

    # ---- 查询 6：标准代码表语义（运作/组织/风险/分红） ----
    def test_query_code_semantics(self) -> None:
        rows = list(self.g.query(
            "SELECT ?mode ?form ?risk WHERE {"
            "  cnfo-a:SampleFund cnfo:hasFundOperationMode ?m ;"
            "     cnfo:hasFundOrganizationForm ?f ; cnfo:hasFundRiskLevel ?r ."
            "  ?m skos:prefLabel ?mode . ?f skos:prefLabel ?form . ?r skos:prefLabel ?risk ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        mode, form, risk = rows[0]
        self.assertEqual(str(mode), "开放式")
        self.assertEqual(str(form), "契约型")
        self.assertIn("R3", str(risk))

        rows = list(self.g.query(
            "SELECT ?modeLabel WHERE {"
            "  cnfo-a:SampleUnitClassA cnfo:hasFundDistributionMode ?c ."
            "  ?c skos:prefLabel ?modeLabel ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0][0]), "现金分红")

    # ---- 基金账户最小闭环 ----
    def test_query_fund_account_closure(self) -> None:
        rows = list(self.g.query(
            "SELECT ?num ?open WHERE {"
            "  cnfo-a:SampleInvestor cnfo:hasFundAccount ?acct ."
            "  ?acct cnfo:accountNumber ?num ; cnfo:accountOpeningDate ?open ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        num, open_date = rows[0]
        self.assertEqual(str(num), "01234567890123456789")
        self.assertEqual(str(open_date), "2020-03-01")

    # ---- 账户与持仓记录闭环 ----
    def test_query_account_and_position_closure(self) -> None:
        rows = list(self.g.query(
            "SELECT ?fund ?position WHERE {"
            "  cnfo-a:SampleInvestorAccount cnfo:accountForFund ?fund ;"
            "     cnfo:accountRecordsPosition ?position ."
            "}"
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], ABOX.SampleFund)
        self.assertEqual(rows[0][1], ABOX.SampleInvestorPosition)

    # ---- OWL 推理：逆关系推导 ----
    def test_reasoning_derives_inverse_edges(self) -> None:
        g = self.g
        self.assertIn(
            (ABOX.SamplePositionEquity, CNFO.positionOfPortfolio, ABOX.SamplePortfolio),
            g,
        )
        self.assertIn(
            (ABOX.SampleEquityAsset, CNFO.assetHasPortfolioPosition, ABOX.SamplePositionEquity),
            g,
        )
        self.assertIn(
            (ABOX.SampleFundMgmtCompany, CNFO.playsFundRole, ABOX.SampleFundManagerRole),
            g,
        )
        self.assertIn(
            (ABOX.SampleUnitClassA, CNFO.issuedByFund, ABOX.SampleFund),
            g,
        )

    # ---- OWL 推理：无意外类归属 ----
    # 持仓公共属性的 domain 指向 FundPositionRecord，避免 FundPosition 与
    # PortfolioPosition 因复用数量/币种字段而被 RDFS domain 交叉归类。
    def test_reasoning_no_unexpected_class_membership(self) -> None:
        g = self.g
        for unexpected in (
            CNFO.ClosedEndedFund,
            CNFO.MoneyMarketFund,
            CNFO.FundOfFunds,
            CNFO.ExchangeTradedFund,
            CNFO.PrivateFund,
            CNFO.PrivateSecuritiesInvestmentFund,
        ):
            self.assertNotIn((ABOX.SampleFund, RDF.type, unexpected), g)
        self.assertNotIn((ABOX.SampleUnitClassA, RDF.type, CNFO.FundPosition), g)
        self.assertNotIn((ABOX.SampleUnitClassA, RDF.type, CNFO.PortfolioPosition), g)
        self.assertNotIn((ABOX.SampleNav20260826, RDF.type, CNFO.FundPosition), g)
        self.assertNotIn((ABOX.SampleNav20260826, RDF.type, CNFO.PortfolioPosition), g)

    def test_reasoning_keeps_position_subtypes_separate(self) -> None:
        g = self.g
        common = {
            CNFO.FundPositionRecord,
            CNFO.FundBusinessObject,
            CNFO.FundObject,
        }
        investor_position_types = common | {
            CNFO.FundPosition,
        }
        portfolio_position_types = common | {
            CNFO.PortfolioPosition,
        }

        for position, expected in (
            (ABOX.SampleInvestorPosition, investor_position_types),
            (ABOX.SamplePositionEquity, portfolio_position_types),
            (ABOX.SamplePositionDebt, portfolio_position_types),
        ):
            named = {
                t
                for t in g.objects(position, RDF.type)
                if isinstance(t, term.URIRef)
                and str(t).startswith(str(CNFO))
            }
            self.assertEqual(named, expected, position)

        self.assertNotIn(
            (ABOX.SampleInvestorPosition, RDF.type, CNFO.PortfolioPosition),
            g,
        )
        self.assertNotIn(
            (ABOX.SamplePositionEquity, RDF.type, CNFO.FundPosition),
            g,
        )
        self.assertNotIn(
            (ABOX.SamplePositionDebt, RDF.type, CNFO.FundPosition),
            g,
        )

    # ---- OWL 推理：类定义值约束保持一致 ----
    def test_reasoning_keeps_class_value_constraints(self) -> None:
        g = self.g
        self.assertIn(
            (ABOX.SampleFund, CNFO.isOpenEnded, Literal(True)),
            g,
        )
        self.assertIn(
            (ABOX.SampleFund, CNFO.isPrivate, Literal(False)),
            g,
        )


if __name__ == "__main__":
    unittest.main()
