"""Offline PDF originals, extraction artifacts and page locator contracts."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.corpus.pdf_extraction import (
    PDFExtractionError, build_extraction, parse_extraction,
    load_extraction_json,
)


class CorpusPDFTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pdf = self.root / "textbook.pdf"
        writer = PdfWriter()
        for page_index in range(2):
            writer.add_blank_page(width=100, height=100)
        output = io.BytesIO()
        writer.write(output)
        self.pdf.write_bytes(output.getvalue())
        self.repository = CorpusRepository(self.root / "corpus.sqlite")
        self.artifact = {
            "schema_version": 1, "source_sha256": self.sha(self.pdf.read_bytes()), "page_count": 2,
            "extractor": {"name": "mineru", "version": "mineru-content-list-v1",
                          "model_version": "offline-fixture"},
            "markdown": "# Synthetic textbook\n\nFirst page.\n\nSecond page.",
            "content_list": [
                {"type": "text", "text": "First page " * 8, "page_idx": 0,
                 "bbox": [0, 0, 1000, 1000], "text_level": 1},
                {"type": "table", "table_body": "<table><tr><td>value</td></tr></table>",
                 "table_caption": ["Table A"], "table_footnote": ["Note A"], "page_idx": 1,
                 "bbox": [1, 1, 999, 999]},
                {"type": "list", "list_items": ["Second item", "Third item"], "page_idx": 1},
                {"type": "image", "img_path": "images/figure.png", "page_idx": 1},
            ],
        }
        self.record = {
            "doc_id": "fixture:pdf-textbook", "title": "Synthetic PDF textbook",
            "doc_type": "textbook", "source_uri": "urn:fixture:pdf-textbook",
            "path": self.pdf.name, "sha256": self.artifact["source_sha256"],
            "issued_date": None, "effective_from": None, "authority": "research_note",
            "status": "verified", "provenance": {"verification": "user_verified_source"},
            "locator": {"format": "pdf"}, "chunker_config": {"max_chars": 30, "overlap": 4},
        }

    @staticmethod
    def sha(source):
        return hashlib.sha256(source).hexdigest()

    def prepare(self, artifact=None, record=None):
        extraction = self.root / "extraction.json"
        extraction.write_text(json.dumps(artifact or self.artifact), encoding="utf-8")
        entry = {**(record or self.record), "extraction": {
            "path": extraction.name, "sha256": self.sha(extraction.read_bytes())}}
        manifest = self.root / "manifest.jsonl"
        manifest.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        return manifest, entry, extraction

    def publish(self):
        manifest, entry, artifact_path = self.prepare()
        version_id = self.repository.import_manifest(manifest)["version_ids"][0]
        self.repository.publish_snapshot("pdf-research", [version_id], kind="research")
        return version_id, entry, artifact_path

    def test_original_extraction_pages_table_restart_and_verification(self):
        version_id, entry, artifact_path = self.publish()
        original = self.pdf.read_bytes()
        artifact_bytes = artifact_path.read_bytes()
        self.pdf.unlink()
        artifact_path.unlink()
        reopened = CorpusRepository.open_existing(self.repository.db_path)
        self.assertEqual(reopened.get_original(version_id), original)
        self.assertEqual(reopened.get_extraction(version_id), artifact_bytes)
        parsed = parse_extraction(self.artifact, source_sha256=entry["sha256"], page_count=2)
        chunks = reopened.get_chunks("pdf-research")
        self.assertEqual({chunk["locator"]["page"] for chunk in chunks}, {1, 2})
        for chunk in chunks:
            locator = chunk["locator"]
            self.assertEqual(chunk["text"], parsed["text"][locator["char_start"]:locator["char_end"]])
            self.assertEqual(locator["pdf_sha256"], entry["sha256"])
            self.assertEqual(locator["extraction_sha256"], entry["extraction"]["sha256"])
            self.assertEqual(chunk["extraction_quality"], "unreviewed")
            self.assertEqual(chunk["status"], "verified")
            self.assertEqual(chunk["authority"], "research_note")
        table_text = "".join(chunk["text"] for chunk in chunks
                             if chunk["locator"]["block_type"] == "table")
        self.assertIn("<table>", table_text)
        self.assertEqual({chunk["locator"]["page_scope"] for chunk in chunks
                          if chunk["locator"]["block_type"] == "table"},
                         {"mineru_reported_start_page_unreviewed"})
        self.assertTrue(reopened.verify_snapshot("pdf-research")["ok"])
        with self.assertRaises(CorpusError):
            reopened.publish_snapshot("not-regulation", [version_id], kind="trusted")

    def test_invalid_nested_structure_source_page_bbox_and_empty_text(self):
        variants = []
        for mutation in (
            {"unknown": True}, {"source_sha256": "0" * 64}, {"page_count": 3},
            {"content_list": [[self.artifact["content_list"][0]]]},
            {"extractor": {**self.artifact["extractor"], "surprise": True}},
        ):
            variants.append({**copy.deepcopy(self.artifact), **mutation})
        for mutation in (
            {"page_idx": -1}, {"page_idx": 2}, {"page_idx": True}, {"bbox": [0, 0, 1001, 1]},
            {"bbox": [5, 0, 1, 10]}, {"bbox": [0, 0, float("nan"), 1]},
            {"text": None}, {"unknown": 1}, {"text_level": "1"}, {"text": {"text": "nested"}},
        ):
            artifact = copy.deepcopy(self.artifact)
            artifact["content_list"][0].update(mutation)
            variants.append(artifact)
        missing_page = copy.deepcopy(self.artifact)
        del missing_page["content_list"][0]["page_idx"]
        variants.append(missing_page)
        invalid_table = copy.deepcopy(self.artifact)
        invalid_table["content_list"][1]["table_caption"] = [{"text": "unexpected"}]
        variants.append(invalid_table)
        for artifact in variants:
            with self.subTest(artifact=artifact), self.assertRaises(CorpusError):
                self.repository.import_manifest(self.prepare(artifact)[0])
        self.assertEqual(self.repository.list_versions(), [])

    def test_missing_artifact_mismatched_hash_and_unknown_reference_field(self):
        manifest, record, artifact_path = self.prepare()
        for mutation in (
            {"path": "missing.json"}, {"sha256": "0" * 64}, {"unknown": "reject"},
        ):
            invalid = {**record, "extraction": {**record["extraction"], **mutation}}
            manifest.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(CorpusError):
                self.repository.import_manifest(manifest)
        altered_source = bytearray(self.pdf.read_bytes())
        altered_source.extend(b"\n")
        self.pdf.write_bytes(altered_source)
        stale = {**self.record, "sha256": self.sha(self.pdf.read_bytes())}
        with self.assertRaisesRegex(CorpusError, "source_sha256"):
            self.repository.import_manifest(self.prepare(record=stale)[0])

    def test_artifact_identity_idempotence_and_immutability(self):
        manifest, entry, artifact_path = self.prepare()
        first = self.repository.import_manifest(manifest)["version_ids"][0]
        self.assertEqual(self.repository.import_manifest(manifest)["version_ids"], [first])
        changed = copy.deepcopy(self.artifact)
        changed["extractor"]["model_version"] = "another-model"
        second = self.repository.import_manifest(self.prepare(changed)[0])["version_ids"][0]
        self.assertNotEqual(first, second)
        connection = sqlite3.connect(self.repository.db_path)
        try:
            for statement in ("UPDATE document_extractions SET normalized_text='bad'",
                              "DELETE FROM document_extractions"):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(statement)
        finally:
            connection.close()

    def test_ingestion_run_records_pdf_text_mixed_and_failed_extractors(self):
        manifest, pdf_record, artifact_path = self.prepare()
        pdf_run = self.repository.import_manifest(manifest)
        reused_pdf_run = self.repository.import_manifest(manifest)
        text_path = self.root / "plain.txt"
        text_path.write_text("Offline text fixture.", encoding="utf-8")
        text_record = {**self.record, "doc_id": "fixture:plain", "path": text_path.name,
                       "sha256": self.sha(text_path.read_bytes())}
        manifest.write_text(json.dumps(text_record), encoding="utf-8")
        text_run = self.repository.import_manifest(manifest)
        manifest.write_text("\n".join(json.dumps(record) for record in (pdf_record, text_record)),
                            encoding="utf-8")
        mixed_run = self.repository.import_manifest(manifest)
        new_pdf = {**pdf_record, "doc_id": "fixture:rollback-pdf"}
        invalid_text = {**text_record, "doc_id": "fixture:invalid", "sha256": "0" * 64}
        manifest.write_text("\n".join(json.dumps(record) for record in (new_pdf, invalid_text)),
                            encoding="utf-8")
        with self.assertRaisesRegex(CorpusError, "line 2"):
            self.repository.import_manifest(manifest)
        connection = sqlite3.connect(self.repository.db_path)
        try:
            for run_id, expected in (
                (pdf_run["run_id"], "mineru-content-list-v1"),
                (reused_pdf_run["run_id"], "mineru-content-list-v1"),
                (text_run["run_id"], "utf8-markdown-v1"), (mixed_run["run_id"], "mixed"),
            ):
                actual = connection.execute(
                    "SELECT extractor_version FROM ingestion_runs WHERE run_id=?", (run_id,)
                ).fetchone()[0]
                self.assertEqual(actual, expected)
            failure = connection.execute(
                "SELECT extractor_version, status, inserted_count, reused_count "
                "FROM ingestion_runs ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(failure, ("unknown", "failed", 0, 0))
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 2)
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM document_extractions").fetchone()[0], 1)
            self.assertFalse(connection.execute(
                "SELECT 1 FROM documents WHERE document_id='fixture:rollback-pdf'").fetchone())
        finally:
            connection.close()

    def test_replaced_pdf_requires_a_new_matching_extraction_and_version(self):
        first = self.repository.import_manifest(self.prepare()[0])["version_ids"][0]
        self.pdf.write_bytes(self.pdf.read_bytes() + b"\n")
        changed = copy.deepcopy(self.artifact)
        changed["source_sha256"] = self.sha(self.pdf.read_bytes())
        record = {**self.record, "sha256": changed["source_sha256"], "supersedes": first}
        second = self.repository.import_manifest(
            self.prepare(changed, record)[0])["version_ids"][0]
        self.assertNotEqual(first, second)
        self.assertNotEqual(self.repository.get_original(first), self.repository.get_original(second))

    def test_integrity_detects_missing_chunks_and_invalid_locator_json(self):
        self.publish()
        connection = sqlite3.connect(self.repository.db_path)
        try:
            connection.execute("DROP TRIGGER immutable_chunks_update")
            connection.execute("UPDATE chunks SET locator_json='not-json' WHERE rowid=("
                               "SELECT MIN(rowid) FROM chunks)")
            connection.commit()
            self.assertFalse(self.repository.verify_snapshot("pdf-research")["ok"])
            connection.execute("DROP TRIGGER immutable_chunks_delete")
            connection.execute("DELETE FROM chunks WHERE rowid=(SELECT MAX(rowid) FROM chunks)")
            connection.commit()
            result = self.repository.verify_snapshot("pdf-research")
            self.assertTrue(any("coverage mismatch" in error for error in result["errors"]))
        finally:
            connection.close()

    def test_integrity_detects_artifact_and_page_locator_tampering(self):
        self.publish()
        connection = sqlite3.connect(self.repository.db_path)
        try:
            connection.execute("DROP TRIGGER immutable_chunks_update")
            row = connection.execute("SELECT chunk_id, locator_json FROM chunks LIMIT 1").fetchone()
            locator = json.loads(row[1])
            locator["page"] = 2
            connection.execute("UPDATE chunks SET locator_json=? WHERE chunk_id=?",
                               (json.dumps(locator), row[0]))
            connection.commit()
            self.assertFalse(self.repository.verify_snapshot("pdf-research")["ok"])
            connection.execute("DROP TRIGGER immutable_document_extractions_update")
            connection.execute("UPDATE document_extractions SET artifact_bytes=?", (b"{}",))
            connection.commit()
            result = self.repository.verify_snapshot("pdf-research")
            self.assertFalse(result["ok"])
            self.assertTrue(any("Extraction hash mismatch" in error for error in result["errors"]))
        finally:
            connection.close()

    def test_existing_v1_migrates_without_changing_text_identity(self):
        source = self.root / "legacy.txt"
        source.write_text("Legacy original.", encoding="utf-8")
        legacy = {**self.record, "path": source.name, "sha256": self.sha(source.read_bytes()),
                  "authority": "synthetic"}
        manifest = self.root / "legacy.jsonl"
        manifest.write_text(json.dumps(legacy), encoding="utf-8")
        path = self.root / "v1.sqlite"
        baseline = CorpusRepository(path)
        version_id = baseline.import_manifest(manifest)["version_ids"][0]
        baseline.publish_snapshot("legacy", [version_id], kind="regression")
        original = baseline.get_original(version_id)
        connection = sqlite3.connect(path)
        connection.execute("DROP TABLE document_extractions")
        connection.execute("PRAGMA user_version = 1")
        rows_before = connection.execute("SELECT * FROM document_versions").fetchall()
        connection.commit()
        connection.close()
        migrated = CorpusRepository.open_existing(path)
        self.assertEqual(migrated.get_original(version_id), original)
        self.assertTrue(migrated.verify_snapshot("legacy")["ok"])
        self.assertEqual(migrated.import_manifest(manifest)["version_ids"], [version_id])
        connection = sqlite3.connect(path)
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT * FROM document_versions").fetchall(),
                             rows_before)
            identity = json.loads(connection.execute(
                "SELECT identity_json FROM document_versions WHERE version_id=?", (version_id,)
            ).fetchone()[0])
            self.assertNotIn("extraction_sha256", identity)
            self.assertEqual(identity["extractor_version"], "utf8-markdown-v1")
        finally:
            connection.close()

    def test_undated_is_explicit_research_only_and_retains_date_filters(self):
        version_id, entry, artifact_path = self.publish()
        self.assertEqual(self.repository.get_chunks("pdf-research", as_of="2026-10-11"), [])
        chunks = self.repository.get_chunks("pdf-research", as_of="2026-10-11",
                                            include_undated=True)
        self.assertTrue(chunks)
        self.assertEqual({chunk["issued_date"] for chunk in chunks}, {None})
        self.assertEqual({chunk["effective_from"] for chunk in chunks}, {None})
        for mutation in (
            {"issued_date": "2027-01-01"}, {"effective_from": "2027-01-01"},
            {"withdrawn_date": "2026-01-01"},
        ):
            record = {**self.record, **mutation, "doc_id": str(mutation)}
            new_version = self.repository.import_manifest(
                self.prepare(record=record)[0])["version_ids"][0]
            snapshot_id = "dated-" + str(len(self.repository.list_snapshots()))
            self.repository.publish_snapshot(snapshot_id, [new_version], kind="research")
            self.assertEqual(self.repository.get_chunks(snapshot_id, as_of="2026-10-11",
                                                        include_undated=True), [])
        with self.assertRaisesRegex(CorpusError, "boolean"):
            self.repository.get_chunks("pdf-research", include_undated=1)
        for kind, authority in (("regression", "synthetic"),
                                ("trusted", "authoritative_original")):
            record = {**self.record, "doc_id": kind, "authority": authority,
                      "issued_date": "2026-01-01"}
            selected = self.repository.import_manifest(
                self.prepare(record=record)[0])["version_ids"][0]
            self.repository.publish_snapshot(kind, [selected], kind=kind)
            with self.assertRaisesRegex(CorpusError, "research"):
                self.repository.get_chunks(kind, as_of="2026-10-11", include_undated=True)
            with self.assertRaisesRegex(CorpusError, "research"):
                self.repository.get_chunks(kind, include_undated=True)

    def test_build_reads_v1_output_and_rejects_missing_or_v2_output(self):
        result_dir = self.root / "mineru"
        result_dir.mkdir()
        with self.assertRaises(PDFExtractionError):
            build_extraction(self.pdf, result_dir)
        (result_dir / "full.md").write_text(self.artifact["markdown"], encoding="utf-8")
        content_path = result_dir / "fixture_content_list.json"
        content_path.write_text(json.dumps(self.artifact["content_list"]), encoding="utf-8")
        artifact = build_extraction(self.pdf, result_dir, model_version="offline-fixture")
        self.assertEqual(artifact, self.artifact)
        (result_dir / "fixture_content_list_v2.json").write_text(
            json.dumps([self.artifact["content_list"]]), encoding="utf-8")
        self.assertEqual(build_extraction(self.pdf, result_dir,
                                         model_version="offline-fixture"), self.artifact)
        content_path.write_text(json.dumps([self.artifact["content_list"]]), encoding="utf-8")
        with self.assertRaisesRegex(PDFExtractionError, "v2"):
            build_extraction(self.pdf, result_dir)
        (result_dir / "other_content_list.json").write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(PDFExtractionError, "exactly one"):
            build_extraction(self.pdf, result_dir)

    def test_discarded_blocks_stay_in_artifact_not_retrieval_text(self):
        artifact = copy.deepcopy(self.artifact)
        artifact["content_list"].insert(
            0, {"type": "discarded", "text": "page header is not evidence", "page_idx": 0})
        manifest, record, artifact_path = self.prepare(artifact)
        version_id = self.repository.import_manifest(manifest)["version_ids"][0]
        self.repository.publish_snapshot("discarded", [version_id], kind="research")
        restored = load_extraction_json(self.repository.get_extraction(version_id))
        self.assertEqual(restored["content_list"][0]["type"], "discarded")
        chunks = self.repository.get_chunks("discarded")
        self.assertFalse(any("page header" in chunk["text"] for chunk in chunks))
        self.assertEqual(chunks[0]["locator"]["block_index"], 1)
        self.assertTrue(self.repository.verify_snapshot("discarded")["ok"])
        discarded_only = {**artifact, "content_list": artifact["content_list"][:1]}
        with self.assertRaisesRegex(PDFExtractionError, "no usable"):
            parse_extraction(discarded_only, source_sha256=self.record["sha256"], page_count=2)

    def test_header_footer_and_page_number_are_validated_but_not_indexed(self):
        artifact = copy.deepcopy(self.artifact)
        suppressed = [
            {"type": block_type, "text": f"synthetic {block_type} marker",
             "page_idx": 0, "bbox": [10, 10, 100, 20]}
            for block_type in ("header", "footer", "page_number")
        ]
        artifact["content_list"] = suppressed + artifact["content_list"]
        manifest, record, artifact_path = self.prepare(artifact)
        version_id = self.repository.import_manifest(manifest)["version_ids"][0]
        self.repository.publish_snapshot("page-furniture", [version_id], kind="research")
        restored = load_extraction_json(self.repository.get_extraction(version_id))
        self.assertEqual(restored["content_list"][:3], suppressed)
        chunks = self.repository.get_chunks("page-furniture")
        self.assertFalse(any("synthetic" in chunk["text"] for chunk in chunks))
        self.assertEqual(chunks[0]["locator"]["block_index"], 3)
        self.assertTrue(self.repository.verify_snapshot("page-furniture")["ok"])
        for mutation in ({"type": "unknown_furniture"}, {"page_idx": 2},
                         {"unknown": True}, {"text": None}, {"bbox": [0, 0, 1001, 1]}):
            invalid = copy.deepcopy(artifact)
            invalid["content_list"][0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(PDFExtractionError):
                parse_extraction(invalid, source_sha256=self.record["sha256"], page_count=2)

    def test_equation_image_path_is_preserved_and_validated(self):
        artifact = copy.deepcopy(self.artifact)
        equation = {"type": "equation", "text": "$$x=1$$", "text_format": "latex",
                    "img_path": "images/equation.png", "page_idx": 1, "bbox": [10, 10, 20, 20]}
        artifact["content_list"].append(equation)
        parsed = parse_extraction(artifact, source_sha256=self.record["sha256"], page_count=2)
        self.assertIn("$$x=1$$", parsed["text"])
        self.assertEqual(artifact["content_list"][-1]["img_path"], "images/equation.png")
        for mutation in ({"img_path": {}}, {"img_path": None}, {"unknown": True}):
            invalid = copy.deepcopy(artifact)
            invalid["content_list"][-1].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(PDFExtractionError):
                parse_extraction(invalid, source_sha256=self.record["sha256"], page_count=2)

    def test_empty_table_and_image_only_chart_report_unindexed_blocks(self):
        artifact = copy.deepcopy(self.artifact)
        empty_table = {"type": "table", "table_body": "", "img_path": "",
                       "table_caption": [], "table_footnote": [],
                       "page_idx": 1, "bbox": [10, 10, 20, 20]}
        chart = {"type": "chart", "content": "", "chart_caption": [], "chart_footnote": [],
                 "img_path": "images/chart.png", "page_idx": 1, "bbox": [20, 20, 40, 40]}
        artifact["content_list"].extend([empty_table, chart])
        parsed = parse_extraction(artifact, source_sha256=self.record["sha256"], page_count=2)
        self.assertEqual(parsed["unindexed_blocks"], [
            {"block_index": 3, "page": 2, "block_type": "image", "reason": "image_without_caption"},
            {"block_index": 4, "page": 2, "block_type": "table", "reason": "empty_table_body"},
            {"block_index": 5, "page": 2, "block_type": "chart", "reason": "image_only_chart"},
        ])
        for content in ([empty_table], [chart], [empty_table, chart]):
            with self.subTest(content=content), self.assertRaisesRegex(PDFExtractionError, "no usable"):
                parse_extraction({**artifact, "content_list": content},
                                 source_sha256=self.record["sha256"], page_count=2)
        for mutation in ({"table_body": None}, {"table_body": "  "}):
            invalid = copy.deepcopy(artifact)
            invalid["content_list"][-2].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(PDFExtractionError):
                parse_extraction(invalid, source_sha256=self.record["sha256"], page_count=2)
        missing = copy.deepcopy(artifact)
        del missing["content_list"][-2]["table_body"]
        self.assertEqual(parse_extraction(missing, source_sha256=self.record["sha256"],
                                         page_count=2)["unindexed_blocks"][-2]["reason"],
                         "missing_table_body_placeholder")
        for mutation in ({"content": {}}, {"content": None}, {"chart_caption": [{"text": "x"}]},
                         {"unknown": True}, {"img_path": []}):
            invalid = copy.deepcopy(artifact)
            invalid["content_list"][-1].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(PDFExtractionError):
                parse_extraction(invalid, source_sha256=self.record["sha256"], page_count=2)
        described = copy.deepcopy(artifact)
        described["content_list"][-1]["content"] = "Synthetic chart machine description"
        self.assertIn("Synthetic chart machine description", parse_extraction(
            described, source_sha256=self.record["sha256"], page_count=2)["text"])

    def test_missing_table_body_only_accepts_explicit_empty_placeholder_structure(self):
        placeholder = {"type": "table", "page_idx": 1, "bbox": [10, 10, 30, 30],
                       "img_path": "", "table_caption": [], "table_footnote": []}
        artifact = {**self.artifact, "content_list": [*self.artifact["content_list"], placeholder]}
        parsed = parse_extraction(artifact, source_sha256=self.record["sha256"], page_count=2)
        self.assertEqual(parsed["unindexed_blocks"][-1], {
            "block_index": 4, "page": 2, "block_type": "table",
            "reason": "missing_table_body_placeholder",
        })
        with self.assertRaisesRegex(PDFExtractionError, "no usable"):
            parse_extraction({**artifact, "content_list": [placeholder]},
                             source_sha256=self.record["sha256"], page_count=2)
        invalids = [{**placeholder, **mutation} for mutation in (
            {"img_path": "images/table.png"}, {"table_caption": ["Caption"]},
            {"table_footnote": ["Footnote"]}, {"table_body": None},
            {"table_caption": None}, {"unknown": 1},
        )]
        for field in ("img_path", "table_caption", "table_footnote"):
            invalid = dict(placeholder)
            del invalid[field]
            invalids.append(invalid)
        for invalid in invalids:
            with self.subTest(invalid=invalid), self.assertRaises(PDFExtractionError):
                parse_extraction({**artifact, "content_list": [invalid]},
                                 source_sha256=self.record["sha256"], page_count=2)

    def test_empty_text_and_equation_report_gaps_empty_headers_only_stay_archived(self):
        artifact = copy.deepcopy(self.artifact)
        artifact["content_list"].extend([
            {"type": "text", "text": "", "page_idx": 1},
            {"type": "equation", "text": "", "page_idx": 1, "img_path": "images/formula.png"},
            {"type": "header", "text": "", "page_idx": 1},
            {"type": "footer", "text": "", "page_idx": 1},
            {"type": "page_number", "text": "", "page_idx": 1},
        ])
        parsed = parse_extraction(artifact, source_sha256=self.record["sha256"], page_count=2)
        self.assertEqual(parsed["unindexed_blocks"][-2:], [
            {"block_index": 4, "page": 2, "block_type": "text", "reason": "empty_text"},
            {"block_index": 5, "page": 2, "block_type": "equation", "reason": "empty_equation"},
        ])
        self.assertEqual({block["locator"]["page_scope"] for block in parsed["blocks"]},
                         {"mineru_reported_start_page_unreviewed"})
        for block_type in ("text", "equation", "header", "footer", "page_number"):
            empty_only = {**artifact, "content_list": [
                {"type": block_type, "text": "", "page_idx": 1}]}
            with self.subTest(block_type=block_type), self.assertRaisesRegex(PDFExtractionError, "no usable"):
                parse_extraction(empty_only, source_sha256=self.record["sha256"], page_count=2)
            for invalid in ({"type": block_type, "page_idx": 1},
                            {"type": block_type, "text": None, "page_idx": 1},
                            {"type": block_type, "text": "  ", "page_idx": 1}):
                with self.subTest(invalid=invalid), self.assertRaises(PDFExtractionError):
                    parse_extraction({**artifact, "content_list": [invalid]},
                                     source_sha256=self.record["sha256"], page_count=2)

    def test_nonstandard_json_constants_and_duplicate_keys_rejected_at_all_entries(self):
        manifest, record, artifact_path = self.prepare()
        ordinary = artifact_path.read_text(encoding="utf-8")
        for source in (
            '{"schema_version": 1, "schema_version": 1}',
            '{"unknown": NaN}', '{"unknown": Infinity}', '{"unknown": -Infinity}',
            ordinary.replace('"page_idx": 0', '"page_idx": 0, "page_idx": 1', 1),
        ):
            with self.subTest(source=source), self.assertRaises(PDFExtractionError):
                load_extraction_json(source)
            artifact_path.write_text(source, encoding="utf-8")
            record["extraction"]["sha256"] = self.sha(artifact_path.read_bytes())
            manifest.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(CorpusError):
                self.repository.import_manifest(manifest)
        result_dir = self.root / "nonstandard"
        result_dir.mkdir()
        (result_dir / "full.md").write_text("fixture", encoding="utf-8")
        (result_dir / "fixture_content_list.json").write_text(
            '[{"type":"text","page_idx":0,"text":"x","bbox":[0,0,NaN,10]}]',
            encoding="utf-8")
        with self.assertRaisesRegex(PDFExtractionError, "Nonstandard"):
            build_extraction(self.pdf, result_dir)


if __name__ == "__main__":
    unittest.main()
