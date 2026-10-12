from __future__ import annotations

import json
import io
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.qa_bench import (
    _load_cases,
    _report_problems,
    run_find_benchmark,
    run_intent_benchmark,
    run_e2e_benchmark,
    run_citation_benchmark,
    run_explain_benchmark,
    main,
)


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "qa_bench_contract"


class QaBenchContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controls = json.loads((FIXTURES / "negative_controls.json").read_text())
        cls.answers = json.loads((FIXTURES / "answers.json").read_text())
        cls.intent = json.loads((FIXTURES / "intent.json").read_text())

    def run_captured(self, runner, *args, **kwargs):
        output = io.StringIO()
        with redirect_stdout(output):
            code = runner(*args, **kwargs)
        return code, output.getvalue()

    def test_invalid_case_shapes_are_rejected(self) -> None:
        for control in self.controls["invalid_find_cases"]:
            with self.subTest(control=control["id"]):
                with patch.object(Path, "read_text", return_value=json.dumps(
                        {"cases": control["cases"]})):
                    with self.assertRaises(ValueError):
                        _load_cases(Path("unused"), "find")

    def test_invalid_intent_expected_types_are_rejected(self) -> None:
        for control in self.controls["invalid_intent_expected"]:
            cases = deepcopy(self.intent)
            cases["cases"][0]["expected"][control["field"]] = control["value"]
            with self.subTest(control=control["id"]), patch.object(
                    Path, "read_text", return_value=json.dumps(cases)):
                with self.assertRaises(ValueError):
                    _load_cases(Path("unused"), "intent")

    def test_unknown_intent_expected_and_missing_gold_fail_acceptance(self) -> None:
        case_file = FIXTURES / "intent.json"
        with patch("tools.qa_bench.OntologyIndex"), patch(
                "tools.qa_bench.build_intent",
                return_value=SimpleNamespace(
                    status="RESOLVED",
                    operation="find",
                    intent={"target_class": "https://ontology.example.cnfo/EquityFund"},
                    used_llm=False,
                    schema_trace={},
                    notes=[],
                )):
            code, output = self.run_captured(
                run_intent_benchmark, None, case_file, use_llm=False, acceptance=True)
            self.assertEqual(code, 1)
            self.assertIn("date_ranges expected=", output)

    def test_acceptance_rejects_missing_declared_gold(self) -> None:
        for slot in self.controls["intent_removed_slots"]:
            cases = deepcopy(self.intent)
            del cases["cases"][0]["expected"][slot]
            with self.subTest(slot=slot), patch.object(
                    Path, "read_text", return_value=json.dumps(cases)):
                with self.assertRaisesRegex(ValueError, "lacks nonempty gold"):
                    _load_cases(Path("unused"), "intent", True)
        cases = deepcopy(self.intent)
        cases["cases"][0].pop("semantic_contract")
        with patch.object(Path, "read_text", return_value=json.dumps(cases)):
            with self.assertRaisesRegex(ValueError, "semantic_contract"):
                _load_cases(Path("unused"), "intent", True)

    def test_intent_complete_gold_passes(self) -> None:
        expected = self.intent["cases"][0]["expected"]
        intent = {key: value for key, value in expected.items()
                  if key not in {"status", "operation", "target"}}
        intent["target_class"] = expected["target"]
        result = SimpleNamespace(status="RESOLVED", operation="find", intent=intent,
                                 used_llm=False, schema_trace={}, notes=[])
        with patch("tools.qa_bench.OntologyIndex"), patch(
                "tools.qa_bench.build_intent", return_value=result):
            self.assertEqual(self.run_captured(
                run_intent_benchmark, None, FIXTURES / "intent.json", acceptance=True)[0], 0)

    def test_intent_negative_control_rejects_dropped_conditions(self) -> None:
        case_file = FIXTURES / "intent.json"
        result = SimpleNamespace(
            status="RESOLVED",
            operation="find",
            intent={"target_class": "EquityFund"},
            used_llm=False,
            schema_trace={},
            notes=[],
        )
        with patch("tools.qa_bench.OntologyIndex"), patch(
                "tools.qa_bench.build_intent", return_value=result):
            self.assertEqual(
                run_intent_benchmark(None, case_file, use_llm=False),
                1,
            )

    def test_find_negative_controls_require_exact_entities_and_evidence(self) -> None:
        case_file = FIXTURES / "find.json"
        negative = self.controls["find"]
        for control in negative:
            with self.subTest(control=control["id"]):
                result = SimpleNamespace(
                    count=control["count"],
                    entities=control["entities"],
                    evidence={},
                    errors=[],
                )
                if control["evidence"] == "declared":
                    result.evidence = {
                        entity: {"kind": "declared", "via": "Fund", "chain": []}
                        for entity in control["entities"]
                    }
                elif control["evidence"] == "bad-inference":
                    result.evidence = {
                        entity: {"kind": "inference", "via": "Wrong", "chain": []}
                        for entity in control["entities"]
                    }
                with patch("tools.qa_bench.plan_find", return_value={"target": {"concept": "Fund"}}), \
                     patch("tools.qa_bench.execute_find", return_value=result):
                    code, output = self.run_captured(
                        run_find_benchmark, SimpleNamespace(tbox=None, abox=None), case_file)
                    self.assertEqual(code, 1)
                    self.assertIn("[FAIL] FIND-TOY", output)
                    self.assertNotIn("[ERROR]", output)

    def test_find_valid_entities_pass_and_missing_gold_is_legacy_only(self) -> None:
        entities = json.loads((FIXTURES / "find.json").read_text())["cases"][0]["expected"]["entities"]
        result = SimpleNamespace(count=2, entities=entities, errors=[], evidence={
            entity: {"kind": "declared", "via": "Fund", "chain": []} for entity in entities})
        with patch("tools.qa_bench.plan_find", return_value={"target": {"concept": "Fund"}}), \
             patch("tools.qa_bench.execute_find", return_value=result):
            self.assertEqual(self.run_captured(
                run_find_benchmark, SimpleNamespace(tbox=None, abox=None),
                FIXTURES / "find.json", acceptance=True)[0], 0)
        cases = {"cases": [{"id": "legacy", "target": "Fund", "expected": {"count": 2}}]}
        with patch.object(Path, "read_text", return_value=json.dumps(cases)):
            self.assertEqual(len(_load_cases(Path("unused"), "find")), 1)
            with self.assertRaisesRegex(ValueError, "expected.entities"):
                _load_cases(Path("unused"), "find", True)

    def test_successful_answers_require_reports(self) -> None:
        for report_case in self.controls["reports"]:
            with self.subTest(report_case=report_case["id"]):
                self.assertTrue(_report_problems(report_case["report"]))

    def test_valid_report_passes_report_contract(self) -> None:
        report = json.loads((FIXTURES / "answers.json").read_text())["valid_report"]
        self.assertEqual(_report_problems(report), [])

    def test_successful_stage_answers_without_report_fail(self) -> None:
        for stage, runner, target in (
                ("e2e", run_e2e_benchmark, "tools.qa_bench.answer"),
                ("citation", run_citation_benchmark, "fondontology.qa.engine.answer_question"),
                ("explain", run_explain_benchmark, "fondontology.qa.engine.answer_question")):
            for report_control in self.controls["reports"]:
                cases = {"cases": [self.answers[stage]["cases"][0]]}
                result = SimpleNamespace(status="ok", text="toy 共找到 2 个", kind="explain",
                                         verdict=None, report=report_control["report"],
                                         explanation={"gate": "template", "ucr": 0})
                with self.subTest(stage=stage, control=report_control["id"]), \
                     patch.object(Path, "read_text", return_value=json.dumps(cases)), \
                     patch(target, return_value=result):
                    code, output = self.run_captured(runner, None, Path("unused"))
                    self.assertEqual(code, 1)
                    self.assertIn("[FAIL]", output)
                    self.assertNotIn("[ERROR]", output)
                    self.assertNotIn("Completeness 100%", output)

    def test_no_evidence_assertions_does_not_claim_completeness(self) -> None:
        for stage, runner, target in (
                ("e2e", run_e2e_benchmark, "tools.qa_bench.answer"),
                ("citation", run_citation_benchmark, "fondontology.qa.engine.answer_question"),
                ("explain", run_explain_benchmark, "fondontology.qa.engine.answer_question")):
            case = self.answers[stage]["cases"][1]
            result = SimpleNamespace(status=case["expected"]["status"], text="", kind="intent",
                                     verdict=None, report=None, explanation=None)
            with self.subTest(stage=stage), patch.object(
                    Path, "read_text", return_value=json.dumps({"cases": [case]})), \
                 patch(target, return_value=result):
                code, output = self.run_captured(runner, None, Path("unused"))
                self.assertEqual(code, 0)
                self.assertNotIn("Completeness 100%", output)

    def test_case_errors_keep_denominator_and_continue(self) -> None:
        cases = deepcopy(self.intent)
        second = deepcopy(cases["cases"][0])
        second["id"] = "SECOND"
        cases["cases"].append(second)
        expected = second["expected"]
        result = SimpleNamespace(
            status="RESOLVED", operation="find", used_llm=False, schema_trace={}, notes=[],
            intent={"target_class": "EquityFund", "date_ranges": expected["date_ranges"],
                    "filters": expected["filters"]})
        with patch.object(Path, "read_text", return_value=json.dumps(cases)), \
             patch("tools.qa_bench.OntologyIndex"), \
             patch("tools.qa_bench.build_intent", side_effect=[RuntimeError("toy error"), result]) as build:
            code, output = self.run_captured(run_intent_benchmark, None, Path("unused"))
            self.assertEqual(code, 1)
            self.assertEqual(build.call_count, 2)
            self.assertIn("1/2", output)
            self.assertIn("[ERROR] INTENT-CONDITIONS", output)

    def test_explicit_online_requires_configuration_and_rejects_fallback(self) -> None:
        with patch("fondontology.qa.config.llm_configured", return_value=False), \
             patch("tools.qa_bench.build_intent") as build:
            code, output = self.run_captured(
                run_intent_benchmark, None, FIXTURES / "intent.json",
                use_llm=True, require_online=True)
            self.assertEqual(code, 1)
            self.assertIn("online benchmark unavailable", output)
            build.assert_not_called()

    def test_cli_acceptance_is_forwarded_and_deterministic_has_no_spot_call(self) -> None:
        stack = SimpleNamespace(tbox=[], abox=[], snapshot=SimpleNamespace(ontology_version="toy"))
        with patch("tools.qa_bench.build_stack", return_value=stack), \
             patch("tools.qa_bench.run_intent_benchmark", return_value=0) as runner, \
             patch("tools.qa_bench.run_intent_llm_spot") as spot:
            self.assertEqual(self.run_captured(
                main, ["--stage", "intent", "--acceptance", "--cqs",
                       str(FIXTURES / "intent.json")])[0], 0)
            self.assertTrue(runner.call_args.kwargs["acceptance"])
            self.assertFalse(runner.call_args.kwargs["use_llm"])
            spot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
