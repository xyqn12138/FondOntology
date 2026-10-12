from __future__ import annotations

import json
import asyncio
import copy
import os
import sqlite3
import subprocess
import sys
import tempfile
import types
from contextlib import closing
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fondontology.evaluation.ragas_runner import (
    MetricResult, RagasInputError, _build_components, _score_row, evaluate, load_input, merge_references,
    save_results, summarize, validate_payload, resolve_judge_config, _response_diagnostic,
)


PROVENANCE = {
    "dataset_snapshot": "docs-v1", "corpus_version": "v1",
    "ontology_version": "o1", "code_version": "test",
    "retrieval_config": {"top_k": 3},
    "llm": {"provider": "none", "model": "none", "prompt_version": "none", "used_llm": False},
    "execution_origin": "recorded_unverified",
}
ROW = {"id": "a1", "user_input": "What?", "response": "Answer",
       "retrieved_contexts": ["Context"]}


class RagasRunnerTest(unittest.TestCase):
    def test_validate_rejects_duplicate_keys_and_unknowns(self):
        with self.assertRaises(RagasInputError):
            load_input(Path(self._write('{"schema_version":"1.0","schema_version":"1.0"}')))
        payload = {"schema_version": "1.0", "provenance": PROVENANCE,
                   "rows": [{**ROW, "unknown": 1}]}
        with self.assertRaises(RagasInputError):
            validate_payload(payload)

    def test_dry_run_has_fixed_denominator_and_no_scores(self):
        payload = evaluate(PROVENANCE, [ROW], execute=False)
        self.assertEqual(payload["summary"]["metrics"]["faithfulness"]["denominator"], 1)
        self.assertIsNone(payload["summary"]["metrics"]["faithfulness"]["mean"])
        self.assertTrue(all(item["status"] == "unavailable" for item in payload["results"]))

    @patch.dict("os.environ", {}, clear=True)
    def test_execute_missing_config_is_unavailable(self):
        payload = evaluate(PROVENANCE, [ROW], execute=True)
        self.assertTrue(all(item["status"] == "unavailable" for item in payload["results"]))

    def test_json_rejects_nonfinite_overflow_and_duplicate_rows(self):
        for invalid in ("NaN", "Infinity", "1e999"):
            payload = json.dumps({"schema_version": "1.0", "provenance": PROVENANCE, "rows": [ROW]})
            payload = payload.replace('"top_k": 3', f'"top_k": {invalid}')
            with self.subTest(invalid=invalid), self.assertRaises(RagasInputError):
                load_input(Path(self._write(payload)))
        with self.assertRaises(RagasInputError):
            validate_payload({"schema_version": "1.0", "provenance": PROVENANCE, "rows": [ROW, ROW]})
        record = {"schema_version": "1.0", "provenance": PROVENANCE, **ROW}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            path.write_text(json.dumps(record) + "\n" + json.dumps(record), encoding="utf-8")
            with self.assertRaises(RagasInputError):
                load_input(path)

    def test_unknown_nested_fields_and_missing_provenance_fail_closed(self):
        for field in ("provenance", "llm"):
            payload = copy.deepcopy({"schema_version": "1.0", "provenance": PROVENANCE, "rows": [ROW]})
            target = payload["provenance"] if field == "provenance" else payload["provenance"]["llm"]
            target["secret"] = "forbidden"
            with self.subTest(field=field), self.assertRaises(RagasInputError):
                validate_payload(payload)

    def test_reference_merge_is_offline_and_never_overwrites(self):
        path = Path(self._write(json.dumps({
            "schema_version": "1.0", "rows": [{"id": ROW["id"], "reference": "Gold",
                                             "review_status": "reviewed"}],
        })))
        rows, review = merge_references([ROW], path)
        self.assertNotIn("reference", ROW)
        self.assertEqual(rows[0]["reference"], "Gold")
        self.assertEqual(review, {"a1": "reviewed"})
        with self.assertRaises(RagasInputError):
            merge_references(rows, path)
        path = Path(self._write(json.dumps({
            "schema_version": "1.0", "rows": [{"id": "unknown", "reference": "Gold"}],
        })))
        with self.assertRaises(RagasInputError):
            merge_references([ROW], path)

    def test_fixed_denominator_does_not_hide_nan_errors_or_missing_scores(self):
        results = [
            MetricResult("a1", "faithfulness", "ok", value=1.0),
            MetricResult("a2", "faithfulness", "unavailable", error="non-finite"),
        ]
        summary = summarize(results, 2, ("faithfulness",))["metrics"]["faithfulness"]
        self.assertEqual(summary["denominator"], 2)
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(summary["unavailable"], 1)
        self.assertIsNone(summary["mean"])

    def test_no_component_construction_or_network_during_dry_run(self):
        with patch("fondontology.evaluation.ragas_runner._build_components",
                   side_effect=AssertionError("must not build components")):
            payload = evaluate(PROVENANCE, [ROW], execute=False)
        self.assertFalse(payload["execution"]["network_authorized"])
        self.assertEqual(payload["execution"]["mode"], "validate_only")
        self.assertEqual(os.environ["RAGAS_DO_NOT_TRACK"], "true")
        self.assertEqual(len(payload["input_sha256"]), 64)
        self.assertTrue(all(len(item["row_sha256"]) == 64 for item in payload["results"]))

    def test_budget_validation(self):
        for options in (
            {"timeout": float("nan")}, {"timeout": 121}, {"max_calls": 0},
            {"max_tokens": 8193}, {"max_rows": 0}, {"metrics": ("fake",)},
        ):
            with self.subTest(options=options), self.assertRaises(RagasInputError):
                evaluate(PROVENANCE, [ROW], **options)

    @patch.dict(os.environ, {"RAGAS_JUDGE_MODEL": "independent", "RAGAS_JUDGE_API_KEY": "private",
                            "OPENAI_API_KEY": "project-private"}, clear=True)
    def test_model_override_keeps_independent_credentials_and_environment(self):
        before = dict(os.environ)
        config = resolve_judge_config(judge_model="deepseek-v4.1-flash")
        self.assertEqual(config.model, "deepseek-v4.1-flash")
        self.assertEqual(config.api_key, "private")
        self.assertEqual(config.credential_policy, "independent_ragas_environment")
        self.assertEqual(dict(os.environ), before)
        report = evaluate(PROVENANCE, [ROW], judge_config=config)
        self.assertTrue(report["execution"]["judge_model_override"])
        self.assertNotIn("private", json.dumps(report))

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_project_reuse_does_not_load_environment_or_modify_file(self):
        with patch("dotenv.dotenv_values", return_value={
            "OPENAI_MODEL": "project-model", "OPENAI_API_KEY": "secret",
            "API_BASE": "https://offline.invalid",
        }) as loader:
            independent = resolve_judge_config()
            loader.assert_not_called()
            self.assertIsNone(independent.api_key)
            config = resolve_judge_config(reuse_project_model=True, judge_model="judge-only")
        self.assertEqual(config.model, "judge-only")
        self.assertEqual(config.api_key, "secret")
        self.assertEqual(config.base_url, "https://offline.invalid")
        self.assertEqual(config.credential_policy, "explicit_process_local_project_reuse")
        self.assertFalse(os.environ)
        self.assertNotIn("secret", repr(config))

    def test_cli_verification_precedes_config_and_judge(self):
        from tools.evaluate_ragas import main
        input_path = Path(self._write(json.dumps({
            "schema_version": "1.0", "provenance": PROVENANCE, "rows": [ROW],
        })))
        with patch("tools.evaluate_ragas.resolve_judge_config") as resolver, \
             patch("fondontology.evaluation.artifact_audit.audit_artifact",
                   side_effect=RagasInputError("invalid trace")), \
             patch("tools.evaluate_ragas.evaluate") as runner:
            self.assertEqual(main(["--input", str(input_path), "--execute",
                                   "--reuse-project-model", "--verify-trace",
                                   "--corpus-db", "absent.sqlite"]), 2)
            resolver.assert_not_called()
            runner.assert_not_called()

    def test_cli_execution_limits_fail_before_config(self):
        from tools.evaluate_ragas import main
        for options in ([], ["--verify-trace", "--timeout", "91"],
                        ["--verify-trace", "--max-judge-calls", "19"],
                        ["--verify-trace", "--max-rows", "4"]):
            with self.subTest(options=options), patch("tools.evaluate_ragas.resolve_judge_config") as resolver:
                self.assertEqual(main(["--input", "absent.json", "--execute", *options]), 2)
                resolver.assert_not_called()

    @patch.dict(os.environ, {"LLM_THINKING": "false", "LLM_THINKING_PARAM": "thinking"}, clear=True)
    def test_thinking_is_explicit_provider_parameter_and_never_inherited(self):
        self.assertEqual(resolve_judge_config().extra_body, {})
        for parameter, expected in (
            ("enable_thinking", {"enable_thinking": False}),
            ("thinking", {"thinking": {"type": "disabled"}}),
        ):
            config = resolve_judge_config(judge_thinking="disabled", judge_thinking_param=parameter)
            self.assertEqual(config.extra_body, expected)
            report = evaluate(PROVENANCE, [ROW], judge_config=config)
            self.assertEqual(report["execution"]["judge_request_extra_body"], expected)
        for options in ({"judge_thinking": "disabled"}, {"judge_thinking_param": "enable_thinking"},
                        {"judge_thinking": "enabled"}):
            with self.subTest(options=options), self.assertRaises(RagasInputError):
                resolve_judge_config(**options)

    def test_provider_diagnostics_never_record_generated_content_or_secrets(self):
        diagnostic = _response_diagnostic({
            "model": "deepseek-v4.1-flash", "secret": "private",
            "usage": {"prompt_tokens": 10, "completion_tokens": 4096, "total_tokens": 4106,
                      "private": "secret", "completion_tokens_details": {"reasoning_tokens": 4095,
                                                                        "secret": "private"}},
            "choices": [{"finish_reason": "length", "message": {"content": "private",
                                                               "reasoning_content": "secret"}}],
        }, 200)
        self.assertEqual(diagnostic["choices"][0]["finish_reason"], "length")
        self.assertEqual(diagnostic["usage"]["completion_tokens_details"]["reasoning_tokens"], 4095)
        self.assertNotIn("private", json.dumps(diagnostic))
        self.assertNotIn("secret", json.dumps(diagnostic))
        self.assertEqual(_response_diagnostic({"error": "private"}, 400), {"http_status": 400})

    def test_real_ragas_api_adapter_uses_official_classes_and_exact_fields(self):
        calls = []

        class FakeMetric:
            def __init__(self, **kwargs):
                self.options = kwargs

            async def ascore(self, **kwargs):
                calls.append(kwargs)
                return types.SimpleNamespace(value=0.75)

        row = {**ROW, "reference": "Gold"}
        with patch("fondontology.evaluation.ragas_runner._metric_classes", return_value=(FakeMetric,) * 4):
            results = asyncio.run(_score_row(row, object(), object(), 1, (
                "faithfulness", "context_precision", "context_recall", "response_relevancy",
            )))
        self.assertTrue(all(item.status == "ok" and item.value == 0.75 for item in results))
        self.assertEqual(calls[0], {"user_input": "What?", "response": "Answer", "retrieved_contexts": ["Context"]})
        self.assertEqual(calls[1], {"user_input": "What?", "reference": "Gold", "retrieved_contexts": ["Context"]})
        self.assertNotIn("reference", calls[-1])

    def test_api_adapter_preserves_nan_error_timeout_missing_reference_embedding(self):
        outcomes = iter((float("nan"), RuntimeError("must not echo secret"), asyncio.TimeoutError()))

        class FakeMetric:
            def __init__(self, **kwargs):
                pass

            async def ascore(self, **kwargs):
                outcome = next(outcomes)
                if isinstance(outcome, Exception):
                    raise outcome
                return types.SimpleNamespace(value=outcome)

        with patch("fondontology.evaluation.ragas_runner._metric_classes", return_value=(FakeMetric,) * 4):
            results = asyncio.run(_score_row({**ROW, "reference": "Gold"}, object(), None, 1, (
                "faithfulness", "context_precision", "context_recall", "response_relevancy",
            )))
            missing = asyncio.run(_score_row(ROW, object(), None, 1, (
                "context_precision", "context_recall", "response_relevancy",
            )))
        self.assertEqual([item.status for item in results], ["unavailable", "error", "timeout", "unavailable"])
        self.assertNotIn("secret", results[1].error)
        self.assertTrue(all(item.status == "unavailable" for item in missing))

    def test_json_sqlite_and_cli_dryrun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            input_path.write_text(json.dumps({"schema_version": "1.0", "provenance": PROVENANCE,
                                             "rows": [ROW]}), encoding="utf-8")
            output_path = root / "output.json"
            database = root / "runs.sqlite"
            completed = subprocess.run([
                sys.executable, str(Path(__file__).resolve().parents[1] / "tools/evaluate_ragas.py"),
                "--input", str(input_path), "--output", str(output_path), "--database", str(database),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(json.loads(output_path.read_text()), result)
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM ragas_runs").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT count(*) FROM ragas_results").fetchone()[0], 4)
            save_results(database, result)
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM ragas_results").fetchone()[0], 4)

    def test_installed_official_ragas_with_mocked_judge_negative_control(self):
        os.environ["RAGAS_DO_NOT_TRACK"] = "true"
        try:
            from ragas.llms.base import InstructorBaseRagasLLM
            from ragas.embeddings.base import BaseRagasEmbedding
        except ImportError:
            self.skipTest("optional compatible ragas package not installed")
        outputs = json.loads((Path(__file__).parent / "fixtures/ragas/judge_outputs.json").read_text())

        class OfflineJudge(InstructorBaseRagasLLM):
            def generate(self, prompt, response_model):
                raise AssertionError("no synchronous calls")

            async def agenerate(self, prompt, response_model):
                return response_model.model_validate(outputs[response_model.__name__])

        class OfflineEmbedding(BaseRagasEmbedding):
            def embed_text(self, text, **kwargs):
                return [1.0, 0.0]

            async def aembed_text(self, text, **kwargs):
                return [1.0, 0.0]

        results = asyncio.run(_score_row(
            {**ROW, "reference": "Gold"}, OfflineJudge(), OfflineEmbedding(), 5,
            ("faithfulness", "context_precision", "context_recall", "response_relevancy"),
        ))
        self.assertEqual([item.status for item in results], ["ok"] * 4)
        self.assertEqual([item.value for item in results], [0.0, 0.0, 0.0, 1.0])

    def test_installed_component_budget_does_not_inherit_production_embedding_credentials(self):
        os.environ["RAGAS_DO_NOT_TRACK"] = "true"
        try:
            import ragas
        except ImportError:
            self.skipTest("optional compatible ragas package not installed")
        with patch.dict(os.environ, {
            "RAGAS_JUDGE_MODEL": "fake-offline-model", "RAGAS_JUDGE_API_KEY": "synthetic-secret",
            "OPENAI_API_KEY": "production-secret", "OPENAI_EMBEDDING_MODEL": "production-embedding",
        }, clear=True):
            os.environ["RAGAS_DO_NOT_TRACK"] = "true"
            judge, embeddings, error, clients = _build_components(1, 256, 1)
            self.assertIsNone(error)
            self.assertIsNone(embeddings)
            self.assertEqual(judge.wrapped.model_args["max_tokens"], 256)
            self.assertEqual(judge.wrapped.model_args["max_retries"], 1)
            override = resolve_judge_config(judge_thinking="disabled", judge_thinking_param="enable_thinking")
            explicit, _, _, extra_clients = _build_components(1, 256, 1, override)
            self.assertEqual(explicit.wrapped.model_args["extra_body"], {"enable_thinking": False})
            async def exercise():
                with patch.object(judge.wrapped, "agenerate", new=AsyncMock(return_value="offline")):
                    self.assertEqual(await judge.agenerate("prompt", object()), "offline")
                    with self.assertRaises(RagasInputError):
                        await judge.agenerate("second prompt", object())
                    self.assertEqual(judge.calls, 1)
                    self.assertEqual(judge.stages[0]["status"], "ok")
                    self.assertNotIn("prompt", judge.stages[0])
                    self.assertEqual(judge.stages[0]["prompt_characters"], 6)
                    self.assertEqual(len(judge.stages[0]["prompt_sha256"]), 64)
                judge.calls = 0
                with patch.object(judge.wrapped, "agenerate", new=AsyncMock(side_effect=asyncio.CancelledError())):
                    with self.assertRaises(asyncio.CancelledError):
                        await judge.agenerate("cancelled", object())
                    self.assertEqual(judge.stages[-1]["status"], "cancelled")
                for client in clients + extra_clients:
                    await client.close()
            asyncio.run(exercise())

    def test_cli_rejects_destructive_output_aliases(self):
        from tools.evaluate_ragas import validate_paths
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            refs = Path(directory) / "refs.json"
            output = Path(directory) / "output.json"
            for destinations in ((source, None), (refs, None), (output, output)):
                with self.subTest(destinations=destinations), self.assertRaises(RagasInputError):
                    validate_paths(source, refs, *destinations)

    def _write(self, text: str) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name


if __name__ == "__main__":
    unittest.main()
