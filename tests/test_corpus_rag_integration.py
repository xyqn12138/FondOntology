from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.qa.engine import answer_question
from fondontology.qa.graph import build_stack
from fondontology.qa.rag.answer import answer_regulation
from fondontology.qa.rag.answer import answer_explain, answer_code
from fondontology.qa.rag.retrieve import retrieve
from fondontology.qa.rag.store import ChunkStore, RagChunk, get_store, load_corpus_store
from fondontology.qa.semantics import OntologyContext
from tools.qa_cli import main


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "corpus_rag"
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")


class CorpusRagIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = json.loads((FIXTURE / "cases.json").read_text(encoding="utf-8"))
        cls.stack = build_stack(
            ROOT / "ontology" / "modules" / "cnfo-domain.ttl",
            ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl")
        entity = URIRef(cls.cases["fund_iri"])
        cls.stack.abox.add((entity, RDF.type, CNFO.MoneyMarketFund))
        cls.stack.abox.add((entity, RDFS.label, Literal(cls.cases["fund_label"], lang="zh")))
        cls.stack.abox.add((entity, CNFO.fundCode, Literal("TOY")))
        cls.stack.abox.add((entity, CNFO.governedByRegulation,
                            URIRef(cls.cases["regulation_iri"])))

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = self.directory / "corpus.sqlite"
        self.repo = CorpusRepository(self.db)
        self.versions = {}
        for filename, document_id, doc_type, links, date in (
                ("fund.md", "toy-fund", "periodic_report", [self.cases["fund_iri"]],
                 self.cases["issued_date"]),
                ("updated.md", "toy-fund-update", "periodic_report", [self.cases["fund_iri"]],
                 self.cases["updated_date"]),
                ("regulation.md", "toy-regulation", "regulation_article",
                 [self.cases["regulation_iri"], self.cases["code_iri"]], self.cases["issued_date"])):
            source = FIXTURE / filename
            record = {
                "doc_id": document_id, "title": document_id, "doc_type": doc_type,
                "path": str(source), "source_uri": f"urn:synthetic:{document_id}",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "authority": "synthetic", "status": "verified",
                "issued_date": date, "fund_code": "TOY" if doc_type == "periodic_report" else None,
                "provenance": {"fixture": "synthetic; not legal or financial evidence"},
                "locator": {"page": 1},
                "entity_links": [{"entity_id": entity, "method": "manual-fixture",
                                  "confidence": 1.0, "review_status": "reviewed"}
                                 for entity in links],
            }
            manifest = self.directory / f"{document_id}.jsonl"
            manifest.write_text(json.dumps(record), encoding="utf-8")
            self.repo.import_manifest(manifest)
            self.versions[filename] = next(version["version_id"] for version in self.repo.list_versions()
                                          if version["doc_id"] == document_id)
        self.repo.publish_snapshot("alpha", [self.versions["fund.md"], self.versions["regulation.md"]],
                                   kind="regression")
        self.repo.publish_snapshot("beta", [self.versions["updated.md"]],
                                   kind="regression")

    def load(self, snapshot="alpha", as_of=None):
        return load_corpus_store(
            self.db, snapshot, as_of=as_of or self.cases["as_of"], allow_nontrusted=True)

    def no_external_calls(self):
        return patch("fondontology.qa.rag.retrieve._vector_index_if_ready",
                     side_effect=AssertionError("legacy vector access forbidden"))

    def test_real_question_consumes_snapshot_and_returns_original_locator(self) -> None:
        store = self.load()
        with self.no_external_calls(), patch(
                "fondontology.qa.rag.retrieve._rerank_call",
                side_effect=AssertionError("network rerank forbidden")):
            result = answer_explain(
                self.cases["snapshot_alpha_marker"],
                {"explain_type": "describe", "entity_iri": self.cases["fund_iri"]},
                OntologyContext.from_stack(self.stack), self.stack.query_graph(), store=store)
        self.assertEqual(result.status, "ok", result.text)
        self.assertIn(self.cases["snapshot_alpha_marker"],
                      result.report["evidence"][0]["text"])
        self.assertEqual(result.report["meta"]["corpus"]["kind"], "regression")
        evidence = result.report["evidence"][0]
        self.assertEqual(evidence["version_id"], self.versions["fund.md"])
        self.assertEqual(evidence["locator"]["page"], 1)
        self.assertEqual(len(evidence["locator"]["sha256"]), 64)
        self.assertEqual(result.report["meta"]["corpus"]["snapshot_id"], "alpha")

    def test_snapshot_and_date_isolation(self) -> None:
        beta = answer_explain(
            self.cases["snapshot_beta_marker"],
            {"explain_type": "describe", "entity_iri": self.cases["fund_iri"]},
            OntologyContext.from_stack(self.stack), self.stack.query_graph(),
            store=self.load("beta"))
        self.assertEqual(beta.status, "ok", beta.text)
        self.assertIn(self.cases["snapshot_beta_marker"],
                      beta.report["evidence"][0]["text"])
        self.assertNotIn(self.cases["snapshot_alpha_marker"],
                         beta.report["evidence"][0]["text"])
        empty = answer_question(self.cases["fund_question"], self.stack,
                                use_llm=False, rag_store=self.load(as_of=self.cases["before_date"]))
        self.assertEqual(empty.status, "unresolved")
        self.assertEqual(self.load("beta", self.cases["issued_date"]).chunks, [])

    def test_regulation_and_code_do_not_parse_legacy_reports(self) -> None:
        store = self.load()
        with patch.object(Graph, "parse", side_effect=AssertionError("legacy TTL forbidden")), \
             self.no_external_calls():
            regulation = answer_regulation(
                self.cases["regulation_question"],
                {"topic": str(CNFO.MoneyMarketFund)},
                OntologyContext.from_stack(self.stack), self.stack.query_graph(),
                store=store)
            code = answer_code(
                self.cases["code_question"],
                {"code": "R4", "explain_type": "code"},
                OntologyContext.from_stack(self.stack), self.stack.query_graph(),
                store=store)
        self.assertEqual(regulation.status, "ok", regulation.text)
        self.assertEqual(code.status, "ok", code.text)
        for result in (regulation, code):
            self.assertEqual(result.report["evidence"][0]["version_id"],
                             self.versions["regulation.md"])

    def test_unmatched_scope_and_lexical_query_return_unresolved(self) -> None:
        graph = Graph()
        graph.add((URIRef(self.cases["fund_iri"]), RDF.type, CNFO.MoneyMarketFund))
        graph.add((URIRef(self.cases["fund_iri"]), CNFO.governedByRegulation,
                   URIRef(self.cases["missing_regulation_iri"])))
        result = answer_regulation(
            self.cases["regulation_question"], {"topic": str(CNFO.MoneyMarketFund)},
            OntologyContext.from_stack(self.stack), graph, store=self.load())
        self.assertEqual(result.status, "unresolved")
        lexical = answer_regulation("zzzz-unmatched", {}, OntologyContext.from_stack(self.stack),
                                    graph, store=self.load())
        self.assertEqual(lexical.status, "unresolved")
        missing_code = answer_question(self.cases["missing_code_question"], self.stack,
                                       use_llm=False, rag_store=self.load())
        self.assertEqual(missing_code.status, "unresolved")

    def test_unknown_anchor_never_becomes_global(self) -> None:
        result = retrieve("测试基金", store=self.load(), entity_iri="urn:missing",
                          query_graph=Graph())
        self.assertTrue(result.anchored)
        self.assertEqual(result.chunks, [])
        self.assertEqual(result.scope_fund_codes, set())

    def test_reviewed_direct_link_survives_graph_code_scope(self) -> None:
        base = self.load()
        direct = RagChunk(
            chunk_id="direct-no-fund-code", doc_id="direct-doc",
            fund_code=None, doc_type="periodic_report", period=None,
            section="补充披露", text="语料验证一号存在补充披露证据 DIRECT_LINK_MARKER。",
            locator={"page": 2}, version_id="direct-version",
            entity_links=[{"entity_id": self.cases["fund_iri"],
                           "method": "manual", "confidence": 1.0,
                           "review_status": "reviewed"}],
            authority="synthetic", status="verified", provenance={})
        augmented = ChunkStore(base.chunks + [direct],
                               corpus_metadata=base.corpus_metadata)
        result = retrieve(
            "语料验证一号补充披露 DIRECT_LINK_MARKER", store=augmented,
            ctx=OntologyContext.from_stack(self.stack),
            query_graph=self.stack.query_graph(),
            entity_iri=self.cases["fund_iri"])
        self.assertIn("direct-no-fund-code", {chunk.chunk_id for chunk in result.chunks})

    def test_repository_configuration_is_fail_closed(self) -> None:
        with self.assertRaises(CorpusError):
            load_corpus_store(self.directory / "missing.sqlite", "alpha",
                              as_of=self.cases["as_of"])
        self.assertFalse((self.directory / "missing.sqlite").exists())
        with self.assertRaises(CorpusError):
            load_corpus_store(self.db, "alpha", as_of=self.cases["as_of"])
        with self.assertRaises(CorpusError):
            self.load("unknown")
        with self.assertRaises(CorpusError):
            self.load(as_of="not-a-date")
        with self.assertRaises(CorpusError):
            load_corpus_store(self.db, "alpha", as_of="", allow_nontrusted=True)

    def test_cli_corpus_arguments_are_grouped(self) -> None:
        with self.assertRaises(SystemExit), patch("tools.qa_cli.build_stack") as build:
            main(["--corpus-db", str(self.db), "question"])
        build.assert_not_called()

    def test_legacy_jsonl_loads_are_isolated(self) -> None:
        first = self.directory / "first.jsonl"
        second = self.directory / "second.jsonl"
        first.write_text(json.dumps({"chunk_id": "FIRST", "text": "alpha"}), encoding="utf-8")
        second.write_text(json.dumps({"chunk_id": "SECOND", "text": "beta"}), encoding="utf-8")
        self.assertEqual(set(get_store(first).by_id), {"FIRST"})
        self.assertEqual(set(get_store(second).by_id), {"SECOND"})


if __name__ == "__main__":
    unittest.main()
