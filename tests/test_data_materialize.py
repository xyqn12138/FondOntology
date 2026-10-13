"""Offline restoration preserves source bytes and conservative review limits."""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from fondontology.corpus.data_catalog import build_catalog_records
from fondontology.corpus.data_materialize import DEFAULT_STATES, _csrc_body, _html_body, _pdf_body, materialize_data
from fondontology.corpus.data_text import CHUNKER_VERSION, catalog_body_sections


class DataMaterializeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data = Path(self.temporary.name) / "data"
        self.data.mkdir()
        self.raw = self.data / "original.html"
        self.raw.write_text(
            '<html><nav>Unrelated navigation</nav><main id="body"><h1>Fixture Law</h1>'
            '<p>Decree and transition remain substantive.</p><h2>第一章 总则</h2>'
            '<p>第一条 First operative article.</p><p>第二条 Second operative article.</p>'
            '<p>附件：</p><h2>第一章 Procedure</h2><p>Important appendix body.</p>'
            '</main><script>outside()</script></html>', encoding="utf-8",
        )
        self.source = {
            "id": "fixture-law", "legacy_path": "legacy.md", "title": "Fixture Law",
            "publisher": "Synthetic issuer", "seed_urls": ["https://issuer.example/law"],
            "source_page_url": "https://issuer.example/law",
            "download_url": "https://issuer.example/law", "format": "html",
            "issued_date": "2024-01-01", "effective_from": None, "expected_articles": 2,
            "origin_kind": "issuer_original", "raw_path": self.raw.name,
            "raw_sha256": self.sha(self.raw.read_bytes()), "body_selector": "#body",
        }
        self.legacy = self.data / "legacy.md"
        self.legacy.write_text("Historical summary stays intact.", encoding="utf-8")
        self.write_json("receipt.json", {
            "requested_url": self.source["download_url"], "final_url": self.source["download_url"],
            "raw_sha256": self.source["raw_sha256"], "bytes": self.raw.stat().st_size,
            "http_status": 200,
        })
        self.manifest = self.data / "sources.json"
        self.save_source()

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    def write_json(self, relative, value):
        path = self.data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def save_source(self):
        self.write_json("sources.json", {"schema_version": 1, "documents": [self.source]})

    def restore(self, write=False):
        self.save_source()
        return materialize_data(self.data, source_paths=["sources.json"], state_paths=[], write=write)

    def test_dry_run_does_not_create_fulltext_or_catalog(self):
        result = self.restore()
        self.assertEqual(result["counts"]["ready"], 1)
        self.assertFalse((self.data / "_fulltext").exists())
        self.assertFalse((self.data / "source_catalog.json").exists())

    def test_technical_examples_do_not_infer_a_legal_article_sequence(self):
        self.source["expected_articles"] = None
        self.raw.write_text(
            '<main id="body"><h1>Fixture Law</h1><p>Technical examples follow.</p>'
            '<p>第一条 Example one.</p><p>第二条 Example two.</p>'
            '<p>第一条 Another example.</p><p>第二条 Another clause.</p></main>',
            encoding="utf-8")
        self.source["raw_sha256"] = self.sha(self.raw.read_bytes())
        self.write_json("receipt.json", {
            "requested_url": self.source["download_url"], "final_url": self.source["download_url"],
            "raw_sha256": self.source["raw_sha256"], "bytes": self.raw.stat().st_size,
            "http_status": 200,
        })
        document = self.restore(write=True)["documents"][0]
        self.assertEqual(document["status"], "ready")
        self.assertIsNone(document["expected_articles"])
        self.assertIsNone(document["verification"]["article_count"])
        records = build_catalog_records(self.data / "source_catalog.json", data_root=self.data)
        self.assertEqual(records["records"][0]["doc_type"], "data_technical_markdown")
        text = (self.data / document["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("Another example.", text)
        self.assertIn("Another clause.", text)

    def test_html_excludes_comments_and_process_metadata_including_tables(self):
        raw = (b'<html><main id="body"><!DOCTYPE html><?process hidden?>'
               b'<!-- [if gte mso 9]>Word condition content<![endif] -->'
               b'<p>Preserved body.</p><table><!-- table comment -->'
               b'<tr><td>Preserved cell.</td></tr></table></main></html>')
        text, observations = _html_body(raw, "#body")
        self.assertIn("Preserved body.", text)
        self.assertIn("Preserved cell.", text)
        self.assertNotIn("Word condition", text)
        self.assertNotIn("table comment", text)
        self.assertNotIn("process", text)
        self.assertNotIn("DOCTYPE", text)
        self.assertEqual(observations["table_count"], 1)

    def test_explicit_title_selector_verifies_same_html_and_excludes_full_title(self):
        self.raw.write_text(
            '<html><nav>Misleading navigation title</nav><article><h2>Fixture Law（2025年修订）</h2>'
            '<main id="body"><p>第一条 Scope.</p><p>第二条 Exception.</p></main>'
            '</article></html>', encoding="utf-8",
        )
        self.source.update({"title": "Fixture Law（2025年修订）",
                            "title_selector": "article h2", "raw_sha256": self.sha(self.raw.read_bytes())})
        self.write_json("receipt.json", {
            "requested_url": self.source["download_url"], "final_url": self.source["download_url"],
            "raw_sha256": self.source["raw_sha256"], "bytes": self.raw.stat().st_size, "http_status": 200,
        })
        result = self.restore(write=True)
        document = result["documents"][0]
        self.assertEqual(document["status"], "ready")
        text = (self.data / document["markdown_path"]).read_text(encoding="utf-8")
        self.assertNotIn("Fixture Law", text)
        self.assertNotIn("Misleading navigation", text)
        self.source.pop("title_selector")
        self.assertEqual(self.restore()["documents"][0]["verification"]["identity"], "not_checked")
        self.source["title_selector"] = "p"
        self.assertEqual(self.restore()["documents"][0]["status"], "downloaded")

    def test_materializer_receipt_uses_same_unicode_url_equivalence(self):
        self.source["download_url"] = "https://issuer.example/%E9%99%84%E4%BB%B6.pdf"
        self.write_json("receipt.json", {
            "requested_url": "https://issuer.example/附件.pdf",
            "actual_url": self.source["download_url"], "final_url": "https://issuer.example/附件.pdf",
            "raw_sha256": self.source["raw_sha256"], "bytes": self.raw.stat().st_size, "http_status": 200,
        })
        self.assertEqual(self.restore()["documents"][0]["status"], "ready")
        self.source["download_url"] = "https://issuer.example/a%2Fb"
        self.write_json("receipt.json", {
            "requested_url": "https://issuer.example/a/b", "final_url": "https://issuer.example/a/b",
            "raw_sha256": self.source["raw_sha256"], "bytes": self.raw.stat().st_size, "http_status": 200,
        })
        self.assertEqual(self.restore()["documents"][0]["status"], "converted_unverified")

    def test_2018_notice_records_known_repeal_evidence_and_never_ready(self):
        self.source["id"] = "amac-manager-registration-notice-2018"
        document = self.restore()["documents"][0]
        self.assertEqual(document["status"], "converted_unverified")
        self.assertIn("repealed on 2023-05-01", document["failure_reason"])
        self.assertNotIn("applicability unresolved", document["failure_reason"])
        evidence = [item for item in document["verification"]["evidence"] if isinstance(item, dict)]
        self.assertEqual(evidence[0]["repealed_on"], "2023-05-01")
        self.assertEqual(evidence[0]["source_article"], "第八十三条")

    def test_html_ready_preserves_decree_appendix_and_source_bytes(self):
        original = self.raw.read_bytes()
        result = self.restore(write=True)
        document = result["documents"][0]
        text = (self.data / document["markdown_path"]).read_text(encoding="utf-8")
        self.assertNotIn("Fixture Law", text)
        self.assertNotIn("Unrelated navigation", text)
        self.assertIn("Decree and transition", text)
        self.assertIn("Important appendix body.", text)
        self.assertEqual(self.raw.read_bytes(), original)
        self.assertEqual(self.legacy.read_text(encoding="utf-8"), "Historical summary stays intact.")
        records = build_catalog_records(self.data / "source_catalog.json", data_root=self.data)
        self.assertEqual(len(records["records"]), 1)
        sections = catalog_body_sections(text, {
            "strategy": CHUNKER_VERSION, "body_start_line": 1, "expected_articles": 2,
            "max_chars": 800, "overlap": 0,
        })
        self.assertEqual(sum("article_number" in section for section in sections), 2)
        supplements = [text[section["char_start"]:section["char_end"]]
                       for section in sections if "article_number" not in section]
        self.assertTrue(any("Decree" in section for section in supplements))
        self.assertTrue(any("appendix" in section for section in supplements))

    def test_repeated_write_is_immutable_and_idempotent(self):
        first = self.restore(write=True)
        catalog = (self.data / "source_catalog.json").read_bytes()
        second = self.restore(write=True)
        self.assertEqual(first, second)
        self.assertEqual((self.data / "source_catalog.json").read_bytes(), catalog)
        markdown = self.data / first["documents"][0]["markdown_path"]
        markdown.write_text("Tampered artifact", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Immutable"):
            self.restore(write=True)
        self.assertEqual((self.data / "source_catalog.json").read_bytes(), catalog)

    def test_same_markdown_preserves_multiple_hashed_conversion_observations(self):
        initial = self.restore(write=True)["documents"][0]
        original_record = self.data / initial["verification"]["conversion"]["record_path"]
        original_bytes = original_record.read_bytes()
        self.source["title_selector"] = "#body h1"
        revised = self.restore(write=True)["documents"][0]
        self.assertEqual(initial["markdown_path"], revised["markdown_path"])
        self.assertEqual(original_record.read_bytes(), original_bytes)
        revised_record = self.data / revised["verification"]["conversion"]["record_path"]
        self.assertNotEqual(revised_record, original_record)
        self.assertEqual(revised_record.stem, self.sha(revised_record.read_bytes()))
        self.assertEqual(len(list(revised_record.parent.glob("*.json"))), 2)

    def test_invalid_ready_catalog_does_not_replace_previous_catalog(self):
        catalog = self.data / "source_catalog.json"
        catalog.write_bytes(b"previous catalog")
        self.source["publisher"] = None
        with self.assertRaisesRegex(ValueError, "publisher"):
            self.restore(write=True)
        self.assertEqual(catalog.read_bytes(), b"previous catalog")
        self.assertEqual(list(self.data.glob("*.catalog.json")), [])

    def test_structural_conflict_and_wrong_identity_remain_unverified(self):
        self.source["expected_articles"] = 3
        self.assertEqual(self.restore()["documents"][0]["status"], "converted_unverified")
        self.source["expected_articles"] = 2
        self.source["title"] = "Different Law"
        document = self.restore()["documents"][0]
        self.assertEqual(document["status"], "converted_unverified")
        self.assertIn("identity", document["failure_reason"])

    def test_visual_html_content_and_missing_date_do_not_qualify(self):
        self.raw.write_text(
            '<main id="body">Fixture Law<p>第一条 Scope.</p><p>第二条 Exception.</p>'
            '<table><tr><td>Preserved table text</td></tr></table><img src="missing.png"></main>',
            encoding="utf-8",
        )
        self.source["raw_sha256"] = self.sha(self.raw.read_bytes())
        self.source["issued_date"] = None
        result = self.restore(write=True)
        document = result["documents"][0]
        self.assertEqual(document["status"], "converted_unverified")
        self.assertIn("<table>", (self.data / document["markdown_path"]).read_text(encoding="utf-8"))
        record = json.loads((self.data / document["verification"]["conversion"]["record_path"]).read_bytes())
        self.assertEqual(record["observations"]["missing_images"], ["missing.png"])

    def test_raw_hash_and_unsafe_paths_fail_closed(self):
        self.source["raw_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.restore()
        self.source["raw_path"] = "../outside.html"
        with self.assertRaisesRegex(ValueError, "traversal"):
            self.restore()
        self.source["id"] = "../unsafe"
        with self.assertRaisesRegex(ValueError, "stable ID"):
            self.restore()

    def test_selector_failure_does_not_claim_conversion(self):
        self.source["body_selector"] = "p"
        document = self.restore()["documents"][0]
        self.assertEqual(document["status"], "downloaded")
        self.assertIn("exactly one", document["failure_reason"])

    def test_json_keeps_active_nested_paragraphs_and_circled_marker(self):
        payload = {
            "success": True, "lawlist": {
                "law": {"secFutrsLawName": "Fixture Law", "secFutrsLawVersion": "20240101"},
                "lawEntryVOs": [
                    {"title": "第一章 总则", "lawEntryStsCde": "0", "secFutrsLawEntryClsfCde": "2"},
                    {"title": "第一条①", "lawEntryStsCde": "0", "secFutrsLawEntryClsfCde": "4",
                     "cntnt": "Operative text.", "itemList": [{"cntnt": "Nested operative paragraph."}],
                     "annoList": [{"cntnt": "Editorial annotation excluded."}]},
                    {"title": "第二条", "lawEntryStsCde": "0", "secFutrsLawEntryClsfCde": "4",
                     "cntnt": "Second article."},
                    {"title": "Old deleted article", "lawEntryStsCde": "1",
                     "secFutrsLawEntryClsfCde": "4", "cntnt": "Inactive text."},
                ],
            },
        }
        text, observations = _csrc_body(json.dumps(payload).encode())
        self.assertIn("第一条 ①", text)
        self.assertIn("Nested operative paragraph.", text)
        self.assertNotIn("Editorial annotation", text)
        self.assertNotIn("Inactive text.", text)
        self.assertEqual(observations["active_article_count"], 2)

    def test_word_hash_bound_assets_and_unverified_review(self):
        self.source["format"] = "doc"
        word_raw = ("Fixture Law\n第一条Direct joined heading.\n第二条  \n\n Other heading.\n"
                    "![figure](full.files/image001.png)\n").encode("utf-8")
        word_path = self.data / "_converted" / "word" / "full.md"
        word_path.parent.mkdir(parents=True)
        word_path.write_bytes(word_raw)
        image = word_path.parent / "full.files" / "image001.png"
        image.parent.mkdir()
        image.write_bytes(b"synthetic image fixture")
        word = {
            "id": self.source["id"], "markdown_path": word_path.relative_to(self.data).as_posix(),
            "source_sha256": self.source["raw_sha256"], "method": "fixture", "version": "1",
            "observations": {
                "markdown_sha256": self.sha(word_raw), "unsupported": [],
                "image_assets": {"full.files/image001.png": self.sha(image.read_bytes())},
                "missing_images": [], "page_count": None, "page_coverage": [],
            },
        }
        self.write_json("_recovery/word-conversions.json", {"documents": [word]})
        result = self.restore(write=True)
        document = result["documents"][0]
        self.assertEqual(document["status"], "converted_unverified")
        self.assertIn("Word full-text fidelity", document["failure_reason"])
        self.assertEqual(document["verification"]["article_count"], 2)
        record = json.loads((self.data / document["verification"]["conversion"]["record_path"]).read_bytes())
        self.assertEqual(record["observations"]["article_heading_separator_insertions"], 1)
        self.assertEqual(record["observations"]["isolated_article_heading_line_joins"], 1)
        output_image = (self.data / document["markdown_path"]).parent / "full.files" / "image001.png"
        self.assertEqual(output_image.read_bytes(), image.read_bytes())
        word["observations"]["markdown_sha256"] = "0" * 64
        self.write_json("_recovery/word-conversions.json", {"documents": [word]})
        document = self.restore()["documents"][0]
        self.assertEqual(document["status"], "downloaded")
        self.assertIn("Markdown hash", document["failure_reason"])

    def test_bound_pdf_records_actual_page_coverage_and_detects_tampering(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=100, height=100)
        stream = io.BytesIO()
        writer.write(stream)
        raw = stream.getvalue()
        directory = self.data / "_converted" / "L3" / "files" / "fixture"
        directory.mkdir(parents=True)
        markdown = "Fixture Law\n第一条 Scope.\n第二条 Exception.\n"
        artifact = {
            "schema_version": 1, "source_sha256": self.sha(raw), "page_count": 2,
            "extractor": {"name": "mineru", "version": "mineru-content-list-v1", "model_version": "fixture"},
            "markdown": markdown, "content_list": [
                {"type": "text", "page_idx": 0, "text": "Fixture Law\n第一条 Scope."},
                {"type": "text", "page_idx": 1, "text": "第二条 Exception."},
                {"type": "table", "page_idx": 1, "img_path": "",
                 "table_caption": [], "table_footnote": []},
            ],
        }
        extraction = json.dumps(artifact).encode()
        (directory / "extraction.json").write_bytes(extraction)
        (directory / "full.md").write_text(markdown, encoding="utf-8", newline="")
        entry = {"sha256": self.sha(raw), "sha256_extraction": self.sha(extraction),
                 "artifacts": {"full.md": self.sha(markdown.encode())}}
        text, observations, assets = _pdf_body(raw, self.raw, (directory, entry))
        self.assertEqual(text, markdown)
        self.assertEqual(observations["page_coverage"], [1, 2])
        self.assertEqual(assets, {})
        self.raw.write_bytes(raw)
        self.source.update({"format": "pdf", "raw_sha256": self.sha(raw)})
        self.save_source()
        self.assertIn("_converted/L3/state.json", DEFAULT_STATES)
        self.write_json("_converted/L3/state.json", {
            "data_root": str(self.data),
            "files": {"fixture": {**entry, "pdf": self.raw.name, "status": "completed"}},
        })
        result = materialize_data(self.data, source_paths=["sources.json"],
                                  state_paths=["_converted/L3/state.json"])
        document = result["documents"][0]
        self.assertEqual(document["status"], "converted_unverified")
        self.assertEqual(document["verification"]["page_count"], 2)
        self.assertEqual(document["verification"]["completeness"], "complete")
        self.assertIn("Acquisition receipt", document["failure_reason"])
        self.assertEqual(observations["unsupported"], [])
        self.assertEqual(len(observations["merged_table_acceptance"]["accepted_blocks"]), 1)
        self.write_json("receipt.json", {
            "requested_url": self.source["download_url"], "final_url": self.source["download_url"],
            "raw_sha256": self.sha(raw), "bytes": len(raw), "http_status": 200,
        })
        self.source["pdf_fidelity_review"] = {
            "source_sha256": self.sha(raw), "markdown_sha256": self.sha(markdown.encode()),
            "basis": "User verified complete text and merged tables.",
            "accepted_blocks": observations["unsupported"],
        }
        self.save_source()
        result = materialize_data(self.data, source_paths=["sources.json"],
                                  state_paths=["_converted/L3/state.json"], write=True)
        self.assertEqual(result["documents"][0]["status"], "ready")
        self.assertEqual(len(build_catalog_records(self.data / "source_catalog.json",
                                                  data_root=self.data)["records"]), 1)
        self.source["pdf_fidelity_review"]["accepted_blocks"] = []
        self.save_source()
        result = materialize_data(self.data, source_paths=["sources.json"],
                                  state_paths=["_converted/L3/state.json"])
        self.assertEqual(result["documents"][0]["status"], "ready")
        self.source["conversion_issues"] = [{
            "block": 0, "reason": "confirmed_latex_transcription_mismatch",
            "basis": "Source comparison found an extra equality.",
        }]
        self.save_source()
        result = materialize_data(self.data, source_paths=["sources.json"],
                                  state_paths=["_converted/L3/state.json"])
        self.assertEqual(result["documents"][0]["status"], "converted_unverified")
        self.source.pop("conversion_issues")
        self.source["pdf_fidelity_review"]["markdown_sha256"] = "0" * 64
        self.save_source()
        result = materialize_data(self.data, source_paths=["sources.json"],
                                  state_paths=["_converted/L3/state.json"])
        self.assertEqual(result["documents"][0]["status"], "downloaded")
        self.assertIn("PDF fidelity review", result["documents"][0]["failure_reason"])
        artifact["content_list"].append({
            "type": "image", "page_idx": 1, "img_path": "",
            "image_caption": ["Substantive diagram"], "image_footnote": [],
        })
        artifact["content_list"].extend([
            {"type": "table", "page_idx": 1, "img_path": "images/recognized.jpg",
             "table_body": "<table><tr><td>Recognized text</td></tr></table>"},
            {"type": "table", "page_idx": 1, "img_path": "images/failed.jpg",
             "table_body": ""},
            {"type": "equation", "page_idx": 1, "img_path": "images/formula.jpg",
             "text": "x = 0"},
        ])
        for name in ["recognized.jpg", "failed.jpg", "formula.jpg"]:
            image = directory / "images" / name
            image.parent.mkdir(exist_ok=True)
            image.write_bytes(name.encode())
            entry["artifacts"]["images/" + name] = self.sha(image.read_bytes())
        extraction = json.dumps(artifact).encode()
        (directory / "extraction.json").write_bytes(extraction)
        entry["sha256_extraction"] = self.sha(extraction)
        _, observations, assets = _pdf_body(raw, self.raw, (directory, entry))
        self.assertNotIn(Path("images/recognized.jpg"), assets)
        self.assertIn(Path("images/failed.jpg"), assets)
        self.assertNotIn(Path("images/formula.jpg"), assets)
        self.assertEqual(observations["omitted_recognition_images"][0]["path"],
                         "images/recognized.jpg")
        self.assertTrue(any(block.get("kind") == "visual_or_formula_requires_review"
                            for block in observations["unsupported"]))
        (directory / "full.md").write_text("Tampered PDF conversion", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs"):
            _pdf_body(raw, self.raw, (directory, entry))


if __name__ == "__main__":
    unittest.main()
