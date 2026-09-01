from __future__ import annotations

import sys
import unittest
from pathlib import Path

# 直接运行本脚本时，Python 将脚本所在目录（tests/）而非项目根目录加入 sys.path；
# 此处补上项目根目录，保证 `fondontology` 包可导入（已安装到环境中时同样生效）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from fondontology.ontology_loader import load_ontology_graph
from fondontology.viewer import OntologyViewerSession


ROOT = Path(__file__).resolve().parents[1]
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFOM = Namespace("https://ontology.example.cn/cnfo/module/")


def load_graph(path: Path) -> Graph:
    return load_ontology_graph(path)


class CnfoOntologyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_graph(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")

    def test_source_and_release_graph_match(self) -> None:
        release = load_graph(ROOT / "artifacts" / "cnfo" / "cnfo-fund-tbox.ttl")
        self.assertTrue(isomorphic(self.source, release))

    def test_schema_has_no_missing_property_endpoints(self) -> None:
        properties = {
            subject
            for rdf_type in (OWL.ObjectProperty, OWL.DatatypeProperty)
            for subject in self.source.subjects(RDF.type, rdf_type)
            if isinstance(subject, URIRef)
        }
        for property_iri in properties:
            self.assertTrue(list(self.source.objects(property_iri, RDFS.domain)), property_iri)
            self.assertTrue(list(self.source.objects(property_iri, RDFS.range)), property_iri)

    def test_restrictions_reference_declared_properties(self) -> None:
        properties = {
            subject
            for rdf_type in (OWL.ObjectProperty, OWL.DatatypeProperty)
            for subject in self.source.subjects(RDF.type, rdf_type)
        }
        for restriction in self.source.subjects(RDF.type, OWL.Restriction):
            self.assertIn(self.source.value(restriction, OWL.onProperty), properties)

    def test_all_disjoint_groups_contain_declared_cnfo_classes(self) -> None:
        for group in self.source.subjects(RDF.type, OWL.AllDisjointClasses):
            head = self.source.value(group, OWL.members)
            members = []
            seen = set()
            while head and head != RDF.nil and head not in seen:
                seen.add(head)
                member = self.source.value(head, RDF.first)
                if isinstance(member, URIRef):
                    members.append(member)
                head = self.source.value(head, RDF.rest)
            self.assertGreaterEqual(len(members), 2)
            for member in members:
                self.assertIn((member, RDF.type, OWL.Class), self.source)

    def test_all_cnfo_classes_have_chinese_definitions(self) -> None:
        classes = {
            subject
            for subject in self.source.subjects(RDF.type, OWL.Class)
            if isinstance(subject, URIRef) and str(subject).startswith(str(CNFO))
        }
        for class_iri in classes:
            definitions = [
                value
                for value in self.source.objects(class_iri, SKOS.definition)
                if getattr(value, "language", None) == "zh"
            ]
            self.assertTrue(definitions, class_iri)

    def test_viewer_does_not_expose_inferred_reflexive_equivalence_as_mapping(self) -> None:
        session = OntologyViewerSession(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
        detail = session.detail(str(CNFO.ExchangeTradedFund))
        self.assertFalse(
            any(item["target"]["iri"] == str(CNFO.ExchangeTradedFund) for item in detail["mappings"])
        )
        self.assertFalse(
            any(item["target"]["iri"] == str(CNFO.ExchangeTradedFund) for item in detail["alignments"])
        )

    def test_key_property_hierarchy_and_inverse_relations(self) -> None:
        self.assertIn(
            (CNFO.hasFundManagerRole, RDFS.subPropertyOf, CNFO.hasFundServiceProviderRole),
            self.source,
        )
        self.assertIn(
            (CNFO.hasFundServiceProviderRole, RDFS.subPropertyOf, CNFO.hasFundRole),
            self.source,
        )
        self.assertIn((CNFO.hasFundRole, OWL.inverseOf, CNFO.roleInFund), self.source)
        self.assertIn((CNFO.rolePlayedBy, OWL.inverseOf, CNFO.playsFundRole), self.source)
        self.assertIn((CNFO.hasNetAssetValueRecord, OWL.inverseOf, CNFO.recordForFund), self.source)
        self.assertIn((CNFO.hasFundPortfolioPosition, OWL.inverseOf, CNFO.positionOfPortfolio), self.source)

    def test_cross_border_mutual_recognition_and_agent_concepts(self) -> None:
        self.assertIn(
            (CNFO.CrossBorderFund, RDFS.subClassOf, CNFO.Fund),
            self.source,
        )
        self.assertIn(
            (
                CNFO.MainlandHongKongMutualRecognitionFund,
                RDFS.subClassOf,
                CNFO.CrossBorderFund,
            ),
            self.source,
        )
        self.assertIn(
            (
                CNFO.HongKongMutualRecognitionFund,
                RDFS.subClassOf,
                CNFO.MainlandHongKongMutualRecognitionFund,
            ),
            self.source,
        )
        self.assertIn((CNFO.FundAgent, RDFS.subClassOf, CNFO.FundParty), self.source)
        self.assertIn(
            (CNFO.FundAgentRole, RDFS.subClassOf, CNFO.FundServiceProviderRole),
            self.source,
        )
        self.assertIn(
            (CNFO.hasFundAgentRole, RDFS.subPropertyOf, CNFO.hasFundServiceProviderRole),
            self.source,
        )
        self.assertIn(
            (CNFO.hasFundAgentRole, OWL.inverseOf, CNFO.agentRoleForFund),
            self.source,
        )

        session = OntologyViewerSession(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
        hk_detail = session.detail(str(CNFO.HongKongMutualRecognitionFund))
        self.assertEqual(hk_detail["current"]["label"], "香港互认基金")
        self.assertEqual(
            hk_detail["parents"][0]["iri"],
            str(CNFO.MainlandHongKongMutualRecognitionFund),
        )
        self.assertIn(
            str(CNFO.HongKongMutualRecognitionFund),
            {item["iri"] for item in session.search("香港互认基金", "cnfo", 100)},
        )

        agent_detail = session.detail(str(CNFO.FundAgent))
        self.assertEqual(agent_detail["current"]["label"], "基金代理人")
        self.assertEqual(agent_detail["parents"][0]["iri"], str(CNFO.FundParty))

        fund_detail = session.detail(str(CNFO.Fund))
        outgoing = {item["iri"] for item in fund_detail["properties"]["outgoing"]}
        self.assertIn(str(CNFO.hasFundAgentRole), outgoing)

        graph = Graph()
        graph += self.source
        fund = CNFO.SampleHongKongMutualRecognitionFund
        role = CNFO.SampleFundAgentRole
        agent = CNFO.SampleFundAgent
        graph.add((fund, RDF.type, CNFO.HongKongMutualRecognitionFund))
        graph.add((role, RDF.type, CNFO.FundAgentRole))
        graph.add((agent, RDF.type, CNFO.FundAgent))
        graph.add((fund, CNFO.hasFundAgentRole, role))
        graph.add((role, CNFO.rolePlayedBy, agent))
        DeductiveClosure(
            OWLRL_Semantics,
            axiomatic_triples=False,
            datatype_axioms=False,
        ).expand(graph)
        self.assertIn((fund, RDF.type, CNFO.CrossBorderFund), graph)
        self.assertIn((role, CNFO.agentRoleForFund, fund), graph)
        self.assertIn((agent, CNFO.playsFundRole, role), graph)

    def test_review_upgrade_axioms_and_concepts(self) -> None:
        for class_iri in (
            CNFO.FundPerformanceRecord,
            CNFO.FundFee,
            CNFO.Regulation,
            CNFO.FundManagerPerson,
            CNFO.MarketIndex,
            CNFO.DerivativeInvestmentAsset,
            CNFO.CashAndDepositAsset,
            CNFO.MoneyMarketInstrument,
            CNFO.AssetBackedSecurity,
            CNFO.InvestorRiskRating,
        ):
            self.assertIn((class_iri, RDF.type, OWL.Class), self.source)
            self.assertTrue(list(self.source.objects(class_iri, SKOS.definition)))

        for class_iri in (
            CNFO.OpenEndedFund,
            CNFO.ClosedEndedFund,
            CNFO.PublicFund,
            CNFO.PrivateFund,
            CNFO.ExchangeTradedFund,
            CNFO.FundOfFunds,
        ):
            self.assertTrue(list(self.source.objects(class_iri, OWL.equivalentClass)))

        for property_iri in (
            CNFO.hasFundManager,
            CNFO.hasFundDepositary,
            CNFO.recordForFund,
        ):
            self.assertTrue(list(self.source.objects(property_iri, OWL.propertyChainAxiom)))

        for property_iri in (
            CNFO.fundCode,
            CNFO.fundUnitCode,
            CNFO.accountNumber,
            CNFO.unitCurrency,
            CNFO.baseCurrency,
            CNFO.hasFundStatus,
        ):
            self.assertIn((property_iri, RDF.type, OWL.FunctionalProperty), self.source)

        self.assertIn((CNFO.FundObject, OWL.disjointWith, CNFO.FundParty), self.source)

    def test_owlrl_entails_local_class_values_and_inverse_edges(self) -> None:
        graph = Graph()
        graph += self.source
        fund = CNFO.SampleEtf
        role = CNFO.SampleManagerRole
        party = CNFO.SampleManagerCompany
        unit = CNFO.SampleUnit
        portfolio = CNFO.SamplePortfolio
        asset = CNFO.SampleEquityAsset
        position = CNFO.SamplePortfolioPosition

        graph.add((fund, RDF.type, CNFO.ExchangeTradedFund))
        graph.add((fund, RDF.type, CNFO.PublicFund))
        graph.add((role, RDF.type, CNFO.FundManagerRole))
        graph.add((party, RDF.type, CNFO.FundManagementCompany))
        graph.add((unit, RDF.type, CNFO.FundUnit))
        graph.add((portfolio, RDF.type, CNFO.FundPortfolio))
        graph.add((asset, RDF.type, CNFO.EquityInvestmentAsset))
        graph.add((position, RDF.type, CNFO.PortfolioPosition))
        graph.add((fund, CNFO.hasFundManagerRole, role))
        graph.add((role, CNFO.rolePlayedBy, party))
        graph.add((fund, CNFO.issuesFundUnit, unit))
        graph.add((portfolio, CNFO.hasFundPortfolioPosition, position))
        graph.add((position, CNFO.positionInAsset, asset))

        DeductiveClosure(
            OWLRL_Semantics,
            axiomatic_triples=False,
            datatype_axioms=False,
        ).expand(graph)

        self.assertIn((fund, CNFO.isOpenEnded, Literal(True, datatype=XSD.boolean)), graph)
        self.assertIn((fund, CNFO.isExchangeTraded, Literal(True, datatype=XSD.boolean)), graph)
        self.assertIn((fund, CNFO.isPrivate, Literal(False, datatype=XSD.boolean)), graph)
        self.assertIn((role, CNFO.roleInFund, fund), graph)
        self.assertIn((party, CNFO.playsFundRole, role), graph)
        self.assertIn((unit, CNFO.issuedByFund, fund), graph)
        self.assertIn((position, CNFO.positionOfPortfolio, portfolio), graph)
        self.assertIn((asset, CNFO.assetHasPortfolioPosition, position), graph)

    def test_owlrl_entails_review_property_chains(self) -> None:
        graph = Graph()
        graph += self.source
        fund = CNFO.ReviewFund
        manager_role = CNFO.ReviewManagerRole
        manager = CNFO.ReviewManager
        depositary_role = CNFO.ReviewDepositaryRole
        depositary = CNFO.ReviewDepositary
        unit = CNFO.ReviewFundUnit
        nav = CNFO.ReviewNav
        graph.add((fund, RDF.type, CNFO.Fund))
        graph.add((fund, CNFO.hasFundManagerRole, manager_role))
        graph.add((manager_role, RDF.type, CNFO.FundManagerRole))
        graph.add((manager_role, CNFO.rolePlayedBy, manager))
        graph.add((depositary_role, RDF.type, CNFO.FundDepositaryRole))
        graph.add((depositary_role, CNFO.rolePlayedBy, depositary))
        graph.add((fund, CNFO.hasFundDepositaryRole, depositary_role))
        graph.add((unit, RDF.type, CNFO.FundUnit))
        graph.add((unit, CNFO.issuedByFund, fund))
        graph.add((nav, RDF.type, CNFO.NetAssetValueRecord))
        graph.add((nav, CNFO.recordForFundUnit, unit))
        DeductiveClosure(
            OWLRL_Semantics,
            axiomatic_triples=False,
            datatype_axioms=False,
        ).expand(graph)
        self.assertIn((fund, CNFO.hasFundManager, manager), graph)
        self.assertIn((fund, CNFO.hasFundDepositary, depositary), graph)
        self.assertIn((fund, CNFO.hasFundParty, manager), graph)
        self.assertIn((nav, CNFO.recordForFund, fund), graph)

    def test_module_interface_only_exposes_current_modules(self) -> None:
        session = OntologyViewerSession(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
        tree = session.modules()

        self.assertEqual(tree["module_count"], 2)
        self.assertEqual(len(tree["roots"]), 1)
        root = tree["roots"][0]
        self.assertEqual(root["iri"], str(CNFO.CNFODomain))
        self.assertEqual(root["label"], "CNFO 基金领域入口")
        self.assertIn((CNFO.CNFODomain, RDF.type, CNFOM.OntologyModule), self.source)
        self.assertEqual(len(root["children"]), 1)
        fund = root["children"][0]
        self.assertEqual(fund["iri"], str(CNFO.CNFOFundOntology))
        self.assertEqual(fund["label"], "基金本体")
        self.assertEqual(fund["class_count"], len(session.class_ids))
        self.assertIn(
            str(CNFO.ExchangeTradedFund),
            {item["iri"] for item in session.search("ETF", "cnfo", 100, fund["iri"])},
        )

    def test_property_neighborhood_preserves_direction_and_endpoint(self) -> None:
        session = OntologyViewerSession(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
        detail = session.detail(str(CNFO.FundUnit))

        outgoing = {item["iri"]: item for item in detail["properties"]["outgoing"]}
        incoming = {item["iri"]: item for item in detail["properties"]["incoming"]}
        self.assertEqual(outgoing[str(CNFO.hasFundPosition)]["direction"], "outgoing")
        self.assertEqual(
            outgoing[str(CNFO.hasFundPosition)]["ranges"][0]["iri"],
            str(CNFO.FundPosition),
        )
        self.assertEqual(incoming[str(CNFO.hasFundUnit)]["direction"], "incoming")
        self.assertEqual(
            incoming[str(CNFO.hasFundUnit)]["domains"][0]["iri"],
            str(CNFO.Fund),
        )

    def test_property_sections_follow_inheritance_chain(self) -> None:
        session = OntologyViewerSession(ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
        detail = session.detail(str(CNFO.FundUnit))
        sections = detail["property_sections"]
        by_local_name = {section["class"]["local_name"]: section for section in sections}

        self.assertEqual(sections[0]["class"]["local_name"], "FundUnit")
        self.assertIn("FundObject", by_local_name)

        fund_unit = by_local_name["FundUnit"]
        fund_unit_properties = {
            item["iri"]
            for direction in ("outgoing", "incoming")
            for item in fund_unit[direction]
        }
        self.assertIn(str(CNFO.hasFundPosition), fund_unit_properties)
        self.assertNotIn(str(CNFO.hasFundObject), fund_unit_properties)

        fund_object = by_local_name["FundObject"]
        self.assertIn(
            str(CNFO.hasFundObject),
            {item["iri"] for item in fund_object["incoming"]},
        )


if __name__ == "__main__":
    unittest.main()
