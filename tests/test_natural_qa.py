"""Natural QA separates runtime questions from gold and supports split evidence."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fondontology.evaluation.natural_qa import (
    NaturalQAError, score_spans, span_coverage, validate_cases, validate_release,
)
from tools.build_natural_qa_release import main
from tools.document_rag import load_cases
from fondontology.evaluation.ragas_runner import merge_references


class NaturalQATests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.data.mkdir()
        text = "# 测试规范\r\n\r\n业务申请受理后需要先核对资料完整性，再按照业务条件判断处理路径。\r\n"
        self.markdown = self.data / "body.md"
        self.markdown.write_bytes(text.encode("utf-8"))
        document = {"id": "fixture-doc", "title": "测试规范",
                    "markdown_path": "body.md", "markdown_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "raw_sha256": "b" * 64, "verification": {"body_start_line": 3}}
        self.sources = {"fixture-doc": document}
        self.lock = {"source_version": "fixture-source", "catalog_sha256": "a" * 64,
                     "snapshot_id": "fixture-snapshot", "snapshot_members_sha256": "c" * 64}
        self.registry = [{"doc_id": "fixture-doc", "title": "测试规范"}]
        self.case = {
            "id": "fixture-q", "question": "客户申请交上来以后，我们运营先做什么？",
            "category": "business", "task_type": "workflow", "difficulty": "single",
            "reference": "先核对资料完整性，再判断处理路径。",
            "expected_behavior": "answer",
            "evidence": [{"doc_id": "fixture-doc", "quote": text.split("\r\n")[2]}],
            "answer_points": ["先核对资料"], "forbidden_claims": ["跳过核对直接办理"],
            "source_notes": "Synthetic source, not a legal claim.",
        }
        self.mock = patch("fondontology.evaluation.natural_qa.load_sources",
                          return_value=(self.lock, self.sources, self.registry))
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def test_source_cues_and_unknown_scope_fields_rejected(self):
        for update in ({"question": "按照《测试规范》怎么处理？"},
                       {"doc_ids": ["fixture-doc"]},
                       {"question": "fixture-doc规定如何处理？"}):
            with self.subTest(update=update):
                with self.assertRaises(NaturalQAError):
                    validate_cases([{**self.case, **update}], self.data)

    def test_evidence_offsets_use_exact_crlf_source(self):
        rows, _report = validate_cases([self.case], self.data)
        target = rows[0]["evidence"][0]
        text = self.markdown.read_bytes().decode()
        self.assertEqual(text[target["char_start"]:target["char_end"]], target["quote"])
        with self.assertRaises(NaturalQAError):
            validate_cases([{**self.case, "evidence": [{"doc_id": "not-frozen", "quote": target["quote"]}]}],
                           self.data)

    def test_runtime_and_references_remain_separate_and_frozen(self):
        author = self.root / "author.json"
        author.write_text(json.dumps({"cases": [self.case]}, ensure_ascii=False), encoding="utf-8")
        directory = self.root / "release"
        with patch("tools.build_natural_qa_release.load_sources",
                   return_value=(self.lock, self.sources, self.registry)):
            self.assertEqual(main(["--authors", str(author), "--directory", str(directory),
                                   "--data-root", str(self.data)]), 0)
        runtime = load_cases(directory / "questions.json")
        self.assertEqual(set(runtime[0]), {"id", "question", "as_of"})
        merged, _review = merge_references(
            [{"id": runtime[0]["id"], "user_input": runtime[0]["question"],
              "response": "", "retrieved_contexts": []}], directory / "references.json")
        self.assertIn("reference", merged[0])
        self.assertNotIn("reference", runtime[0])
        validate_release(directory, self.data)
        freeze_path = directory / "freeze.json"
        freeze_raw = freeze_path.read_bytes()
        freeze = json.loads(freeze_raw)
        freeze["independent_human_review"] = True
        freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
        with self.assertRaisesRegex(NaturalQAError, "review declaration"):
            validate_release(directory, self.data)
        freeze_path.write_bytes(freeze_raw)
        with (directory / "questions.json").open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaisesRegex(NaturalQAError, "file hash mismatch"):
            validate_release(directory, self.data)

    def test_split_chunk_coverage_requires_correct_document_and_hash(self):
        target = {"doc_id": "fixture-doc", "markdown_sha256": "a" * 64,
                  "char_start": 10, "char_end": 30}
        def evidence(start, end, digest="a" * 64):
            return {"doc_id": "fixture-doc", "sha256": digest,
                    "locator": {"char_start": start, "char_end": end}}
        self.assertEqual(span_coverage(target, [evidence(10, 20), evidence(20, 30)]), 1)
        self.assertEqual(span_coverage(target, [evidence(10, 25), evidence(15, 25)]), 0.75)
        self.assertEqual(span_coverage(target, [evidence(10, 30, "b" * 64)]), 0)

    def test_review_requires_exact_author_and_every_case_acceptance(self):
        author = self.root / "author.json"
        author.write_text(json.dumps({"cases": [self.case]}, ensure_ascii=False), encoding="utf-8")
        review_path = self.root / "review.json"
        review = {
            "full_batch_approved": True, "human_reviewed": False,
            "author_input_sha256": {author.name: hashlib.sha256(author.read_bytes()).hexdigest()},
            "source_version": self.lock["source_version"],
            "catalog_sha256": self.lock["catalog_sha256"],
            "cases": [{"id": self.case["id"], "decision": "accept"}],
        }
        arguments = ["--authors", str(author), "--review", str(review_path),
                     "--directory", str(self.root / "reviewed"), "--data-root", str(self.data)]
        with patch("tools.build_natural_qa_release.load_sources",
                   return_value=(self.lock, self.sources, self.registry)):
            for changes in ({"full_batch_approved": False}, {"human_reviewed": True},
                            {"author_input_sha256": {author.name: "d" * 64}},
                            {"cases": [{"id": self.case["id"], "decision": "revise"}]}):
                with self.subTest(changes=changes):
                    review_path.write_text(json.dumps({**review, **changes}), encoding="utf-8")
                    self.assertEqual(main(arguments), 2)
                    self.assertFalse((self.root / "reviewed").exists())
            review_path.write_text(json.dumps(review), encoding="utf-8")
            self.assertEqual(main(arguments), 0)
        validate_release(self.root / "reviewed", self.data)

    def test_error_stays_in_answerable_denominator_and_controls_are_separate(self):
        target = {"doc_id": "fixture-doc", "markdown_sha256": "a" * 64,
                  "char_start": 10, "char_end": 30}
        oracle = [
            {"id": "answer", "expected_behavior": "answer", "category": "business",
             "split": "dev", "evidence": [target]},
            {"id": "clarify", "expected_behavior": "clarify", "category": "user",
             "split": "challenge", "evidence": []},
        ]
        score = score_spans(oracle, [{"id": "answer", "status": "error"},
                                    {"id": "clarify", "status": "retrieved"}])
        self.assertEqual(score["answerable_denominator"], 1)
        self.assertEqual(score["complete_evidence_rate"], 0)
        self.assertEqual(score["behavior_review_denominator"], 1)
        self.assertIsNone(score["cases"][1]["complete_evidence"])
        self.assertTrue(score["cases"][1]["response_behavior_requires_review"])


if __name__ == "__main__":
    unittest.main()
