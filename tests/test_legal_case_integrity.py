from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from fondontology.corpus.legal_text import extract_official_html, legal_article_sections
from fondontology.evaluation.legal_retrieval import load_oracle, load_questions
from fondontology.evaluation.ragas_runner import merge_references


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evaluation/cases"
LEDGER_PATH = CASES / "official_laws_revision_r1.json"
FILE_KINDS = ("questions", "oracle", "references")
ROW_KEYS = {"questions": "cases", "oracle": "rows", "references": "rows"}
EDITABLE_FIELDS = {"questions": "question", "oracle": "source_notes", "references": "reference"}
QUESTION_FIELDS = {"id", "question", "as_of", "doc_ids", "version_ids"}
REVIEWER = {"model": "gpt-6-astra", "effort": "high"}


def read_json(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_path(prefix, kind):
    return CASES / f"{prefix}_{kind}.json"


def article_key(article):
    return article["doc_id"], article["article_number"]


class LegalCaseIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = read_json(LEDGER_PATH)
        cls.sets = cls.ledger["sets"]
        cls.sources = read_json(ROOT / "evaluation/corpora/official-laws-v1.sources.json")["sources"]

    def official_articles(self):
        missing = [
            source["doc_id"] for source in self.sources
            if not (ROOT / "data/official-laws-v1" / f"{source['doc_id']}.html").is_file()
        ]
        if missing:
            self.skipTest(f"Local official HTML integration fixtures unavailable: {', '.join(missing)}")
        articles = {}
        for source in self.sources:
            raw = (ROOT / "data/official-laws-v1" / f"{source['doc_id']}.html").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), source["raw_sha256"])
            text = extract_official_html(raw, source["extraction"])["text"]
            articles[source["doc_id"]] = legal_article_sections(
                text, expected_articles=source["expected_articles"])
        return articles

    def iter_pairs(self):
        for entry in self.sets:
            for kind in FILE_KINDS:
                yield entry, kind, read_json(content_path(entry["parent_set"], kind)), read_json(
                    content_path(entry["revision_set"], kind))

    def test_parent_freezes_and_ledger_hash_bindings(self):
        for entry in self.sets:
            with self.subTest(parent=entry["parent_set"]):
                freeze_path = content_path(entry["parent_set"], "freeze")
                self.assertEqual(sha256(freeze_path), entry["parent_freeze_sha256"])
                freeze = read_json(freeze_path)
                self.assertEqual(freeze["files"], entry["parent_files_sha256"])
                for name, digest in freeze["files"].items():
                    self.assertEqual(sha256(CASES / name), digest, name)
                for name, digest in entry["revision_files_sha256"].items():
                    self.assertEqual(sha256(CASES / name), digest, name)

    def test_revision_freezes_bind_content_parent_ledger_and_snapshot(self):
        for entry in self.sets:
            with self.subTest(revision=entry["revision_set"]):
                freeze = read_json(content_path(entry["revision_set"], "freeze"))
                expected_names = {
                    f"{entry['revision_set']}_{kind}.json" for kind in FILE_KINDS
                } | {f"{entry['revision_set']}_README.md"}
                self.assertEqual(set(freeze["files"]), expected_names)
                self.assertEqual(freeze["files"], entry["revision_files_sha256"])
                for name, digest in freeze["files"].items():
                    self.assertEqual(sha256(CASES / name), digest, name)
                self.assertEqual(freeze["revision_record_sha256"], sha256(LEDGER_PATH))
                self.assertEqual(freeze["parent_freeze_sha256"], entry["parent_freeze_sha256"])
                self.assertEqual(freeze["dataset_snapshot"], self.ledger["dataset_snapshot"])
                self.assertEqual(freeze["parent_set"], entry["parent_set"])
                self.assertEqual(freeze["revision_id"], entry["revision_set"])
                self.assertEqual(freeze["ai_reviewed_by"], REVIEWER)
                self.assertFalse(freeze["independent_human_review"])
                self.assertTrue(freeze["exposed_regression"])
                self.assertEqual(freeze["review_status"], "draft")
                self.assertEqual(freeze["domain_review"]["result"], "approved_for_draft_freeze")
                report_path = CASES / freeze["domain_review"]["report"]
                self.assertTrue(report_path.is_file())
                self.assertEqual(freeze["domain_review"]["approved_content_sha256"], freeze["files"])
                self.assertEqual(freeze["source_raw_sha256"], {
                    source["doc_id"]: source["raw_sha256"] for source in self.sources})

    def test_ids_are_unique_ordered_and_aligned(self):
        for entry in self.sets:
            parent_ids = None
            for prefix in (entry["parent_set"], entry["revision_set"]):
                for kind in FILE_KINDS:
                    payload = read_json(content_path(prefix, kind))
                    ids = [row["id"] for row in payload[ROW_KEYS[kind]]]
                    self.assertEqual(len(ids), entry["case_count"])
                    self.assertEqual(len(set(ids)), len(ids))
                    if parent_ids is None:
                        parent_ids = ids
                    self.assertEqual(ids, parent_ids, (prefix, kind))

    def test_only_recorded_text_fields_change_and_gold_remains_equal(self):
        for entry, kind, before, after in self.iter_pairs():
            for old_row, new_row in zip(before[ROW_KEYS[kind]], after[ROW_KEYS[kind]]):
                with self.subTest(prefix=entry["revision_set"], kind=kind, case=old_row["id"]):
                    self.assertEqual(set(old_row), set(new_row))
                    self.assertEqual(
                        {key: value for key, value in old_row.items() if key != EDITABLE_FIELDS[kind]},
                        {key: value for key, value in new_row.items() if key != EDITABLE_FIELDS[kind]})
                    if kind == "questions":
                        self.assertLessEqual(set(new_row), QUESTION_FIELDS)
                    if kind == "references":
                        self.assertEqual(new_row["review_status"], "draft")
                    if kind == "oracle":
                        for field in self.ledger["unchanged_gold_fields"]:
                            self.assertEqual(old_row[field], new_row[field])

    def test_top_level_metadata_and_readme_provenance_are_explicit(self):
        self.assertEqual(self.ledger["dataset_snapshot"], "official-laws-v1")
        self.assertEqual(self.ledger["ai_reviewed_by"], REVIEWER)
        self.assertFalse(self.ledger["independent_human_review"])
        self.assertTrue(self.ledger["exposed_regression"])
        self.assertTrue(self.ledger["created_without_actuals"])
        self.assertFalse(self.ledger["tested_system_invoked"])
        self.assertEqual(self.ledger["review_status"], "draft")
        for entry, kind, before, after in self.iter_pairs():
            added = self.ledger["non_row_changes"][kind]["added_top_level_fields"]
            self.assertEqual(set(after), set(before) | set(added))
            for key in before:
                if key != ROW_KEYS[kind]:
                    self.assertEqual(before[key], after[key])
        for entry in self.sets:
            old_readme = (CASES / f"{entry['parent_set']}_README.md").read_text(encoding="utf-8")
            new_readme = (CASES / f"{entry['revision_set']}_README.md").read_text(encoding="utf-8")
            self.assertTrue(new_readme.endswith(old_readme.split("\n", 1)[1].lstrip("\n")))
            self.assertNotEqual(new_readme, old_readme)
            self.assertIn(entry["revision_set"], new_readme)
            self.assertIn(LEDGER_PATH.name, new_readme)
            for declaration in ("independent_human_review=false", "exposed_regression=true", "draft"):
                self.assertIn(declaration, new_readme)

    def test_content_passes_existing_loaders_and_reference_merge(self):
        for entry in self.sets:
            for prefix in (entry["parent_set"], entry["revision_set"]):
                with self.subTest(prefix=prefix):
                    questions = load_questions(content_path(prefix, "questions"))
                    authorship, oracle = load_oracle(content_path(prefix, "oracle"))
                    merged, review = merge_references(
                        [{"id": question["id"]} for question in questions],
                        content_path(prefix, "references"))
                    self.assertEqual([row["id"] for row in questions], [row["id"] for row in oracle])
                    self.assertEqual([row["id"] for row in merged], [row["id"] for row in questions])
                    self.assertEqual(authorship["review_status"], "draft")
                    self.assertEqual(set(review.values()), {"draft"})
                    self.assertTrue(all(row.get("reference") for row in merged))

    def test_target_groups_scope_and_official_articles(self):
        available = {
            (source["doc_id"], number)
            for source in self.sources for number in range(1, source["expected_articles"] + 1)
        }
        for entry in self.sets:
            for prefix in (entry["parent_set"], entry["revision_set"]):
                questions = {row["id"]: row for row in read_json(content_path(prefix, "questions"))["cases"]}
                for row in read_json(content_path(prefix, "oracle"))["rows"]:
                    with self.subTest(prefix=prefix, case=row["id"]):
                        targets = {article_key(article) for article in row["target_articles"]}
                        grouped = {
                            article_key(article) for group in row["required_groups"] for article in group
                        }
                        self.assertEqual(targets, grouped)
                        self.assertEqual(len(targets), len(row["target_articles"]))
                        self.assertLessEqual(targets, available)
                        self.assertLessEqual({doc_id for doc_id, _ in targets}, set(row["allowed_doc_ids"]))
                        if "doc_ids" in questions[row["id"]]:
                            self.assertEqual(questions[row["id"]]["doc_ids"], row["allowed_doc_ids"])
                        if row["expected_status"] == "unresolved":
                            self.assertEqual(row["target_articles"], [])
                            self.assertEqual(row["required_groups"], [])
                        else:
                            self.assertTrue(targets)
                            self.assertTrue(all(row["required_groups"]))

    def test_source_snapshot_hashes_counts_and_revision_evidence_exist(self):
        articles = self.official_articles()
        for source in self.sources:
            raw_path = ROOT / "data/official-laws-v1" / f"{source['doc_id']}.html"
            self.assertEqual(sha256(raw_path), source["raw_sha256"])
            sections = articles[source["doc_id"]]
            self.assertEqual(len(sections), source["expected_articles"])
            self.assertEqual(
                [section["article_number"] for section in sections],
                list(range(1, source["expected_articles"] + 1)))
            self.assertTrue(all(section["heading"] and section["chapter"] for section in sections))
        available = {
            (doc_id, section["article_number"])
            for doc_id, sections in articles.items() for section in sections
        }
        for issue in self.ledger["issues"]:
            self.assertTrue(issue["source_articles"])
            self.assertLessEqual({article_key(article) for article in issue["source_articles"]}, available)
            self.assertTrue(issue["necessity"])
            self.assertFalse(issue["gold_targets_changed"])

    def test_ledger_exactly_matches_all_real_row_changes(self):
        recorded = {}
        issue_ids = set()
        known_sets = {entry["parent_set"] for entry in self.sets}
        for issue in self.ledger["issues"]:
            self.assertNotIn(issue["issue_id"], issue_ids)
            issue_ids.add(issue["issue_id"])
            self.assertIn(issue["parent_set"], known_sets)
            self.assertEqual(issue["severity"], "P1")
            self.assertTrue(issue["changes"])
            revision_entry = next(entry for entry in self.sets if entry["parent_set"] == issue["parent_set"])
            readme = (CASES / f"{revision_entry['revision_set']}_README.md").read_text(encoding="utf-8")
            self.assertIn(issue["issue_id"], readme)
            for change in issue["changes"]:
                key = issue["parent_set"], change["file_kind"], issue["case_id"], change["field"]
                self.assertNotIn(key, recorded)
                self.assertEqual(change["field"], EDITABLE_FIELDS[change["file_kind"]])
                self.assertNotEqual(change["before"], change["after"])
                recorded[key] = change["before"], change["after"]
        actual = {}
        for entry, kind, before, after in self.iter_pairs():
            for old_row, new_row in zip(before[ROW_KEYS[kind]], after[ROW_KEYS[kind]]):
                for field in old_row:
                    if old_row[field] != new_row[field]:
                        key = entry["parent_set"], kind, old_row["id"], field
                        actual[key] = old_row[field], new_row[field]
        self.assertEqual(recorded, actual)


if __name__ == "__main__":
    unittest.main()
