"""The data catalog is an explicit local whitelist, not a discovery heuristic."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fondontology.corpus import CorpusRepository
from fondontology.corpus.data_catalog import _url_equivalent, artifact_output, build_catalog_records


CLI = Path(__file__).resolve().parents[1] / "tools" / "import_data_corpus.py"


class DataCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.raw = self.data / "law.html"
        self.raw.write_bytes(b"<html>synthetic official source fixture</html>")
        self.markdown = self.data / "law.md"
        self.markdown.write_text(
            "# Synthetic fixture law\n\n**Source**: https://issuer.example/law\n\n"
            "## 第一章 总则\n\n### 第一条 Scope.\n\n### 第二条 Exception.\n",
            encoding="utf-8",
        )
        self.document = {
            "id": "synthetic-catalog-law", "legacy_path": "law.md",
            "title": "Synthetic fixture law", "publisher": "Synthetic issuer",
            "seed_urls": ["https://issuer.example/law"], "source_page_url": "https://issuer.example/law",
            "download_url": "https://issuer.example/law", "format": "html", "issued_date": "2024-01-01",
            "effective_from": None, "expected_articles": 2, "origin_kind": "issuer_original",
            "raw_path": "law.html", "raw_sha256": self.checksum(self.raw),
            "markdown_path": "law.md", "markdown_sha256": self.checksum(self.markdown),
            "status": "ready", "verification": {
                "identity": "verified", "completeness": "complete",
                "evidence": ["Synthetic fixture review, not an actual authority claim"],
                "article_count": 2, "page_count": None,
            }, "failure_reason": None,
        }
        self.catalog = self.data / "source_catalog.json"
        self.write_catalog(self.document)

    @staticmethod
    def checksum(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write_catalog(self, *documents):
        for document in documents:
            self.bind_records(document)
        self.catalog.write_text(json.dumps({"schema_version": 1, "documents": documents}),
                                encoding="utf-8")

    def bind_records(self, document):
        verification = document.get("verification")
        if not isinstance(verification, dict):
            return
        receipt = self.data / (document["id"] + ".receipt.json")
        conversion = self.data / (document["id"] + ".conversion.json")
        receipt.write_text(json.dumps({
            "requested_url": document.get("download_url"), "final_url": document.get("download_url"),
            "raw_sha256": document.get("raw_sha256"), "bytes": self.raw.stat().st_size,
            "http_status": 200,
        }), encoding="utf-8")
        conversion.write_text(json.dumps({
            "schema_version": 1, "raw_path": document.get("raw_path"),
            "source_sha256": document.get("raw_sha256"), "markdown_path": document.get("markdown_path"),
            "markdown_sha256": document.get("markdown_sha256"), "method": "synthetic-fixture",
            "version": "1", "observations": {
                "original_format": document.get("format"), "page_count": verification.get("page_count"),
                "page_coverage": list(range(1, verification["page_count"] + 1))
                if verification.get("page_count") is not None else [],
                "article_count": verification.get("article_count"), "missing_images": [],
                "unsupported": [],
            }, "identity_review": {"scope": "machine_conversion_and_structure_only",
                                   "human_reviewed": False},
        }), encoding="utf-8")
        verification["acquisition"] = {"receipt_path": receipt.name,
                                       "receipt_sha256": self.checksum(receipt)}
        verification["conversion"] = {"record_path": conversion.name,
                                      "record_sha256": self.checksum(conversion)}

    def test_frozen_catalog_rejects_changes_even_for_subset_selection(self):
        lock = {"schema_version": 1, "catalog_path": "source_catalog.json",
                "catalog_sha256": self.checksum(self.catalog),
                "document_ids": [self.document["id"]], "document_count": 1}
        lock_path = self.data / "rag_source_lock.json"
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        self.assertEqual(len(self.build()["records"]), 1)
        self.catalog.write_bytes(self.catalog.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Frozen RAG source catalog hash mismatch"):
            self.build([self.document["id"]])

    def test_frozen_source_rejects_image_changes(self):
        image = self.data / "diagram.png"
        image.write_bytes(b"original diagram")
        lock = {"schema_version": 1, "catalog_path": "source_catalog.json",
                "catalog_sha256": self.checksum(self.catalog),
                "document_ids": [self.document["id"]], "document_count": 1,
                "image_sha256": {image.name: self.checksum(image)}}
        (self.data / "rag_source_lock.json").write_text(json.dumps(lock), encoding="utf-8")
        self.assertEqual(len(self.build()["records"]), 1)
        image.write_bytes(b"changed diagram")
        with self.assertRaisesRegex(ValueError, "Frozen RAG source image hash mismatch"):
            self.build()

    def build(self, document_ids=None):
        return build_catalog_records(self.catalog, data_root=self.data, document_ids=document_ids)

    def import_records(self, records):
        manifest = self.root / "artifacts" / "manifest.jsonl"
        manifest.parent.mkdir()
        manifest.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        repository = CorpusRepository(manifest.parent / "corpus.sqlite")
        imported = repository.import_manifest(manifest)
        repository.publish_snapshot("catalog-test", imported["version_ids"], kind="trusted")
        return repository

    def test_legal_body_headings_offsets_and_no_metadata_chunks(self):
        result = self.build()
        repository = self.import_records(result["records"])
        chunks = repository.get_chunks("catalog-test")
        self.assertEqual([chunk["locator"]["article_number"] for chunk in chunks], [1, 2])
        self.assertEqual(len(chunks), 2)
        self.assertNotIn("**Source**", "".join(chunk["text"] for chunk in chunks))
        self.assertNotIn("Synthetic fixture law", "".join(chunk["text"] for chunk in chunks))
        for chunk in chunks:
            locator = chunk["locator"]
            self.assertEqual(chunk["text"], self.markdown.read_bytes().decode("utf-8")[
                locator["char_start"]:locator["char_end"]])
        self.assertTrue(repository.verify_snapshot("catalog-test")["ok"])
        self.assertEqual(result["records"][0]["provenance"]["legal_validity"], "not_checked_current")

    def test_technical_body_uses_explicit_start_without_article_guess(self):
        self.markdown.write_text("# Protocol\n\n**Source**: https://issuer.example\n\n"
                                 "## 1 Scope\nFields and units.\n## 2 Records\nDetails.\n", encoding="utf-8")
        document = {**self.document, "expected_articles": None,
                    "markdown_sha256": self.checksum(self.markdown),
                    "verification": {**self.document["verification"], "article_count": None,
                                     "body_start_line": 5}}
        self.write_catalog(document)
        repository = self.import_records(self.build()["records"])
        chunks = repository.get_chunks("catalog-test")
        self.assertEqual(len(chunks), 2)
        self.assertEqual({chunk["locator"]["content_kind"] for chunk in chunks}, {"technical_body"})
        self.assertNotIn("**Source**", "".join(chunk["text"] for chunk in chunks))
        self.assertTrue(repository.verify_snapshot("catalog-test")["ok"])
        document["verification"].pop("body_start_line")
        self.write_catalog(document)
        with self.assertRaises(ValueError):
            self.build()
        document["title"] = "Protocol"
        document["verification"]["body_start_line"] = 1
        self.write_catalog(document)
        with self.assertRaisesRegex(ValueError, "header"):
            self.build()
        document["verification"]["body_start_line"] = 3
        self.write_catalog(document)
        with self.assertRaisesRegex(ValueError, "header"):
            self.build()

    def test_unresolved_source_may_leave_origin_unknown_without_claiming_authority(self):
        document = {**self.document, "origin_kind": None, "status": "unresolved",
                    "raw_path": None, "raw_sha256": None,
                    "markdown_path": None, "markdown_sha256": None}
        self.write_catalog(document)
        result = self.build()
        self.assertEqual(result["records"], [])
        self.assertEqual(result["skipped"][0]["status"], "unresolved")
        document["status"] = "downloaded"
        self.write_catalog(document)
        with self.assertRaisesRegex(ValueError, "origin_kind"):
            self.build()

    def test_receipt_urls_allow_encoded_unicode_without_changing_url_boundaries(self):
        encoded = "https://issuer.example/%E9%99%84%E4%BB%B6.pdf?name=%E4%B8%AD%E6%96%87"
        literal = "https://issuer.example/附件.pdf?name=中文"
        self.document["download_url"] = encoded
        self.write_catalog(self.document)
        reference = self.document["verification"]["acquisition"]
        path = self.data / reference["receipt_path"]
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt.update({"requested_url": literal, "actual_url": encoded, "final_url": literal})
        path.write_text(json.dumps(receipt), encoding="utf-8")
        reference["receipt_sha256"] = self.checksum(path)
        self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                encoding="utf-8")
        self.assertEqual(len(self.build()["records"]), 1)
        pairs = [
            ("https://issuer.example/a%2Fb", "https://issuer.example/a/b"),
            ("https://issuer.example/a%252Fb", "https://issuer.example/a%2Fb"),
            ("https://issuer.example/law?a=1%26b=2", "https://issuer.example/law?a=1&b=2"),
            ("https://issuer.example/law?a%3Db=1", "https://issuer.example/law?a=b=1"),
            ("https://issuer.example/law?a=one+two", "https://issuer.example/law?a=one%20two"),
            (encoded, literal.replace("issuer.example", "unrelated.example")),
            (encoded, literal.replace("https://", "http://")),
        ]
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                self.assertFalse(_url_equivalent(first, second))
        self.assertTrue(_url_equivalent("https://issuer.example/a%2fb", "https://issuer.example/a%2Fb"))
        self.assertTrue(_url_equivalent("https://issuer.example/%41", "https://issuer.example/A"))
        self.assertFalse(_url_equivalent("https://issuer.example/%FF", "https://issuer.example/�"))
        receipt["final_url"] = "https://unrelated.example/附件.pdf?name=中文"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        reference["receipt_sha256"] = self.checksum(path)
        self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bind"):
            self.build()

    def test_only_ready_whitelisted_documents_no_glob_or_network(self):
        unresolved = {**self.document, "id": "unresolved", "status": "unresolved",
                      "failure_reason": "Not acquired", "raw_path": None, "raw_sha256": None,
                      "markdown_path": None, "markdown_sha256": None}
        self.write_catalog(unresolved)
        with patch("pathlib.Path.rglob", side_effect=AssertionError("glob forbidden")), patch(
                "urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            result = self.build()
        self.assertEqual(result["records"], [])
        self.assertEqual(result["skipped"][0]["id"], "unresolved")
        with self.assertRaisesRegex(ValueError, "not ready"):
            self.build(["unresolved"])
        with self.assertRaisesRegex(ValueError, "Unknown catalog"):
            self.build(["absent"])
        self.catalog.unlink()
        with self.assertRaises(OSError):
            self.build()

    def test_incomplete_unverified_secondary_missing_raw_or_date_ready_fail(self):
        invalid = [
            {"origin_kind": "secondary"}, {"raw_path": None, "raw_sha256": None},
            {"issued_date": None},
            {"verification": {**self.document["verification"], "identity": "not_checked"}},
            {"verification": {**self.document["verification"], "completeness": "incomplete"}},
            {"verification": {**self.document["verification"], "evidence": []}},
            {"verification": {**self.document["verification"], "article_count": 1}},
        ]
        for mutation in invalid:
            with self.subTest(mutation=mutation):
                self.write_catalog({**self.document, **mutation})
                with self.assertRaises(ValueError):
                    self.build()

    def test_all_references_are_inside_data_with_matching_bytes_even_if_unselected(self):
        for field in ("legacy_path", "raw_path", "markdown_path"):
            for path in ("../outside.md", str(self.root / "outside.md")):
                with self.subTest(field=field, path=path):
                    self.write_catalog({**self.document, field: path, "status": "unresolved"})
                    with self.assertRaises(ValueError):
                        self.build()
        for field in ("raw_sha256", "markdown_sha256"):
            self.write_catalog({**self.document, field: "0" * 64})
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build()
        self.write_catalog(self.document, {**self.document, "id": "unselected-bad",
                                          "raw_sha256": "0" * 64})
        with self.assertRaises(ValueError):
            self.build([self.document["id"]])

    def test_legal_gaps_and_duplicate_keys_fail(self):
        self.markdown.write_text("第一条 One.\n第三条 Three.\n", encoding="utf-8")
        self.write_catalog({**self.document, "markdown_sha256": self.checksum(self.markdown)})
        with self.assertRaises(ValueError):
            self.build()
        self.catalog.write_text('{"schema_version":1,"documents":[],"overflow":1e999}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "number"):
            self.build()
        self.catalog.write_text('{"schema_version":1,"schema_version":1,"documents":[]}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.build()
        self.write_catalog(self.document, deepcopy(self.document))
        with self.assertRaises(ValueError):
            self.build()

    def test_derived_artifacts_never_written_under_data(self):
        allowed = self.root / "artifacts" / "corpus.sqlite"
        self.assertEqual(artifact_output(allowed, artifacts_root=self.root / "artifacts",
                                        data_root=self.data), allowed)
        for target in (self.data / "corpus.sqlite", self.root / "outside.sqlite"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                artifact_output(target, artifacts_root=self.root / "artifacts", data_root=self.data)

    def test_catalog_verify_detects_deleted_chunk(self):
        repository = self.import_records(self.build()["records"])
        with closing(sqlite3.connect(repository.db_path)) as connection:
            with connection:
                connection.execute("DROP TRIGGER immutable_chunks_delete")
                connection.execute("DELETE FROM chunks WHERE rowid=(SELECT MIN(rowid) FROM chunks)")
        result = repository.verify_snapshot("catalog-test")
        self.assertFalse(result["ok"])
        self.assertTrue(any("coverage" in error for error in result["errors"]))

    def test_cli_missing_catalog_and_empty_import_do_not_create_database(self):
        artifacts = self.root / "artifacts"
        database = artifacts / "corpus.sqlite"
        manifest = artifacts / "manifest.jsonl"
        self.write_catalog({**self.document, "status": "converted_unverified"})
        command = [sys.executable, str(CLI), "--catalog", str(self.catalog),
                   "--data-root", str(self.data), "--manifest-out", str(manifest),
                   "--db", str(database), "--import-ready", "--snapshot-id", "test"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertFalse(database.exists())
        self.assertFalse(manifest.exists())
        self.catalog.unlink()
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(database.exists())

    def test_cli_ready_import_and_offline_replay_preserve_data(self):
        artifacts = self.root / "artifacts"
        database = artifacts / "corpus.sqlite"
        manifest = artifacts / "manifest.jsonl"
        before = {path.name: path.read_bytes() for path in self.data.iterdir()}
        command = [sys.executable, str(CLI), "--catalog", str(self.catalog),
                   "--data-root", str(self.data), "--manifest-out", str(manifest),
                   "--db", str(database), "--import-ready", "--snapshot-id", "test"]
        first = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(first.returncode, 0, first.stderr)
        output = json.loads(first.stdout)
        self.assertEqual(output["ready"], 1)
        self.assertEqual(output["import"]["inserted"], 1)
        self.assertTrue(output["verification"]["ok"])
        replay = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout)["import"]["reused"], 1)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.data.iterdir()})

    def test_ready_requires_bound_receipt_and_conversion_records(self):
        mutations = [
            ("acquisition", "requested_url", "https://unrelated.example/file"),
            ("acquisition", "final_url", "https://unrelated.example/file"),
            ("acquisition", "raw_sha256", "0" * 64),
            ("acquisition", "bytes", 1),
            ("conversion", "source_sha256", "0" * 64),
            ("conversion", "markdown_sha256", "0" * 64),
            ("conversion", "markdown_path", "unrelated.md"),
            ("conversion", "raw_path", "unrelated.html"),
            ("conversion", "identity_review", {"scope": "human_verified", "human_reviewed": True}),
            ("conversion", "observations", {"original_format": "html"}),
        ]
        for reference_field, field, value in mutations:
            with self.subTest(reference=reference_field, field=field):
                self.write_catalog(self.document)
                reference = self.document["verification"][reference_field]
                path_field = "receipt_path" if reference_field == "acquisition" else "record_path"
                hash_field = "receipt_sha256" if reference_field == "acquisition" else "record_sha256"
                path = self.data / reference[path_field]
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload[field] = value
                path.write_text(json.dumps(payload), encoding="utf-8")
                reference[hash_field] = self.checksum(path)
                self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                        encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.build()
        for reference_field in ("acquisition", "conversion"):
            self.write_catalog(self.document)
            self.document["verification"].pop(reference_field)
            self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                    encoding="utf-8")
            with self.subTest(missing=reference_field), self.assertRaises(ValueError):
                self.build()

    def test_unselected_ready_entries_still_require_complete_ready_gate(self):
        invalid = {**self.document, "id": "unselected", "origin_kind": "secondary"}
        self.write_catalog(self.document, invalid)
        with self.assertRaisesRegex(ValueError, "verified official"):
            self.build([self.document["id"]])
        invalid = {**self.document, "id": "unselected", "verification": {
            **self.document["verification"], "completeness": "incomplete"}}
        self.write_catalog(self.document, invalid)
        with self.assertRaises(ValueError):
            self.build([self.document["id"]])

    def test_receipt_aliases_are_supported_but_conflicts_are_rejected(self):
        reference = self.document["verification"]["acquisition"]
        path = self.data / reference["receipt_path"]
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["actual_url"] = receipt.pop("requested_url")
        receipt["sha256"] = receipt.pop("raw_sha256")
        receipt["byte_count"] = receipt.pop("bytes")
        receipt["status_code"] = receipt.pop("http_status")
        path.write_text(json.dumps(receipt), encoding="utf-8")
        reference["receipt_sha256"] = self.checksum(path)
        self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                encoding="utf-8")
        self.assertEqual(len(self.build()["records"]), 1)
        receipt["bytes"] = 999
        path.write_text(json.dumps(receipt), encoding="utf-8")
        reference["receipt_sha256"] = self.checksum(path)
        self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "consistent"):
            self.build()

    def test_conversion_missing_pages_images_and_unsupported_content_fail_ready(self):
        self.document["verification"]["page_count"] = 3
        mutations = [
            {"page_coverage": [1, 2]}, {"page_coverage": [1, 1, 3]},
            {"page_count": 2}, {"missing_images": ["figure-1.png"]},
            {"unsupported": ["embedded table object"]}, {"article_count": True},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.write_catalog(self.document)
                reference = self.document["verification"]["conversion"]
                path = self.data / reference["record_path"]
                record = json.loads(path.read_text(encoding="utf-8"))
                record["observations"].update(mutation)
                path.write_text(json.dumps(record), encoding="utf-8")
                reference["record_sha256"] = self.checksum(path)
                self.catalog.write_text(json.dumps({"schema_version": 1, "documents": [self.document]}),
                                        encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.build()
        self.write_catalog(self.document)
        reference = self.document["verification"]["conversion"]
        path = self.data / reference["record_path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "sha256"):
            self.build()

    def test_appendix_body_is_preserved_as_non_article_chunks(self):
        self.markdown.write_text(
            "第一条 Main one.\n第二条 Main two.\n附件：\n第一章 Procedure\nImportant appendix body.\n",
            encoding="utf-8",
        )
        self.document["markdown_sha256"] = self.checksum(self.markdown)
        self.write_catalog(self.document)
        repository = self.import_records(self.build()["records"])
        chunks = repository.get_chunks("catalog-test")
        self.assertEqual(sum("article_number" in chunk["locator"] for chunk in chunks), 2)
        supplements = [chunk for chunk in chunks
                       if chunk["locator"]["content_kind"] == "supplementary_body"]
        self.assertEqual(len(supplements), 1)
        self.assertIn("Important appendix body.", supplements[0]["text"])
        self.assertNotIn("article_number", supplements[0]["locator"])
        self.assertTrue(repository.verify_snapshot("catalog-test")["ok"])


if __name__ == "__main__":
    unittest.main()
