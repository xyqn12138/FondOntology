"""Tests for auditable Markdown inventory and explicit selection conversion."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fondontology.corpus.markdown_inventory import (
    build_repository_records,
    inspect_markdown,
    inventory_markdown,
    load_selection,
)
from fondontology.corpus import CorpusRepository


FIXTURES = Path(__file__).parent / "fixtures" / "markdown_inventory"
CLI = Path(__file__).resolve().parents[1] / "tools" / "import_legal_markdown.py"


class MarkdownInventoryTests(unittest.TestCase):
    def selection(self, filename="full.md"):
        return {
            "path": filename,
            "sha256": hashlib.sha256((FIXTURES / filename).read_bytes()).hexdigest(),
            "doc_id": "synthetic:" + filename,
            "source_uri": "https://www.gov.cn/example",
            "source_verification": {"status": "not_checked"},
            "authority": "research_note",
            "status": "unverified",
        }

    def test_inventory_hashes_and_completeness_without_promoting_summary(self):
        report = inventory_markdown(FIXTURES)
        self.assertEqual(report["file_count"], 2)
        records = {item["path"]: item for item in report["records"]}
        self.assertEqual(records["full.md"]["completeness"], "explicit_full")
        self.assertEqual(records["full.md"]["authority_recommendation"],
                         "candidate_authoritative_original")
        self.assertEqual(records["summary.md"]["completeness"], "incomplete")
        self.assertEqual(records["summary.md"]["authority_recommendation"], "research_note")
        self.assertEqual(len(records["full.md"]["sha256"]), 64)
        self.assertEqual(records["full.md"]["date_declarations"][0]["iso"], "2024-01-02")

    def test_selection_manifest_controls_authority_and_status(self):
        selections = [{
            "path": "full.md",
            "sha256": hashlib.sha256((FIXTURES / "full.md").read_bytes()).hexdigest(),
            "doc_id": "synthetic:full-rule",
            "source_uri": "https://www.gov.cn/example",
            "source_verification": {"status": "not_checked"},
            "authority": "research_note",
            "status": "unverified",
            "selection_basis": "human review pending source check",
        }]
        records = build_repository_records(FIXTURES, selections)
        self.assertEqual(records[0]["authority"], "research_note")
        self.assertEqual(records[0]["status"], "unverified")
        self.assertEqual(records[0]["source_uri"], "https://www.gov.cn/example")
        self.assertEqual(records[0]["locator"]["kind"], "markdown")

    def test_load_selection_accepts_wrapped_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selection.json"
            path.write_text(json.dumps({"documents": [{"path": "full.md"}]}), encoding="utf-8")
            self.assertEqual(load_selection(path)[0]["path"], "full.md")

    def test_load_selection_rejects_duplicate_keys_nonfinite_numbers_and_unknown_envelope(self):
        invalid_payloads = [
            '{"documents":[{"path":"full.md","status":"verified","status":"unverified"}]}',
            '{"documents":[],"documents":[{"path":"full.md"}]}',
            '{"documents":[{"path":"full.md","confidence":NaN}]}',
            '{"documents":[{"path":"full.md","confidence":Infinity}]}',
            '{"documents":[{"path":"full.md","confidence":-Infinity}]}',
            '{"documents":[{"path":"full.md","confidence":1e999}]}',
            '{"documents":[{"path":"full.md"}],"unchecked":true}',
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selection.json"
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_selection(path)

    def test_load_selection_accepts_document_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selection.json"
            path.write_text('[{"path":"full.md"}]', encoding="utf-8")
            self.assertEqual(load_selection(path), [{"path": "full.md"}])

    def test_inspect_rejects_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.md"
            path.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                inspect_markdown(path)

    def test_hash_cannot_verify_authority_or_source(self):
        selection = {**self.selection("summary.md"), "authority": "authoritative_original"}
        with self.assertRaisesRegex(ValueError, "explicit full"):
            build_repository_records(FIXTURES, [selection])
        selection = {**self.selection(), "status": "verified"}
        with self.assertRaisesRegex(ValueError, "upstream"):
            build_repository_records(FIXTURES, [selection])

    def test_title_and_contiguous_articles_do_not_claim_full_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rule.md"
            path.write_text("# Rule\n第一条 text\n第二条 text\n", encoding="utf-8")
            record = inspect_markdown(path)
            self.assertEqual(record["completeness"], "uncertain")
            self.assertEqual(record["authority_recommendation"], "research_note")

    def test_cross_reference_is_not_an_omitted_article_range(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rule.md"
            path.write_text("# Rule\n**说明**：逐条全文，全文2条\n第一条 text\n"
                            "第二条 根据其他办法第二十三条至第二十七条执行。\n", encoding="utf-8")
            record = inspect_markdown(path)
            self.assertEqual(record["completeness"], "explicit_full")
            self.assertEqual(record["article_range_marker_count"], 0)

    def test_claimed_full_text_with_missing_articles_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rule.md"
            path.write_text("# Rule\n**说明**：全文4条\n第一条 text\n第四条 text\n", encoding="utf-8")
            record = inspect_markdown(path)
            self.assertEqual(record["completeness"], "incomplete")
            self.assertEqual(record["missing_article_numbers"], [2, 3])

    def test_declared_dates_are_not_automatically_assigned_version_dates(self):
        record = build_repository_records(FIXTURES, [self.selection()])[0]
        self.assertIsNone(record["issued_date"])
        self.assertIsNone(record["effective_from"])
        self.assertEqual(record["provenance"]["date_declarations"][0]["iso"], "2024-01-02")

    def test_selection_rejects_hash_drift_path_escape_duplicates_and_date_typos(self):
        mutations = [
            {"sha256": "0" * 64}, {"path": "../full.md"}, {"issued_date": "2024-2-1"},
            {"source_uri": None}, {"doc_id": None}, {"source_verification": None},
            {"effective_form": "2024-02-01"},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                build_repository_records(FIXTURES, [{**self.selection(), **mutation}])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_repository_records(FIXTURES, [self.selection(), self.selection()])

    def test_repository_import_preserves_original_and_store_locators(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = build_repository_records(FIXTURES, [self.selection()])
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
            repository = CorpusRepository(root / "corpus.sqlite")
            imported = repository.import_manifest(manifest)
            repository.publish_snapshot("synthetic-research", imported["version_ids"], kind="research")
            chunks = repository.get_chunks("synthetic-research")
            self.assertTrue(chunks)
            self.assertIn("char_start", chunks[0]["locator"])
            self.assertIn("section", chunks[0]["locator"])
            original = repository.get_original(imported["version_ids"][0]).decode("utf-8")
            for chunk in chunks:
                self.assertEqual(
                    chunk["text"],
                    original[chunk["locator"]["char_start"]:chunk["locator"]["char_end"]],
                )
            self.assertEqual(repository.get_original(imported["version_ids"][0]),
                             (FIXTURES / "full.md").read_bytes())
            self.assertTrue(repository.verify_snapshot("synthetic-research")["ok"])

    def test_cli_dry_run_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selection = root / "selection.json"
            selection.write_text(json.dumps({"documents": [self.selection()]}), encoding="utf-8")
            database = root / "corpus.sqlite"
            result = subprocess.run([sys.executable, str(CLI), "--root", str(FIXTURES),
                                     "--selection", str(selection), "--db", str(database),
                                     "--kind", "research"], capture_output=True, text=True,
                                    encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"dry_run": true', result.stdout)
            self.assertFalse(database.exists())

    def test_cli_rejects_output_inside_sources(self):
        result = subprocess.run([sys.executable, str(CLI), "--root", str(FIXTURES),
                                 "--report", str(FIXTURES / "full.md")],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the source root", result.stderr)

    def test_cli_import_publishes_only_explicit_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selection = root / "selection.json"
            selection.write_text(json.dumps({"documents": [self.selection()]}), encoding="utf-8")
            database = root / "corpus.sqlite"
            manifest = root / "manifest.jsonl"
            result = subprocess.run(
                [sys.executable, str(CLI), "--root", str(FIXTURES),
                 "--selection", str(selection), "--db", str(database),
                 "--manifest-out", str(manifest), "--kind", "research",
                 "--snapshot-id", "synthetic-selection", "--import-selected"],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            repository = CorpusRepository.open_existing(database)
            self.assertEqual(len(repository.list_versions()), 1)
            self.assertEqual(repository.get_snapshot("synthetic-selection")["kind"], "research")
            self.assertTrue(repository.verify_snapshot("synthetic-selection")["ok"])

    def test_cli_cannot_publish_research_notes_as_trusted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selection = root / "selection.json"
            selection.write_text(json.dumps({"documents": [self.selection()]}), encoding="utf-8")
            database = root / "corpus.sqlite"
            result = subprocess.run(
                [sys.executable, str(CLI), "--root", str(FIXTURES),
                 "--selection", str(selection), "--db", str(database),
                 "--manifest-out", str(root / "manifest.jsonl"), "--kind", "trusted",
                 "--snapshot-id", "incorrect-trusted", "--import-selected"],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("trusted requires", result.stderr)
            self.assertFalse(database.exists())
