from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import httpx

from fondontology.corpus import CorpusError
from fondontology.qa.rag.document_providers import build_resources


class DocumentProviderTests(unittest.TestCase):
    def resources(self):
        with patch("fondontology.qa.config.embedding_config", return_value={
                "EMBEDDING_MODEL": "synthetic-embedding", "EMBEDDING_URL": "https://fixture.invalid/v1",
                "EMBEDDING_KEY": "synthetic-secret"}), patch(
                "fondontology.qa.config.rerank_config", return_value={
                    "RERANK_MODEL": "synthetic-rerank", "RERANK_URL": "https://fixture.invalid/rerank",
                    "RERANK_KEY": "synthetic-secret"}):
            return build_resources()

    def test_construction_is_offline_and_public_metadata_excludes_credentials(self):
        with patch("httpx.post", side_effect=AssertionError("Unexpected network")):
            resources = self.resources()
        self.assertNotIn("synthetic-secret", json.dumps(resources.embedding_config))
        self.assertNotIn("synthetic-secret", json.dumps(resources.rerank_config))
        self.assertEqual(resources.events, [])

    def test_batch_order_and_call_receipts(self):
        resources = self.resources()

        def reply(endpoint, **kwargs):
            count = len(kwargs["json"]["input"])
            return httpx.Response(200, json={"data": [
                {"index": index, "embedding": [1.0, float(index)]}
                for index in reversed(range(count))], "usage": {"total_tokens": count}})

        with patch("httpx.post", side_effect=reply) as network:
            vectors = resources.embed([f"text {index}" for index in range(27)])
        self.assertEqual(len(vectors), 27)
        self.assertEqual(vectors[24], [1.0, 24.0])
        self.assertEqual(network.call_count, 2)
        self.assertEqual([event["input_count"] for event in resources.events], [25, 2])
        self.assertTrue(all(event["status"] == "ok"
                            and event["response_validation_status"] == "ok"
                            for event in resources.events))
        self.assertNotIn("synthetic-secret", json.dumps(resources.events))

    def test_invalid_embedding_indexes_vectors_and_dimensions_raise(self):
        responses = [
            [{"index": 0, "embedding": [1.0]}, {"index": 0, "embedding": [1.0]}],
            [{"index": 0, "embedding": [0.0]}, {"index": 1, "embedding": [1.0]}],
            [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [1.0, 1.0]}],
        ]
        for items in responses:
            with self.subTest(items=items), patch("httpx.post", return_value=httpx.Response(
                    200, json={"data": items})):
                resources = self.resources()
                with self.assertRaises(CorpusError):
                    resources.embed(["first", "second"])
                event = resources.events[-1]
                self.assertEqual(event["status"], "ok")
                self.assertEqual(event["response_validation_status"], "error")
                self.assertEqual(event["response_validation_error_type"], "CorpusError")

    def test_rerank_covers_every_input_and_keeps_finite_scores(self):
        resources = self.resources()
        with patch("httpx.post", return_value=httpx.Response(200, json={"output": {"results": [
                {"index": 1, "relevance_score": 0.8}, {"index": 0, "relevance_score": 0.2}]}})):
            self.assertEqual(resources.rerank("query", ["first", "second"]), [(1, 0.8), (0, 0.2)])
        with patch("httpx.post", return_value=httpx.Response(200, json={"output": {"results": [
                {"index": 1, "relevance_score": 0.8}]}})):
            with self.assertRaises(CorpusError):
                resources.rerank("query", ["first", "second"])
        self.assertEqual(resources.events[-1]["status"], "ok")
        self.assertEqual(resources.events[-1]["response_validation_status"], "error")

    def test_network_errors_are_redacted_and_never_silently_fall_back(self):
        resources = self.resources()
        with patch("httpx.post", return_value=httpx.Response(401, text="synthetic-secret")) as network:
            with self.assertRaises(CorpusError) as error:
                resources.embed(["query"])
        self.assertEqual(network.call_count, 1)
        self.assertNotIn("synthetic-secret", str(error.exception))
        self.assertEqual(resources.events[0]["status"], "error")
        self.assertEqual(resources.events[0]["response_validation_status"], "not_checked")

    def test_unused_invalid_endpoint_never_blocks_valid_resource(self):
        for invalid_resource in ("embedding", "rerank"):
            embedding = {
                "EMBEDDING_MODEL": "fake", "EMBEDDING_URL": "https://fixture.invalid/v1",
                "EMBEDDING_KEY": "synthetic-secret"}
            rerank = {
                "RERANK_MODEL": "fake", "RERANK_URL": "https://fixture.invalid/rerank",
                "RERANK_KEY": "synthetic-secret"}
            if invalid_resource == "embedding":
                embedding["EMBEDDING_URL"] = "https://synthetic-secret@fixture.invalid/v1"
            else:
                rerank["RERANK_URL"] = "http://fixture.invalid/rerank?key=synthetic-secret"
            with patch("fondontology.qa.config.embedding_config", return_value=embedding), patch(
                    "fondontology.qa.config.rerank_config", return_value=rerank):
                resources = build_resources()
            self.assertNotIn("synthetic-secret", json.dumps(
                [resources.embedding_config, resources.rerank_config]))
            invalid_configuration = (resources.embedding_config if invalid_resource == "embedding"
                                     else resources.rerank_config)
            self.assertIsNone(invalid_configuration["endpoint"])
            self.assertEqual(invalid_configuration["endpoint_validation_status"], "invalid")
            with patch("httpx.post", return_value=httpx.Response(200, json={
                    "data": [{"index": 0, "embedding": [1.0]}],
                    "output": {"results": [{"index": 0, "relevance_score": 0.8}]},
            })) as network:
                if invalid_resource == "embedding":
                    resources.rerank("query", ["document"])
                    with self.assertRaises(CorpusError):
                        resources.embed(["query"])
                else:
                    resources.embed(["query"])
                    with self.assertRaises(CorpusError):
                        resources.rerank("query", ["document"])
            self.assertEqual(network.call_count, 1)

    def test_http_200_bad_json_preserves_transport_success_with_validation_error(self):
        for response in (httpx.Response(200, text="synthetic-secret"), httpx.Response(200, json=[])):
            resources = self.resources()
            with patch("httpx.post", return_value=response):
                with self.assertRaises(CorpusError) as error:
                    resources.embed(["query"])
            self.assertNotIn("synthetic-secret", str(error.exception))
            event = resources.events[-1]
            self.assertEqual(event["status"], "ok")
            self.assertEqual(event["response_validation_status"], "error")
            self.assertNotIn("synthetic-secret", json.dumps(event))

    def test_cross_batch_dimension_error_is_attached_to_failed_response_validation(self):
        resources = self.resources()
        with patch("httpx.post", side_effect=[
            httpx.Response(200, json={"data": [
                {"index": index, "embedding": [1.0]} for index in range(25)]}),
            httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 1.0]}]}),
        ]):
            with self.assertRaises(CorpusError):
                resources.embed([f"item {index}" for index in range(26)])
        self.assertEqual([event["status"] for event in resources.events], ["ok", "ok"])
        self.assertEqual([event["response_validation_status"] for event in resources.events],
                         ["ok", "error"])


if __name__ == "__main__":
    unittest.main()
