from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fondontology.evaluation.artifact_audit import ArtifactAuditError, _html_text, audit_artifact, read_only_connection
from fondontology.evaluation.legal_retrieval import load_oracle, load_questions, score_retrieval


FIXTURES = Path(__file__).parent / "fixtures/legal_retrieval"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value).hexdigest()


class ArtifactAuditTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.db = self.root / "corpus.sqlite"
        self.actual = self.root / "actual.json"
        self.trace = self.root / "actual.traces.jsonl"
        self.questions = load_questions(FIXTURES / "questions.json")
        self.authorship, self.oracle = load_oracle(FIXTURES / "oracle.json")
        original = "第1条 Synthetic article has no ceiling.\n第2条 Synthetic ceiling is seventeen.\n".encode("utf-8")
        original_sha = digest(original)
        identity = {
            "fixture": "S0", "document": {"document_id": "synthetic-law"},
            "source_uri": "urn:synthetic", "sha256": original_sha, "issued_date": "2025-01-01",
            "effective_from": "2025-01-01", "withdrawn_date": None,
            "authority": "synthetic", "status": "verified", "extractor_version": "utf8-markdown-v1",
            "provenance": {"fixture": "S0"},
        }
        version_id = "version_" + digest(encoded(identity).encode())
        self.version_id = version_id
        self.member_sha = digest(encoded([version_id]).encode())
        self.evidence = []
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.executescript("""
                CREATE TABLE corpus_snapshots(snapshot_id TEXT,kind TEXT,index_version TEXT,created_at TEXT,members_sha256 TEXT);
                CREATE TABLE snapshot_members(snapshot_id TEXT,version_id TEXT,document_id TEXT);
                CREATE TABLE document_versions(version_id TEXT,document_id TEXT,title TEXT,source_uri TEXT,source_path TEXT,sha256 TEXT,original_bytes BLOB,issued_date TEXT,effective_from TEXT,withdrawn_date TEXT,authority TEXT,status TEXT,provenance_json TEXT,identity_json TEXT,extractor_version TEXT);
                CREATE TABLE sections(section_id TEXT,version_id TEXT,char_start INTEGER,char_end INTEGER,text TEXT,extraction_quality TEXT);
                CREATE TABLE chunks(chunk_id TEXT,version_id TEXT,section_id TEXT,char_start INTEGER,char_end INTEGER,text TEXT,text_sha256 TEXT,locator_json TEXT);
                CREATE TABLE entity_links(chunk_id TEXT,entity_id TEXT,method TEXT,confidence REAL,review_status TEXT);
            """)
            connection.execute("INSERT INTO corpus_snapshots VALUES(?,?,?,?,?)",
                               ("S0", "regression", "synthetic-v1", "2026-01-01", self.member_sha))
            connection.execute("INSERT INTO snapshot_members VALUES(?,?,?)", ("S0", version_id, "synthetic-law"))
            connection.execute("INSERT INTO document_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                               (version_id, "synthetic-law", "Synthetic Law", "urn:synthetic",
                                "fixture.md", original_sha, original, "2025-01-01", "2025-01-01",
                                None, "synthetic", "verified", encoded({"fixture": "S0"}),
                                encoded(identity), "utf8-markdown-v1"))
            start = 0
            for article_number, line in enumerate(original.decode().splitlines(keepends=True), 1):
                end = start + len(line.rstrip())
                line_text = line.rstrip()
                chunk_id = f"synthetic-chunk-{article_number}"
                locator = {
                    "kind": "markdown", "char_start": start, "char_end": end,
                    "section_char_start": start, "section_char_end": end,
                    "article_number": article_number, "content_kind": "legal_article",
                }
                connection.execute("INSERT INTO sections VALUES(?,?,?,?,?,?)",
                                   (f"section-{article_number}", version_id, start, end, line_text, "synthetic"))
                connection.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)",
                                   (chunk_id, version_id, f"section-{article_number}", start, end,
                                    line_text, digest(line_text.encode()), encoded(locator)))
                locator.update({"source_uri": "urn:synthetic", "source_path": "fixture.md",
                                "sha256": original_sha, "version_id": version_id,
                                "original_storage": "sqlite:document_versions.original_bytes"})
                self.evidence.append({
                    "evidence_id": f"R{article_number}", "chunk_id": chunk_id,
                    "doc_id": "synthetic-law", "version_id": version_id, "text": line_text,
                    "locator": locator, "sha256": original_sha, "authority": "synthetic",
                    "status": "verified", "provenance": {"fixture": "S0"}, "entity_links": [],
                    "issued_date": "2025-01-01", "effective_from": "2025-01-01",
                    "withdrawn_date": None, "extraction_quality": "synthetic",
                })
                start += len(line)
        self.traces = []
        for question in self.questions:
            evidence = copy.deepcopy(self.evidence) if question["id"] == "synthetic-1" else []
            self.traces.append({
                "id": question["id"], "user_input": question["question"],
                "response": "".join(item["text"] for item in evidence) if evidence else "UNRESOLVED",
                "retrieved_contexts": [item["text"] for item in evidence],
                "status": "retrieved" if evidence else "unresolved", "answer_mode": "extractive",
                "evidence": evidence, "warnings": ["synthetic"],
                "retrieval_latency_ms": 0, "generation_latency_ms": 0,
                "corpus": {"snapshot_id": "S0", "kind": "regression", "index_version": "synthetic-v1",
                           "created_at": "2026-01-01", "members_sha256": self.member_sha,
                           "version_ids": [version_id], "db_path": str(self.db), "as_of": "2026-01-01",
                           "include_undated_research": False},
                "config": {"doc_ids": ["synthetic-law"], "version_ids": None,
                           "entity_iri": None, "allow_nontrusted": True, "top_k": 2,
                           "include_undated_research": False, "generate_requested": False},
            })
        self.payload = {
            "schema_version": "1.0", "provenance": {
                "dataset_snapshot": "S0", "corpus_version": self.member_sha,
                "ontology_version": "none", "code_version": "synthetic",
                "retrieval_config": {"as_of": "2026-01-01", "allow_nontrusted": True},
                "llm": {"provider": "none", "model": "none", "prompt_version": "none", "used_llm": False},
                "execution_origin": "recorded_unverified",
                "trace_path": str(self.trace), "trace_sha256": "0" * 64,
            }, "rows": [],
        }
        self.save()

    def save(self):
        self.payload["rows"] = [
            {field: trace[field] for field in ("id", "user_input", "response", "retrieved_contexts")}
            for trace in self.traces
        ]
        raw = "".join(encoded(trace) + "\n" for trace in self.traces).encode()
        self.trace.write_bytes(raw)
        self.payload["provenance"]["trace_sha256"] = digest(raw)
        self.actual.write_text(encoded(self.payload), encoding="utf-8")

    def audit(self):
        return audit_artifact(self.actual, self.db, questions=self.questions)

    def test_read_only_verification_does_not_upgrade_recorded_or_source_authority(self):
        before = self.db.read_bytes()
        result = self.audit()
        self.assertTrue(result["verified"])
        self.assertEqual(result["execution_origin"], "recorded_unverified")
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["legal_currency_verified"])
        self.assertEqual(before, self.db.read_bytes())
        with closing(read_only_connection(self.db)) as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM chunks")

    def test_missing_db_never_creates_file(self):
        missing = self.root / "missing.sqlite"
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, missing)
        self.assertFalse(missing.exists())

    def test_trace_hash_duplicate_ids_missing_questions_and_mismatches_fail(self):
        raw = self.trace.read_bytes()
        self.trace.write_bytes(raw + b"\n")
        with self.assertRaises(ArtifactAuditError):
            self.audit()
        self.save()
        self.traces.append(copy.deepcopy(self.traces[0]))
        self.save()
        with self.assertRaises(ValueError):
            self.audit()
        self.traces.pop()
        self.save()
        self.payload["rows"][0]["response"] = "mutated"
        self.actual.write_text(encoded(self.payload), encoding="utf-8")
        with self.assertRaises(ArtifactAuditError):
            self.audit()
        self.save()
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, self.db, questions=self.questions[:1])

    def test_evidence_text_version_locator_hash_and_date_tampering_fail(self):
        original = copy.deepcopy(self.traces)
        mutations = [
            lambda item: item.update(version_id="wrong"),
            lambda item: item.update(sha256="0" * 64),
            lambda item: item["locator"].update(char_start=1),
            lambda item: item.update(text="wrong"),
            lambda item: item.update(authority="authoritative_original"),
        ]
        for mutation in mutations:
            self.traces = copy.deepcopy(original)
            mutation(self.traces[0]["evidence"][0])
            self.save()
            with self.subTest(mutation=mutation), self.assertRaises(ArtifactAuditError):
                self.audit()
        self.traces = copy.deepcopy(original)
        for trace in self.traces:
            trace["corpus"]["as_of"] = "2024-01-01"
        self.payload["provenance"]["retrieval_config"]["as_of"] = "2024-01-01"
        self.save()
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, self.db)

    def test_membership_and_original_database_tampering_fail(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE corpus_snapshots SET members_sha256=?", ("0" * 64,))
        with self.assertRaises(ArtifactAuditError):
            self.audit()

    def test_fixed_denominator_exact_article_rank_and_unresolved_negative_control(self):
        result = score_retrieval(self.questions, self.oracle, self.audit())
        self.assertEqual(result["denominator"], 2)
        self.assertEqual(result["cases"][0]["target_article_recall"], 1.0)
        self.assertEqual(result["cases"][0]["first_target_mrr"], 0.5)
        self.assertEqual(result["metrics"]["target_article_recall"], 0.5)
        self.assertEqual(result["metrics"]["unresolved_rate"], 0.5)
        self.assertTrue(result["cases"][1]["expected_status_match"])
        self.assertEqual(result["metrics"], {
            "target_article_recall": 0.5, "first_target_mrr": 0.25,
            "required_group_coverage": 0.5, "scope_violation_rate": 0,
            "unresolved_rate": 0.5, "error_rate": 0,
            "expected_status_match_rate": 1,
        })
        self.assertEqual(result["pass_count"], 2)
        self.assertEqual(result["by_split"]["test"]["denominator"], 1)
        self.assertEqual(result["by_split"]["challenge"]["denominator"], 1)
        self.assertEqual(result["by_split"]["train"]["denominator"], 0)
        self.assertIsNone(result["by_split"]["train"]["expected_status_match_rate"])
        self.assertEqual(result["by_expected_status"]["unresolved"]["target_article_recall"], 0)
        self.assertEqual(result["by_expected_status"]["unresolved"]["pass_count"], 1)

    def test_predeclared_subsets_keep_missing_targets_errors_and_undeclared_rows(self):
        base_audit = self.audit()
        questions, oracle, audited_rows = [], [], []
        for split in ("train", "dev", "test", "challenge", None):
            for outcome in ("pass", "missing", "error"):
                identifier = f"{split or 'undeclared'}-{outcome}"
                question = {**self.questions[0], "id": identifier}
                expected = copy.deepcopy(self.oracle[0])
                expected["id"] = identifier
                if split is None:
                    expected.pop("split", None)
                    expected.pop("category", None)
                else:
                    expected["split"] = split
                actual = copy.deepcopy(base_audit["rows"][0])
                actual["id"] = identifier
                if outcome == "missing":
                    actual["evidence"] = actual["evidence"][:1]
                elif outcome == "error":
                    actual["status"] = "error"
                    actual["evidence"] = []
                questions.append(question)
                oracle.append(expected)
                audited_rows.append(actual)
        for outcome in ("pass", "error"):
            identifier = f"unresolved-{outcome}"
            questions.append({**self.questions[1], "id": identifier})
            oracle.append({**copy.deepcopy(self.oracle[1]), "id": identifier})
            actual = {**copy.deepcopy(base_audit["rows"][1]), "id": identifier}
            if outcome == "error":
                actual["status"] = "error"
            audited_rows.append(actual)
        result = score_retrieval(questions, oracle, {**base_audit, "rows": audited_rows})
        self.assertEqual(result["denominator"], 17)
        self.assertEqual(result["pass_count"], 6)
        self.assertEqual(result["nonpass_count"], 11)
        for split in ("train", "dev", "test", "undeclared"):
            summary = result["by_split"][split]
            self.assertEqual(summary["denominator"], 3)
            self.assertEqual(summary["pass_count"], 1)
            self.assertEqual(summary["nonpass_count"], 2)
            self.assertEqual(summary["target_article_recall"], 1 / 3)
            self.assertEqual(summary["error_rate"], 1 / 3)
            self.assertEqual(summary["expected_status_match_rate"], 2 / 3)
            self.assertFalse(summary["acceptance"])
        challenge = result["by_split"]["challenge"]
        self.assertEqual(challenge["denominator"], 5)
        self.assertEqual(challenge["pass_count"], 2)
        self.assertEqual(challenge["nonpass_count"], 3)
        self.assertEqual(challenge["expected_status_match_rate"], 3 / 5)
        retrieved = result["by_expected_status"]["retrieved"]
        self.assertEqual(retrieved["denominator"], 15)
        self.assertEqual(retrieved["pass_count"], 5)
        self.assertEqual(retrieved["nonpass_count"], 10)
        self.assertEqual(retrieved["expected_status_match_rate"], 2 / 3)
        unresolved = result["by_expected_status"]["unresolved"]
        self.assertEqual(unresolved["denominator"], 2)
        self.assertEqual(unresolved["pass_count"], 1)
        self.assertEqual(unresolved["nonpass_count"], 1)
        self.assertEqual(unresolved["expected_status_match_rate"], 0.5)
        self.assertEqual(unresolved["target_article_recall"], 0)
        for grouping in ("by_split", "by_expected_status", "by_category"):
            self.assertEqual(sum(summary["denominator"] for summary in result[grouping].values()), 17)
            self.assertEqual(sum(summary["nonpass_count"] for summary in result[grouping].values()), 11)

    def test_partial_article_wrong_document_wrong_version_error_stays_denominator(self):
        audit = self.audit()
        for item in audit["rows"][0]["evidence"]:
            item["complete_article"] = False
        result = score_retrieval(self.questions, self.oracle, audit)
        self.assertEqual(result["cases"][0]["target_article_recall"], 0)
        self.assertEqual(result["cases"][0]["first_target_mrr"], 0)
        audit["rows"][0]["status"] = "error"
        audit["rows"][0]["evidence"] = []
        result = score_retrieval(self.questions, self.oracle, audit)
        self.assertEqual(result["denominator"], 2)
        self.assertEqual(result["metrics"]["error_rate"], 0.5)
        audit = self.audit()
        for item in audit["rows"][0]["evidence"]:
            item["doc_id"] = "wrong-doc"
        result = score_retrieval(self.questions, self.oracle, audit)
        self.assertEqual(result["cases"][0]["target_article_recall"], 0)
        self.assertEqual(result["metrics"]["scope_violation_rate"], 0.5)

    def test_oracle_duplicate_unknown_nonfinite_and_actual_authored_claim_rejected(self):
        oracle = json.loads((FIXTURES / "oracle.json").read_text())
        oracle["authorship"]["created_without_actuals"] = False
        path = self.root / "oracle.json"
        path.write_text(encoded(oracle), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_oracle(path)
        oracle["authorship"]["created_without_actuals"] = True
        oracle["rows"][0]["unsupported"] = 1
        path.write_text(encoded(oracle), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_oracle(path)

    def test_audit_fails_before_ragas_judge_execution(self):
        from tools.evaluate_ragas import main
        self.trace.write_bytes(b"tampered")
        with patch("tools.evaluate_ragas.evaluate", side_effect=AssertionError("must not evaluate")):
            result = main([
                "--input", str(self.actual), "--output", str(self.root / "result.json"),
                "--corpus-db", str(self.db), "--verify-trace", "--execute",
            ])
        self.assertEqual(result, 2)

    def test_independent_html_normalization_inline_unicode_nul_and_control_contract(self):
        identity = {"html_extraction": {"kind": "official_html", "encoding": "utf-8",
                    "selector": {"tag": "div", "attribute": "id", "value": "body"}}}
        raw = "<div id='body'><p>第1条\n Alpha&ensp;<span>inline</span>\n text\x00.</p><p>第2条 Beta.</p><script>ignored</script></div>".encode("utf-8")
        normalized, removed = _html_text(raw, identity)
        self.assertEqual(normalized, "第1条 Alpha inline text.\n第2条 Beta.")
        self.assertEqual(removed, 1)
        self.assertEqual(_html_text(b"<div id='body'>first<br/>second</div>", identity)[0], "first\nsecond")
        with self.assertRaises(ArtifactAuditError):
            _html_text(b"<div id='body'>bad\x01control</div>", identity)
        with self.assertRaises(ArtifactAuditError):
            _html_text(b"<div id='body'>one</div><div id='body'>two</div>", identity)

    def test_version_specific_oracle_does_not_match_another_version(self):
        oracle = copy.deepcopy(self.oracle)
        oracle[0]["target_articles"][0]["version_id"] = "wrong-version"
        oracle[0]["required_groups"][0][0]["version_id"] = "wrong-version"
        result = score_retrieval(self.questions, oracle, self.audit())
        self.assertEqual(result["cases"][0]["target_article_recall"], 0)
        self.assertEqual(result["cases"][0]["required_group_coverage"], 0)

    def test_candidates_scope_tamper_rank_and_truncated_article_fail(self):
        trace = self.traces[0]
        trace["scope"] = {
            "status": "resolved", "requested_doc_ids": ["synthetic-law"],
            "requested_version_ids": None, "entity_iri": None,
            "selected_doc_ids": ["synthetic-law"], "selected_version_ids": [self.version_id],
            "eligible_chunk_ids": [item["chunk_id"] for item in self.evidence],
            "article_numbers": [1, 2],
        }
        trace["retrieval_candidates"] = [
            {"rank": position, "chunk_id": item["chunk_id"], "doc_id": item["doc_id"],
             "version_id": item["version_id"], "score": None, "selected": True,
             "ranking": "article_locator"}
            for position, item in enumerate(self.evidence, 1)
        ]
        self.save()
        self.assertTrue(self.audit()["verified"])
        trace["retrieval_candidates"][0]["rank"] = 2
        self.save()
        with self.assertRaises(ArtifactAuditError):
            self.audit()
        trace["retrieval_candidates"][0]["rank"] = 1
        trace["scope"]["eligible_chunk_ids"] = ["outside-snapshot"]
        self.save()
        with self.assertRaises(ArtifactAuditError):
            self.audit()

    def strategy_fixture(self, requested):
        trace = self.traces[0]
        config = {
            "retrieval_strategy": requested, "candidate_k": 20, "rrf_k": 60,
            "child_target_chars": 240, "retrieval_cache": None, "allow_retrieval_network": False,
        }
        trace["config"].update(config)
        self.payload["provenance"]["retrieval_config"].update(config)
        trace["scope"] = {
            "status": "resolved", "requested_doc_ids": ["synthetic-law"],
            "requested_version_ids": None, "entity_iri": None,
            "selected_doc_ids": ["synthetic-law"], "selected_version_ids": [self.version_id],
            "eligible_chunk_ids": [item["chunk_id"] for item in self.evidence],
            "article_numbers": [], "body_query": "Synthetic",
        }
        lexical = [{"chunk_id": item["chunk_id"], "rank": rank, "score": 3.0 - rank}
                   for rank, item in enumerate(self.evidence, 1)]
        strategy = {
            "requested_strategy": requested, "effective_strategy": requested, "status": "ok",
            "candidate_k": 20, "rrf_k": 60, "child_target_chars": 240,
            "channels": {"bm25": lexical}, "child_matches": [],
            "model_config": {"embedding": {}, "rerank": {}},
            "cache": {"enabled": False, "hits": 0, "misses": 0, "path": None, "entries": []},
            "stages": [{"stage": "bm25", "status": "completed", "network": False}],
            "fusion": [], "rerank": [], "resource_events": [],
        }
        ranking = {"bm25": "bm25", "parent_child": "parent_bm25",
                   "hybrid_rrf": "hybrid_rrf", "bm25_rerank": "rerank"}[requested]
        scores = [2.0, 1.0]
        if requested == "parent_child":
            children = []
            for rank, item in enumerate(self.evidence, 1):
                identity = {"parent": item["chunk_id"], "start": 0, "end": len(item["text"]),
                            "text": item["text"], "policy": "sentence-boundary-240-v1"}
                child_id = "child_" + digest(json.dumps(
                    identity, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
                children.append({
                    "child_id": child_id, "parent_chunk_id": item["chunk_id"], "rank": rank,
                    "score": scores[rank - 1], "char_start": item["locator"]["char_start"],
                    "char_end": item["locator"]["char_end"],
                    "parent_char_start": item["locator"]["char_start"],
                    "parent_char_end": item["locator"]["char_end"],
                    "text_sha256": digest(item["text"].encode()),
                })
            strategy["channels"]["child_bm25"] = children
            strategy["child_matches"] = copy.deepcopy(children)
            strategy["stages"].append({"stage": "parent_child", "status": "completed",
                                       "network": False, "input_count": 2})
        elif requested == "hybrid_rrf":
            strategy["channels"]["dense"] = [
                {"chunk_id": item["chunk_id"], "rank": rank, "score": 0.9 / rank}
                for rank, item in enumerate(self.evidence, 1)]
            scores = [2.0 / 61, 2.0 / 62]
            strategy["fusion"] = [
                {"chunk_id": item["chunk_id"], "score": scores[rank - 1],
                 "bm25_rank": rank, "dense_rank": rank} for rank, item in enumerate(self.evidence, 1)]
            strategy["model_config"]["embedding"] = {"provider": "offline", "model": "synthetic"}
            for kind, texts in (("embed_documents", [item["text"] for item in self.evidence]),
                                ("embed_query", ["Synthetic"])):
                for text in texts:
                    identity = {"schema_version": "1.0", "snapshot": self.member_sha,
                                "embedding": strategy["model_config"]["embedding"], "kind": kind, "text": text}
                    key = digest(json.dumps(identity, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
                    strategy["cache"]["entries"].append({"kind": kind, "key": key, "vector_sha256": "a" * 64})
            strategy["cache"]["misses"] = 3
        elif requested == "bm25_rerank":
            scores = [0.0, -0.5]
            strategy["rerank"] = [
                {"chunk_id": item["chunk_id"], "index": index, "score": scores[index]}
                for index, item in enumerate(self.evidence)]
            strategy["model_config"]["rerank"] = {"provider": "offline", "model": "synthetic"}
        trace["strategy_trace"] = strategy
        trace["retrieval_candidates"] = [
            {"rank": rank, "chunk_id": item["chunk_id"], "doc_id": item["doc_id"],
             "version_id": item["version_id"], "score": scores[rank - 1], "selected": True,
             "ranking": ranking} for rank, item in enumerate(self.evidence, 1)]
        trace["retrieval_debug"] = {
            "ranking": ranking, "top_k": 2, "candidate_count": 2, "selected_count": 2,
            "budget_excluded_chunk_ids": [], "budget_excluded_articles": [],
            "article_budget_sufficient": True,
        }
        other = self.traces[1]
        other["config"].update(config)
        other["scope"] = {
            "status": "unresolved", "requested_doc_ids": ["synthetic-law"],
            "requested_version_ids": None, "entity_iri": None, "selected_doc_ids": [],
            "selected_version_ids": [], "eligible_chunk_ids": [], "article_numbers": [],
        }
        other["strategy_trace"] = {
            **copy.deepcopy(strategy), "status": "bypassed", "effective_strategy": "none",
            "reason": "unresolved_scope", "channels": {}, "child_matches": [], "stages": [],
            "fusion": [], "rerank": [], "resource_events": [],
            "model_config": {"embedding": {}, "rerank": {}},
            "cache": {"enabled": False, "hits": 0, "misses": 0, "path": None, "entries": []},
        }
        other["retrieval_candidates"] = []
        other["retrieval_debug"] = {
            "ranking": ranking, "top_k": 2, "candidate_count": 0, "selected_count": 0,
            "budget_excluded_chunk_ids": [], "budget_excluded_articles": [],
            "article_budget_sufficient": True,
        }
        return trace

    def test_strategy_membership_child_offsets_rrf_and_rerank_positive_controls(self):
        for requested in ("bm25", "parent_child", "hybrid_rrf", "bm25_rerank"):
            with self.subTest(requested=requested):
                self.strategy_fixture(requested)
                self.save()
                result = self.audit()
                self.assertTrue(result["verified"])
                self.assertFalse(result["ranking_scores_independently_recomputed"])
                self.assertEqual(result["dense_and_rerank_scores_verification"], "declared_only")

    def test_strategy_resigned_tampering_fails_closed(self):
        controls = (
            ("bm25", lambda trace: trace["strategy_trace"].update(candidate_k=21)),
            ("bm25", lambda trace: trace["strategy_trace"]["channels"]["bm25"][0].update(chunk_id="outside")),
            ("parent_child", lambda trace: trace["strategy_trace"]["channels"]["child_bm25"][0].update(char_end=3)),
            ("parent_child", lambda trace: trace["strategy_trace"]["channels"]["child_bm25"][0].update(text_sha256="b" * 64)),
            ("hybrid_rrf", lambda trace: trace["strategy_trace"]["fusion"][0].update(score=0.1)),
            ("hybrid_rrf", lambda trace: trace["strategy_trace"]["cache"]["entries"][0].update(key="b" * 64)),
            ("hybrid_rrf", lambda trace: trace["strategy_trace"]["channels"]["dense"][0].update(rank=2)),
            ("bm25_rerank", lambda trace: trace["strategy_trace"]["rerank"][0].update(index=1)),
            ("bm25_rerank", lambda trace: trace["strategy_trace"]["model_config"]["rerank"].update(api_key="secret")),
            ("bm25", lambda trace: trace["strategy_trace"].update(status="error", reason="failed")),
        )
        for requested, mutate in controls:
            with self.subTest(requested=requested, mutate=mutate):
                trace = self.strategy_fixture(requested)
                mutate(trace)
                self.save()
                with self.assertRaises(ValueError):
                    self.audit()

    def test_strategy_requires_envelope_policy_and_no_legacy_downgrade(self):
        trace = self.strategy_fixture("hybrid_rrf")
        self.payload["provenance"]["retrieval_config"]["candidate_k"] = 19
        self.save()
        with self.assertRaises(ArtifactAuditError):
            self.audit()
        self.payload["provenance"]["retrieval_config"]["candidate_k"] = 20
        trace.pop("strategy_trace")
        self.save()
        with self.assertRaises(ArtifactAuditError):
            self.audit()

    def test_provider_event_metadata_is_bounded_and_unused_invalid_endpoint_allowed(self):
        trace = self.strategy_fixture("bm25_rerank")
        trace["strategy_trace"]["model_config"]["embedding"] = {
            "provider": "unused", "model": "unused", "endpoint": None,
            "endpoint_validation_status": "invalid",
        }
        for item in self.traces:
            item["config"]["allow_retrieval_network"] = True
        self.payload["provenance"]["retrieval_config"]["allow_retrieval_network"] = True
        event = {
            "kind": "rerank", "input_count": 2, "status": "ok", "http_status": 200,
            "request_sha256": "a" * 64, "response_sha256": "b" * 64, "elapsed_ms": 1.2,
            "response_validation_status": "ok", "usage": {"input_tokens": 5},
        }
        trace["strategy_trace"]["resource_events"] = [event]
        self.save()
        self.assertTrue(self.audit()["verified"])
        event.update(response_validation_status="error", response_validation_error_type="CorpusError")
        self.save()
        with self.assertRaises(ArtifactAuditError):
            self.audit()
        event.update(response_validation_status="ok")
        event.pop("response_validation_error_type")
        event["api_key"] = "secret"
        self.save()
        with self.assertRaises(ValueError):
            self.audit()

    def test_resigned_empty_scope_cannot_escape_without_scope_object(self):
        self.traces[0]["config"]["doc_ids"] = []
        self.save()
        questions = copy.deepcopy(self.questions)
        questions[0]["doc_ids"] = []
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, self.db, questions=questions)
        self.traces[0]["config"]["doc_ids"] = None
        self.save()
        questions[0]["doc_ids"] = []
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, self.db, questions=questions)

    def test_resigned_empty_version_scope_and_declared_scope_mismatch_fail(self):
        self.traces[0]["config"]["version_ids"] = []
        self.save()
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, self.db)

    def test_legal_cli_offline_verified_report_and_nonpass_exit(self):
        from tools.evaluate_legal_retrieval import main
        question_path = self.root / "questions.json"
        oracle_path = self.root / "oracle.json"
        question_path.write_text(encoded({"schema_version": "1.0", "cases": self.questions}), encoding="utf-8")
        oracle_path.write_text(encoded({"schema_version": "1.0", "authorship": self.authorship,
                                       "rows": self.oracle}), encoding="utf-8")
        output = self.root / "score.json"
        arguments = [
            "--actual", str(self.actual), "--corpus-db", str(self.db),
            "--questions", str(question_path), "--oracle", str(oracle_path),
            "--output", str(output), "--verify-trace",
        ]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), 0)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(report["acceptance"])
        self.assertEqual(report["nonpass_count"], 0)
        self.assertEqual(report["denominator"], 2)
        self.oracle[0]["target_articles"][0]["article_number"] = 99
        self.oracle[0]["required_groups"][0][0]["article_number"] = 99
        oracle_path.write_text(encoded({"schema_version": "1.0", "authorship": self.authorship,
                                       "rows": self.oracle}), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), 1)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["nonpass_count"], 1)
        self.traces[0]["config"]["version_ids"] = None
        self.payload["provenance"]["retrieval_config"]["case_scopes"] = [{
            "id": trace["id"], "as_of": "2026-01-01", "doc_ids": [],
            "version_ids": None, "entity_iri": None,
        } for trace in self.traces]
        self.save()
        with self.assertRaises(ArtifactAuditError):
            audit_artifact(self.actual, self.db)


if __name__ == "__main__":
    unittest.main()
