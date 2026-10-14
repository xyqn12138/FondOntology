from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from fondontology.qa.engine import QaAnswer
from fondontology.qa.service import (
    DocumentRequest, DocumentService, KnowledgeGraphRequest, KnowledgeGraphService, RetrievalPlan,
)


class QaServiceTest(unittest.TestCase):
    def request(self, **kwargs):
        return DocumentRequest("allocation", "fixture.sqlite", "synthetic", "2026-10-14", **kwargs)

    def test_plan_rejects_invalid_budgets_and_unsupported_composition(self):
        for configuration in (
                {"top_k": True}, {"top_k": 0}, {"candidate_k": 4}, {"candidate_k": 20.5},
                {"strategy": "automatic"}, {"query_transform": "unknown"},
                {"query_transform": "hyde"}):
            with self.subTest(configuration=configuration), self.assertRaises(ValueError):
                RetrievalPlan(**configuration)
        self.assertEqual(RetrievalPlan("hybrid_rrf", "hyde").query_transform, "hyde")

    def test_request_validates_scope_types_date_and_explicit_flags(self):
        for configuration in (
                {"doc_ids": []}, {"doc_ids": ("a", "a")}, {"version_ids": (" ",)},
                {"generate": 1}, {"allow_retrieval_network": "true"},
                {"include_undated_research": True}, {"entity_iri": ""}, {"plan": {}},
                {"retrieval_cache": ""}):
            with self.subTest(configuration=configuration), self.assertRaises(ValueError):
                self.request(**configuration)
        for as_of in ("20261014", "2026-02-30", "today"):
            with self.subTest(as_of=as_of), self.assertRaises(ValueError):
                DocumentRequest("question", "db", "snapshot", as_of)
        with self.assertRaises(ValueError):
            KnowledgeGraphRequest("  ")
        with self.assertRaises(ValueError):
            KnowledgeGraphRequest("question", use_llm="false")

    def test_document_adapter_preserves_none_versus_empty_scope_and_native_result(self):
        result = {"status": "retrieved", "response": "excerpt", "evidence": [{"chunk_id": "one"}],
                  "corpus": {"snapshot_id": "synthetic"}, "scope": {}, "strategy_trace": {}, "config": {}}
        handler = Mock(return_value=result)
        resources = object()
        service = DocumentService(handler=handler, resources=resources)
        for identifiers, expected in ((None, None), ((), []), (("one",), ["one"])):
            with self.subTest(identifiers=identifiers):
                response = service.answer(self.request(doc_ids=identifiers, version_ids=identifiers))
                self.assertEqual(handler.call_args.kwargs["doc_ids"], expected)
                self.assertEqual(handler.call_args.kwargs["version_ids"], expected)
                self.assertIs(handler.call_args.kwargs["resources"], resources)
                self.assertEqual(response.route, "document_rag")
                self.assertEqual(response.status, "retrieved")
                self.assertEqual(response.evidence, ({"chunk_id": "one"},))
                self.assertIs(response.payload, result)
                self.assertEqual(response.trace["corpus"], result["corpus"])
        self.assertNotIn("reference", handler.call_args.kwargs)
        self.assertNotIn("oracle", handler.call_args.kwargs)

    def test_model_resource_construction_is_lazy_and_injected_factory_wins(self):
        handler = Mock(return_value={"status": "unresolved", "response": "no evidence", "evidence": [],
                                     "corpus": {}, "scope": {}, "strategy_trace": {}, "config": {}})
        with patch("fondontology.qa.rag.document_providers.build_resources") as factory:
            DocumentService(handler=handler).answer(self.request(plan=RetrievalPlan("hybrid_rrf")))
            self.assertIs(handler.call_args.kwargs["resources"], factory)
            factory.assert_not_called()
        custom = Mock()
        DocumentService(handler=handler, resources=custom).answer(self.request())
        self.assertIs(handler.call_args.kwargs["resources"], custom)
        custom.assert_not_called()

    def test_graph_status_mapping_preserves_negative_verdict_and_evidence(self):
        stack = object()
        result = QaAnswer("verify", "ok", "not entailed", verdict="CONTRADICTED",
                          report={"evidence": [{"id": "E1"}]}, schema_trace={"selected": ["term"]})
        handler = Mock(return_value=result)
        response = KnowledgeGraphService(stack, handler=handler).answer(
            KnowledgeGraphRequest("verification question", use_llm=False))
        handler.assert_called_once_with("verification question", stack, use_llm=False, rag_store=None)
        self.assertEqual(response.route, "knowledge_graph")
        self.assertEqual(response.status, "answered")
        self.assertEqual(response.trace["verdict"], "CONTRADICTED")
        self.assertEqual(response.evidence, ({"id": "E1"},))
        self.assertIs(response.payload, result)
        result.status = "ambiguous"
        self.assertEqual(KnowledgeGraphService(stack, handler=handler).answer(
            KnowledgeGraphRequest("which fund")).status, "clarification")

    def test_explicit_routes_reject_wrong_request_without_calling_other_engine(self):
        handler = Mock()
        with self.assertRaises(TypeError):
            DocumentService(handler=handler).answer(KnowledgeGraphRequest("question"))
        with self.assertRaises(TypeError):
            KnowledgeGraphService(object(), handler=handler).answer(self.request())
        with self.assertRaises(ValueError):
            KnowledgeGraphService(None)
        handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
