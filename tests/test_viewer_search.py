"""Regression tests for the ontology browser class search.

These lock in the two search fixes:

* Precision: queries never match the shared IRI prefix or incidental
  definition text, and short Latin tokens (``ETF``, ``LOF``) match whole
  words only, so ``ETF`` finds exactly ``ExchangeTradedFund`` instead of
  every ``...getFund`` local name.
* Completeness: an empty query returns all classes so the sidebar can
  show the full class index instead of a fixed 40/100 slice.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# 直接运行本脚本时，Python 将脚本所在目录（tests/）而非项目根目录加入 sys.path；
# 此处补上项目根目录，保证 `fondontology` 包可导入（已安装到环境中时同样生效）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.viewer import OntologyViewerSession


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "artifacts" / "cnfo" / "cnfo-fund-tbox.ttl"


class ViewerSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = OntologyViewerSession(RELEASE)

    def names(self, query: str, **kwargs: object) -> set[str]:
        return {item["local_name"] for item in self.session.search(query, "all", 1000, **kwargs)}

    def test_empty_query_returns_every_class(self) -> None:
        results = self.session.search("", "all", 1000)
        self.assertEqual(len(results), len(self.session.class_ids))
        self.assertEqual(
            {item["iri"] for item in results},
            {str(item) for item in self.session.class_ids},
        )

    def test_shared_iri_prefix_is_never_a_match(self) -> None:
        for noise in ("ontology", "cnfo", "example", "http", "www.w3.org"):
            self.assertEqual(self.names(noise), set(), msg=noise)

    def test_short_latin_token_matches_whole_word_only(self) -> None:
        # "etf" is a substring of PensionTargetFund / MoneyMarketFund /
        # ExchangeTradedFund local names; only the alt-label "ETF" class may match.
        self.assertEqual(self.names("ETF"), {"ExchangeTradedFund"})
        self.assertEqual(self.names("LOF"), {"ListedOpenEndedFund"})
        self.assertEqual(self.names("FOF"), {"FundOfFunds"})

    def test_acronyms_with_plural_or_longer_forms(self) -> None:
        self.assertEqual(self.names("QDII"), {"QDIIFund"})
        self.assertEqual(self.names("REIT"), {"InfrastructurePublicREIT"})
        self.assertEqual(self.names("REITs"), {"InfrastructurePublicREIT"})

    def test_definition_text_is_not_searchable(self) -> None:
        # Previously the definition haystack made MoneyMarketFund and
        # PensionTargetFund match "ETF"; identifiers must win over prose.
        self.assertEqual(self.names("ETF"), {"ExchangeTradedFund"})

    def test_chinese_substring_matching(self) -> None:
        self.assertIn("HongKongMutualRecognitionFund", self.names("香港互认基金"))
        self.assertIn("MainlandHongKongMutualRecognitionFund", self.names("香港互认基金"))
        self.assertEqual(self.names("管理"), {"FundManagerRole", "FundManagementCompany", "FundAdministratorRole"})

    def test_exact_label_ranks_first(self) -> None:
        results = self.session.search("基金", "all", 1000)
        self.assertEqual(results[0]["local_name"], "Fund")

    def test_multiple_tokens_are_anded(self) -> None:
        self.assertEqual(self.names("ETF 基金"), {"ExchangeTradedFund"})
        self.assertEqual(
            self.names("指数"),
            {"IndexTrackingStrategy", "ExchangeTradedFund", "MarketIndex"},
        )

    def test_module_scope_preserves_alt_label_matches(self) -> None:
        fund_module = ""
        for root in self.session.modules()["roots"]:
            for child in root.get("children", []):
                if child["label"] == "基金本体":
                    fund_module = str(child["iri"])
        self.assertTrue(fund_module, "基金本体 module not found")
        self.assertIn("ExchangeTradedFund", self.names("ETF", module_iri=fund_module))

    def test_limit_is_respected(self) -> None:
        self.assertEqual(len(self.session.search("基金", "all", 5)), 5)


if __name__ == "__main__":
    unittest.main()
