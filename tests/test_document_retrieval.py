from __future__ import annotations

import json
import hashlib
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from fondontology.qa.rag.document_retrieval import (
    RetrievalResources, RetrievalStrategyError, child_chunks, retrieve_documents,
)
from fondontology.qa.rag.document_pipeline import answer_document
from fondontology.qa.rag.store import ChunkStore, RagChunk
from fondontology.corpus import CorpusRepository
from tools.document_rag import main


def parent(identifier, text, start=20):
    return RagChunk(
        identifier, identifier, None, "regulation_article", None, "article", text,
        {"char_start": start, "char_end": start + len(text), "title": identifier},
        version_id=f"v-{identifier}")


def scope(identifiers, query="allocation"):
    return {"status": "resolved", "eligible_chunk_ids": identifiers,
            "body_query": query, "article_numbers": []}


class DocumentRetrievalTest(unittest.TestCase):
    def setUp(self):
        self.parents = [parent("alpha", "allocation limit with exception retained."),
                        parent("beta", "different investment rule"),
                        parent("outside", "allocation allocation allocation")]
        self.store = ChunkStore(self.parents, corpus_metadata={"members_sha256": "a" * 64})
        self.scope = scope(["alpha", "beta"])

    def test_all_strategies_filter_before_calls_and_article_scope_bypasses_models(self):
        embed = Mock(return_value=[[1, 0], [0, 1]])
        rerank = Mock(return_value=[(0, 1.0)])
        resources = RetrievalResources(
            embed=embed, rerank=rerank, embed_requires_network=False,
            rerank_requires_network=False)
        for strategy in ("bm25", "parent_child", "hybrid_rrf", "bm25_rerank"):
            denied = retrieve_documents(
                self.store, {"status": "unresolved", "eligible_chunk_ids": []},
                strategy=strategy, resources=resources)
            self.assertEqual(denied.hits, [])
            self.assertEqual(denied.strategy_trace["status"], "bypassed")
            direct = retrieve_documents(
                self.store, {**self.scope, "article_numbers": [3]},
                strategy=strategy, resources=resources)
            self.assertEqual(direct.ranking, "article_locator")
            self.assertEqual([chunk.chunk_id for chunk, score in direct.hits], ["alpha", "beta"])
        embed.assert_not_called()
        rerank.assert_not_called()
        result = retrieve_documents(self.store, self.scope)
        self.assertEqual([chunk.chunk_id for chunk, score in result.hits], ["alpha"])

    def test_children_cover_exact_parent_offsets_and_final_evidence_keeps_exception(self):
        text = ("allocation sentence. " * 30) + "Exception: the limit does not apply to exempt funds."
        full = parent("long", text)
        children, origins = child_chunks([full])
        self.assertEqual("".join(child.text for child in children), text)
        self.assertTrue(all(len(child.text) <= 240 for child in children))
        for child in children:
            origin = origins[child.chunk_id]
            self.assertEqual(child.text, text[
                origin["char_start"] - 20:origin["char_end"] - 20])
        base = ChunkStore([full], corpus_metadata={"members_sha256": "a" * 64})
        result = retrieve_documents(base, scope(["long"]), strategy="parent_child")
        self.assertEqual(len(result.hits), 1)
        self.assertEqual(result.hits[0][0].text, text)
        self.assertIn("exempt funds", result.hits[0][0].text)
        self.assertTrue(result.strategy_trace["child_matches"])

    def test_rrf_is_equal_weight_rank_sixty_and_dense_only_candidates_are_scoped(self):
        def embed(texts):
            return [[0, 1] if text == "different investment rule" else [1, 0] for text in texts]
        result = retrieve_documents(
            self.store, self.scope, strategy="hybrid_rrf",
            resources=RetrievalResources(
                embed=embed, embedding_config={"provider": "fake", "model": "test"},
                embed_requires_network=False))
        self.assertEqual(result.ranking, "hybrid_rrf")
        self.assertEqual(result.hits[0][0].chunk_id, "alpha")
        self.assertAlmostEqual(result.hits[0][1], 2 / 61)
        self.assertNotIn("outside", [chunk.chunk_id for chunk, score in result.hits])
        self.assertEqual(len(result.strategy_trace["channels"]["dense"]), 2)

    def test_embedding_cache_reuse_and_model_snapshot_query_identity(self):
        with tempfile.TemporaryDirectory() as root:
            embed = Mock(side_effect=lambda texts: [[1, 2] for text in texts])
            resources = RetrievalResources(
                embed=embed, embedding_config={"provider": "fake", "model": "one"},
                embed_requires_network=False)
            first = retrieve_documents(
                self.store, self.scope, strategy="hybrid_rrf", resources=resources, cache_path=root)
            self.assertEqual(first.strategy_trace["cache"]["misses"], 3)
            second = retrieve_documents(
                self.store, self.scope, strategy="hybrid_rrf", resources=resources, cache_path=root)
            self.assertEqual(second.strategy_trace["cache"]["hits"], 3)
            self.assertEqual(embed.call_count, 2)
            self.assertEqual(second.strategy_trace["cache"]["entries"],
                             first.strategy_trace["cache"]["entries"])
            retrieve_documents(
                self.store, scope(["alpha", "beta"], "changed query"),
                strategy="hybrid_rrf", resources=resources, cache_path=root)
            self.assertEqual(embed.call_count, 3)
            resources.embedding_config["model"] = "two"
            retrieve_documents(
                self.store, self.scope, strategy="hybrid_rrf", resources=resources, cache_path=root)
            self.assertEqual(embed.call_count, 5)
            self.store.corpus_metadata["members_sha256"] = "b" * 64
            retrieve_documents(
                self.store, self.scope, strategy="hybrid_rrf", resources=resources, cache_path=root)
            self.assertEqual(embed.call_count, 7)
            path = next(Path(root).glob("*.json"))
            payload = json.loads(path.read_text())
            self.assertEqual(len(payload["vector_sha256"]), 64)

    def test_remote_network_requires_permission_and_failure_never_falls_back(self):
        resources = RetrievalResources(embed=Mock(side_effect=RuntimeError("secret should not leak")))
        with self.assertRaises(RetrievalStrategyError) as denied:
            retrieve_documents(self.store, self.scope, strategy="hybrid_rrf", resources=resources)
        self.assertEqual(denied.exception.reason, "retrieval_network_not_allowed")
        resources.embed.assert_not_called()
        with self.assertRaises(RetrievalStrategyError) as failed:
            retrieve_documents(
                self.store, self.scope, strategy="hybrid_rrf",
                resources=resources, allow_network=True)
        self.assertEqual(failed.exception.reason, "embedding_call_failed")
        self.assertNotIn("secret", str(failed.exception))
        self.assertEqual(failed.exception.strategy_trace["status"], "error")

    def test_rerank_has_full_candidate_validation_and_original_input_indices(self):
        base = ChunkStore([
            parent("alpha", "allocation allocation"), parent("beta", "allocation other")],
            corpus_metadata={"members_sha256": "a" * 64})
        resources = RetrievalResources(
            rerank=lambda query, texts: [(1, 0.9), (0, 0.1)], rerank_requires_network=False)
        result = retrieve_documents(
            base, scope(["alpha", "beta"]), strategy="bm25_rerank", resources=resources)
        self.assertEqual(result.ranking, "rerank")
        self.assertEqual(result.hits[0][0].chunk_id, "beta")
        self.assertEqual(result.strategy_trace["rerank"][0]["index"], 1)
        resources.rerank = lambda query, texts: [(0, 0.9), (0, 0.1)]
        with self.assertRaises(RetrievalStrategyError):
            retrieve_documents(
                base, scope(["alpha", "beta"]), strategy="bm25_rerank", resources=resources)

    def test_bad_embeddings_and_corrupt_cache_fail_closed(self):
        for vectors in ([[float("nan"), 1]], [[0, 0]], [[1, 0]]):
            with self.subTest(vectors=vectors):
                resources = RetrievalResources(
                    embed=lambda texts: vectors, embed_requires_network=False)
                with self.assertRaises(RetrievalStrategyError):
                    retrieve_documents(
                        self.store, self.scope, strategy="hybrid_rrf", resources=resources)
        with tempfile.TemporaryDirectory() as root:
            resources = RetrievalResources(
                embed=lambda texts: [[1, 0] for text in texts], embed_requires_network=False)
            retrieve_documents(
                self.store, self.scope, strategy="hybrid_rrf", resources=resources, cache_path=root)
            for path in Path(root).glob("*.json"):
                path.write_text("{}")
            with self.assertRaises(RetrievalStrategyError) as corrupt:
                retrieve_documents(
                    self.store, self.scope, strategy="hybrid_rrf", resources=resources, cache_path=root)
            self.assertEqual(corrupt.exception.reason, "invalid_embedding_cache")

    def test_pipeline_error_preserves_real_scope_and_produces_no_contexts(self):
        base = self.store
        base.corpus_metadata.update(
            db_path=str(Path("unused").resolve()), snapshot_id="fixture", as_of="2026-10-11",
            kind="regression", include_undated_research=False)
        resources = RetrievalResources(embed=Mock(side_effect=RuntimeError()))
        result = answer_document(
            "allocation", db_path="unused", snapshot_id="fixture", as_of="2026-10-11",
            allow_nontrusted=True, store=base, retrieval_strategy="hybrid_rrf",
            resources=resources)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["scope"]["status"], "resolved")
        self.assertEqual(result["retrieved_contexts"], [])
        self.assertEqual(result["strategy_trace"]["reason"], "retrieval_network_not_allowed")

    def test_resource_events_record_actual_provider_invocations(self):
        resources = RetrievalResources(embedding_config={"model": "fake"},
                                       embed_requires_network=False)
        def embed(texts):
            resources.events.append({"kind": "embedding", "input_count": len(texts)})
            return [[1, 0] for text in texts]
        resources.embed = embed
        result = retrieve_documents(
            self.store, self.scope, strategy="hybrid_rrf", resources=resources)
        self.assertEqual(len(result.strategy_trace["resource_events"]), 2)

    def test_cli_parent_child_is_offline_and_remote_failure_exits_one_with_trace(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            source = directory / "synthetic.md"
            source.write_text("allocation limit. The exception remains present.", encoding="utf-8")
            manifest = directory / "manifest.jsonl"
            manifest.write_text(json.dumps({
                "doc_id": "alpha", "title": "Alpha Act", "doc_type": "regulation_article",
                "path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_uri": "urn:synthetic:alpha", "authority": "synthetic",
                "status": "verified", "issued_date": "2026-01-01",
                "provenance": {"fixture": "synthetic"}, "locator": {"title": "Alpha Act"},
            }), encoding="utf-8")
            database = directory / "corpus.sqlite"
            repository = CorpusRepository(database)
            versions = repository.import_manifest(manifest)["version_ids"]
            repository.publish_snapshot("fixture", versions, kind="regression")
            output = directory / "actual.json"
            arguments = [
                "--db", str(database), "--snapshot", "fixture", "--as-of", "2026-10-11",
                "--allow-nontrusted", "--question", "allocation", "--output", str(output),
                "--top-k", "3", "--candidate-k", "20", "--retrieval-strategy",
            ]
            with patch("tools.document_rag._provider_resources",
                       side_effect=AssertionError("Offline strategy cannot build models")), redirect_stdout(io.StringIO()):
                self.assertEqual(main([*arguments, "parent_child"]), 0)
            trace = json.loads(output.with_suffix(".traces.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(trace["config"]["retrieval_strategy"], "parent_child")
            self.assertEqual(trace["strategy_trace"]["effective_strategy"], "parent_child")
            self.assertTrue(trace["strategy_trace"]["child_matches"])
            resource = RetrievalResources(embed=Mock(side_effect=RuntimeError()))
            with patch("tools.document_rag._provider_resources", return_value=resource), redirect_stdout(io.StringIO()):
                self.assertEqual(main([*arguments, "hybrid_rrf"]), 1)
            resource.embed.assert_not_called()
            trace = json.loads(output.with_suffix(".traces.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(trace["status"], "error")
            self.assertEqual(trace["scope"]["status"], "resolved")
            self.assertEqual(trace["config"]["retrieval"], "hybrid_rrf")


if __name__ == "__main__":
    unittest.main()
