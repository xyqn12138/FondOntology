from __future__ import annotations

import unittest
from copy import deepcopy

from fondontology.evaluation.retrieval_comparison import (
    _cache_state, _distribution, _paired_identity, summarize_run,
)


class RetrievalComparisonTests(unittest.TestCase):
    def test_fixed_denominator_retains_errors_and_negative_controls(self):
        target = {"doc_id": "synthetic", "article_number": 1}
        questions = [{"id": "answerable"}, {"id": "negative"}]
        oracle = [
            {"id": "answerable", "expected_status": "retrieved", "target_articles": [target],
             "required_groups": [[target]], "allowed_doc_ids": ["synthetic"]},
            {"id": "negative", "expected_status": "unresolved", "target_articles": [],
             "required_groups": [], "allowed_doc_ids": []},
        ]
        audit = {"verified": True, "verification_kind": "local_artifact_consistency_only", "rows": [
            {"id": "answerable", "status": "error", "evidence": [], "retrieval_latency_ms": None,
             "strategy_trace": {"resource_events": [{"kind": "rerank", "status": "error"}]}},
            {"id": "negative", "status": "unresolved", "evidence": [], "retrieval_latency_ms": 1.0},
        ]}
        result = summarize_run(audit, questions, oracle)
        self.assertEqual(result["retrieval_score"]["denominator"], 2)
        self.assertEqual(result["retrieval_score"]["pass_count"], 1)
        self.assertEqual(result["diagnostics"]["target_only_precision"], 0)
        self.assertIsNone(result["diagnostics"]["retrieval_latency_ms"]["mean"])
        self.assertEqual(result["diagnostics"]["http_transport_error_count"], 1)
        self.assertEqual(result["by_expected_status"]["retrieved"]["denominator"], 1)

    def test_nearest_rank_percentile_and_empty_group_are_explicit(self):
        self.assertEqual(_distribution([1, 2, 4, 8], 4)["p95"], 8)
        self.assertEqual(_distribution([1, 2, 4, 8], 4)["p50"], 3)
        self.assertIsNone(_distribution([], 0)["mean"])

    def test_cache_states_do_not_conflate_cold_mixed_warm_or_bypass(self):
        strategy = {"requested_strategy": "hybrid_rrf", "status": "ok",
                    "cache": {"enabled": True, "hits": 0, "misses": 4}}
        self.assertEqual(_cache_state(strategy), "cold")
        strategy["cache"]["hits"] = 3
        self.assertEqual(_cache_state(strategy), "mixed")
        strategy["cache"]["misses"] = 0
        self.assertEqual(_cache_state(strategy), "warm")
        strategy["status"] = "bypassed"
        self.assertEqual(_cache_state(strategy), "bypassed")
        self.assertEqual(_cache_state({"requested_strategy": "bm25"}), "not_used")

    def test_pair_identity_locks_scopes_dates_budget_and_code(self):
        audit = {"snapshot_id": "synthetic", "snapshot_members_sha256": "members"}
        envelope = {"provenance": {"code_version": "code", "ontology_version": "unused",
                    "retrieval_config": {"top_k": 3, "candidate_k": 20, "rrf_k": 60,
                                         "case_scopes": [{"id": "question", "doc_ids": []}],
                                         "per_case_dates": {"question": "2026-10-12"},
                                         "retrieval_strategy": "bm25"}}}
        identity = _paired_identity(audit, envelope)
        candidate = deepcopy(envelope)
        candidate["provenance"]["retrieval_config"].update(
            retrieval_strategy="hybrid_rrf", allow_retrieval_network=True, retrieval_cache="cache")
        self.assertEqual(identity, _paired_identity(audit, candidate))
        for field, value in (("candidate_k", 40), ("rrf_k", 30), ("case_scopes", []),
                             ("per_case_dates", {"question": "2025-01-01"})):
            with self.subTest(field=field):
                changed = deepcopy(envelope)
                changed["provenance"]["retrieval_config"][field] = value
                self.assertNotEqual(identity, _paired_identity(audit, changed))
        candidate["provenance"]["code_version"] = "changed"
        self.assertNotEqual(identity, _paired_identity(audit, candidate))


if __name__ == "__main__":
    unittest.main()
