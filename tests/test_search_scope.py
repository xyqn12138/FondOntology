from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path

from fondontology.evaluation.artifact_audit import ArtifactAuditError
from fondontology.evaluation.search_scope import (
    SearchScopeError, check_output_path, diagnose_search_scope,
)
from tools.audit_search_scope import main


FIXTURES = Path(__file__).parent / "fixtures/search_scope"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class SearchScopeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.db = self.root / "corpus.sqlite"
        self.actual = self.root / "actual.json"
        self.trace = self.root / "actual.traces.jsonl"
        self.questions = self.root / "questions.json"
        self.output = self.root / "report.json"
        self.registry = FIXTURES / "registry.json"
        self.case = copy.deepcopy(json.loads((FIXTURES / "questions.json").read_text(
            encoding="utf-8"))["cases"][0])
        self.fixture = json.loads((FIXTURES / "corpus.json").read_text(encoding="utf-8"))
        self.snapshot = self.fixture["snapshot_id"]
        self.versions = {}
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.executescript("""
                CREATE TABLE corpus_snapshots(snapshot_id TEXT,kind TEXT,index_version TEXT,created_at TEXT,members_sha256 TEXT);
                CREATE TABLE snapshot_members(snapshot_id TEXT,version_id TEXT,document_id TEXT);
                CREATE TABLE document_versions(version_id TEXT,document_id TEXT,title TEXT,source_uri TEXT,source_path TEXT,sha256 TEXT,original_bytes BLOB,issued_date TEXT,effective_from TEXT,withdrawn_date TEXT,authority TEXT,status TEXT,provenance_json TEXT,identity_json TEXT,extractor_version TEXT);
                CREATE TABLE sections(section_id TEXT,version_id TEXT,char_start INTEGER,char_end INTEGER,text TEXT,extraction_quality TEXT);
                CREATE TABLE chunks(chunk_id TEXT,version_id TEXT,section_id TEXT,char_start INTEGER,char_end INTEGER,text TEXT,text_sha256 TEXT,locator_json TEXT);
                CREATE TABLE entity_links(chunk_id TEXT,entity_id TEXT,method TEXT,confidence REAL,review_status TEXT);
            """)
            for document in self.fixture["documents"]:
                raw = document["text"].encode()
                identity = {
                    "document": {"document_id": document["doc_id"], "title": document["title"]},
                    "source_uri": "urn:" + document["doc_id"], "sha256": digest(raw),
                    "issued_date": document["issued_date"], "effective_from": document["effective_from"],
                    "withdrawn_date": document["withdrawn_date"], "authority": "synthetic",
                    "status": "verified", "extractor_version": "utf8-markdown-v1",
                    "provenance": {"fixture": self.snapshot},
                }
                version = "version_" + digest(encoded(identity).encode())
                self.versions[document["doc_id"]] = version
                connection.execute("INSERT INTO snapshot_members VALUES(?,?,?)",
                                   (self.snapshot, version, document["doc_id"]))
                connection.execute("INSERT INTO document_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                   (version, document["doc_id"], document["title"], identity["source_uri"],
                                    "fixture.md", digest(raw), raw, document["issued_date"],
                                    document["effective_from"], document["withdrawn_date"],
                                    "synthetic", "verified", encoded(identity["provenance"]),
                                    encoded(identity), "utf8-markdown-v1"))
                lines = document["text"].splitlines(keepends=True)
                for specification in document["chunks"]:
                    line_number = specification["line"]
                    start = sum(len(line) for line in lines[:line_number])
                    text = lines[line_number].rstrip()
                    end = start + len(text)
                    chunk_id = specification["chunk_id"]
                    locator = {
                        "title": document["title"], "section": document["title"]
                        if line_number == 0 and text.startswith("#") else "article",
                        "char_start": start, "char_end": end,
                        "section_char_start": start, "section_char_end": end,
                        "content_kind": specification["content_kind"],
                    }
                    if "article_number" in specification:
                        locator["article_number"] = specification["article_number"]
                    connection.execute("INSERT INTO sections VALUES(?,?,?,?,?,?)",
                                       ("section-" + chunk_id, version, start, end, text, "synthetic"))
                    connection.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)",
                                       (chunk_id, version, "section-" + chunk_id, start, end,
                                        text, digest(text.encode()), encoded(locator)))
                    if specification["content_kind"] == "legal_article":
                        connection.execute("INSERT INTO entity_links VALUES(?,?,?,?,?)",
                                           (chunk_id, "urn:" + document["doc_id"],
                                            "synthetic", 1.0, "reviewed"))
            self.member_hash = digest(encoded(sorted(self.versions.values())).encode())
            connection.execute("INSERT INTO corpus_snapshots VALUES(?,?,?,?,?)",
                               (self.snapshot, "regression", "synthetic-v1", "2026-01-01",
                                self.member_hash))
        self.save()

    def save(self, *, eligible=None, scope_changes=None, trace_changes=None):
        date = self.case["as_of"]
        available_docs = [
            document["doc_id"] for document in self.fixture["documents"]
            if document["issued_date"] is not None and document["issued_date"] <= date
            and (document["effective_from"] is None or document["effective_from"] <= date)
            and (document["withdrawn_date"] is None or document["withdrawn_date"] > date)
        ]
        if eligible is None:
            eligible = [
                item["chunk_id"] for document in self.fixture["documents"]
                if document["doc_id"] in available_docs for item in document["chunks"]
                if item["content_kind"] == "legal_article"
            ]
        scope = {
            "status": "resolved" if eligible else "unresolved",
            "requested_doc_ids": self.case.get("doc_ids"),
            "requested_version_ids": self.case.get("version_ids"),
            "entity_iri": self.case.get("entity_iri"),
            "selected_doc_ids": sorted(available_docs),
            "selected_version_ids": sorted(self.versions[identifier] for identifier in available_docs),
            "eligible_chunk_ids": eligible, "title_mentions": [], "article_numbers": [],
            "requested_articles": [],
        }
        scope.update(scope_changes or {})
        trace = {
            "id": self.case["id"], "user_input": self.case["question"], "response": "UNRESOLVED",
            "retrieved_contexts": [], "status": "unresolved", "answer_mode": "extractive",
            "evidence": [], "warnings": ["synthetic"], "retrieval_latency_ms": 0,
            "generation_latency_ms": 0, "scope": scope, "retrieval_candidates": [],
            "corpus": {
                "snapshot_id": self.snapshot, "members_sha256": self.member_hash,
                "kind": "regression", "db_path": str(self.db),
                "version_ids": sorted(self.versions.values()), "as_of": date,
                "include_undated_research": False,
            },
            "config": {
                "doc_ids": self.case.get("doc_ids"), "version_ids": self.case.get("version_ids"),
                "entity_iri": self.case.get("entity_iri"), "allow_nontrusted": True, "top_k": 1,
            },
        }
        trace.update(trace_changes or {})
        raw_trace = (encoded(trace) + "\n").encode()
        self.trace.write_bytes(raw_trace)
        payload = {
            "schema_version": "1.0",
            "provenance": {
                "dataset_snapshot": self.snapshot, "corpus_version": self.member_hash,
                "ontology_version": "none", "code_version": "synthetic",
                "retrieval_config": {"as_of": date, "allow_nontrusted": True},
                "llm": {"provider": "none", "model": "none", "prompt_version": "none",
                        "used_llm": False},
                "execution_origin": "recorded_unverified",
                "trace_path": self.trace.name, "trace_sha256": digest(raw_trace),
            },
            "rows": [{name: trace[name] for name in
                      ("id", "user_input", "response", "retrieved_contexts")}],
        }
        self.actual.write_text(encoded(payload), encoding="utf-8")
        self.questions.write_text(encoded({"schema_version": "1.0", "cases": [self.case]}),
                                  encoding="utf-8")

    def diagnose(self, require=True):
        return diagnose_search_scope(
            self.questions, self.registry, actual_path=self.actual, corpus_db=self.db,
            require_unscoped=require)

    def cli(self, *extra):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return main(["--questions", str(self.questions), "--registry", str(self.registry),
                         "--output", str(self.output), *extra])

    def test_static_cues_and_business_date_are_distinct(self):
        report = diagnose_search_scope(FIXTURES / "questions.json", self.registry,
                                       require_unscoped=True)
        rows = {row["id"]: row for row in report["cases"]}
        self.assertFalse(rows["natural"]["input_cues"]["has_source_cues"])
        self.assertFalse(rows["natural"]["violations"])
        for identifier in ("ordinary-rules", "company-rules"):
            with self.subTest(identifier=identifier):
                self.assertFalse(rows[identifier]["input_cues"]["has_source_cues"])
                self.assertFalse(rows[identifier]["violations"])
        for identifier in (
                "book", "bare", "bare-law", "unknown-name", "article", "version",
                "iso-version", "revision", "empty",
                "entity", "document", "version-scope", "metadata-case"):
            with self.subTest(identifier=identifier):
                self.assertTrue(rows[identifier]["violations"])
        self.assertEqual(rows["empty"]["input_cues"]["scope_fields"], {"doc_ids": []})
        self.assertTrue(rows["bare"]["input_cues"]["registered_title_mentions"])
        self.assertEqual(rows["version"]["input_cues"]["version_mentions"],
                         ["2020年3月20日修订版本"])
        self.assertTrue(report["heuristic_limitations"])
        self.assertFalse(report["execution_checked"])
        ordinary = diagnose_search_scope(FIXTURES / "questions.json", self.registry)
        self.assertTrue(ordinary["passed"])
        self.assertGreater(ordinary["cue_case_count"], 0)

    def test_unhinted_run_searches_all_available_body_and_counts_articles(self):
        before = self.db.read_bytes()
        report = self.diagnose()
        self.assertTrue(report["passed"])
        self.assertEqual(self.db.read_bytes(), before)
        execution = report["cases"][0]["execution"]
        self.assertEqual(execution["candidate_searchable_doc_ids"], ["alpha", "beta"])
        self.assertEqual(execution["candidate_searchable_document_count"], 2)
        self.assertEqual(execution["eligible_chunk_count"], 3)
        self.assertEqual(execution["available_body_chunk_count"], 3)
        self.assertEqual(execution["snapshot_full_article_count"], 5)
        self.assertEqual(execution["available_full_article_count"], 3)
        self.assertEqual(execution["searchable_full_article_count"], 3)
        self.assertEqual(report["audit"]["execution_origin"], "recorded_unverified")
        self.assertIn("real execution certification", report["claims_not_established"])

    def test_preselection_and_underreported_eligible_counts_fail(self):
        self.save(eligible=["alpha-1", "alpha-2"], scope_changes={
            "selected_doc_ids": ["alpha"], "selected_version_ids": [self.versions["alpha"]]})
        report = self.diagnose()
        self.assertFalse(report["passed"])
        self.assertEqual(report["cases"][0]["execution"]["missing_available_chunk_ids"], ["beta-1"])
        self.save(scope_changes={"eligible_chunk_count": 1})
        report = self.diagnose()
        self.assertIn("declared_eligible_chunk_count_disagrees", report["cases"][0]["violations"])
        self.assertEqual(report["cases"][0]["execution"]["eligible_chunk_count"], 3)

    def test_runtime_title_and_direct_article_bypass_fail_even_with_full_eligible_set(self):
        self.save(scope_changes={"title_mentions": ["基金运作管理办法"]})
        self.assertIn("runtime_title_scope_present", self.diagnose()["cases"][0]["violations"])
        self.save(scope_changes={"article_numbers": [1]})
        self.assertIn("direct_article_bypass_present", self.diagnose()["cases"][0]["violations"])

    def test_entity_and_empty_scopes_are_reported_without_being_global(self):
        self.case["entity_iri"] = "urn:alpha"
        self.save(eligible=["alpha-1", "alpha-2"])
        self.assertTrue(self.diagnose(False)["passed"])
        self.assertFalse(self.diagnose()["passed"])
        self.assertEqual(self.diagnose(False)["cases"][0]["execution"][
            "candidate_searchable_document_count"], 1)
        self.case.pop("entity_iri")
        self.case["doc_ids"] = []
        self.save(eligible=[], scope_changes={"selected_doc_ids": [], "selected_version_ids": []})
        self.assertTrue(self.diagnose(False)["passed"])
        self.assertFalse(self.diagnose()["passed"])
        self.assertEqual(self.diagnose(False)["cases"][0]["execution"]["eligible_chunk_count"], 0)

    def test_legal_dates_and_metadata_boundaries(self):
        for date, expected in (
                ("2019-12-31", 0), ("2020-01-01", 0), ("2020-02-01", 2),
                ("2020-03-01", 2), ("2020-04-01", 3), ("2026-11-01", 2),
                ("2027-02-01", 3)):
            with self.subTest(date=date):
                self.case["as_of"] = date
                self.save()
                report = self.diagnose()
                self.assertTrue(report["passed"])
                self.assertEqual(report["cases"][0]["execution"]["eligible_chunk_count"], expected)
        self.case["as_of"] = "2026-10-13"
        for identifier in ("alpha-metadata", "beta-heading"):
            with self.subTest(identifier=identifier):
                self.save(eligible=["alpha-1", "alpha-2", "beta-1", identifier])
                self.assertIn("eligible_set_contains_metadata_or_date_ineligible_chunks",
                              self.diagnose()["cases"][0]["violations"])

    def test_unretrieved_body_corruption_is_contract_error(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE chunks SET text='changed' WHERE chunk_id='beta-1'")
        with self.assertRaises(SearchScopeError):
            self.diagnose()

    def test_full_text_article_count_does_not_claim_missing_chunks_searchable(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("DELETE FROM chunks WHERE chunk_id='beta-1'")
        self.save(eligible=["alpha-1", "alpha-2"])
        report = self.diagnose()
        self.assertTrue(report["passed"])
        execution = report["cases"][0]["execution"]
        self.assertEqual(execution["available_full_article_count"], 3)
        self.assertEqual(execution["searchable_full_article_count"], 2)
        self.assertEqual(execution["available_body_chunk_count"], 2)

    def test_actual_binding_is_audited_with_questions(self):
        self.trace.write_bytes(self.trace.read_bytes() + b"\n")
        with self.assertRaises(ArtifactAuditError):
            self.diagnose()
        self.save()
        self.case["question"] += " changed"
        self.questions.write_text(encoded({"schema_version": "1.0", "cases": [self.case]}),
                                  encoding="utf-8")
        with self.assertRaises(ArtifactAuditError):
            self.diagnose()

    def test_cli_exit_codes_and_pair_contract(self):
        self.assertEqual(self.cli("--require-unscoped"), 0)
        self.assertEqual(self.cli("--actual", str(self.actual)), 2)
        self.save(eligible=["alpha-1"])
        self.assertEqual(self.cli("--actual", str(self.actual), "--corpus-db", str(self.db),
                                  "--require-unscoped"), 1)
        self.trace.write_bytes(b"broken")
        self.assertEqual(self.cli("--actual", str(self.actual), "--corpus-db", str(self.db)), 2)

    def test_output_protects_all_inputs_relative_trace_and_hardlinks(self):
        inputs = [self.questions, self.registry, self.actual, self.db]
        for source in inputs + [self.trace]:
            with self.subTest(source=source):
                before = source.read_bytes()
                with self.assertRaises(SearchScopeError):
                    check_output_path(source, inputs, self.actual)
                self.assertEqual(source.read_bytes(), before)
        alias = self.root / "alias.json"
        os.link(self.trace, alias)
        with self.assertRaises(SearchScopeError):
            check_output_path(alias, inputs, self.actual)
        for source in inputs + [self.trace]:
            self.output = source
            self.assertEqual(self.cli("--actual", str(self.actual), "--corpus-db", str(self.db)), 2)


if __name__ == "__main__":
    unittest.main()
