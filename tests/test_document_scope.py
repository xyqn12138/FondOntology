from __future__ import annotations

import unittest
from unittest.mock import patch

from fondontology.corpus import CorpusError
from fondontology.qa.rag.document_pipeline import answer_document
from fondontology.qa.rag.document_scope import resolve_scope
from fondontology.qa.rag.store import ChunkStore, RagChunk


def chunk(identifier, document="alpha", version="v-alpha", title="Alpha Act",
          text="allocation ceiling seventeen percent", kind="legal_article",
          article=3, entity="urn:alpha"):
    return RagChunk(
        identifier, document, None, "regulation_article", None, "article", text,
        {"title": title, "content_kind": kind, "article_number": article,
         "char_start": 10, "char_end": 10 + len(text),
         "section_char_start": 10, "section_char_end": 10 + len(text)},
        version_id=version, authority="synthetic", status="verified",
        entity_links=[{"entity_id": entity, "review_status": "reviewed"}])


def store(chunks, extra_directory=()):
    directory = list({
        (item.doc_id, item.version_id): {
            "doc_id": item.doc_id, "version_id": item.version_id,
            "title": item.locator["title"],
        } for item in chunks
    }.values()) + list(extra_directory)
    return ChunkStore(chunks, corpus_metadata={
        "db_path": "unused", "snapshot_id": "fixture", "as_of": "2026-10-11",
        "kind": "regression", "include_undated_research": False,
        "members_sha256": "a" * 64,
        "document_directory": directory,
    })


class DocumentScopeTest(unittest.TestCase):
    def decision(self, question="allocation", **kwargs):
        base = kwargs.pop("store", store([chunk("alpha"), chunk(
            "beta", "beta", "v-beta", "Beta Act", entity="urn:beta")]))
        return resolve_scope(
            question, base, doc_ids=kwargs.get("doc_ids"),
            version_ids=kwargs.get("version_ids"), entity_iri=kwargs.get("entity_iri"))

    def test_none_empty_unknown_and_out_of_snapshot_version_are_distinct(self):
        self.assertEqual(len(self.decision()["eligible_chunk_ids"]), 2)
        for field, reason in (
                ("doc_ids", "empty_doc_id_scope"), ("version_ids", "empty_version_id_scope")):
            self.assertEqual(self.decision(**{field: []})["reason"], reason)
        self.assertEqual(self.decision(doc_ids=["missing"])["reason"], "unknown_doc_id")
        self.assertEqual(self.decision(version_ids=["v-other-snapshot"])["reason"], "unknown_version_id")
        with self.assertRaises(CorpusError):
            self.decision(doc_ids="alpha")

    def test_explicit_constraints_intersect_and_never_widen(self):
        decision = self.decision(doc_ids=["alpha"], version_ids=["v-beta"])
        self.assertEqual(decision["reason"], "conflicting_document_version_scope")
        decision = self.decision(doc_ids=["alpha"], entity_iri="urn:beta")
        self.assertEqual(decision["reason"], "empty_entity_intersection")
        self.assertEqual(self.decision(doc_ids=["alpha"], version_ids=["v-alpha"],
                                       entity_iri="urn:alpha")["eligible_chunk_ids"], ["alpha"])

    def test_title_unknown_ambiguity_conflict_and_explicit_disambiguation(self):
        self.assertEqual(self.decision("依据《Missing Act》，allocation")["reason"],
                         "unknown_document_title")
        duplicate = store([chunk("one"), chunk("two", "alpha-other", "v-two", "Alpha Act")])
        self.assertEqual(self.decision("《Alpha Act》allocation", store=duplicate)["reason"],
                         "ambiguous_document_title")
        self.assertEqual(self.decision("《Alpha Act》allocation", store=duplicate,
                                       version_ids=["v-two"])["eligible_chunk_ids"], ["two"])
        self.assertEqual(self.decision("《Alpha Act》allocation",
                                       doc_ids=["beta"])["reason"], "conflicting_title_scope")
        old = store([chunk("beta", "beta", "v-beta", "Beta Act")], [{
            "doc_id": "alpha", "version_id": "v-alpha", "title": "Alpha Act",
            "withdrawn_date": "2025-01-01",
        }])
        self.assertEqual(self.decision("《Alpha Act》allocation", store=old)["reason"],
                         "no_documents_available_at_as_of")

    def test_title_reference_in_body_does_not_become_document_scope(self):
        decision = self.decision("正文引用《Alpha Act》，allocation如何处理")
        self.assertEqual(decision["title_mentions"], [])
        self.assertEqual(len(decision["eligible_chunk_ids"]), 2)

    def test_explicit_scope_rejects_known_title_outside_scope(self):
        decision = self.decision(
            "仅限Beta Act文档，但我要的是《Alpha Act》第三条原文",
            doc_ids=["beta"],
        )
        self.assertEqual(decision["reason"], "conflicting_title_scope")

    def test_natural_direct_requests_use_syntax_not_known_title_membership(self):
        for prefix in (
                "请告诉我", "请解释一下", "我想查看", "能否提供",
                "只查所选文档，但我要的是", "请问一下"):
            for constraint in ({}, {"doc_ids": ["alpha"]}, {"version_ids": ["v-alpha"]}):
                with self.subTest(prefix=prefix, constraint=constraint):
                    decision = self.decision(f"{prefix}《Alpha Act》第三条原文", **constraint)
                    self.assertEqual(decision["title_mentions"], ["Alpha Act"])
                    self.assertEqual(decision["eligible_chunk_ids"], ["alpha"])
                    self.assertEqual(decision["article_numbers"], [3])
                    missing = self.decision(f"{prefix}《Missing Act》第三条原文", **constraint)
                    self.assertEqual(missing["reason"], "unknown_document_title")
                    self.assertEqual(missing["eligible_chunk_ids"], [])

    def test_natural_direct_title_requests_intersect_doc_and_version_constraints(self):
        for constraint in (
                {"doc_ids": ["beta"]}, {"version_ids": ["v-beta"]},
                {"doc_ids": ["beta"], "version_ids": ["v-beta"]}):
            with self.subTest(constraint=constraint):
                decision = self.decision(
                    "限定所选材料，不过请告诉我《Alpha Act》第三条原文", **constraint)
                self.assertEqual(decision["reason"], "conflicting_title_scope")
                self.assertEqual(decision["eligible_chunk_ids"], [])
        self.assertEqual(self.decision(
            "请告诉我《Alpha Act》第三条", doc_ids=[])["reason"], "empty_doc_id_scope")
        self.assertEqual(self.decision(
            "请告诉我《Alpha Act》第三条", version_ids=[])["reason"], "empty_version_id_scope")

    def test_body_references_with_article_numbers_do_not_override_explicit_scope(self):
        for question in (
                "正文引用《Alpha Act》第三条，allocation如何处理",
                "例如《Alpha Act》第三条，但按所选文档回答allocation",
                "例如根据《Alpha Act》第三条，allocation如何处理",
                "正文引用依据《Alpha Act》第三条，allocation如何处理",
                "原文提到《Alpha Act》第三条，allocation如何处理",
                "请解释正文引用《Alpha Act》第三条的含义",
                "正文引用《Missing Act》第三条，allocation如何处理"):
            for constraint in ({"doc_ids": ["beta"]}, {"version_ids": ["v-beta"]}):
                with self.subTest(question=question, constraint=constraint):
                    decision = self.decision(question, **constraint)
                    self.assertEqual(decision["status"], "resolved")
                    self.assertEqual(decision["title_mentions"], [])
                    self.assertEqual(decision["article_numbers"], [])
                    self.assertEqual(decision["selected_doc_ids"], ["beta"])
                    self.assertEqual(decision["eligible_chunk_ids"], ["beta"])
                    self.assertEqual(decision["body_query"], question)
        for prefix in ("依据", "请根据", "说明问题，请依据入库的"):
            decision = self.decision(f"{prefix}《Alpha Act》第三条原文")
            self.assertEqual(decision["eligible_chunk_ids"], ["alpha"])

    def test_unclassified_direct_article_syntax_cannot_substitute_explicit_document(self):
        for title in ("Alpha Act", "Missing Act"):
            for constraint in ({"doc_ids": ["beta"]}, {"version_ids": ["v-beta"]}):
                with self.subTest(title=title, constraint=constraint):
                    decision = self.decision(
                        f"我好奇有关《{title}》第三条的内容", **constraint)
                    self.assertEqual(decision["reason"], "unsupported_title_scope_syntax")
                    self.assertEqual(decision["eligible_chunk_ids"], [])
        decision = self.decision("我好奇有关《Alpha Act》第三条的内容")
        self.assertEqual(decision["title_mentions"], [])
        self.assertEqual(len(decision["eligible_chunk_ids"]), 2)

    def test_limited_basis_prefixes_identify_known_unknown_and_explicit_constraints(self):
        for prefix in (
                "请仅依据入库的", "截至2026-10-11，请只依据入库的",
                "请仅仅根据所选的", "仅按", "请只按照", "请仅依照"):
            for title, expected in (("Alpha Act", None), ("Missing Act", "unknown_document_title")):
                for constraint in ({}, {"doc_ids": ["alpha"]}, {"version_ids": ["v-alpha"]}):
                    with self.subTest(prefix=prefix, title=title, constraint=constraint):
                        decision = self.decision(
                            f"{prefix}《{title}》2026版本的allocation规定", **constraint)
                        self.assertEqual(decision["title_mentions"], [title])
                        self.assertEqual(decision["reason"], expected)
                        if expected is None:
                            self.assertEqual(decision["eligible_chunk_ids"], ["alpha"])
                        else:
                            self.assertEqual(decision["eligible_chunk_ids"], [])
            for constraint in ({"doc_ids": ["beta"]}, {"version_ids": ["v-beta"]}):
                self.assertEqual(self.decision(
                    f"{prefix}《Alpha Act》allocation", **constraint)["reason"],
                    "conflicting_title_scope")

    def test_direct_request_year_modifier_does_not_override_scope_or_known_status(self):
        for prefix in (
                "但我要的是入库的2014版", "不过请给我所选的2026年版",
                "请查看2014版", "我要的是所选的"):
            for constraint in ({}, {"doc_ids": ["alpha"]}, {"version_ids": ["v-alpha"]}):
                with self.subTest(prefix=prefix, constraint=constraint):
                    decision = self.decision(f"{prefix}《Alpha Act》第三条", **constraint)
                    self.assertEqual(decision["eligible_chunk_ids"], ["alpha"])
                    self.assertEqual(decision["article_numbers"], [3])
                    self.assertEqual(self.decision(
                        f"{prefix}《Missing Act》第三条", **constraint)["reason"],
                        "unknown_document_title")
            for constraint in ({"doc_ids": ["beta"]}, {"version_ids": ["v-beta"]}):
                self.assertEqual(self.decision(
                    f"{prefix}《Alpha Act》第三条", **constraint)["reason"],
                    "conflicting_title_scope")
        self.assertEqual(self.decision(
            "我要的是入库的201444版《Alpha Act》第三条", doc_ids=["alpha"])["reason"],
            "unsupported_title_scope_syntax")

    def test_reference_prefix_is_local_to_title_clause(self):
        for question in (
                "例如说明背景，我好奇有关《Missing Act》第三条",
                "前句引用示例。再说有关《Alpha Act》第三条",
                "举例解释背景；我好奇有关《Missing Act》第三条"):
            for constraint in ({"doc_ids": ["beta"]}, {"version_ids": ["v-beta"]}):
                with self.subTest(question=question, constraint=constraint):
                    self.assertEqual(self.decision(question, **constraint)["reason"],
                                     "unsupported_title_scope_syntax")
        for question in (
                "背景说明，正文引用《Missing Act》第三条，allocation如何处理",
                "说明背景。例如《Alpha Act》第三条，allocation如何处理"):
            decision = self.decision(question, doc_ids=["beta"])
            self.assertEqual(decision["reason"], None)
            self.assertEqual(decision["title_mentions"], [])
            self.assertEqual(decision["eligible_chunk_ids"], ["beta"])

    def test_metadata_excluded_title_removed_and_empty_body_unresolved(self):
        base = store([chunk("metadata", text="Alpha Act allocation", kind="metadata"),
                      chunk("article")])
        decision = self.decision("依据入库的《Alpha Act》，allocation", store=base)
        self.assertEqual(decision["eligible_chunk_ids"], ["article"])
        self.assertEqual(decision["metadata_excluded_ids"], ["metadata"])
        self.assertNotIn("Alpha Act", decision["body_query"])
        self.assertEqual(self.decision("《Alpha Act》", store=base)["reason"], "empty_body_query")

    def test_explicit_multiple_titles_are_union_without_gold(self):
        decision = self.decision("依据《Alpha Act》与《Beta Act》，allocation如何处理")
        self.assertEqual(set(decision["eligible_chunk_ids"]), {"alpha", "beta"})
        self.assertNotIn("Act", decision["body_query"])

    def test_article_scope_requires_whole_body_article_and_matches_numbers(self):
        base = store([chunk("three"), chunk("four", article=4)])
        decision = self.decision("《Alpha Act》第三条规定什么", store=base)
        self.assertEqual(decision["article_numbers"], [3])
        self.assertEqual(decision["eligible_chunk_ids"], ["three"])
        self.assertEqual(self.decision("第4条规定什么", store=base,
                                       doc_ids=["alpha"])["eligible_chunk_ids"], ["four"])
        base.by_id["three"].locator["char_end"] -= 1
        self.assertEqual(self.decision("《Alpha Act》第三条规定什么", store=base)["reason"],
                         "article_not_available")
        self.assertEqual(self.decision("《Alpha Act》第0条", store=base)["reason"],
                         "invalid_article_number")
        self.assertEqual(self.decision("第3条", doc_ids=["alpha", "beta"])["reason"],
                         "ambiguous_article_document_scope")

    def test_pre_ranking_scope_does_not_depend_on_top_k(self):
        distractors = [chunk(f"d-{number}", "beta", "v-beta", "Beta Act",
                            text="allocation allocation allocation", entity="urn:beta")
                       for number in range(6)]
        base = store([chunk("target")] + distractors)
        scoped = self.decision(doc_ids=["alpha"], store=base)
        hits = base.bm25_search("allocation", k=1,
                               scope_chunk_ids=set(scoped["eligible_chunk_ids"]))
        self.assertEqual([item.chunk_id for item, score in hits], ["target"])
        self.assertEqual(base.bm25_search("allocation", scope_chunk_ids=set()), [])

    def test_pipeline_trace_has_actual_filtered_scores_contexts_and_question(self):
        from pathlib import Path
        base = store([chunk("target"), chunk(
            "cross-reference", "beta", "v-beta", "Beta Act",
            text="Alpha Act allocation allocation ceiling seventeen percent")])
        base.corpus_metadata["db_path"] = str(Path("unused").resolve())
        with patch("fondontology.qa.rag.document_pipeline._generate",
                   side_effect=AssertionError("No generation")):
            result = answer_document(
                "《Alpha Act》allocation", db_path="unused", snapshot_id="fixture",
                as_of="2026-10-11", allow_nontrusted=True, store=base, top_k=1)
        self.assertEqual(result["user_input"], "《Alpha Act》allocation")
        self.assertEqual(result["scope"]["eligible_chunk_ids"], ["target"])
        self.assertEqual([item["chunk_id"] for item in result["retrieval_candidates"]], ["target"])
        self.assertTrue(result["retrieval_candidates"][0]["selected"])
        self.assertGreater(result["retrieval_candidates"][0]["score"], 0)
        self.assertEqual(result["retrieved_contexts"], [base.by_id["target"].text])

    def test_direct_article_lookup_has_no_fabricated_bm25_score_and_no_fallback(self):
        from pathlib import Path
        base = store([chunk("target", text="body with no lexical article numeral overlap")])
        base.corpus_metadata["db_path"] = str(Path("unused").resolve())
        result = answer_document(
            "《Alpha Act》第3条", db_path="unused", snapshot_id="fixture",
            as_of="2026-10-11", allow_nontrusted=True, store=base)
        self.assertEqual(result["status"], "retrieved")
        self.assertEqual(result["retrieval_candidates"][0]["ranking"], "article_locator")
        self.assertIsNone(result["retrieval_candidates"][0]["score"])
        missing = answer_document(
            "《Alpha Act》第4条", db_path="unused", snapshot_id="fixture",
            as_of="2026-10-11", allow_nontrusted=True, store=base)
        self.assertEqual(missing["unresolved_reason"], "article_not_available")
        self.assertEqual(missing["retrieval_candidates"], [])

    def test_multiple_articles_require_every_address_and_ranges_fail_explicitly(self):
        base = store([chunk("sixteen", article=16), chunk("twenty-three", article=23)])
        decision = self.decision("《Alpha Act》第十六条和第二十三条规定什么", store=base)
        self.assertEqual(decision["article_numbers"], [16, 23])
        self.assertEqual(set(decision["eligible_chunk_ids"]), {"sixteen", "twenty-three"})
        decision = self.decision("《Alpha Act》第十六条和第二十四条规定什么", store=base)
        self.assertEqual(decision["reason"], "article_not_available")
        self.assertEqual(decision["eligible_chunk_ids"], [])
        self.assertEqual(decision["missing_articles"], [{
            "doc_id": "alpha", "version_id": "v-alpha", "article_number": 24}])
        self.assertEqual(self.decision(
            "《Alpha Act》第十六条至第二十三条规定什么", store=base)["reason"],
            "unsupported_article_range")
        multi = store([chunk("alpha-three"), chunk(
            "beta-four", "beta", "v-beta", "Beta Act", article=4)])
        decision = self.decision(
            "依据《Alpha Act》第三条和《Beta Act》第五条如何处理", store=multi)
        self.assertEqual(decision["reason"], "article_not_available")
        self.assertEqual(decision["missing_articles"][0]["doc_id"], "beta")
        decision = self.decision(
            "依据《Alpha Act》第三条和《Beta Act》第四条如何处理", store=multi)
        self.assertEqual(set(decision["eligible_chunk_ids"]), {"alpha-three", "beta-four"})

    def test_multiple_article_top_k_budget_is_explicit_and_never_exceeded(self):
        from pathlib import Path
        base = store([chunk("sixteen", article=16), chunk("twenty-three", article=23)])
        base.corpus_metadata["db_path"] = str(Path("unused").resolve())
        result = answer_document(
            "《Alpha Act》第十六条和第二十三条", db_path="unused", snapshot_id="fixture",
            as_of="2026-10-11", allow_nontrusted=True, store=base, top_k=1)
        self.assertEqual(len(result["evidence"]), 1)
        self.assertFalse(result["retrieval_debug"]["article_budget_sufficient"])
        self.assertEqual(result["retrieval_debug"]["budget_excluded_chunk_ids"], ["twenty-three"])
        self.assertEqual(result["retrieval_debug"]["budget_excluded_articles"], [{
            "doc_id": "alpha", "version_id": "v-alpha", "article_number": 23}])
        self.assertTrue(any("budget excluded" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
