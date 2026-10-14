from __future__ import annotations

import copy
import json
import tempfile
import unittest
from unittest.mock import Mock

from fondontology.corpus import CorpusError
from fondontology.qa.rag.document_retrieval import (
    RetrievalResources, RetrievalStrategyError, retrieve_documents,
)
from fondontology.qa.rag.query_transforms import (
    MAX_QUERY_CHARACTERS, MAX_TRANSFORM_CHARACTERS, QueryTransformError,
    QueryTransformResource, text_hash, transform_query,
)
from fondontology.qa.rag.ranking import reciprocal_rank_fusion, validate_rerank_scores
from fondontology.qa.rag.store import ChunkStore, RagChunk


class QueryTransformTest(unittest.TestCase):
    def setUp(self):
        self.store = ChunkStore([
            RagChunk(identifier, identifier, None, "regulation_article", None, "article", text,
                     {"char_start": 0, "char_end": len(text)}, version_id="version-" + identifier)
            for identifier, text in (("first", "allocation exception retained"),
                                     ("second", "redemption deadline"),
                                     ("outside", "redemption redemption deadline"))
        ], corpus_metadata={"members_sha256": "a" * 64})
        self.scope = {"status": "resolved", "eligible_chunk_ids": ["first", "second"],
                      "body_query": "allocation", "article_numbers": []}

    def resource(self, output="redemption"):
        return QueryTransformResource(Mock(return_value=output), "synthetic", "fixture", False)

    def test_identity_and_explicit_bypass_do_not_construct_resources(self):
        factory = Mock(side_effect=AssertionError("Resource must stay unused"))
        for mode, bypass in (("identity", False), ("rewrite", True)):
            result = transform_query("allocation", mode=mode, bypass=bypass, resource=factory)
            self.assertEqual(result.lexical_query, "allocation")
            self.assertEqual(result.dense_query, "allocation")
        factory.assert_not_called()

    def test_network_gate_precedes_call_and_failures_are_redacted(self):
        resource = self.resource()
        resource.requires_network = True
        with self.assertRaises(QueryTransformError) as error:
            transform_query("allocation", mode="rewrite", resource=resource)
        self.assertEqual(error.exception.reason, "query_transform_network_not_allowed")
        resource.transform.assert_not_called()
        resource.transform.side_effect = RuntimeError("synthetic-secret")
        with self.assertRaises(QueryTransformError) as error:
            transform_query("allocation", mode="rewrite", resource=resource, allow_network=True)
        self.assertEqual(error.exception.reason, "query_transform_call_failed")
        self.assertNotIn("synthetic-secret", json.dumps(error.exception.trace))
        self.assertIsNone(error.exception.trace["output"])

    def test_bad_output_and_input_budgets_fail_without_fallback(self):
        for output in (None, 1, "  ", "x" * (MAX_TRANSFORM_CHARACTERS + 1)):
            with self.subTest(output_type=type(output)), self.assertRaises(QueryTransformError):
                transform_query("allocation", mode="rewrite", resource=self.resource(output))
        factory = Mock()
        with self.assertRaises(QueryTransformError) as error:
            transform_query("x" * (MAX_QUERY_CHARACTERS + 1), mode="rewrite", resource=factory)
        self.assertEqual(error.exception.reason, "query_transform_input_too_long")
        factory.assert_not_called()
        with self.assertRaises(CorpusError):
            transform_query("allocation", mode="automatic")

    def test_rewrite_changes_lexical_search_but_never_resolves_scope_again(self):
        original_scope = copy.deepcopy(self.scope)
        resource = self.resource("《Invented Act》第999条 redemption")
        result = retrieve_documents(self.store, self.scope, query_transform="rewrite",
                                    query_transform_resource=resource)
        self.assertEqual(self.scope, original_scope)
        self.assertEqual([chunk.chunk_id for chunk, score in result.hits], ["second"])
        transformed = result.strategy_trace["query_transform"]
        self.assertEqual(transformed["input_sha256"], text_hash("allocation"))
        self.assertEqual(transformed["output_sha256"], text_hash(transformed["output"]))

    def test_hyde_changes_only_dense_input_and_never_adds_synthetic_evidence(self):
        embed = Mock(side_effect=lambda texts: [[1, 0] for text in texts])
        resource = self.resource("HYPOTHETICAL passage")
        result = retrieve_documents(
            self.store, self.scope, strategy="hybrid_rrf", query_transform="hyde",
            query_transform_resource=resource,
            resources=RetrievalResources(embed=embed, embed_requires_network=False))
        self.assertEqual(embed.call_args_list[-1].args[0], ["HYPOTHETICAL passage"])
        self.assertEqual(result.strategy_trace["channels"]["bm25"][0]["chunk_id"], "first")
        self.assertEqual({chunk.chunk_id for chunk, score in result.hits}, {"first", "second"})
        self.assertTrue(all("HYPOTHETICAL" not in chunk.text for chunk, score in result.hits))
        with self.assertRaises(CorpusError):
            retrieve_documents(self.store, self.scope, query_transform="hyde")

    def test_rerank_receives_original_not_rewritten_question(self):
        rerank = Mock(return_value=[(0, 0.9)])
        result = retrieve_documents(
            self.store, self.scope, strategy="bm25_rerank", query_transform="rewrite",
            query_transform_resource=self.resource(),
            resources=RetrievalResources(rerank=rerank, rerank_requires_network=False))
        rerank.assert_called_once_with("allocation", ["redemption deadline"])
        self.assertEqual(result.hits[0][0].chunk_id, "second")

    def test_scope_bypasses_transform_and_failed_transform_stops_every_stage(self):
        resource = self.resource()
        for selected_scope in ({"status": "unresolved", "eligible_chunk_ids": []},
                               {**self.scope, "article_numbers": [1]}):
            result = retrieve_documents(self.store, selected_scope, query_transform="rewrite",
                                        query_transform_resource=resource)
            self.assertNotIn("query_transform", result.strategy_trace)
        resource.transform.assert_not_called()
        resource.transform.side_effect = RuntimeError("failure")
        with self.assertRaises(RetrievalStrategyError) as error:
            retrieve_documents(self.store, self.scope, query_transform="rewrite",
                               query_transform_resource=resource)
        self.assertEqual(error.exception.strategy_trace["channels"], {})
        self.assertEqual(error.exception.strategy_trace["stages"], [])

    def test_transformed_text_is_bound_to_embedding_cache_identity(self):
        resource = self.resource("first hypothesis")
        embed = Mock(side_effect=lambda texts: [[1, 0] for text in texts])
        resources = RetrievalResources(embed=embed, embed_requires_network=False)
        with tempfile.TemporaryDirectory() as directory:
            configuration = dict(strategy="hybrid_rrf", query_transform="hyde", resources=resources,
                                 query_transform_resource=resource, cache_path=directory)
            first = retrieve_documents(self.store, self.scope, **configuration)
            resource.transform.return_value = "second hypothesis"
            second = retrieve_documents(self.store, self.scope, **configuration)
            self.assertEqual(second.strategy_trace["cache"]["hits"], 2)
            self.assertEqual(second.strategy_trace["cache"]["misses"], 1)
            self.assertNotEqual(first.strategy_trace["cache"]["entries"][-1]["key"],
                                second.strategy_trace["cache"]["entries"][-1]["key"])

    def test_standalone_ranking_has_stable_ties_and_strict_candidate_coverage(self):
        self.assertEqual(reciprocal_rank_fusion({"one": ["b"], "two": ["a"]}, limit=2),
                         [("a", 1 / 61), ("b", 1 / 61)])
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion({"one": ["a", "a"]}, limit=2)
        for scores in ([(0, 1)], [(0, float("nan")), (1, 0.5)], [(True, 1), (0, 0.5)]):
            with self.subTest(scores=scores), self.assertRaises(ValueError):
                validate_rerank_scores(scores, 2)


if __name__ == "__main__":
    unittest.main()
