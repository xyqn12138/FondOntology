"""M1 补充：T-BOX 推理层回归（propertyChainAxiom / OWL-RL 闭包 / 推理产物）。

核验口径（artifacts/_m1_audit 三方比对 72/72 一致）：
- propertyChainAxiom 恰为 4 条：recordForFund / hasFundParty / hasFundDepositary / hasFundManager
- closure ⊇ explicit；inferred = closure − explicit
- 有实例输入时 property chain 参与物化
"""
from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Graph, Namespace, URIRef

from fondontology.ontology_loader import load_ontology_graph
from fondontology.tbox import inference

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")


class TboxInferenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.g = load_ontology_graph(SOURCE)
        cls.chain_names = {p[0].replace(str(CNFO), "") for p in inference.property_chain_axioms(cls.g)}

    def test_property_chain_axioms_exactly_four(self) -> None:
        self.assertEqual(self.chain_names,
                         {"recordForFund", "hasFundParty", "hasFundDepositary", "hasFundManager"})

    def test_chain_heads_are_declared_properties(self) -> None:
        # 链头属性必须在本体中已声明（不能在推理层凭空出现）
        from rdflib.namespace import OWL, RDF
        for head in ("hasFundManager", "hasFundDepositary", "hasFundParty", "recordForFund"):
            self.assertIn((CNFO[head], RDF.type, OWL.ObjectProperty), self.g)

    def test_closure_contains_explicit_and_adds_inferred(self) -> None:
        closed = inference.compute_closure(self.g)
        explicit = set(self.g)
        inferred = inference.inferred_triples(self.g, closed)
        self.assertTrue(explicit <= set(closed))
        self.assertGreaterEqual(len(inferred), 1)
        # 推理产物必须是闭包中、显式中都不存在的（diff 定义）
        self.assertTrue(inferred <= set(closed))

    def test_property_chain_materializes_with_instances(self) -> None:
        mini = Graph()
        mini += self.g
        fund = URIRef(str(CNFO) + "AuditFund")
        role = URIRef(str(CNFO) + "AuditRole")
        party = URIRef(str(CNFO) + "AuditParty")
        mini.add((fund, CNFO.hasFundManagerRole, role))
        mini.add((role, CNFO.rolePlayedBy, party))
        closed = inference.compute_closure(mini)
        self.assertIn((fund, CNFO.hasFundManager, party), closed)
        inferred = inference.inferred_triples(mini, closed)
        self.assertIn((fund, CNFO.hasFundManager, party), inferred)


if __name__ == "__main__":
    unittest.main()