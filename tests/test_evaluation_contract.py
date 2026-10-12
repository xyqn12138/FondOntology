from __future__ import annotations

import copy
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fondontology.evaluation import ContractError, SkipCase, load_suite, run_suite, save_run, validate_case
from fondontology.evaluation.adapters import ReplayAdapter, RulesIntentAdapter
from fondontology.evaluation.contracts import Suite, content_hash, read_json
from fondontology.evaluation.matchers import evaluate_case

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/manifests/synthetic_contract.json"
METADATA = {
    "corpus": "synthetic", "ontology": "none", "code": "test-only",
    "model": "none", "prompt": "none", "execution_config": {"online_execution": False},
}


class EvaluationContractTest(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite(MANIFEST)
        self.case = copy.deepcopy(self.suite.cases[0])
        self.actual = read_json(ROOT / "evaluation/examples/synthetic_actuals.json")[self.case["case_id"]]

    def passed(self, actual):
        return all(assertion["passed"] for assertion in evaluate_case(self.case, actual))

    def test_correct_structured_answer(self):
        self.assertTrue(self.passed(self.actual))

    def test_wrong_ids_same_count_and_duplicates_fail(self):
        for entities in (["wrong-A", "wrong-B"], ["F-A", "F-A"], ["F-A"], ["F-A", "F-B", "F-C"]):
            with self.subTest(entities=entities):
                actual = copy.deepcopy(self.actual)
                actual["entities"] = entities
                self.assertFalse(self.passed(actual))

    def test_missing_threshold_date_unit_manager_change_order_fail(self):
        for field in ("threshold", "as_of", "unit", "ordering", "manager_changed"):
            with self.subTest(field=field):
                actual = copy.deepcopy(self.actual)
                del actual["slots"][field]
                self.assertFalse(self.passed(actual))
        for field, value in (("unit", "basis_points"), ("as_of", "2024-12-31"),
                             ("ordering", ["F-A", "F-B"]), ("threshold", "20"),
                             ("manager_changed", 1)):
            with self.subTest(field=field, value=value):
                actual = copy.deepcopy(self.actual)
                actual["slots"][field] = value
                self.assertFalse(self.passed(actual))

    def test_missing_wrong_version_or_incomplete_evidence_fail(self):
        for references in ([], self.actual["evidence"][:1],
                           [{"source_version": "fictional-document-v2", "locator": "table:1/row:F-A"}]):
            with self.subTest(references=references):
                actual = copy.deepcopy(self.actual)
                actual["evidence"] = references
                self.assertFalse(self.passed(actual))
        actual = copy.deepcopy(self.actual)
        del actual["evidence"]
        self.assertFalse(self.passed(actual))

    def test_equivalent_evidence_group_can_pass(self):
        self.case["oracle"]["matchers"][-1]["expected"].append(
            [{"source_version": "alternative-v1", "locator": "page:2"}])
        actual = copy.deepcopy(self.actual)
        actual["evidence"] = [{"source_version": "alternative-v1", "locator": "page:2"}]
        self.assertTrue(self.passed(actual))

    def test_answerable_refusal_and_ambiguous_guess_fail(self):
        actual = copy.deepcopy(self.actual)
        actual["status"] = "refused"
        self.assertFalse(self.passed(actual))
        clarification = self.suite.cases[1]
        self.assertFalse(all(item["passed"] for item in evaluate_case(clarification, self.actual)))
        self.assertFalse(all(item["passed"] for item in evaluate_case(clarification, {"status": "refused"})))

    def test_non_answer_cannot_carry_factual_answer(self):
        clarification = self.suite.cases[1]
        for payload in (
            {"status": "clarification", "entities": ["F-A"]},
            {"status": "clarification", "slots": {"threshold": 20}},
            {"status": "clarification", "evidence": self.actual["evidence"]},
        ):
            with self.subTest(payload=payload):
                self.assertFalse(all(item["passed"] for item in evaluate_case(clarification, payload)))
        case = copy.deepcopy(clarification)
        case["oracle"]["matchers"] = [
            {"matcher": "status", "expected": "empty"}, {"matcher": "entity_set", "expected": []}]
        self.assertFalse(all(item["passed"] for item in evaluate_case(case, {"status": "empty"})))
        self.assertTrue(all(item["passed"] for item in evaluate_case(case, {"status": "empty", "entities": []})))
        for extra in ({"slots": {"threshold": 20}}, {"evidence": self.actual["evidence"]}):
            self.assertFalse(all(item["passed"] for item in evaluate_case(
                case, {"status": "empty", "entities": [], **extra})))

    def test_unknown_fields_fail_closed(self):
        for target in ("case", "inputs", "oracle", "matcher", "slot", "provenance"):
            with self.subTest(target=target):
                case = copy.deepcopy(self.case)
                mapping = {
                    "case": case, "inputs": case["inputs"], "oracle": case["oracle"],
                    "matcher": case["oracle"]["matchers"][0],
                    "slot": case["oracle"]["matchers"][2]["expected"][0],
                    "provenance": case["provenance"],
                }
                mapping[target]["unsupported"] = True
                with self.assertRaises(ContractError):
                    validate_case(case)
        actual = copy.deepcopy(self.actual)
        actual["count"] = 2
        self.assertFalse(self.passed(actual))

    def test_unknown_matcher_missing_gold_and_invalid_type_fail(self):
        mutations = [
            lambda case: case["oracle"]["matchers"][0].update(matcher="keyword"),
            lambda case: case["oracle"].update(matchers=[]),
            lambda case: case.update(schema_version="2.0"),
            lambda case: case.update(eligible=1),
            lambda case: case["oracle"].update(matchers=[{"matcher": "status", "expected": "answered"}]),
            lambda case: case["oracle"]["matchers"][2]["expected"][0].update(value="2025-99-99"),
            lambda case: case["oracle"]["matchers"][2]["expected"][1].update(value=True),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                case = copy.deepcopy(self.case)
                mutation(case)
                with self.assertRaises(ContractError):
                    validate_case(case)

    def test_empty_duplicate_ineligible_suite_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = copy.deepcopy(self.suite.manifest)
            manifest["case_files"] = ["cases.json"]
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            ineligible = copy.deepcopy(self.case)
            ineligible["eligible"] = False
            for cases in ([], [self.case, self.case], [ineligible]):
                with self.subTest(cases=cases):
                    (root / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
                    with self.assertRaises(ContractError):
                        load_suite(manifest_path)

    def test_manifest_case_paths_cannot_escape_by_traversal_or_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = copy.deepcopy(self.suite.manifest)
            manifest["allow_external_case_files"] = False
            manifest["case_files"] = ["../outside.json"]
            manifest_path = root / "nested" / "manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "outside.json").write_text(json.dumps([self.case]), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_suite(manifest_path)

            try:
                symlink = manifest_path.parent / "linked.json"
                symlink.symlink_to(root / "outside.json")
            except (OSError, NotImplementedError):
                symlink = None
            if symlink is not None:
                manifest["case_files"] = ["linked.json"]
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ContractError):
                    load_suite(manifest_path)

    def test_manifest_external_case_files_require_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = copy.deepcopy(self.suite.manifest)
            manifest.pop("allow_external_case_files", None)
            manifest["case_files"] = ["../cases.json"]
            manifest_path = root / "nested" / "manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "cases.json").write_text(json.dumps([self.case]), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_suite(manifest_path)
            manifest["allow_external_case_files"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(len(load_suite(manifest_path).cases), 1)

    def test_manifest_external_opt_in_must_be_boolean_and_does_not_allow_rooted_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = copy.deepcopy(self.suite.manifest)
            manifest["case_files"] = ["cases.json"]
            manifest_path = root / "manifest.json"
            (root / "cases.json").write_text(json.dumps([self.case]), encoding="utf-8")
            for value in (None, 0, "true"):
                with self.subTest(value=value):
                    manifest["allow_external_case_files"] = value
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaises(ContractError):
                        load_suite(manifest_path)
            manifest["allow_external_case_files"] = True
            manifest["case_files"] = [str(root / "cases.json")]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_suite(manifest_path)

    def test_json_duplicate_keys_nonfinite_and_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "input.json"
            for raw in ('{"status":"answered","status":"refused"}', '{"value":NaN}'):
                path.write_text(raw, encoding="utf-8")
                with self.assertRaises(ContractError):
                    read_json(path)
            manifest = copy.deepcopy(self.suite.manifest)
            manifest["case_files"] = ["cases.jsonl"]
            path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "cases.jsonl").write_text(json.dumps(self.case) + "\n", encoding="utf-8")
            self.assertEqual(len(load_suite(path).cases), 1)

    def test_mutated_suite_fail(self):
        self.suite.cases[0]["inputs"]["question"] = "mutated"
        with self.assertRaises(ContractError):
            run_suite(self.suite, lambda inputs: self.actual, mode="replay", metadata=METADATA)

    def test_runner_fixed_denominator_errors_timeouts_skips_not_run(self):
        for exception, expected in ((RuntimeError("boom"), "error"), (TimeoutError("late"), "timeout"),
                                    (SkipCase("missing dependency"), "skip")):
            with self.subTest(expected=expected):
                def adapter(inputs):
                    self.assertNotIn("oracle", inputs)
                    raise exception
                run = run_suite(self.suite, adapter, mode="replay", metadata=METADATA)
                self.assertEqual(run.eligible_count, 2)
                self.assertEqual(run.summary()["outcomes"][expected], 2)
                self.assertEqual(run.summary()["success_rate"], 0)
        run = run_suite(self.suite, lambda inputs: self.actual, mode="replay",
                        metadata=METADATA, max_cases=0)
        self.assertEqual(run.summary()["outcomes"]["not_run"], 2)
        self.assertEqual(run.eligible_count, 2)

    def test_stop_on_error_not_run_keeps_denominator(self):
        def adapter(inputs):
            raise RuntimeError("boom")
        run = run_suite(self.suite, adapter, mode="replay", metadata=METADATA, stop_on_error=True)
        self.assertEqual([result.outcome for result in run.results], ["error", "not_run"])
        self.assertEqual(run.summary()["eligible_count"], 2)

    def test_elapsed_timeout_not_success(self):
        with patch("fondontology.evaluation.runner.time.monotonic", side_effect=[0.0, 2.0, 2.0]):
            run = run_suite(self.suite, lambda inputs: self.actual, mode="replay", metadata=METADATA,
                            timeout_seconds=1.0, max_cases=1)
        self.assertEqual(run.results[0].outcome, "timeout")
        self.assertEqual(run.summary()["success_rate"], 0)
        self.assertEqual(
            run.metadata["execution_config"]["timeout_enforcement"],
            "hard deadline not enforced; elapsed check only",
        )

    def test_sqlite_only_results_and_hashes_metadata(self):
        adapter = ReplayAdapter(ROOT / "evaluation/examples/synthetic_actuals.json", self.suite.cases)
        run = run_suite(self.suite, adapter, mode="replay", metadata=METADATA)
        self.assertEqual(run.summary()["passed"], 2)
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "evaluation.sqlite"
            save_run(database, run)
            with closing(sqlite3.connect(database)) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertEqual(tables, {"eval_runs", "case_results"})
                stored = connection.execute("SELECT mode, eligible_count, metadata_json FROM eval_runs").fetchone()
                self.assertEqual(stored[:2], ("replay", 2))
                self.assertEqual(json.loads(stored[2])["model"], "none")
                hashes = connection.execute("SELECT case_hash FROM case_results ORDER BY case_id").fetchall()
                self.assertEqual(len(hashes), 2)
                self.assertTrue(all(len(row[0]) == 64 for row in hashes))
                columns = {row[1] for row in connection.execute("PRAGMA table_info(case_results)")}
                self.assertNotIn("oracle", columns)

    def test_rules_adapter_rejects_unconsumed_inputs_and_kills_timeout(self):
        adapter = RulesIntentAdapter(ROOT / "ontology/modules/cnfo-domain.ttl", None, timeout_seconds=1)
        inputs = {"question": "test", "dataset_snapshot": "test", "allowed_capabilities": ["intent"]}
        with patch("fondontology.evaluation.adapters.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("rules", 1)) as mocked:
            with self.assertRaises(TimeoutError):
                adapter(inputs)
            self.assertEqual(mocked.call_args.kwargs["timeout"], 1)
            payload = json.loads(mocked.call_args.kwargs["input"])
            self.assertEqual(payload, {"question": "test"})
        for extra in ({"as_of": "2025-12-31"}, {"allowed_capabilities": ["answer"]}):
            with self.subTest(extra=extra):
                with self.assertRaises(ContractError):
                    adapter({**inputs, **extra})

    def test_rules_mode_cannot_execute_answer_or_claim_model(self):
        with self.assertRaises(ContractError):
            run_suite(self.suite, lambda inputs: self.actual, mode="rules_intent", metadata=METADATA)
        with self.assertRaises(ContractError):
            run_suite(self.suite, lambda inputs: self.actual, mode="rules_intent",
                      metadata={**METADATA, "model": "pretend-online"})

    def test_rules_runner_requires_explicit_no_model_actual(self):
        suite = load_suite(ROOT / "evaluation/manifests/synthetic_intent.json")
        actual = {
            "status": "intent_only", "intent_status": "RESOLVED",
            "slots": {"operation": "find", "intent": {
                "target_class": "https://ontology.example.cn/cnfo/ontology/ExchangeTradedFund", "filters": []}},
        }
        for used_llm in (True, None, 0):
            with self.subTest(used_llm=used_llm):
                payload = {**actual, "used_llm": used_llm} if used_llm is not None else actual
                run = run_suite(suite, lambda inputs: payload, mode="rules_intent", metadata=METADATA)
                self.assertEqual(run.results[0].outcome, "error")
        run = run_suite(suite, lambda inputs: {**actual, "used_llm": False},
                        mode="rules_intent", metadata=METADATA)
        self.assertEqual(run.results[0].outcome, "pass")

    def test_replay_cli_is_explicitly_not_e2e(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tools/evaluate_qa.py"), "--mode", "replay",
                 "--manifest", str(MANIFEST), "--actuals",
                 str(ROOT / "evaluation/examples/synthetic_actuals.json"), "--database",
                 str(Path(directory) / "runs.sqlite")],
                text=True, encoding="utf-8", capture_output=True, timeout=30, cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = json.loads(completed.stdout)
            self.assertEqual(output["summary"]["mode"], "replay")
            self.assertFalse(output["summary"]["business_e2e"])
            self.assertEqual(output["summary"]["eligible_count"], 2)
            self.assertEqual(output["summary"]["execution_origin"], "recorded_unverified")

    def test_schema_and_readme_mark_portable_structural_only_contract(self):
        schema_text = (ROOT / "evaluation/schemas/case.schema.json").read_text(encoding="utf-8")
        manifest_schema = (ROOT / "evaluation/schemas/manifest.schema.json").read_text(encoding="utf-8")
        result_schema = (ROOT / "evaluation/schemas/result.schema.json").read_text(encoding="utf-8")
        readme = (ROOT / "evaluation/README.md").read_text(encoding="utf-8")
        self.assertIn('"$comment": "Portable schema is structural-only;', schema_text)
        self.assertIn('"$comment": "Portable schema is structural-only;', manifest_schema)
        self.assertIn('"$comment": "Portable schema is structural-only;', result_schema)
        self.assertIn("portable schema is structural-only", readme)
        self.assertIn("recorded_unverified", readme)
        self.assertIn("used_llm=true` or `false`", readme)

    def test_replay_used_llm_claim_does_not_verify_recording_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actuals.json"
            for used_llm in (True, False):
                with self.subTest(used_llm=used_llm):
                    actuals = read_json(ROOT / "evaluation/examples/synthetic_actuals.json")
                    for actual in actuals.values():
                        actual["used_llm"] = used_llm
                    path.write_text(json.dumps(actuals), encoding="utf-8")
                    run = run_suite(self.suite, ReplayAdapter(path, self.suite.cases),
                                    mode="replay", metadata=METADATA)
                    self.assertEqual(run.summary()["passed"], 2)
                    self.assertEqual(run.summary()["execution_origin"], "recorded_unverified")
                    self.assertFalse(run.summary()["business_e2e"])


if __name__ == "__main__":
    unittest.main()
