from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.qa.engine import QaAnswer, answer_question
from fondontology.qa.rag.answer import _document_evidence
from fondontology.qa.rag.store import load_corpus_store
from tools.qa_cli import main


class ResearchDateScopeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "corpus.sqlite"
        self.repository = CorpusRepository(self.database)
        source = self.root / "research.md"
        source.write_text("Research evidence with unknown publication date.", encoding="utf-8")
        record = {
            "doc_id": "research-date-fixture", "title": "Research date fixture",
            "doc_type": "educational_reference", "path": "research.md",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_uri": "urn:synthetic:research-date-fixture",
            "authority": "research_note", "status": "verified", "issued_date": None,
            "provenance": {"fixture": "synthetic date-policy contract"},
            "locator": {"section": "document"},
        }
        manifest = self.root / "manifest.jsonl"
        manifest.write_text(json.dumps(record) + "\n", encoding="utf-8")
        versions = self.repository.import_manifest(manifest)["version_ids"]
        self.repository.publish_snapshot("research", versions, kind="research")

    def test_unknown_dates_require_explicit_research_opt_in(self):
        strict = load_corpus_store(self.database, "research", as_of="2026-10-12",
                                   allow_nontrusted=True)
        self.assertEqual(strict.chunks, [])
        allowed = load_corpus_store(
            self.database, "research", as_of="2026-10-12", allow_nontrusted=True,
            include_undated_research=True)
        self.assertTrue(allowed.chunks)
        self.assertTrue(allowed.corpus_metadata["include_undated_research"])
        self.assertIsNone(_document_evidence(1, allowed.chunks[0])["issued_date"])
        with self.assertRaises(CorpusError):
            load_corpus_store(self.database, "research", as_of="2026-10-12",
                              include_undated_research=True)
        with self.assertRaises(CorpusError):
            load_corpus_store(self.database, "research", as_of="2026-10-12",
                              allow_nontrusted=True, include_undated_research="yes")

    def test_cli_opt_in_requires_nontrusted_and_corpus_arguments(self):
        for arguments in (
            ["--include-undated-research", "question"],
            ["--include-undated-research", "--corpus-db", str(self.database),
             "--corpus-snapshot", "research", "--as-of", "2026-10-12", "question"],
        ):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()):
                with patch("tools.qa_cli.build_stack") as build:
                    with self.assertRaises(SystemExit):
                        main(arguments)
                    build.assert_not_called()

    def test_library_answer_discloses_unknown_date_scope(self):
        store = load_corpus_store(
            self.database, "research", as_of="2026-10-12", allow_nontrusted=True,
            include_undated_research=True)
        with patch("fondontology.qa.engine._answer_question_impl", return_value=QaAnswer(
                kind="explain", status="ok", text="fixture", report={})):
            result = answer_question("fixture", None, use_llm=False, rag_store=store)
        self.assertIn("不证明历史可用性或现行法律效力", result.text)
        self.assertTrue(result.report["meta"]["corpus"]["include_undated_research"])


if __name__ == "__main__":
    unittest.main()
