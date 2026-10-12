"""Bounded, explicit providers for audited document retrieval experiments."""

from __future__ import annotations

import hashlib
import json
import math
from time import perf_counter
from urllib.parse import urlsplit

from fondontology.corpus import CorpusError


def _endpoint(value: str, suffix: str = "") -> str:
    endpoint = value.rstrip("/") + suffix
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise CorpusError("Retrieval provider requires a credential-free HTTPS endpoint")
    return endpoint


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _post(endpoint: str, key: str, payload: dict, events: list[dict],
          kind: str, input_count: int) -> dict:
    import httpx

    started = perf_counter()
    event = {"kind": kind, "input_count": input_count, "status": "running",
             "request_sha256": _digest(payload), "elapsed_ms": 0,
             "response_validation_status": "not_checked"}
    events.append(event)
    try:
        response = httpx.post(
            endpoint, headers={"Authorization": f"Bearer {key}"}, json=payload,
            timeout=httpx.Timeout(30.0), follow_redirects=False,
        )
        event["http_status"] = response.status_code
        if response.status_code != 200:
            raise CorpusError(f"{kind} provider HTTP {response.status_code}; body withheld")
        event["status"] = "ok"
        event["response_sha256"] = hashlib.sha256(response.content).hexdigest()
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise CorpusError(f"{kind} provider returned a non-object response")
        except Exception as error:
            event["response_validation_status"] = "error"
            event["response_validation_error_type"] = type(error).__name__
            raise
        usage = result.get("usage")
        if isinstance(usage, dict):
            event["usage"] = {
                field: value for field, value in usage.items()
                if field in {"total_tokens", "prompt_tokens", "input_tokens", "output_tokens"}
                and type(value) is int and value >= 0
            }
        return result
    except Exception as error:
        if event["status"] != "ok":
            event["status"] = "error"
        event["error_type"] = type(error).__name__
        if isinstance(error, CorpusError):
            raise
        raise CorpusError(f"{kind} provider failed ({type(error).__name__}); details withheld") from None
    finally:
        event["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)


def build_resources():
    from fondontology.qa.config import embedding_config, rerank_config
    from .document_retrieval import RetrievalResources

    embedding = embedding_config()
    reranking = rerank_config()
    events: list[dict] = []
    embedding_ready = all(embedding.get(field) for field in
                          ("EMBEDDING_MODEL", "EMBEDDING_URL", "EMBEDDING_KEY"))
    rerank_ready = all(reranking.get(field) for field in
                       ("RERANK_MODEL", "RERANK_URL", "RERANK_KEY"))
    def safe_endpoint(value, suffix=""):
        try:
            return _endpoint(value, suffix)
        except CorpusError:
            return None

    embedding_endpoint = (safe_endpoint(embedding["EMBEDDING_URL"], "/embeddings")
                          if embedding_ready else None)
    rerank_endpoint = safe_endpoint(reranking["RERANK_URL"]) if rerank_ready else None

    def validation_error(message: str):
        events[-1]["response_validation_status"] = "error"
        events[-1]["response_validation_error_type"] = "CorpusError"
        raise CorpusError(message)

    def embed(texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise CorpusError("Embedding inputs must be nonblank text")
        if embedding_endpoint is None:
            raise CorpusError("Embedding provider requires a credential-free HTTPS endpoint")
        vectors = []
        dimension = None
        for start in range(0, len(texts), 25):
            batch = texts[start:start + 25]
            payload = _post(
                embedding_endpoint, embedding["EMBEDDING_KEY"],
                {"model": embedding["EMBEDDING_MODEL"], "input": batch},
                events, "embedding", len(batch),
            )
            items = payload.get("data")
            if (not isinstance(items, list) or len(items) != len(batch)
                    or any(not isinstance(item, dict) or type(item.get("index")) is not int
                           for item in items)
                    or {item["index"] for item in items} != set(range(len(batch)))):
                validation_error("Embedding response indexes must exactly cover the batch")
            for item in sorted(items, key=lambda item: item["index"]):
                vector = item.get("embedding")
                if (not isinstance(vector, list) or not vector
                        or any(type(value) not in {int, float} or not math.isfinite(value)
                               for value in vector)
                        or not any(value != 0 for value in vector)):
                    validation_error("Embedding response has an invalid vector")
                dimension = dimension or len(vector)
                if len(vector) != dimension:
                    validation_error("Embedding response dimensions disagree")
                vectors.append(vector)
            events[-1]["response_validation_status"] = "ok"
        return vectors

    def rerank(query: str, documents: list[str]) -> list[tuple[int, float]]:
        if not documents:
            return []
        if (not isinstance(query, str) or not query.strip()
                or any(not isinstance(document, str) or not document.strip()
                       for document in documents)):
            raise CorpusError("Rerank query and documents must be nonblank text")
        if rerank_endpoint is None:
            raise CorpusError("Rerank provider requires a credential-free HTTPS endpoint")
        payload = _post(
            rerank_endpoint, reranking["RERANK_KEY"],
            {"model": reranking["RERANK_MODEL"],
             "input": {"query": query, "documents": documents},
             "parameters": {"top_n": len(documents), "return_documents": False}},
            events, "rerank", len(documents),
        )
        output = payload.get("output")
        items = output.get("results") if isinstance(output, dict) else None
        if (not isinstance(items, list) or len(items) != len(documents)
                or any(not isinstance(item, dict) or type(item.get("index")) is not int
                       for item in items)
                or {item["index"] for item in items} != set(range(len(documents)))):
            validation_error("Rerank response indexes must exactly cover the candidates")
        scores = []
        for item in items:
            score = item.get("relevance_score")
            if type(score) not in {int, float} or not math.isfinite(score):
                validation_error("Rerank response has an invalid score")
            scores.append((item["index"], float(score)))
        events[-1]["response_validation_status"] = "ok"
        return sorted(scores, key=lambda item: (-item[1], item[0]))

    return RetrievalResources(
        embed=embed if embedding_ready else None,
        rerank=rerank if rerank_ready else None,
        embedding_config=({"provider": "openai-compatible", "model": embedding["EMBEDDING_MODEL"],
                           "endpoint": embedding_endpoint, "timeout_seconds": 30,
                           "endpoint_validation_status": "valid" if embedding_endpoint else "invalid",
                           "batch_size": 25, "max_attempts": 1}
                          if embedding_ready else {}),
        rerank_config=({"provider": "dashscope-native", "model": reranking["RERANK_MODEL"],
                        "endpoint": rerank_endpoint, "timeout_seconds": 30, "max_attempts": 1,
                        "endpoint_validation_status": "valid" if rerank_endpoint else "invalid"}
                       if rerank_ready else {}),
        events=events,
    )
