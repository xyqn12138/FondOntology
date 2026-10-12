"""Offline corpus contracts using external, explicitly synthetic fixtures."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fondontology.corpus import CorpusError, CorpusRepository


FIXTURES = Path(__file__).parent / "fixtures" / "corpus"
CLI = Path(__file__).resolve().parents[1] / "tools" / "corpus_cli.py"


class CorpusStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.db_path = self.root / "corpus.sqlite"
        self.repository = CorpusRepository(self.db_path)
        self.record = json.loads((FIXTURES / "manifest-template.json").read_text(encoding="utf-8"))
        for filename in ("synthetic-report-v1.md", "synthetic-report-v2.md"):
            (self.root / filename).write_bytes((FIXTURES / filename).read_bytes())
        self.record["sha256"] = self.checksum(self.root / self.record["path"])

    @staticmethod
    def checksum(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def manifest(self, *records):
        path = self.root / "manifest.jsonl"
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        return path

    def import_record(self, record=None):
        result = self.repository.import_manifest(self.manifest(record or self.record))
        return result["version_ids"][0]

    def publish(self, snapshot_id="regression-v1", record=None):
        version_id = self.import_record(record)
        self.repository.publish_snapshot(snapshot_id, [version_id], kind="regression")
        return version_id

    def test_import_restart_original_locator_and_entity_links(self):
        version_id = self.publish()
        self.root.joinpath(self.record["path"]).unlink()
        reopened = CorpusRepository.open_existing(self.db_path)
        chunks = reopened.get_chunks("regression-v1")
        self.assertGreater(len(chunks), 2)
        self.assertEqual({chunk["doc_id"] for chunk in chunks}, {self.record["doc_id"]})
        original = reopened.get_original(version_id)
        self.assertEqual(hashlib.sha256(original).hexdigest(), self.record["sha256"])
        for chunk in chunks:
            self.assertEqual(chunk["authority"], "synthetic")
            self.assertEqual(chunk["version_id"], version_id)
            locator = chunk["locator"]
            self.assertEqual(locator["source_uri"], self.record["source_uri"])
            self.assertEqual(locator["sha256"], self.record["sha256"])
            self.assertEqual(chunk["text"],
                             original.decode("utf-8")[locator["char_start"]:locator["char_end"]])
            self.assertEqual(chunk["entity_links"], self.record["entity_links"])
        self.assertTrue(reopened.verify_snapshot("regression-v1")["ok"])

    def test_same_input_is_idempotent_and_path_independent(self):
        version_id = self.import_record()
        duplicate = self.repository.import_manifest(self.manifest(self.record))
        self.assertEqual(duplicate["inserted"], 0)
        self.assertEqual(duplicate["reused"], 1)
        self.assertEqual(duplicate["version_ids"], [version_id])
        self.root.joinpath("copy.md").write_bytes(self.root.joinpath(self.record["path"]).read_bytes())
        moved = {**self.record, "path": "copy.md"}
        self.assertEqual(self.import_record(moved), version_id)
        self.assertEqual(len(self.repository.list_versions()), 1)

    def test_version_switch_date_filter_and_title_change(self):
        old_version = self.publish()
        revised = copy.deepcopy(self.record)
        revised.update({
            "title": "Revised synthetic report title",
            "path": "synthetic-report-v2.md",
            "source_uri": "urn:synthetic:fixture-fund-a:report:v2",
            "sha256": self.checksum(self.root / "synthetic-report-v2.md"),
            "issued_date": "2026-04-01", "effective_from": "2026-04-01",
            "withdrawn_date": None, "supersedes": old_version, "period": "2026",
        })
        new_version = self.publish("regression-v2", revised)
        self.assertNotEqual(old_version, new_version)
        new_chunks = self.repository.get_chunks("regression-v2", as_of="2026-05-01")
        self.assertEqual({chunk["version_id"] for chunk in new_chunks}, {new_version})
        self.assertEqual({chunk["title"] for chunk in new_chunks}, {revised["title"]})
        self.assertEqual({chunk["period"] for chunk in new_chunks}, {"2026"})
        self.assertEqual(self.repository.get_chunks("regression-v2", as_of="2025-05-01"), [])
        self.assertEqual(self.repository.get_chunks("regression-v1", as_of="2026-04-01"), [])
        self.assertTrue(self.repository.get_chunks("regression-v1", as_of="2025-05-01"))
        self.assertTrue(self.repository.verify_snapshot("regression-v1")["ok"])

    def test_failed_batch_rolls_back_and_keeps_published_snapshot(self):
        self.publish()
        first = {**self.record, "doc_id": "synthetic:new-doc"}
        invalid = {**self.record, "doc_id": "synthetic:bad-doc", "sha256": "0" * 64}
        with self.assertRaisesRegex(CorpusError, "line 2.*sha256"):
            self.repository.import_manifest(self.manifest(first, invalid))
        self.assertEqual(len(self.repository.list_versions()), 1)
        self.assertTrue(self.repository.get_chunks("regression-v1"))
        connection = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)
            run = connection.execute(
                "SELECT status, inserted_count FROM ingestion_runs ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(run, ("failed", 0))
        finally:
            connection.close()

    def test_publish_is_atomic_idempotent_and_kind_guarded(self):
        version_id = self.import_record()
        with self.assertRaises(CorpusError):
            self.repository.publish_snapshot("bad", [version_id, "missing"], kind="regression")
        self.assertEqual(self.repository.list_snapshots(), [])
        with self.assertRaises(CorpusError):
            self.repository.publish_snapshot("bad-trusted", [version_id])
        published = self.repository.publish_snapshot("regression", [version_id], kind="regression")
        self.assertEqual(published, self.repository.publish_snapshot(
            "regression", [version_id], kind="regression"))
        modified = {**self.record, "title": "new synthetic version"}
        other_version = self.import_record(modified)
        with self.assertRaises(CorpusError):
            self.repository.publish_snapshot("regression", [other_version], kind="regression")
        with self.assertRaises(CorpusError):
            self.repository.publish_snapshot("two-versions", [version_id, other_version], kind="regression")
        quarantined = {**self.record, "doc_id": "synthetic:quarantined", "status": "quarantined"}
        quarantined_version = self.import_record(quarantined)
        with self.assertRaises(CorpusError):
            self.repository.publish_snapshot("quarantined", [quarantined_version], kind="regression")

    def test_input_validation_utf8_hash_dates_fields_and_empty(self):
        mutations = [
            {"sha256": "wrong"}, {"effective_from": "2026-99-01"},
            {"effective_form": "2025-01-01"}, {"withdrawn_date": "2025-01-01"},
            {"chunker_config": {"max_chars": 4, "overlap": 4}},
            {"supersedes": "missing"}, {"authority": "official"},
            {"provenance": {}}, {"entity_links": [{"entity_id": "x", "confidence": 9}]},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(CorpusError):
                self.import_record({**self.record, **mutation})
        invalid_path = self.root / "invalid.txt"
        invalid_path.write_bytes(b"\xff")
        with self.assertRaises(CorpusError):
            self.import_record({**self.record, "path": invalid_path.name,
                                "sha256": self.checksum(invalid_path)})
        empty = self.root / "empty.txt"
        empty.write_bytes(b" \n")
        with self.assertRaises(CorpusError):
            self.import_record({**self.record, "path": empty.name, "sha256": self.checksum(empty)})
        self.assertEqual(self.repository.list_versions(), [])

    def test_chunk_identity_depends_on_document_and_config_not_only_text(self):
        first = self.publish("first")
        other = {**self.record, "doc_id": "synthetic:other"}
        second = self.publish("second", other)
        changed = {**self.record, "chunker_config": {"max_chars": 80, "overlap": 0}}
        third = self.publish("third", changed)
        self.assertEqual(len({first, second, third}), 3)
        identifiers = [
            {chunk["chunk_id"] for chunk in self.repository.get_chunks(snapshot_id)}
            for snapshot_id in ("first", "second", "third")
        ]
        self.assertFalse(identifiers[0] & identifiers[1])
        self.assertFalse(identifiers[0] & identifiers[2])

    def test_date_filter_uses_issue_date_without_inventing_effective_date(self):
        record = {**self.record, "effective_from": None, "withdrawn_date": None}
        self.publish(record=record)
        self.assertEqual(self.repository.get_chunks("regression-v1", as_of="2025-03-31"), [])
        self.assertTrue(self.repository.get_chunks("regression-v1", as_of="2025-04-01"))
        with self.assertRaises(CorpusError):
            self.repository.get_chunks("regression-v1", as_of="20250401")
        with self.assertRaises(CorpusError):
            self.repository.get_chunks("missing")

    def test_immutable_records_and_missing_existing_database(self):
        self.publish()
        connection = sqlite3.connect(self.db_path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE chunks SET text='changed'")
        finally:
            connection.close()
        missing = self.root / "typo.sqlite"
        with self.assertRaises(CorpusError):
            CorpusRepository.open_existing(missing)
        self.assertFalse(missing.exists())
        empty = self.root / "empty.sqlite"
        empty.touch()
        with self.assertRaises(CorpusError):
            CorpusRepository.open_existing(empty)

    def test_cli_init_import_publish_list_verify_and_missing_path(self):
        database = self.root / "cli.sqlite"
        def run(*arguments):
            result = subprocess.run(
                [sys.executable, str(CLI), "--db", str(database), *arguments],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertTrue(run("init")["initialized"])
        imported = run("import", str(self.manifest(self.record)))
        run("publish", "cli-regression", *imported["version_ids"], "--kind", "regression")
        self.assertEqual(len(run("list")), 1)
        self.assertEqual(len(run("list", "--versions")), 1)
        self.assertTrue(run("verify", "cli-regression")["ok"])
        missing = self.root / "missing.sqlite"
        result = subprocess.run(
            [sys.executable, str(CLI), "--db", str(missing), "list"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
