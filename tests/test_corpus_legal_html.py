"""Offline HTML-byte retention and article-level legal evidence contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.corpus.legal_text import extract_official_html, legal_article_sections


FIXTURE = Path(__file__).parent / "fixtures" / "legal_html" / "synthetic-rule.html"
REFERENCE = {"kind": "official_html",
             "selector": {"tag": "div", "attribute": "class", "value": "Custom_UnionStyle"},
             "encoding": "utf-8"}


class LegalHTMLTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "rule.html"
        self.source.write_bytes(FIXTURE.read_bytes())
        self.repository = CorpusRepository(self.root / "corpus.sqlite")
        self.record = {
            "doc_id": "synthetic:legal-html", "title": "合成测试法规", "doc_type": "legal_rule",
            "source_uri": "urn:synthetic:legal-html", "path": self.source.name,
            "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "issued_date": "2024-01-01", "effective_from": "2024-02-01",
            "authority": "synthetic", "status": "unverified",
            "provenance": {"kind": "synthetic_algorithm_fixture"},
            "locator": {"format": "html"}, "extraction": copy.deepcopy(REFERENCE),
            "chunker_config": {"strategy": "legal-article-v1", "max_chars": 20,
                               "overlap": 0, "expected_articles": 3},
        }

    def import_record(self, record=None):
        path = self.root / "manifest.jsonl"
        path.write_text(json.dumps(record or self.record) + "\n", encoding="utf-8")
        return self.repository.import_manifest(path)

    def publish(self):
        result = self.import_record()
        self.repository.publish_snapshot("legal-fixture", result["version_ids"], kind="regression")
        return result["version_ids"][0]

    def test_raw_restore_normalized_identity_scripts_metadata_chapters_and_idempotency(self):
        version_id = self.publish()
        original = self.source.read_bytes()
        normalized = self.repository.get_normalized_text(version_id)
        self.assertIn("发布元数据", normalized)
        self.assertNotIn("Do not index", normalized)
        self.assertNotIn("不得进入正文", normalized)
        chunks = self.repository.get_chunks("legal-fixture")
        self.assertEqual(len(chunks), 3)
        self.assertEqual([chunk["locator"]["article_number"] for chunk in chunks], [1, 2, 3])
        self.assertNotIn("发布元数据", "".join(chunk["text"] for chunk in chunks))
        self.assertNotIn("第二章", chunks[1]["text"])
        for chunk in chunks:
            locator = chunk["locator"]
            self.assertEqual(locator["content_kind"], "legal_article")
            self.assertEqual(locator["title"], self.record["title"])
            self.assertEqual(locator["raw_html_sha256"], self.record["sha256"])
            self.assertEqual(chunk["text"], normalized[locator["char_start"]:locator["char_end"]])
            self.assertEqual(locator["section_char_start"], locator["char_start"])
            self.assertEqual(locator["section_char_end"], locator["char_end"])
            self.assertEqual(locator["dom_locator"]["selector"], REFERENCE["selector"])
            self.assertTrue(locator["oversized"])
            self.assertGreater(len(chunk["text"]), self.record["chunker_config"]["max_chars"])
        self.assertEqual(chunks[2]["locator"]["chapter"], "第二章 附则")
        duplicate = self.import_record()
        self.assertEqual(duplicate["reused"], 1)
        self.assertEqual(duplicate["version_ids"], [version_id])
        self.source.unlink()
        reopened = CorpusRepository.open_existing(self.repository.db_path)
        self.assertEqual(reopened.get_original(version_id), original)
        self.assertEqual(reopened.get_normalized_text(version_id), normalized)
        self.assertTrue(reopened.verify_snapshot("legal-fixture")["ok"])
        receipt = json.loads(reopened.get_extraction(version_id))
        self.assertEqual(receipt["normalized_text"], normalized)

    def test_selector_requires_one_closed_match_and_excludes_nested_scripts(self):
        bodies = [
            b"<div class='other'>content</div>",
            b"<div class='Custom_UnionStyle'>one</div><div class='Custom_UnionStyle'>two</div>",
            b"<div class='Custom_UnionStyle'>not closed",
            b"<div class='Custom_UnionStyle'><p>unbalanced</div>",
        ]
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(ValueError):
                extract_official_html(body, REFERENCE)
        with self.assertRaisesRegex(ValueError, "control character"):
            extract_official_html(b"<div class='Custom_UnionStyle'>a\x01b</div>", REFERENCE)
        parsed = extract_official_html(
            b"<div class='Custom_UnionStyle extra'><p>a<span>b</span>c</p>"
            b"<script>bad</script><p>d&nbsp;e</p></div>", REFERENCE)
        self.assertEqual(parsed["text"], "abc\nd e")
        nul = extract_official_html(
            b"<div class='Custom_UnionStyle'><p>a\x00b</p></div>", REFERENCE)
        self.assertEqual(nul["text"], "ab")
        self.assertEqual(nul["removed_nul_count"], 1)
        self.assertEqual(extract_official_html(
            "<div class='Custom_UnionStyle'><p>第一条&ensp;&ensp;正文</p></div>".encode(),
            REFERENCE)["text"], "第一条 正文")
        font_body = (
            "<div class='Custom_UnionStyle'><p><font>第一条</font>\n"
            "<span>&ensp;&ensp;测试正文。</span></p>\n"
            "<p><font>第二条</font>&ensp;&ensp;<span>第二条规定不是边界。</span></p></div>"
        ).encode()
        font_text = extract_official_html(font_body, REFERENCE)["text"]
        self.assertEqual(len(legal_article_sections(font_text, expected_articles=2)), 2)

    def test_article_gaps_duplicates_references_and_expected_tail_are_rejected(self):
        texts = [
            "第一条 a\n第三条 c",
            "第一条 a\n第一条 duplicate",
            "第一条 a\n第二条 b\n第四条 c",
            "第二条规定不构成法条",
            "第一条 a\n第二条 b",
        ]
        for text in texts:
            with self.subTest(text=text), self.assertRaises(ValueError):
                legal_article_sections(text, expected_articles=3)
        sections = legal_article_sections(
            "第一条 a\n第二条规定是引用，不是标题\n第二条 b", expected_articles=2)
        self.assertEqual(len(sections), 2)
        self.assertGreater(sections[0]["char_end"], len("第一条 a"))

    def test_long_article_is_never_truncated_or_split(self):
        parsed = legal_article_sections("第一条 " + "长正文。" * 1000, expected_articles=1)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["char_end"], len("第一条 " + "长正文。" * 1000))
        self.source.write_bytes(
            ("<div class='Custom_UnionStyle'><p>第一条 " + "长正文。" * 1000
             + "</p></div>").encode("utf-8")
        )
        record = {**self.record, "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                  "chunker_config": {**self.record["chunker_config"], "expected_articles": 1}}
        result = self.import_record(record)
        self.repository.publish_snapshot("long-article", result["version_ids"], kind="regression")
        chunks = self.repository.get_chunks("long-article")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["text"], "第一条 " + "长正文。" * 1000)
        self.assertTrue(chunks[0]["locator"]["oversized"])
        self.assertTrue(self.repository.verify_snapshot("long-article")["ok"])

    def test_bad_extraction_config_and_sequence_roll_back(self):
        invalid = [
            {"extraction": {**REFERENCE, "encoding": "guess"}},
            {"extraction": {**REFERENCE, "unknown": "value"}},
            {"chunker_config": {"max_chars": 800, "overlap": 0}},
            {"chunker_config": {**self.record["chunker_config"], "overlap": 1}},
            {"chunker_config": {**self.record["chunker_config"], "expected_articles": 4}},
        ]
        for mutation in invalid:
            with self.subTest(mutation=mutation), self.assertRaises(CorpusError):
                self.import_record({**self.record, **mutation})
        self.assertEqual(self.repository.list_versions(), [])

    def test_old_text_snapshot_retains_v1_behavior(self):
        text_path = self.root / "old.md"
        text_path.write_text("# Old fixture\n" + "old text " * 20, encoding="utf-8")
        record = {**self.record, "doc_id": "synthetic:old", "path": text_path.name,
                  "sha256": hashlib.sha256(text_path.read_bytes()).hexdigest(),
                  "chunker_config": {"max_chars": 30, "overlap": 4}}
        record.pop("extraction")
        result = self.import_record(record)
        self.repository.publish_snapshot("old-v1", result["version_ids"], kind="regression")
        self.assertGreater(len(self.repository.get_chunks("old-v1")), 1)
        self.assertTrue(self.repository.verify_snapshot("old-v1")["ok"])

    def test_verify_detects_tampered_html_normalized_text_and_locator(self):
        self.publish()
        with closing(sqlite3.connect(self.repository.db_path)) as connection:
            with connection:
                connection.execute("DROP TRIGGER immutable_document_extractions_update")
                connection.execute("UPDATE document_extractions SET normalized_text='tampered'")
        result = self.repository.verify_snapshot("legal-fixture")
        self.assertFalse(result["ok"])
        self.assertTrue(any("normalized metadata" in error for error in result["errors"]))

    def test_verify_rejects_dom_locator_tampering_and_deleted_article(self):
        self.publish()
        with closing(sqlite3.connect(self.repository.db_path)) as connection:
            with connection:
                connection.execute("DROP TRIGGER immutable_sections_update")
                row = connection.execute("SELECT section_id, locator_json FROM sections").fetchone()
                locator = json.loads(row[1])
                locator["dom_locator"]["path"] = "/incorrect[1]"
                connection.execute("UPDATE sections SET locator_json=? WHERE section_id=?",
                                   (json.dumps(locator), row[0]))
        self.assertFalse(self.repository.verify_snapshot("legal-fixture")["ok"])

    def test_different_original_html_has_separate_identity_even_when_normalized_text_is_equal(self):
        first = self.publish()
        self.source.write_bytes(self.source.read_bytes().replace(
            b"outside noise", b"changed outside noise"))
        record = {**self.record, "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()}
        second = self.import_record(record)["version_ids"][0]
        self.assertNotEqual(first, second)
        self.assertNotEqual(self.repository.get_original(first), self.repository.get_original(second))
        self.assertEqual(self.repository.get_normalized_text(first),
                         self.repository.get_normalized_text(second))

    def test_verify_rejects_deleted_complete_article_chunk(self):
        self.publish()
        with closing(sqlite3.connect(self.repository.db_path)) as connection:
            with connection:
                connection.execute("DROP TRIGGER immutable_chunks_delete")
                connection.execute("DELETE FROM chunks WHERE chunk_id="
                                   "(SELECT chunk_id FROM chunks LIMIT 1)")
        result = self.repository.verify_snapshot("legal-fixture")
        self.assertFalse(result["ok"])
        self.assertTrue(any("coverage" in error or "chunk count" in error
                            for error in result["errors"]))

    def test_metadata_prefix_is_preserved_but_never_chunked_for_legal_text(self):
        source = self.root / "rule.txt"
        text = "合成测试法规\n发布元数据\n第一章 总则\n第一条 正文。\n第二条 正文。\n"
        source.write_bytes(text.encode("utf-8"))
        record = {**self.record, "path": source.name,
                  "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "chunker_config": {**self.record["chunker_config"], "expected_articles": 2}}
        record.pop("extraction")
        imported = self.import_record(record)
        self.repository.publish_snapshot("legal-text", imported["version_ids"], kind="regression")
        self.assertEqual(self.repository.get_normalized_text(imported["version_ids"][0]), text)
        chunks = self.repository.get_chunks("legal-text")
        self.assertEqual(len(chunks), 2)
        self.assertNotIn("发布元数据", "".join(chunk["text"] for chunk in chunks))
        self.assertTrue(self.repository.verify_snapshot("legal-text")["ok"])
