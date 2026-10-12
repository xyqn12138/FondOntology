"""Strict, optional Ragas evaluation for externally recorded RAG rows.

The module deliberately does not execute the production pipeline.  It evaluates
rows supplied by JSON/JSONL and labels missing dependencies/configuration as
``unavailable`` instead of manufacturing scores.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from dataclasses import dataclass, asdict, field
from contextlib import closing
from pathlib import Path
from typing import Any

RAGAS_VERSION = "0.4.3"
SCHEMA_VERSION = "1.0"
ROW_FIELDS = {"id", "user_input", "response", "retrieved_contexts", "reference", "reference_contexts"}
PROVENANCE_FIELDS = {
    "dataset_snapshot", "corpus_version", "ontology_version", "code_version",
    "retrieval_config", "llm", "execution_origin", "trace_path", "trace_sha256",
}
METRICS = ("faithfulness", "context_precision", "context_recall", "response_relevancy")


class RagasInputError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RagasInputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                RagasInputError(f"non-finite JSON constant: {value}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise RagasInputError(str(exc)) from exc


def _finite(value: Any, where: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise RagasInputError(f"{where}: non-finite number")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item, where)
    elif isinstance(value, list):
        for item in value:
            _finite(item, where)


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RagasInputError(f"{where}: expected nonblank string")
    return value


def _obj(value: Any, required: set[str], optional: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RagasInputError(f"{where}: expected object")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise RagasInputError(f"{where}: missing={sorted(missing)}, unknown={sorted(unknown)}")
    _finite(value, where)
    return value


def validate_payload(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate an envelope and return ``(provenance, rows)``."""
    envelope = _obj(payload, {"schema_version", "provenance", "rows"}, set(), "payload")
    if envelope["schema_version"] != SCHEMA_VERSION:
        raise RagasInputError("payload.schema_version must be 1.0")
    provenance = _obj(
        envelope["provenance"],
        {"dataset_snapshot", "corpus_version", "ontology_version", "code_version",
         "retrieval_config", "llm", "execution_origin"},
        {"trace_path", "trace_sha256"},
        "provenance",
    )
    for key in ("dataset_snapshot", "corpus_version", "ontology_version", "code_version", "execution_origin"):
        _text(provenance[key], f"provenance.{key}")
    if not isinstance(provenance["retrieval_config"], dict):
        raise RagasInputError("provenance.retrieval_config: expected object")
    if not isinstance(provenance["llm"], dict):
        raise RagasInputError("provenance.llm: expected object")
    llm = _obj(provenance["llm"], {"provider", "model", "prompt_version", "used_llm"}, set(), "provenance.llm")
    for key in ("provider", "model", "prompt_version"):
        _text(llm[key], f"provenance.llm.{key}")
    if type(llm["used_llm"]) is not bool:
        raise RagasInputError("provenance.llm.used_llm: expected boolean")
    if provenance["execution_origin"] not in {"recorded_unverified", "rag_pipeline"}:
        raise RagasInputError("provenance.execution_origin: unsupported value")
    if "trace_path" in provenance:
        _text(provenance["trace_path"], "provenance.trace_path")
    if "trace_sha256" in provenance and (
        not isinstance(provenance["trace_sha256"], str)
        or len(provenance["trace_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in provenance["trace_sha256"])
    ):
        raise RagasInputError("provenance.trace_sha256: expected lowercase sha256")
    if not isinstance(envelope["rows"], list) or not envelope["rows"]:
        raise RagasInputError("rows: expected nonempty array")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, row in enumerate(envelope["rows"]):
        row = _obj(row, {"id", "user_input", "response", "retrieved_contexts"},
                   {"reference", "reference_contexts"}, f"rows[{index}]")
        identifier = _text(row["id"], f"rows[{index}].id")
        if identifier in ids:
            raise RagasInputError(f"duplicate row id: {identifier}")
        ids.add(identifier)
        _text(row["user_input"], f"rows[{index}].user_input")
        if not isinstance(row["response"], str):
            raise RagasInputError(f"rows[{index}].response: expected string")
        contexts = row["retrieved_contexts"]
        if not isinstance(contexts, list) or any(not isinstance(item, str) or not item.strip() for item in contexts):
            raise RagasInputError(f"rows[{index}].retrieved_contexts: expected array of nonblank strings")
        if "reference" in row:
            _text(row["reference"], f"rows[{index}].reference")
        if "reference_contexts" in row:
            values = row["reference_contexts"]
            if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
                raise RagasInputError(f"rows[{index}].reference_contexts: expected array of nonblank strings")
        rows.append(row)
    return provenance, rows


def load_input(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load an envelope JSON or JSONL with one consistent provenance."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() != ".jsonl":
        return validate_payload(_parse(text))
    records = [_parse(line) for line in text.splitlines() if line.strip()]
    if not records:
        raise RagasInputError("JSONL is empty")
    prov: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        obj = _obj(record, {"schema_version", "provenance", "id", "user_input", "response", "retrieved_contexts"},
                   {"reference", "reference_contexts"}, f"line {index + 1}")
        current = {"schema_version": obj.pop("schema_version"), "provenance": obj.pop("provenance"), "rows": [obj]}
        current_provenance, current_rows = validate_payload(current)
        if prov is None:
            prov = current_provenance
        elif current_provenance != prov:
            raise RagasInputError("JSONL provenance must be identical on every line")
        rows.extend(current_rows)
    assert prov is not None
    return validate_payload({"schema_version": SCHEMA_VERSION, "provenance": prov, "rows": rows})


def merge_references(rows: list[dict[str, Any]], path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Merge an external reference file; references never enter the production RAG."""
    payload = _obj(_parse(path.read_text(encoding="utf-8")), {"schema_version", "rows"}, set(), "references")
    if payload["schema_version"] != SCHEMA_VERSION or not isinstance(payload["rows"], list) or not payload["rows"]:
        raise RagasInputError("references: expected schema_version=1.0 and nonempty rows")
    actual = {row["id"]: dict(row) for row in rows}
    seen: set[str] = set()
    review: dict[str, str] = {}
    for item in payload["rows"]:
        item = _obj(item, {"id"}, {"reference", "reference_contexts", "review_status"}, "references.row")
        identifier = _text(item["id"], "references.row.id")
        if identifier in seen or identifier not in actual:
            raise RagasInputError(f"references: duplicate or unknown id: {identifier}")
        seen.add(identifier)
        if "reference" not in item and "reference_contexts" not in item:
            raise RagasInputError("references.row: reference or reference_contexts required")
        for field in ("reference", "reference_contexts"):
            if field in item:
                if field in actual[identifier]:
                    raise RagasInputError(f"references cannot overwrite {identifier}.{field}")
                actual[identifier][field] = item[field]
        status = item.get("review_status", "draft")
        if status not in {"draft", "reviewed"}:
            raise RagasInputError("references.review_status: expected draft or reviewed")
        review[identifier] = status
    return [actual[row["id"]] for row in rows], review


@dataclass
class MetricResult:
    row_id: str
    metric: str
    status: str
    value: float | None = None
    error: str | None = None
    elapsed_ms: int = 0
    row_sha256: str = ""


def _config(name: str) -> str | None:
    return os.getenv(f"RAGAS_{name}")


@dataclass(frozen=True)
class JudgeConfig:
    model: str | None
    api_key: str | None = field(repr=False)
    base_url: str | None = field(repr=False)
    credential_policy: str = "independent_ragas_environment"
    model_override: bool = False
    thinking: str = "default"
    thinking_param: str | None = None

    @property
    def extra_body(self) -> dict[str, Any]:
        if self.thinking == "default":
            return {}
        if self.thinking_param == "enable_thinking":
            return {"enable_thinking": False}
        return {"thinking": {"type": "disabled"}}


def resolve_judge_config(*, reuse_project_model: bool = False,
                         judge_model: str | None = None, judge_thinking: str = "default",
                         judge_thinking_param: str | None = None) -> JudgeConfig:
    if judge_model is not None and (not isinstance(judge_model, str) or not judge_model.strip()):
        raise RagasInputError("judge_model: expected nonblank model identifier")
    if (judge_thinking not in {"default", "disabled"}
            or judge_thinking_param not in {None, "enable_thinking", "thinking"}
            or (judge_thinking == "disabled") != (judge_thinking_param is not None)):
        raise RagasInputError("disabled thinking requires an explicitly selected provider parameter")
    if not reuse_project_model:
        return JudgeConfig(judge_model or _config("JUDGE_MODEL"), _config("JUDGE_API_KEY"),
                           _config("JUDGE_BASE_URL"), model_override=judge_model is not None,
                           thinking=judge_thinking, thinking_param=judge_thinking_param)
    from dotenv import dotenv_values
    project_values = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
    values = {**project_values, **os.environ}
    model = values.get("OPENAI_MODEL") or values.get("MODEL")
    base_url = values.get("OPENAI_BASE_URL") or values.get("API_BASE")
    return JudgeConfig(
        judge_model or model, values.get("OPENAI_API_KEY"), base_url,
        credential_policy="explicit_process_local_project_reuse",
        model_override=judge_model is not None,
        thinking=judge_thinking, thinking_param=judge_thinking_param,
    )


def _response_diagnostic(payload: Any, http_status: int) -> dict[str, Any]:
    result: dict[str, Any] = {"http_status": http_status}
    if http_status != 200 or not isinstance(payload, dict):
        return result
    if isinstance(payload.get("model"), str) and len(payload["model"]) <= 200:
        result["returned_model"] = payload["model"]
    usage = payload.get("usage")
    if isinstance(usage, dict):
        result["usage"] = {
            name: value for name, value in usage.items()
            if name in {"prompt_tokens", "completion_tokens", "total_tokens",
                        "input_tokens", "output_tokens"} and type(value) is int and value >= 0
        }
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict):
            result["usage"]["completion_tokens_details"] = {
                name: value for name, value in details.items()
                if name in {"reasoning_tokens", "text_tokens", "audio_tokens",
                            "accepted_prediction_tokens", "rejected_prediction_tokens"}
                and type(value) is int and value >= 0
            }
    result["choices"] = []
    choices = payload.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            finish_reason = choice.get("finish_reason")
            message = choice.get("message")
            item = {"finish_reason": finish_reason if finish_reason in {
                "stop", "length", "tool_calls", "function_call", "content_filter", None,
            } else "unknown"}
            if isinstance(message, dict):
                for name in ("content", "reasoning_content"):
                    value = message.get(name)
                    if isinstance(value, str):
                        item[f"{name}_characters"] = len(value)
            result["choices"].append(item)
    return result


def installed_version() -> str | None:
    try:
        return version("ragas")
    except PackageNotFoundError:
        return None


def package_versions() -> dict[str, str | None]:
    packages = {}
    for name in ("ragas", "openai", "instructor", "langchain-community", "langchain-core",
                 "langchain", "langchain-openai", "httpx", "aiohttp", "numpy", "pydantic"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return packages


def _build_components(timeout: float, max_tokens: int, max_calls: int,
                      judge_config: JudgeConfig | None = None) -> tuple[Any, Any, str | None, list[Any]]:
    """Build a judge from explicit configuration; embeddings remain independent."""
    judge_config = judge_config or resolve_judge_config()
    model, key, base_url = judge_config.model, judge_config.api_key, judge_config.base_url
    if not model or not key:
        return None, None, "judge configuration unavailable (RAGAS_JUDGE_MODEL/API_KEY)", []
    try:
        from openai import AsyncOpenAI
        from ragas.llms.base import InstructorBaseRagasLLM, llm_factory
    except ImportError:
        return None, None, "ragas optional dependency unavailable; install ragas==0.4.3", []
    if installed_version() != RAGAS_VERSION:
        return None, None, "ragas version mismatch; require ragas==0.4.3", []
    client = AsyncOpenAI(api_key=key, base_url=base_url or None, timeout=timeout, max_retries=0)
    diagnostics: list[dict[str, Any]] = []

    async def record_response(response: Any) -> None:
        await response.aread()
        try:
            payload = response.json() if response.status_code == 200 else None
        except ValueError:
            payload = None
        diagnostics.append(_response_diagnostic(payload, response.status_code))

    client._client.event_hooks["response"].append(record_response)
    clients = [client]
    options = {"extra_body": judge_config.extra_body} if judge_config.extra_body else {}
    llm = llm_factory(model, provider="openai", client=client, max_tokens=max_tokens,
                      max_retries=1, **options)

    class BudgetedLLM(InstructorBaseRagasLLM):
        def __init__(self, wrapped: Any):
            self.wrapped = wrapped
            self.calls = 0
            self.stages: list[dict[str, Any]] = []
            self.stage_context: dict[str, str] = {}

        def generate(self, prompt: str, response_model: Any) -> Any:
            raise RuntimeError("only asynchronous judge execution is permitted")

        async def agenerate(self, prompt: str, response_model: Any) -> Any:
            if self.calls >= max_calls:
                raise RagasInputError("judge request budget exhausted")
            self.calls += 1
            started = time.monotonic()
            diagnostic_start = len(diagnostics)
            stage = {
                "call": self.calls, "response_model": getattr(response_model, "__name__", "unknown"),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "prompt_characters": len(prompt), "status": "running", "elapsed_ms": 0,
                **self.stage_context,
            }
            self.stages.append(stage)
            try:
                response = await self.wrapped.agenerate(prompt, response_model)
                stage["status"] = "ok"
                if hasattr(response, "statements"):
                    stage["statement_count"] = len(response.statements)
                return response
            except asyncio.CancelledError:
                stage["status"] = "cancelled"
                raise
            except Exception as exc:
                stage["status"] = "error"
                stage["error_type"] = type(exc).__name__
                raise
            finally:
                stage["elapsed_ms"] = int((time.monotonic() - started) * 1000)
                stage["provider_responses"] = diagnostics[diagnostic_start:]

    llm = BudgetedLLM(llm)
    embeddings = None
    embedding_model = _config("EMBEDDING_MODEL")
    embedding_key = _config("EMBEDDING_API_KEY")
    if embedding_model and embedding_key:
        from ragas.embeddings.base import embedding_factory
        embedding_client = AsyncOpenAI(
            api_key=embedding_key, base_url=_config("EMBEDDING_BASE_URL") or None,
            timeout=timeout, max_retries=0,
        )
        clients.append(embedding_client)
        embeddings = embedding_factory(
            "openai", model=embedding_model,
            client=embedding_client,
        )
    return llm, embeddings, None, clients


def _metric_classes() -> tuple[Any, Any, Any, Any]:
    from ragas.metrics.collections import (
        AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness,
    )
    return AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness


async def _score_row(row: dict[str, Any], llm: Any, embeddings: Any, timeout: float,
                     selected: tuple[str, ...]) -> list[MetricResult]:
    AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness = _metric_classes()
    metrics: list[tuple[str, Any, dict[str, Any] | None]] = [
        ("faithfulness", Faithfulness(llm=llm),
         {"user_input": row["user_input"], "response": row["response"], "retrieved_contexts": row["retrieved_contexts"]}),
    ]
    if "reference" in row:
        metrics.extend([
            ("context_precision", ContextPrecision(llm=llm),
             {"user_input": row["user_input"], "reference": row["reference"], "retrieved_contexts": row["retrieved_contexts"]}),
            ("context_recall", ContextRecall(llm=llm),
             {"user_input": row["user_input"], "reference": row["reference"], "retrieved_contexts": row["retrieved_contexts"]}),
        ])
    else:
        metrics.extend([(name, None, None) for name in ("context_precision", "context_recall")])
    if embeddings is None:
        metrics.append(("response_relevancy", None, None))
    else:
        metrics.append(("response_relevancy", AnswerRelevancy(llm=llm, embeddings=embeddings),
                        {"user_input": row["user_input"], "response": row["response"]}))
    results: list[MetricResult] = []
    for name, metric, kwargs in metrics:
        if name not in selected:
            continue
        started = time.monotonic()
        if metric is None:
            reason = (
                "reference unavailable" if name.startswith("context_") and "reference" not in row
                else "embedding unavailable"
            )
            results.append(MetricResult(row["id"], name, "unavailable", error=reason))
            continue
        if name != "response_relevancy" and not row["retrieved_contexts"]:
            results.append(MetricResult(row["id"], name, "unavailable", error="retrieved_contexts unavailable"))
            continue
        if name in {"faithfulness", "response_relevancy"} and not row["response"].strip():
            results.append(MetricResult(row["id"], name, "unavailable", error="response unavailable"))
            continue
        try:
            if hasattr(llm, "stage_context"):
                llm.stage_context = {"row_id": row["id"], "metric": name}
            score = await asyncio.wait_for(metric.ascore(**kwargs), timeout=timeout)
            value = float(score.value)
            if not math.isfinite(value):
                results.append(MetricResult(row["id"], name, "unavailable", error="metric returned non-finite value"))
            else:
                results.append(MetricResult(row["id"], name, "ok", value=value))
        except asyncio.TimeoutError:
            results.append(MetricResult(row["id"], name, "timeout", error=f"timeout>{timeout}s"))
        except Exception as exc:
            results.append(MetricResult(row["id"], name, "error", error=f"{type(exc).__name__}: judge/metric failed (details withheld)"))
        results[-1].elapsed_ms = int((time.monotonic() - started) * 1000)
    return results


def evaluate(
    provenance: dict[str, Any], rows: list[dict[str, Any]], *,
    execute: bool = False, timeout: float = 30.0,
    metrics: tuple[str, ...] = METRICS, max_tokens: int = 4096,
    max_calls: int = 40, max_rows: int = 100,
    reference_review: dict[str, str] | None = None,
    judge_config: JudgeConfig | None = None,
) -> dict[str, Any]:
    """Evaluate rows; default mode is validation-only and never contacts a judge."""
    started_at = datetime.now(timezone.utc).isoformat()
    provenance, rows = validate_payload({"schema_version": SCHEMA_VERSION, "provenance": provenance, "rows": rows})
    if not metrics or len(set(metrics)) != len(metrics) or set(metrics) - set(METRICS):
        raise RagasInputError("metrics: expected nonempty unique supported metrics")
    if not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise RagasInputError("timeout: expected 0 < timeout <= 120 seconds")
    if type(max_calls) is not int or not 1 <= max_calls <= 1000:
        raise RagasInputError("max_calls: expected integer 1..1000")
    if type(max_tokens) is not int or not 256 <= max_tokens <= 8192:
        raise RagasInputError("max_tokens: expected integer 256..8192")
    if type(max_rows) is not int or not 1 <= max_rows <= 1000 or len(rows) > max_rows:
        raise RagasInputError("max_rows: invalid value or input exceeds limit")
    if any(len(json.dumps(row, ensure_ascii=False)) > 100000 for row in rows):
        raise RagasInputError("row exceeds 100000 character input budget")
    judge_config = judge_config or resolve_judge_config()
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    all_results: list[MetricResult] = []
    unavailable_reason = None
    judge_call_count = 0
    judge_stages: list[dict[str, Any]] = []
    async def run() -> None:
        nonlocal unavailable_reason, judge_call_count, judge_stages
        clients: list[Any] = []
        try:
            llm = embeddings = None
            if execute:
                try:
                    llm, embeddings, unavailable_reason, clients = _build_components(
                        timeout, max_tokens, max_calls, judge_config)
                except Exception as exc:
                    unavailable_reason = f"{type(exc).__name__}: judge setup failed (details withheld)"
            for row in rows:
                if not execute or unavailable_reason:
                    reason = unavailable_reason or "dry-run; use --execute"
                    all_results.extend(MetricResult(row["id"], metric, "unavailable", error=reason)
                                       for metric in metrics)
                else:
                    try:
                        all_results.extend(await _score_row(row, llm, embeddings, timeout, metrics))
                    except Exception as exc:
                        all_results.extend(MetricResult(
                            row["id"], metric, "error",
                            error=f"{type(exc).__name__}: metric setup failed (details withheld)",
                        ) for metric in metrics)
        finally:
            judge_call_count = getattr(llm, "calls", 0)
            judge_stages = getattr(llm, "stages", [])
            for client in clients:
                await client.close()

    asyncio.run(run())
    row_hashes = {row["id"]: _hash(row) for row in rows}
    for item in all_results:
        item.row_sha256 = row_hashes[item.row_id]
    return {
        "run_id": str(uuid.uuid4()), "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(), "package_versions": package_versions(),
        "ragas_version": installed_version(), "required_ragas_version": RAGAS_VERSION,
        "schema_version": SCHEMA_VERSION, "input_sha256": _hash({"provenance": provenance, "rows": rows}),
        "execution": {
            "mode": "ragas_judge" if execute else "validate_only", "network_authorized": execute,
            "business_e2e": False, "telemetry_disabled": True,
            "selected_metrics": list(metrics), "max_workers": 1,
            "timeout_seconds_per_metric": timeout, "max_judge_calls": max_calls,
            "actual_judge_calls": judge_call_count,
            "judge_stages": judge_stages,
            "max_output_tokens_per_call": max_tokens, "max_attempts_per_call": 1,
            "judge_model": judge_config.model or "unconfigured",
            "judge_key_configured": bool(judge_config.api_key),
            "judge_credential_policy": judge_config.credential_policy,
            "judge_model_override": judge_config.model_override,
            "judge_thinking": judge_config.thinking,
            "judge_thinking_param": judge_config.thinking_param,
            "judge_request_extra_body": judge_config.extra_body,
            "judge_returned_models": sorted({
                response["returned_model"] for stage in judge_stages
                for response in stage.get("provider_responses", []) if "returned_model" in response
            }),
            "project_config_modified": False,
            "embedding_model": _config("EMBEDDING_MODEL") or "unconfigured",
            "embedding_key_configured": bool(_config("EMBEDDING_API_KEY")),
            "response_relevancy_implementation": "ragas.metrics.collections.AnswerRelevancy",
            "scoring_scope": "diagnostic_not_acceptance",
            "provenance_verification": "declared_only; trace paths/hashes are not independently verified",
            "reference_review_status": reference_review or {},
        },
        "provenance": provenance, "results": [asdict(item) for item in all_results],
        "summary": summarize(all_results, len(rows), metrics),
    }


def summarize(results: list[MetricResult], row_count: int, metrics: tuple[str, ...] = METRICS) -> dict[str, Any]:
    by_metric: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        subset = [item for item in results if item.metric == metric]
        ok = [item.value for item in subset if item.status == "ok" and item.value is not None]
        by_metric[metric] = {
            "denominator": row_count, "ok": len(ok),
            "unavailable": sum(item.status == "unavailable" for item in subset),
            "error": sum(item.status == "error" for item in subset),
            "timeout": sum(item.status == "timeout" for item in subset),
            "mean": (sum(ok) / row_count) if len(ok) == row_count else None,
        }
    return {"row_count": row_count, "metrics": by_metric}


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def save_results(path: Path, payload: dict[str, Any]) -> None:
    """Persist one run to JSON or SQLite based on suffix."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() != ".sqlite":
        path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, allow_nan=False, indent=2), encoding="utf-8")
        return
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS ragas_runs (run_id TEXT PRIMARY KEY, input_sha256 TEXT, ragas_version TEXT, metadata_json TEXT, summary_json TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS ragas_results (run_id TEXT, row_id TEXT, metric TEXT, status TEXT, value REAL, error TEXT, elapsed_ms INTEGER, row_sha256 TEXT, PRIMARY KEY(run_id,row_id,metric))")
        metadata = {key: value for key, value in payload.items() if key not in {"results", "summary"}}
        db.execute("INSERT OR REPLACE INTO ragas_runs VALUES (?,?,?,?,?)",
                   (payload["run_id"], payload["input_sha256"], payload["ragas_version"],
                    json.dumps(metadata, sort_keys=True, allow_nan=False), json.dumps(payload["summary"], sort_keys=True, allow_nan=False)))
        db.executemany("INSERT OR REPLACE INTO ragas_results VALUES (?,?,?,?,?,?,?,?)",
                       [(payload["run_id"], item["row_id"], item["metric"], item["status"], item["value"], item["error"], item["elapsed_ms"], item["row_sha256"])
                        for item in payload["results"]])
