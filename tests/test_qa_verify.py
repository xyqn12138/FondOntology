"""M1：T-BOX 语义验证（verify 四状态）回归测试。

覆盖：subClassOf 判链（ENTAILED/UNKNOWN/CONTRADICTED）、disjointWith、equivalentClass、
subPropertyOf、domainOf/rangeOf、INVALID_REQUEST。期望值对照真实 CNFO T-BOX。
"""
from __future__ import annotations

import unittest
from pathlib import Path

from fondontology.ontology_loader import load_ontology_graph
from fondontology.qa.verify import (
    CONTRADICTED, ENTAILED, INVALID_REQUEST, UNKNOWN, verify,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"


class TboxVerifyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.g = load_ontology_graph(SOURCE)

    def check(self, subject, relation, object, expected) -> None:
        result = verify(self.g, subject, relation, object)
        self.assertEqual(result.answer, expected, f"{subject} {relation} {object}")

    # ---- subClassOf ----
    def test_subclass_entailed_chains(self) -> None:
        self.check("ExchangeTradedFund", "subClassOf", "OpenEndedFund", ENTAILED)
        self.check("ExchangeTradedFund", "subClassOf", "Fund", ENTAILED)
        self.check("HongKongMutualRecognitionFund", "subClassOf", "CrossBorderFund", ENTAILED)
        self.check("QDIIFund", "subClassOf", "PublicFund", ENTAILED)
        self.check("FundUnitClass", "subClassOf", "FundUnit", ENTAILED)
        self.check("FundManagerRole", "subClassOf", "FundRole", ENTAILED)
        self.check("QualifiedInvestor", "subClassOf", "FundParty", ENTAILED)

    def test_subclass_unknown_open_world(self) -> None:
        # 无链且未声明互斥 → UNKNOWN（开放世界：不能证明 ≠ 证明为假）
        self.check("ExchangeTradedFund", "subClassOf", "MoneyMarketFund", UNKNOWN)
        self.check("FundUnit", "subClassOf", "Fund", UNKNOWN)
        self.check("NetAssetValueRecord", "subClassOf", "FundBusinessObject", UNKNOWN)
        self.check("FundAgent", "subClassOf", "FundRole", UNKNOWN)

    def test_subclass_contradicted(self) -> None:
        self.check("OpenEndedFund", "subClassOf", "ClosedEndedFund", CONTRADICTED)
        self.check("PublicFund", "subClassOf", "PrivateFund", CONTRADICTED)
        self.check("OperatingStatus", "subClassOf", "TerminatedStatus", CONTRADICTED)
        self.check("EquityFund", "subClassOf", "BondFund", CONTRADICTED)

    # ---- disjointWith ----
    def test_disjoint_declared(self) -> None:
        self.check("OpenEndedFund", "disjointWith", "ClosedEndedFund", ENTAILED)
        self.check("PublicFund", "disjointWith", "PrivateFund", ENTAILED)
        self.check("FundManagerRole", "disjointWith", "FundDepositaryRole", ENTAILED)

    def test_disjoint_unknown_not_declared(self) -> None:
        self.check("ExchangeTradedFund", "disjointWith", "MoneyMarketFund", UNKNOWN)
        self.check("QDIIFund", "disjointWith", "PrivateFund", UNKNOWN)

    # ---- equivalentClass ----
    def test_equivalent_unknown_and_contradicted(self) -> None:
        # CNFO 无等价声明：单向子类链不构成等价（不越权）
        self.check("ExchangeTradedFund", "equivalentClass", "OpenEndedFund", UNKNOWN)
        self.check("PublicFund", "equivalentClass", "PrivateFund", CONTRADICTED)

    # ---- subPropertyOf ----
    def test_subproperty(self) -> None:
        self.check("hasFundManagerRole", "subPropertyOf", "hasFundServiceProviderRole", ENTAILED)
        self.check("hasFundAgentRole", "subPropertyOf", "hasFundServiceProviderRole", ENTAILED)
        self.check("hasFundManagerRole", "subPropertyOf", "hasFundRole", ENTAILED)
        self.check("rolePlayedBy", "subPropertyOf", "hasFundManagerRole", UNKNOWN)

    # ---- domainOf / rangeOf ----
    def test_domain_range(self) -> None:
        self.check("hasFundManagerRole", "domainOf", "Fund", ENTAILED)
        self.check("rolePlayedBy", "domainOf", "FundRole", ENTAILED)
        self.check("positionInAsset", "domainOf", "PortfolioPosition", ENTAILED)
        self.check("hasFundManagerRole", "rangeOf", "FundManagerRole", ENTAILED)
        self.check("hasFundStatus", "rangeOf", "FundLifecycleStatus", ENTAILED)
        self.check("hasFundManagerRole", "domainOf", "FundParty", UNKNOWN)

    # ---- INVALID_REQUEST ----
    def test_invalid_request(self) -> None:
        self.check("FundPositionCheck", "subClassOf", "Fund", INVALID_REQUEST)
        self.check("Fund", "subClassOf", "不存在的类名", INVALID_REQUEST)
        self.check("Fund", "notARelation", "Fund", INVALID_REQUEST)
        self.check("", "subClassOf", "Fund", INVALID_REQUEST)


if __name__ == "__main__":
    unittest.main()