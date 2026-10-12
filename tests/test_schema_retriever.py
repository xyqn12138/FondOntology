"""问题驱动本体裁剪原型回归。"""
from __future__ import annotations

import unittest
from pathlib import Path

from test_support import shared_stack as build_stack, shared_index as OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


class SchemaRetrieverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = OntologyIndex(build_stack(SOURCE, ABOX))
        cls.retriever = SchemaRetriever(cls.index)

    def test_cross_node_topic_query_keeps_path_and_domain(self) -> None:
        result = self.retriever.retrieve("医药主题的股票型基金有哪些？")
        self.assertIn("EquityFund", result.render_text)
        self.assertIn("FundInvestmentStrategy", result.render_text)
        self.assertIn("usesInvestmentStrategy", result.render_text)
        self.assertIn("investmentFocus", result.render_text)

    def test_aggregation_keeps_inverse_manager_path(self) -> None:
        result = self.retriever.retrieve("同时管理多个基金的基金经理有哪些？")
        self.assertIn("FundManagerPerson", result.render_text)
        self.assertIn("Fund", result.render_text)
        self.assertIn("hasFundManager", result.render_text)
        self.assertIn("^hasFundManager", result.render_text)

    def test_context_is_smaller_than_full_view(self) -> None:
        result = self.retriever.retrieve("R4以上的基金有哪些？")
        full = self.retriever.ctx.render_for_llm()
        self.assertLess(len(result.render_text), len(full))
        self.assertLessEqual(result.char_count, 10000)
        self.assertGreater(result.token_count, 0)
        self.assertIn(result.tokenizer, ("cl100k_base", "char_heuristic"))


if __name__ == "__main__":
    unittest.main()
