from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.qa.rag.document_pipeline import _generate, answer_document
from tools.document_rag import load_cases, main


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "document_rag"


class DocumentRagTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.db = self.root / "corpus.sqlite"
        self.repository = CorpusRepository(self.db)
        versions = []
        for name, entity in (("source.md", "alpha"), ("other.md", "beta")):
            source = FIXTURE / name
            record = {
                "doc_id": entity, "title": entity, "doc_type": "regulation_article",
                "path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_uri": f"urn:synthetic:{entity}", "authority": "synthetic",
                "status": "verified", "issued_date": "2026-01-01",
                "provenance": {"fixture": "synthetic; not legal or financial evidence"},
                "locator": {"page": 1},
                "entity_links": [{
                    "entity_id": f"urn:fixture:{entity}", "method": "manual",
                    "confidence": 1.0, "review_status": "reviewed",
                }],
            }
            manifest = self.root / f"{entity}.jsonl"
            manifest.write_text(json.dumps(record), encoding="utf-8")
            versions.extend(self.repository.import_manifest(manifest)["version_ids"])
        self.repository.publish_snapshot("both", versions, kind="regression")
        self.repository.publish_snapshot("beta", [versions[1]], kind="regression")

    def answer(self, question="ALPHA_ONLY", **kwargs):
        return answer_document(
            question, db_path=self.db, snapshot_id=kwargs.pop("snapshot_id", "both"),
            as_of=kwargs.pop("as_of", "2026-10-11"), allow_nontrusted=True, **kwargs)

    def test_extracts_full_actual_context_and_original_locator_without_network(self):
        with patch("fondontology.qa.rag.retrieve._vector_index_if_ready",
                   side_effect=AssertionError("No vector/network access")), patch(
                "fondontology.qa.rag.retrieve._rerank_call",
                side_effect=AssertionError("No rerank/network access")), patch(
                "fondontology.qa.rag.document_pipeline._generate",
                side_effect=AssertionError("Generation must be explicit")):
            result = self.answer(entity_iri="urn:fixture:alpha")
        self.assertEqual(result["answer_mode"], "extractive")
        self.assertEqual(result["status"], "retrieved")
        self.assertFalse(result["config"]["llm"]["used_llm"])
        self.assertEqual(result["generation_latency_ms"], 0.0)
        self.assertEqual(result["retrieved_contexts"], [item["text"] for item in result["evidence"]])
        for item in result["evidence"]:
            self.assertIn(item["text"], result["response"])
            self.assertEqual(item["locator"]["page"], 1)
            self.assertEqual(len(item["sha256"]), 64)
            self.assertEqual(item["version_id"], item["locator"]["version_id"])
        self.assertTrue(result["warnings"])

    def test_unmatched_scope_query_date_and_snapshot_never_fall_back(self):
        for kwargs in (
                {"entity_iri": "urn:missing"}, {"question": "ZZZ_UNMATCHED"},
                {"as_of": "2025-12-31"}):
            with self.subTest(kwargs=kwargs):
                result = self.answer(**kwargs)
                self.assertEqual(result["status"], "unresolved")
                self.assertEqual(result["retrieved_contexts"], [])
                self.assertIn("UNRESOLVED", result["response"])
        result = self.answer(question="ALPHA_ONLY", snapshot_id="beta",
                             entity_iri="urn:fixture:alpha")
        self.assertEqual(result["status"], "unresolved")
        with self.assertRaises(CorpusError):
            self.answer(entity_iri="")
        with self.assertRaises(CorpusError):
            self.answer(as_of="invalid")

    def test_cli_exports_strict_ragas_envelope_and_separate_hashed_trace_without_gold(self):
        output = self.root / "actual.json"
        cases = load_cases(FIXTURE / "cases.json")
        with redirect_stdout(io.StringIO()), patch(
                "tools.document_rag.answer_document", wraps=answer_document) as call:
            code = main([
                "--db", str(self.db), "--snapshot", "both", "--as-of", "2026-10-11",
                "--cases", str(FIXTURE / "cases.json"), "--allow-nontrusted",
                "--output", str(output),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(set(call.call_args.kwargs), {
            "db_path", "snapshot_id", "as_of", "top_k", "entity_iri",
            "allow_nontrusted", "include_undated_research", "generate", "store",
            "doc_ids", "version_ids"})
        payload = json.loads(output.read_text(encoding="utf-8"))
        row = payload["rows"][0]
        self.assertEqual(set(row), {"id", "user_input", "response", "retrieved_contexts"})
        self.assertEqual(row["id"], cases[0]["id"])
        self.assertNotIn(cases[0]["reference"], json.dumps(payload))
        provenance = payload["provenance"]
        self.assertEqual(provenance["execution_origin"], "rag_pipeline")
        trace_bytes = Path(provenance["trace_path"]).read_bytes()
        self.assertEqual(hashlib.sha256(trace_bytes).hexdigest(), provenance["trace_sha256"])
        trace = json.loads(trace_bytes.decode("utf-8"))
        self.assertTrue(trace["evidence"])
        self.assertGreaterEqual(trace["retrieval_latency_ms"], 0)
        self.assertNotIn(cases[0]["reference"], trace_bytes.decode("utf-8"))

    def test_json_and_jsonl_exports_match_ragas_input_contract(self):
        from fondontology.evaluation.ragas_runner import load_input
        for suffix in ("json", "jsonl"):
            output = self.root / f"actual.{suffix}"
            with redirect_stdout(io.StringIO()):
                code = main([
                    "--db", str(self.db), "--snapshot", "both", "--as-of", "2026-10-11",
                    "--question", "ALPHA_ONLY", "--allow-nontrusted",
                    "--output", str(output)])
            self.assertEqual(code, 0)
            provenance, rows = load_input(output)
            self.assertEqual(provenance["execution_origin"], "rag_pipeline")
            self.assertEqual(rows[0]["user_input"], "ALPHA_ONLY")
            self.assertTrue(rows[0]["retrieved_contexts"])

    def test_case_schema_rejects_unknown_fields_and_duplicate_ids(self):
        for cases in (
                [{"id": "one", "question": "alpha", "surprise": "ignored?"}],
                [{"id": "one", "question": "alpha"}, {"id": "one", "question": "beta"}]):
            path = self.root / "invalid.json"
            path.write_text(json.dumps({"schema_version": "1.0", "cases": cases}), encoding="utf-8")
            with self.assertRaises(CorpusError):
                load_cases(path)
        for raw in (
                '{"schema_version":"1.0","cases":[],"cases":[]}',
                '{"schema_version":"1.0","cases":[{"id":"x","question":"alpha","reference":NaN}]}',
                '{"schema_version":"1.0","cases":[{"id":"x","question":"alpha","reference":3}]}',
                '{"schema_version":"1.0","cases":[{"id":"x","question":"alpha","review_status":[]}]}'):
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(CorpusError):
                load_cases(path)

    def test_case_errors_retain_denominator_and_dates_and_reuse_index(self):
        cases_path = self.root / "cases.json"
        cases_path.write_text(json.dumps({"schema_version": "1.0", "cases": [
            {"id": "first", "question": "alpha"},
            {"id": "failed", "question": "alpha", "as_of": "invalid"},
            {"id": "last", "question": "beta"},
        ]}), encoding="utf-8")
        output = self.root / "actual.json"
        with patch("tools.document_rag.load_corpus_store", wraps=__import__(
                "fondontology.qa.rag.store", fromlist=["load_corpus_store"]
        ).load_corpus_store) as load, redirect_stdout(io.StringIO()):
            code = main([
                "--db", str(self.db), "--snapshot", "both", "--as-of", "2026-10-11",
                "--cases", str(cases_path), "--allow-nontrusted", "--output", str(output)])
        self.assertEqual(code, 1)
        self.assertEqual(load.call_count, 2)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual([row["id"] for row in payload["rows"]], ["first", "failed", "last"])
        self.assertEqual(payload["rows"][1]["retrieved_contexts"], [])
        self.assertEqual(payload["provenance"]["retrieval_config"]["per_case_dates"]["failed"], "invalid")
        self.assertIn("dependencies", payload["provenance"]["retrieval_config"]["code_identity"])
        traces = [json.loads(line) for line in Path(
            payload["provenance"]["trace_path"]).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(traces[1]["status"], "error")

    def test_cli_explicit_ids_and_empty_case_scope_are_not_widened(self):
        for options, expected in (
                (["--doc-id", "alpha"], ["alpha"]),
                (["--version-id", self.repository.get_snapshot("beta")["version_ids"][0]], ["beta"])):
            output = self.root / "explicit.json"
            with redirect_stdout(io.StringIO()):
                code = main([
                    "--db", str(self.db), "--snapshot", "both", "--as-of", "2026-10-11",
                    "--question", "allocation", "--allow-nontrusted",
                    "--output", str(output), *options])
            self.assertEqual(code, 0)
            traces = json.loads(output.with_suffix(".traces.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(traces["scope"]["selected_doc_ids"], expected)
            self.assertEqual({item["doc_id"] for item in traces["evidence"]}, set(expected))
        cases = self.root / "empty-cases.json"
        cases.write_text(json.dumps({"schema_version": "1.0", "cases": [
            {"id": "empty", "question": "allocation", "doc_ids": []},
        ]}), encoding="utf-8")
        output = self.root / "empty.json"
        with redirect_stdout(io.StringIO()):
            code = main([
                "--db", str(self.db), "--snapshot", "both", "--as-of", "2026-10-11",
                "--cases", str(cases), "--allow-nontrusted", "--output", str(output)])
        self.assertEqual(code, 0)
        trace = json.loads(output.with_suffix(".traces.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(trace["unresolved_reason"], "empty_doc_id_scope")
        self.assertEqual(trace["retrieved_contexts"], [])
        self.assertEqual(trace["config"]["doc_ids"], [])
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))[
            "provenance"]["retrieval_config"]["case_scopes"][0]["doc_ids"], [])

    def test_real_snapshot_titles_versions_and_effective_withdrawn_boundaries(self):
        manifest = self.root / "version-scope.jsonl"
        versions = []
        for doc_id, issued, effective, withdrawn, supersedes in (
                ("same-doc", "2025-01-01", "2025-02-01", "2026-01-01", None),
                ("same-doc", "2026-01-01", "2026-01-01", None, "previous"),
                ("same-title-other-doc", "2026-01-01", "2026-01-01", None, None)):
            source = self.root / f"title-{len(versions)}.md"
            source.write_text("allocation ceiling test evidence", encoding="utf-8")
            record = {
                "doc_id": doc_id, "title": "Identical Act", "doc_type": "regulation_article",
                "path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_uri": "urn:synthetic:version-scope", "authority": "synthetic",
                "status": "verified", "issued_date": issued, "effective_from": effective,
                "withdrawn_date": withdrawn, "provenance": {"fixture": "synthetic"},
                "locator": {"title": "Identical Act"},
            }
            if supersedes:
                record["supersedes"] = versions[-1]
            manifest.write_text(json.dumps(record), encoding="utf-8")
            versions.extend(self.repository.import_manifest(manifest)["version_ids"])
        self.repository.publish_snapshot("old", [versions[0]], kind="regression")
        self.repository.publish_snapshot("same-title", versions[1:], kind="regression")
        result = self.answer("《Identical Act》allocation", snapshot_id="old", as_of="2025-01-31")
        self.assertEqual(result["unresolved_reason"], "no_documents_available_at_as_of")
        result = self.answer("《Identical Act》allocation", snapshot_id="old", as_of="2025-02-01")
        self.assertEqual({item["version_id"] for item in result["evidence"]}, {versions[0]})
        result = self.answer("《Identical Act》allocation", snapshot_id="old", as_of="2026-01-01")
        self.assertEqual(result["unresolved_reason"], "no_documents_available_at_as_of")
        result = self.answer("《Identical Act》allocation", snapshot_id="same-title")
        self.assertEqual(result["unresolved_reason"], "ambiguous_document_title")
        result = self.answer("《Identical Act》allocation", snapshot_id="same-title",
                             version_ids=[versions[1]])
        self.assertEqual({item["version_id"] for item in result["evidence"]}, {versions[1]})
        result = self.answer("allocation", snapshot_id="same-title", version_ids=[versions[0]])
        self.assertEqual(result["unresolved_reason"], "unknown_version_id")

    def test_explicit_generation_and_citation_failure_are_disclosed(self):
        with patch("fondontology.qa.rag.document_pipeline._generate", return_value=(
                "Grounded generation [R1]", {"provider": "test", "model": "test",
                                             "prompt_version": "test", "used_llm": True})):
            result = self.answer(generate=True)
        self.assertEqual(result["answer_mode"], "generated")
        self.assertEqual(result["status"], "answered")
        with patch("fondontology.qa.rag.document_pipeline._generate", return_value=(
                None, {"provider": "test", "model": "test", "prompt_version": "test",
                       "used_llm": True, "validation": "invalid_citations"})):
            result = self.answer(generate=True)
        self.assertEqual(result["answer_mode"], "extractive")
        self.assertIn("Generation failed validation", " ".join(result["warnings"]))

    def test_generation_prompt_uses_full_context_and_no_reference(self):
        evidence = self.answer(entity_iri="urn:fixture:alpha")["evidence"]
        with patch("fondontology.qa.config.llm_configured", return_value=True), patch(
                "fondontology.qa.config.llm_config", return_value={"OPENAI_MODEL": "test"}), patch(
                "fondontology.qa.intent._stream_chat_content", return_value=json.dumps({
                    "sentences": [{"text": "Seventeen percent", "evidence_ids": ["R1"]}]
                })) as chat:
            response, metadata = _generate("allocation ceiling", evidence)
        prompt = chat.call_args.args[0]
        for item in evidence:
            self.assertIn(item["text"], json.loads(prompt.split("\n", 1)[1])["contexts"][0]["text"])
        self.assertNotIn("GOLD_MUST", prompt)
        self.assertIn("[R1]", response)
        self.assertEqual(metadata["validation"], "citation_ids_only")


if __name__ == "__main__":
    unittest.main()
