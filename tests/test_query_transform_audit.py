from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.evaluation.artifact_audit import ArtifactAuditError, audit_artifact
from fondontology.qa.rag.document_pipeline import answer_document
from fondontology.qa.rag.document_providers import build_query_transform_resource
from fondontology.qa.rag.document_retrieval import RetrievalResources
from fondontology.qa.rag.query_transforms import QueryTransformResource
from tools.document_rag import main


FIXTURES = Path(__file__).parent / "fixtures" / "document_rag"


class QueryProviderTest(unittest.TestCase):
    def resource(self):
        with patch("fondontology.qa.config.llm_config", return_value={
                "OPENAI_MODEL": "synthetic-model", "OPENAI_BASE_URL": "https://fixture.invalid/v1",
                "OPENAI_API_KEY": "synthetic-secret"}):
            return build_query_transform_resource()

    def response(self, content='{"text":"retrieval query"}', finish_reason="stop"):
        return httpx.Response(200, json={"choices": [{"finish_reason": finish_reason,
                                                    "message": {"content": content}}]})

    def test_provider_is_lazy_bounded_and_does_not_log_secrets(self):
        with patch("httpx.post", side_effect=AssertionError("unexpected network")):
            resource = self.resource()
        with patch("httpx.post", return_value=self.response()) as network, patch(
                "fondontology.qa.config.llm_thinking_override", return_value={}):
            self.assertEqual(resource.transform("original question", "rewrite"), "retrieval query")
        self.assertEqual(network.call_count, 1)
        request = network.call_args.kwargs
        self.assertEqual(request["json"]["messages"][1]["content"], "original question")
        self.assertEqual(request["json"]["max_tokens"], 1536)
        self.assertEqual(request["timeout"].read, 30)
        self.assertFalse(request["follow_redirects"])
        self.assertNotIn("synthetic-secret", json.dumps(resource.events))
        self.assertEqual(resource.events[-1]["response_validation_status"], "ok")

    def test_malformed_partial_and_oversized_responses_are_rejected(self):
        responses = [self.response("not json"), self.response('{"text":"partial"}', "length"),
                     self.response(json.dumps({"text": "x" * 4001})), self.response('{"text":null}'),
                     self.response('{"text":"query","document_id":"invented"}'),
                     httpx.Response(200, json={"choices": [None]})]
        for response in responses:
            resource = self.resource()
            with self.subTest(response=response.text[:80]), patch("httpx.post", return_value=response), patch(
                    "fondontology.qa.config.llm_thinking_override", return_value={}):
                with self.assertRaises(CorpusError):
                    resource.transform("question", "hyde")
            self.assertEqual(resource.events[-1]["response_validation_status"], "error")

    def test_http_errors_are_redacted_and_not_retried(self):
        resource = self.resource()
        with patch("httpx.post", return_value=httpx.Response(429, text="synthetic-secret")) as network, patch(
                "fondontology.qa.config.llm_thinking_override", return_value={}):
            with self.assertRaises(CorpusError) as error:
                resource.transform("question", "rewrite")
        self.assertEqual(network.call_count, 1)
        self.assertNotIn("synthetic-secret", str(error.exception))
        self.assertNotIn("synthetic-secret", json.dumps(resource.events))


class QueryTransformAuditTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "corpus.sqlite"
        repository = CorpusRepository(self.database)
        versions = []
        for identifier, filename in (("alpha", "source.md"), ("beta", "other.md")):
            source = FIXTURES / filename
            manifest = self.root / f"{identifier}.jsonl"
            manifest.write_text(json.dumps({
                "doc_id": identifier, "title": f"Synthetic {identifier} document",
                "doc_type": "regulation_article", "path": str(source.resolve()),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_uri": f"urn:synthetic:{identifier}", "authority": "synthetic",
                "status": "verified", "issued_date": "2026-01-01",
                "provenance": {"fixture": "synthetic; not legal evidence"}, "locator": {"page": 1},
            }), encoding="utf-8")
            versions.extend(repository.import_manifest(manifest)["version_ids"])
        repository.publish_snapshot("fixture", versions, kind="regression")

    def resource(self, output="ALPHA_ONLY", requires_network=False):
        return QueryTransformResource(Mock(return_value=output), "synthetic", "fixture", requires_network)

    def run_cli(self, mode="rewrite", strategy="bm25", resource=None, expected_exit=0, **extra):
        output = self.root / "actual.json"
        resource = resource or self.resource()
        models = RetrievalResources(embed=lambda texts: [[1, 0] for text in texts],
                                    embedding_config={"provider": "synthetic", "model": "fixture"},
                                    embed_requires_network=False)
        arguments = ["--db", str(self.database), "--snapshot", "fixture", "--as-of", "2026-10-14",
                     "--allow-nontrusted", "--question", "allocation", "--query-transform", mode,
                     "--retrieval-strategy", strategy, "--output", str(output)]
        arguments.extend(extra.get("arguments", []))
        with patch("fondontology.qa.rag.document_providers.build_query_transform_resource",
                   return_value=resource), patch("tools.document_rag._provider_resources", return_value=models), \
                patch("httpx.post", side_effect=AssertionError("No live network in tests")), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), expected_exit)
        return output, output.with_suffix(".traces.jsonl")

    def test_cli_rewrite_and_hyde_are_accepted_by_independent_artifact_audit(self):
        for mode, strategy in (("rewrite", "bm25"), ("rewrite", "parent_child"), ("hyde", "hybrid_rrf")):
            with self.subTest(mode=mode, strategy=strategy):
                output, trace_path = self.run_cli(mode, strategy)
                audit = audit_artifact(output, self.database)
                self.assertTrue(audit["verified"])
                self.assertEqual(audit["row_count"], 1)
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                self.assertEqual(set(trace["scope"]["selected_doc_ids"]), {"alpha", "beta"})
                self.assertEqual(trace["user_input"], "allocation")

    def test_error_trace_is_auditable_and_has_no_silent_baseline_results(self):
        resource = self.resource(requires_network=True)
        output, trace_path = self.run_cli(resource=resource, expected_exit=1)
        resource.transform.assert_not_called()
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(trace["status"], "error")
        self.assertEqual(trace["evidence"], [])
        self.assertEqual(trace["strategy_trace"]["channels"], {})
        self.assertTrue(audit_artifact(output, self.database)["verified"])

    def test_hash_mode_input_and_missing_trace_tampering_are_rejected(self):
        def tamper(trace, kind):
            if kind == "missing":
                del trace["strategy_trace"]
                return
            transformed = trace["strategy_trace"]["query_transform"]
            if kind == "hash":
                transformed["output_sha256"] = "a" * 64
            elif kind == "mode":
                transformed["mode"] = "identity"
            elif kind == "input":
                transformed["input"] = "different question"
            elif kind == "network":
                transformed["network"] = True
        for kind in ("hash", "mode", "input", "missing", "network"):
            with self.subTest(kind=kind):
                output, trace_path = self.run_cli()
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                tamper(trace, kind)
                raw_trace = (json.dumps(trace) + "\n").encode("utf-8")
                trace_path.write_bytes(raw_trace)
                envelope = json.loads(output.read_text(encoding="utf-8"))
                envelope["provenance"]["trace_sha256"] = hashlib.sha256(raw_trace).hexdigest()
                output.write_text(json.dumps(envelope), encoding="utf-8")
                with self.assertRaises(ArtifactAuditError):
                    audit_artifact(output, self.database)

    def test_generation_keeps_original_question_and_only_retrieved_source_text(self):
        with patch("fondontology.qa.rag.document_pipeline._generate", return_value=(
                "grounded [R1]", {"provider": "synthetic", "model": "fixture", "used_llm": True,
                                  "prompt_version": "fixture"})) as generate:
            result = answer_document(
                "original user inquiry", db_path=self.database, snapshot_id="fixture", as_of="2026-10-14",
                allow_nontrusted=True, generate=True, top_k=1, query_transform="rewrite",
                query_transform_resource=self.resource())
        self.assertEqual(generate.call_args.args[0], "original user inquiry")
        self.assertEqual(generate.call_args.args[1], result["evidence"])
        self.assertEqual({item["doc_id"] for item in result["evidence"]}, {"alpha"})
        self.assertNotIn("query_transform", generate.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
