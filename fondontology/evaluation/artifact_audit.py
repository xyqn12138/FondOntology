"""Independent, read-only validation of recorded document retrieval artifacts."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import re
import math
from html.parser import HTMLParser
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .ragas_runner import RagasInputError, _hash, _obj, _parse, _text, load_input


class ArtifactAuditError(RagasInputError):
    pass


TRACE_REQUIRED = {
    "id", "user_input", "response", "retrieved_contexts", "status", "answer_mode",
    "evidence", "warnings", "corpus", "config", "retrieval_latency_ms", "generation_latency_ms",
}
TRACE_OPTIONAL = {"scope", "retrieval_candidates", "unresolved_reason", "retrieval_debug", "strategy_trace"}
EVIDENCE_REQUIRED = {
    "evidence_id", "chunk_id", "doc_id", "version_id", "text", "locator", "sha256",
    "authority", "status", "provenance", "entity_links", "issued_date", "effective_from",
    "withdrawn_date", "extraction_quality",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactAuditError(message)


def _iso(value: Any, where: str) -> str:
    _text(value, where)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ArtifactAuditError(f"{where}: invalid date") from exc
    _require(parsed.isoformat() == value, f"{where}: expected YYYY-MM-DD")
    return value


def read_only_connection(path: Path) -> sqlite3.Connection:
    path = path.resolve()
    _require(path.is_file(), "corpus database does not exist")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _stored_hash(value: Any) -> str:
    return _sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8"))


def _eligible(version: dict[str, Any], as_of: str, include_undated: bool) -> bool:
    issued = version["issued_date"]
    effective = version["effective_from"]
    withdrawn = version["withdrawn_date"]
    for field, value in (("issued_date", issued), ("effective_from", effective), ("withdrawn_date", withdrawn)):
        if value is not None:
            _iso(value, field)
    return ((issued is not None and issued <= as_of) or (issued is None and include_undated)) \
        and (effective is None or effective <= as_of) \
        and (withdrawn is None or withdrawn > as_of)


def _list_ids(value: Any, where: str) -> list[str]:
    _require(isinstance(value, list), f"{where}: expected array")
    for identifier in value:
        _text(identifier, where)
    _require(len(set(value)) == len(value), f"{where}: duplicate identifiers")
    return value


def _score(value: Any, where: str, *, positive: bool = False) -> None:
    _require(type(value) in {int, float} and math.isfinite(value)
             and (not positive or value > 0), f"{where}: invalid finite score")


def _audit_strategy(trace: dict[str, Any], declared: dict[str, Any],
                    chunks: dict[str, Any], texts: dict[str, str]) -> None:
    strategy = _obj(trace["strategy_trace"], {
        "requested_strategy", "effective_strategy", "status", "candidate_k", "rrf_k",
        "child_target_chars", "channels", "child_matches", "model_config", "cache",
        "stages", "fusion", "rerank", "resource_events",
    }, {"reason"}, "strategy_trace")
    config = trace["config"]
    for name in ("retrieval_strategy", "candidate_k", "rrf_k", "child_target_chars",
                 "retrieval_cache", "allow_retrieval_network"):
        _require(name in config and name in declared and config[name] == declared[name],
                 f"strategy trace/envelope {name} mismatch")
    for name in ("retrieval",):
        if name in config or name in declared:
            _require(name in config and name in declared and config[name] == declared[name],
                     "strategy retrieval declaration mismatch")
            expected_label = "bm25-only" if config["retrieval_strategy"] == "bm25" else config["retrieval_strategy"]
            _require(config[name] == expected_label, "strategy retrieval declaration mislabels active policy")
    requested = strategy["requested_strategy"]
    _require(requested == config["retrieval_strategy"]
             and requested in {"bm25", "parent_child", "hybrid_rrf", "bm25_rerank"},
             "strategy requested policy mismatch")
    _require(type(strategy["candidate_k"]) is int and strategy["candidate_k"] > 0
             and strategy["candidate_k"] == config["candidate_k"],
             "strategy candidate budget mismatch")
    _require(type(strategy["rrf_k"]) is int and strategy["rrf_k"] == config["rrf_k"] == 60,
             "strategy RRF policy mismatch")
    _require(type(strategy["child_target_chars"]) is int
             and strategy["child_target_chars"] == config["child_target_chars"] == 240,
             "strategy child policy mismatch")
    _require(strategy["status"] in {"ok", "bypassed", "error"}, "invalid strategy status")
    _require(type(config["allow_retrieval_network"]) is bool, "invalid strategy network authorization")
    scope = _obj(trace.get("scope"), {"status", "eligible_chunk_ids", "article_numbers"},
                 set(trace.get("scope", {})) - {"status", "eligible_chunk_ids", "article_numbers"},
                 "strategy scope")
    eligible = set(scope["eligible_chunk_ids"])
    channels = _obj(strategy["channels"], set(), {"bm25", "dense", "child_bm25"}, "strategy channels")
    candidate_k = strategy["candidate_k"]
    channel_maps: dict[str, dict[str, Any]] = {}
    for name in ("bm25", "dense"):
        values = channels.get(name, [])
        _require(isinstance(values, list), "strategy channel must be an array")
        _require(name == "bm25" and requested == "bm25" or len(values) <= candidate_k,
                 "strategy channel exceeds candidate budget")
        mapping = {}
        last_score = None
        for rank, item in enumerate(values, 1):
            _obj(item, {"chunk_id", "rank", "score"}, set(), "strategy channel candidate")
            identifier = item["chunk_id"]
            _require(identifier in eligible and identifier not in mapping,
                     "strategy channel duplicate or out-of-scope candidate")
            _require(type(item["rank"]) is int and item["rank"] == rank,
                     "strategy channel rank mismatch")
            _score(item["score"], name, positive=name == "bm25")
            _require(last_score is None or item["score"] <= last_score,
                     "strategy channel scores not descending")
            if name == "dense":
                _require(-1.000000001 <= item["score"] <= 1.000000001, "invalid declared cosine score")
                if last_score == item["score"]:
                    _require(values[rank - 2]["chunk_id"] < identifier, "dense tie order mismatch")
            mapping[identifier] = item
            last_score = item["score"]
        channel_maps[name] = mapping
    child_values = channels.get("child_bm25", [])
    _require(isinstance(child_values, list) and len(child_values) <= candidate_k,
             "child channel exceeds candidate budget")
    _require(strategy["child_matches"] == child_values, "child matches/channel mismatch")
    children = {}
    for identifier in scope["eligible_chunk_ids"]:
        parent = chunks[identifier]
        original = texts[parent["version_id"]]
        _require(type(parent["char_start"]) is int and type(parent["char_end"]) is int
                 and 0 <= parent["char_start"] < parent["char_end"] <= len(original)
                 and parent["section_version"] == parent["version_id"]
                 and parent["section_start"] <= parent["char_start"] < parent["char_end"] <= parent["section_end"]
                 and original[parent["section_start"]:parent["section_end"]] == parent["section_text"]
                 and original[parent["char_start"]:parent["char_end"]] == parent["text"]
                 and _sha(parent["text"].encode("utf-8")) == parent["text_sha256"],
                 "strategy parent text/hash/offset mismatch")
        locator = _parse(parent["locator_json"])
        _require(locator.get("char_start") == parent["char_start"]
                 and locator.get("char_end") == parent["char_end"], "strategy parent locator offset mismatch")
        start = 0
        while start < len(parent["text"]):
            end = min(start + 240, len(parent["text"]))
            if end < len(parent["text"]):
                boundaries = list(re.finditer(r"[。！？.!?；;\n]", parent["text"][start:end]))
                if boundaries and boundaries[-1].end() >= 120:
                    end = start + boundaries[-1].end()
            text = parent["text"][start:end]
            identity = {"parent": identifier, "start": start, "end": end, "text": text,
                        "policy": "sentence-boundary-240-v1"}
            child_id = "child_" + _sha(json.dumps(
                identity, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8"))
            children[child_id] = {
                "child_id": child_id, "parent_chunk_id": identifier,
                "char_start": parent["char_start"] + start, "char_end": parent["char_start"] + end,
                "parent_char_start": parent["char_start"], "parent_char_end": parent["char_end"],
                "text_sha256": _sha(text.encode("utf-8")),
            }
            start = end
    parent_hits = []
    seen_children, seen_parents = set(), set()
    last_score = None
    for rank, item in enumerate(child_values, 1):
        _obj(item, {"child_id", "parent_chunk_id", "rank", "score", "char_start", "char_end",
                    "parent_char_start", "parent_char_end", "text_sha256"}, set(), "child candidate")
        _require(type(item["rank"]) is int and item["rank"] == rank, "child candidate rank mismatch")
        _require(all(type(item[name]) is int for name in
                     ("char_start", "char_end", "parent_char_start", "parent_char_end")),
                 "invalid child offset types")
        child_id = item["child_id"]
        _require(child_id in children and child_id not in seen_children,
                 "child candidate not a unique independently reconstructed child")
        _require({name: item[name] for name in children[child_id]} == children[child_id],
                 "child identity/offset/hash/parent mismatch")
        _score(item["score"], "child BM25", positive=True)
        _require(last_score is None or item["score"] <= last_score, "child scores not descending")
        seen_children.add(child_id)
        last_score = item["score"]
        if item["parent_chunk_id"] not in seen_parents:
            seen_parents.add(item["parent_chunk_id"])
            parent_hits.append((item["parent_chunk_id"], item["score"]))
    model_config = _obj(strategy["model_config"], {"embedding", "rerank"}, set(), "strategy models")
    for name, model in model_config.items():
        _obj(model, set(), {"provider", "model", "endpoint", "timeout_seconds", "batch_size",
                           "max_attempts", "endpoint_validation_status"}, f"strategy model {name}")
        if "endpoint_validation_status" in model:
            _require(model["endpoint_validation_status"] in {"valid", "invalid"},
                     "invalid endpoint validation status")
            _require(model["endpoint_validation_status"] != "invalid" or model.get("endpoint") is None,
                     "invalid endpoint must be withheld")
        for field in ("provider", "model", "endpoint"):
            if field in model and not (field == "endpoint" and model.get("endpoint_validation_status") == "invalid"):
                _text(model[field], f"strategy model {field}")
        if model.get("endpoint") is not None:
            endpoint = urlsplit(model["endpoint"])
            _require(endpoint.scheme == "https" and endpoint.hostname
                     and not endpoint.username and not endpoint.password
                     and not endpoint.query and not endpoint.fragment, "unsafe strategy model endpoint")
        for field in ("timeout_seconds", "batch_size", "max_attempts"):
            if field in model:
                _require(type(model[field]) in {int, float} and model[field] > 0,
                         "invalid strategy model budget")
    cache = _obj(strategy["cache"], {"enabled", "hits", "misses", "path", "entries"}, set(), "strategy cache")
    _require(type(cache["enabled"]) is bool and cache["enabled"] == (config["retrieval_cache"] is not None)
             and cache["path"] == config["retrieval_cache"], "strategy cache config mismatch")
    _require(all(type(cache[name]) is int and cache[name] >= 0 for name in ("hits", "misses")),
             "invalid strategy cache counts")
    _require(cache["enabled"] or cache["hits"] == 0, "disabled cache records hits")
    _require(isinstance(cache["entries"], list), "cache entries must be an array")
    expected_cache = {}
    for kind, inputs in (
        ("embed_documents", [chunks[identifier]["text"] for identifier in scope["eligible_chunk_ids"]]),
        ("embed_query", [scope.get("body_query", "")]),
    ):
        expected_cache[kind] = []
        for text in inputs:
            identity = {"schema_version": "1.0", "snapshot": trace["corpus"]["members_sha256"],
                        "embedding": model_config["embedding"], "kind": kind, "text": text}
            key = _sha(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                  allow_nan=False).encode("utf-8"))
            if key not in expected_cache[kind]:
                expected_cache[kind].append(key)
    cache_keys = {"embed_documents": [], "embed_query": []}
    for entry in cache["entries"]:
        _obj(entry, {"key", "kind", "vector_sha256"}, set(), "cache entry")
        _require(entry["kind"] in cache_keys and entry["key"] in expected_cache[entry["kind"]]
                 and entry["key"] not in cache_keys[entry["kind"]],
                 "cache key not bound to scoped text/model/snapshot/kind")
        _require(isinstance(entry["vector_sha256"], str)
                 and re.fullmatch(r"[0-9a-f]{64}", entry["vector_sha256"]), "invalid cache vector hash")
        cache_keys[entry["kind"]].append(entry["key"])
    _require(isinstance(strategy["stages"], list), "strategy stages must be an array")
    for stage in strategy["stages"]:
        _obj(stage, {"stage", "status", "network"}, {"input_count"}, "strategy stage")
        _require(stage["stage"] in {"bm25", "parent_child", "embed_documents", "embed_query",
                                   "hybrid_rrf", "rerank"}
                 and stage["status"] in {"completed", "started", "blocked", "failed", "cache_hit"},
                 "invalid strategy stage")
        _require(type(stage["network"]) is bool, "invalid strategy stage network flag")
        _require(not stage["network"] or config["allow_retrieval_network"]
                 or stage["status"] == "blocked", "strategy network lacks authorization")
        if "input_count" in stage:
            _require(type(stage["input_count"]) is int and stage["input_count"] >= 0,
                     "invalid strategy stage input count")
        if stage["stage"] == "parent_child":
            _require(stage.get("input_count") == len(children), "child generation count mismatch")
    _require(isinstance(strategy["resource_events"], list), "resource events must be an array")
    for event in strategy["resource_events"]:
        _obj(event, {"kind", "input_count", "status", "request_sha256", "elapsed_ms"},
             {"http_status", "response_sha256", "usage", "error_type",
              "response_validation_status", "response_validation_error_type"}, "resource event")
        _require(config["allow_retrieval_network"] and event["kind"] in {"embedding", "rerank"}
                 and event["status"] in {"ok", "error", "running"}, "invalid resource event authorization/status")
        _require(type(event["input_count"]) is int and event["input_count"] > 0,
                 "invalid resource event input count")
        _require(type(event["elapsed_ms"]) in {int, float} and event["elapsed_ms"] >= 0,
                 "invalid resource event duration")
        if "response_validation_status" in event:
            validation = event["response_validation_status"]
            _require(validation in {"not_checked", "ok", "error"}, "invalid provider validation status")
            _require(validation == "not_checked" or event["status"] == "ok" and event.get("http_status") == 200,
                     "provider validation status lacks successful HTTP response")
            _require(("response_validation_error_type" in event) == (validation == "error"),
                     "provider response validation error diagnosis mismatch")
        for field in ("error_type", "response_validation_error_type"):
            if field in event:
                _require(isinstance(event[field], str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", event[field]),
                         "provider error diagnosis must be type only")
        for field in ("request_sha256", "response_sha256"):
            if field in event:
                _require(isinstance(event[field], str) and re.fullmatch(r"[0-9a-f]{64}", event[field]),
                         "invalid resource event hash")
        if "usage" in event:
            usage = _obj(event["usage"], set(),
                         {"total_tokens", "prompt_tokens", "input_tokens", "output_tokens"}, "resource usage")
            _require(all(type(value) is int and value >= 0 for value in usage.values()), "invalid resource usage")
    _require(isinstance(strategy["fusion"], list) and isinstance(strategy["rerank"], list),
             "strategy final scores must be arrays")
    expected = []
    if strategy["status"] == "error":
        _require(trace["status"] == "error" and not trace["retrieval_candidates"] and not trace["evidence"],
                 "strategy error silently fell back to retrieved results")
        _text(strategy.get("reason"), "strategy error reason")
        _require(trace.get("unresolved_reason") == strategy["reason"], "strategy error reason mismatch")
    elif strategy["status"] == "bypassed":
        reason = strategy.get("reason")
        if reason == "direct_address":
            _require(strategy["effective_strategy"] == "article_locator" and scope["article_numbers"],
                     "invalid direct article bypass")
            expected = [(identifier, None) for identifier in scope["eligible_chunk_ids"]]
            _require(not channels and not strategy["stages"], "direct article bypass performed strategy work")
        elif reason == "unresolved_scope":
            _require(strategy["effective_strategy"] == "none"
                     and (scope["status"] != "resolved" or not eligible), "invalid unresolved scope bypass")
        elif reason == "no_lexical_candidates":
            _require(requested == "bm25_rerank" and not channel_maps["bm25"],
                     "invalid lexical-empty bypass")
        else:
            _require(False, "unsupported strategy bypass")
        _require(not child_values and not channels.get("dense") and not strategy["fusion"]
                 and not strategy["rerank"] and not strategy["resource_events"],
                 "bypassed strategy carries extra retrieval work")
    else:
        _require(strategy["effective_strategy"] == requested and scope["status"] == "resolved"
                 and bool(eligible) and not scope["article_numbers"], "invalid active strategy scope")
        required_channels = {
            "bm25": {"bm25"}, "parent_child": {"bm25", "child_bm25"},
            "hybrid_rrf": {"bm25", "dense"}, "bm25_rerank": {"bm25"},
        }[requested]
        _require(set(channels) == required_channels, "strategy channel set mismatch")
        if requested == "hybrid_rrf":
            _require(cache_keys == expected_cache
                     and cache["hits"] + cache["misses"] == len(cache["entries"]),
                     "successful embedding cache provenance/count mismatch")
            _require(model_config["embedding"], "successful dense retrieval lacks embedding model declaration")
            _require(model_config["embedding"].get("endpoint_validation_status") != "invalid",
                     "successful embedding uses invalid endpoint")
        if requested == "bm25_rerank":
            _require(model_config["rerank"], "successful rerank lacks model declaration")
            _require(model_config["rerank"].get("endpoint_validation_status") != "invalid",
                     "successful rerank uses invalid endpoint")
        _require(all(stage["status"] in {"completed", "cache_hit"} for stage in strategy["stages"]),
                 "successful strategy has incomplete or failed stage")
        _require(all(event["status"] == "ok" and event.get("response_validation_status", "ok") == "ok"
                     for event in strategy["resource_events"]),
                 "successful strategy has failed HTTP or payload validation")
        if requested in {"bm25", "parent_child"}:
            _require(not strategy["resource_events"] and not cache["entries"]
                     and cache["hits"] == cache["misses"] == 0
                     and all(not stage["network"] for stage in strategy["stages"]),
                     "local lexical strategy carries model/network work")
        if requested == "bm25":
            expected = [(item["chunk_id"], item["score"]) for item in channels["bm25"]]
        elif requested == "parent_child":
            expected = parent_hits
        elif requested == "hybrid_rrf":
            ranks = {name: {identifier: item["rank"] for identifier, item in mapping.items()}
                     for name, mapping in channel_maps.items()}
            fused = {}
            for mapping in ranks.values():
                for identifier, rank in mapping.items():
                    fused[identifier] = fused.get(identifier, 0.0) + 1.0 / (60 + rank)
            expected = sorted(fused.items(), key=lambda item: (-item[1], item[0]))[:candidate_k]
            expected_fusion = [{"chunk_id": identifier, "score": score,
                                "bm25_rank": ranks["bm25"].get(identifier),
                                "dense_rank": ranks["dense"].get(identifier)} for identifier, score in expected]
            _require(strategy["fusion"] == expected_fusion, "RRF fusion/rank arithmetic mismatch")
        else:
            rerank = strategy["rerank"]
            lexical = channels["bm25"]
            _require(len(rerank) == len(lexical), "rerank must cover all lexical candidates")
            indices = set()
            for item in rerank:
                _obj(item, {"chunk_id", "score", "index"}, set(), "rerank score")
                index = item["index"]
                _require(type(index) is int and 0 <= index < len(lexical) and index not in indices
                         and item["chunk_id"] == lexical[index]["chunk_id"], "rerank index/membership mismatch")
                _score(item["score"], "rerank")
                indices.add(index)
            _require(rerank == sorted(rerank, key=lambda item: (-item["score"], item["index"])),
                     "rerank score/tie order mismatch")
            expected = [(item["chunk_id"], item["score"]) for item in rerank]
        _require(requested == "hybrid_rrf" or not strategy["fusion"], "unexpected fusion scores")
        _require(requested == "bm25_rerank" or not strategy["rerank"], "unexpected rerank scores")
    if strategy["status"] != "error":
        actual = [(item["chunk_id"], item["score"]) for item in trace["retrieval_candidates"]]
        _require(actual == expected, "strategy final candidates differ from declared channel selection")
        ranking = {"bm25": "bm25", "parent_child": "parent_bm25", "hybrid_rrf": "hybrid_rrf",
                   "bm25_rerank": "rerank"}[requested]
        if strategy["effective_strategy"] == "article_locator":
            ranking = "article_locator"
        _require(all(item.get("ranking", "bm25") == ranking for item in trace["retrieval_candidates"]),
                 "strategy final ranking label mismatch")


class _IndependentHtmlText(HTMLParser):
    def __init__(self, selector: dict[str, str]):
        super().__init__(convert_charrefs=True)
        self.selector = selector
        self.stack: list[str] = []
        self.active_depth: int | None = None
        self.matches = 0
        self.parts: list[str] = []
        self.removed_nul_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = [value for key, value in attrs if key == self.selector["attribute"]]
        _require(len(values) <= 1, "ambiguous HTML selector attribute")
        value = values[0] if values else None
        matched = tag == self.selector["tag"] and value is not None and (
            self.selector["value"] in value.split() if self.selector["attribute"] == "class"
            else self.selector["value"] == value
        )
        if matched:
            self.matches += 1
            _require(self.matches == 1, "ambiguous HTML body selector")
            self.active_depth = len(self.stack)
        if self.active_depth is not None and tag in {
            "p", "div", "section", "article", "header", "footer", "li", "ul", "ol",
            "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr",
        }:
            self.parts.append("\n")
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"area", "base", "br", "col", "embed", "hr", "img", "input",
                   "link", "meta", "param", "source", "track", "wbr"}:
            return
        if not self.stack or self.stack[-1] != tag:
            _require(self.active_depth is None, "unbalanced selected HTML")
            return
        if self.active_depth is not None:
            self.parts.append("\n" if tag in {
                "p", "div", "section", "article", "header", "footer", "li", "ul", "ol",
                "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
            } else "")
        self.stack.pop()
        if self.active_depth == len(self.stack):
            self.active_depth = None

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.active_depth is not None and not any(
            tag in {"script", "style", "noscript", "template"} for tag in self.stack[self.active_depth:]
        ):
            _require(not any(ord(character) < 32 and character not in "\x00\t\r\n\f\v" for character in data),
                     "unsupported control character in selected HTML")
            self.removed_nul_count += data.count("\x00")
            self.parts.append(re.sub(r"\s+", " ", data.replace("\x00", "")))


def _html_text(raw: bytes, identity: dict[str, Any]) -> tuple[str, int]:
    reference = identity.get("html_extraction")
    _require(isinstance(reference, dict) and reference.get("encoding") == "utf-8"
             and reference.get("kind") == "official_html" and isinstance(reference.get("selector"), dict),
             "unsupported HTML extraction identity")
    selector = _obj(reference["selector"], {"tag", "attribute", "value"}, set(), "HTML selector")
    parser = _IndependentHtmlText(selector)
    parser.feed(raw.decode("utf-8"))
    parser.close()
    _require(parser.matches == 1 and parser.active_depth is None, "selected HTML body missing or unclosed")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip()
             for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line), parser.removed_nul_count


def _article_ranges(text: str) -> dict[int, tuple[int, int]]:
    numeral = r"[一二三四五六七八九十百千零〇0-9]+"
    starts = list(re.finditer(rf"(?m)^第({numeral})条[ \t\u3000]+(?=\S)", text))
    chapters = [match.start() for match in re.finditer(rf"(?m)^第{numeral}[章节][ \t\u3000]+\S", text)]
    ranges = {}
    for position, match in enumerate(starts):
        raw_number = match.group(1)
        if raw_number.isascii() and raw_number.isdigit():
            number = int(raw_number)
        else:
            digits = dict(zip("零〇一二三四五六七八九", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9)))
            number, current = 0, 0
            for character in raw_number:
                if character in digits:
                    current = digits[character]
                else:
                    number += (current or 1) * {"十": 10, "百": 100, "千": 1000}[character]
                    current = 0
            number += current
        _require(number == position + 1 and number not in ranges, "stored legal article sequence not consecutive")
        end = starts[position + 1].start() if position + 1 < len(starts) else len(text)
        end = min([end] + [boundary for boundary in chapters if match.start() < boundary < end])
        while end > match.start() and text[end - 1].isspace():
            end -= 1
        ranges[number] = match.start(), end
    _require(bool(ranges), "legal article chunks require independently parseable article boundaries")
    return ranges


def audit_artifact(input_path: Path, corpus_db: Path, *, trace_path: Path | None = None,
                   questions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Verify bindings and exact evidence bytes without importing production code.

    A successful audit demonstrates internal consistency with the selected local
    database, not original-source authenticity, legal currency, or execution of
    the declared code. Recorded-unverified artifacts remain recorded-unverified.
    """
    try:
        provenance, rows = load_input(input_path)
    except UnicodeError as exc:
        raise ArtifactAuditError("actual artifact must be UTF-8") from exc
    _require("trace_path" in provenance and "trace_sha256" in provenance,
             "audit requires trace_path and trace_sha256")
    declared_trace = Path(provenance["trace_path"])
    if not declared_trace.is_absolute():
        declared_trace = input_path.resolve().parent / declared_trace
    chosen_trace = (trace_path or declared_trace).resolve()
    _require(chosen_trace.is_file(), "trace file does not exist")
    raw_trace = chosen_trace.read_bytes()
    _require(_sha(raw_trace) == provenance["trace_sha256"], "trace SHA256 mismatch")
    traces = [_parse(line) for line in raw_trace.decode("utf-8").splitlines() if line.strip()]
    for trace in traces:
        _obj(trace, TRACE_REQUIRED, TRACE_OPTIONAL, "trace")
        _text(trace["id"], "trace.id")
    trace_ids = [trace["id"] for trace in traces]
    _require(len(trace_ids) == len(set(trace_ids)), "duplicate trace IDs")
    _require(set(trace_ids) == {row["id"] for row in rows}, "trace/envelope IDs differ")
    by_id = {trace["id"]: trace for trace in traces}
    if questions is not None:
        question_ids = [question["id"] for question in questions]
        _require(len(question_ids) == len(set(question_ids)), "duplicate question IDs")
        _require(set(question_ids) == set(trace_ids), "question/actual IDs differ")
    retrieval_config = provenance["retrieval_config"]
    dates = retrieval_config.get("per_case_dates", {})
    scopes = retrieval_config.get("case_scopes", [])
    _require(isinstance(dates, dict) and isinstance(scopes, list), "invalid declared per-case configuration")
    scope_by_id = {}
    for scope in scopes:
        _require(isinstance(scope, dict) and scope.get("id") in by_id, "invalid declared case scope")
        _require(scope["id"] not in scope_by_id, "duplicate declared case scope")
        scope_by_id[scope["id"]] = scope
    if scopes:
        _require(set(scope_by_id) == set(trace_ids), "declared case scopes lose rows")
    normalized: list[dict[str, Any]] = []
    try:
        with closing(read_only_connection(corpus_db)) as connection:
            _require(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity failure")
            _require(not connection.execute("PRAGMA foreign_key_check").fetchone(), "SQLite foreign key failure")
            snapshot = connection.execute("SELECT * FROM corpus_snapshots WHERE snapshot_id=?",
                                          (provenance["dataset_snapshot"],)).fetchone()
            _require(snapshot is not None, "selected snapshot does not exist")
            snapshot = dict(snapshot)
            members = [dict(record) for record in connection.execute(
                "SELECT v.*,m.document_id AS member_document_id FROM snapshot_members m JOIN document_versions v "
                "ON v.version_id=m.version_id WHERE m.snapshot_id=? ORDER BY v.version_id",
                (snapshot["snapshot_id"],),
            )]
            version_ids = [member["version_id"] for member in members]
            _require(bool(version_ids), "snapshot has no members")
            members_hash = _stored_hash(version_ids)
            _require(members_hash == snapshot["members_sha256"] == provenance["corpus_version"],
                     "snapshot membership hash mismatch")
            versions = {member["version_id"]: member for member in members}
            _require(len(versions) == len(members)
                     and len({member["document_id"] for member in members}) == len(members),
                     "duplicate snapshot version/document membership")
            texts = {}
            article_ranges = {}
            for member in members:
                _require(member["member_document_id"] == member["document_id"], "snapshot member document/version mismatch")
                raw = bytes(member["original_bytes"])
                _require(_sha(raw) == member["sha256"], "stored original hash mismatch")
                identity = _parse(member["identity_json"])
                _require("version_" + _stored_hash(identity) == member["version_id"], "stored version identity mismatch")
                _require(isinstance(identity.get("document"), dict)
                         and identity["document"].get("document_id") == member["document_id"],
                         "version document identity mismatch")
                if "title" in identity["document"]:
                    _require(identity["document"]["title"] == member["title"], "stored title identity mismatch")
                for field in ("source_uri", "sha256", "issued_date", "effective_from", "withdrawn_date",
                              "authority", "status", "extractor_version"):
                    _require(identity.get(field) == member[field], f"version identity {field} mismatch")
                _require(identity.get("provenance") == _parse(member["provenance_json"]),
                         "version provenance identity mismatch")
                if snapshot["kind"] == "trusted":
                    _require(member["authority"] == "authoritative_original" and member["status"] == "verified",
                             "trusted snapshot has unverified/non-authoritative member")
                if member["extractor_version"] == "utf8-markdown-v1":
                    texts[member["version_id"]] = raw.decode("utf-8")
                else:
                    extraction = connection.execute("SELECT * FROM document_extractions WHERE version_id=?",
                                                    (member["version_id"],)).fetchone()
                    _require(extraction is not None, "unsupported extraction without stored normalized text")
                    _require(_sha(bytes(extraction["artifact_bytes"])) == extraction["artifact_sha256"],
                             "stored extraction hash mismatch")
                    _require(identity.get("extraction_sha256") == extraction["artifact_sha256"],
                             "extraction identity mismatch")
                    texts[member["version_id"]] = extraction["normalized_text"]
                    if member["extractor_version"] == "official-html-v1":
                        normalized_html, removed_nul_count = _html_text(raw, identity)
                        extraction_receipt = _parse(bytes(extraction["artifact_bytes"]).decode("utf-8"))
                        _require(normalized_html == extraction["normalized_text"]
                                 and _sha(normalized_html.encode("utf-8")) == identity.get("normalized_text_sha256"),
                                 "independent HTML normalization differs from stored text")
                        _require(extraction_receipt.get("removed_nul_count") == removed_nul_count
                                 and extraction_receipt.get("normalized_text") == normalized_html
                                 and extraction_receipt.get("source_sha256") == member["sha256"],
                                 "HTML extraction receipt normalization mismatch")
            chunk_records = [dict(record) for record in connection.execute(
                "SELECT c.*, s.char_start AS section_start,s.char_end AS section_end,"
                "s.version_id AS section_version,s.text AS section_text,s.extraction_quality "
                "FROM chunks c JOIN sections s ON s.section_id=c.section_id "
                "JOIN snapshot_members m ON m.version_id=c.version_id WHERE m.snapshot_id=?",
                (snapshot["snapshot_id"],),
            )]
            chunks = {chunk["chunk_id"]: chunk for chunk in chunk_records}
            for row in rows:
                trace = by_id[row["id"]]
                for field in ("user_input", "response", "retrieved_contexts"):
                    _require(trace[field] == row[field], f"{row['id']}: trace/envelope {field} mismatch")
                _require(trace["status"] in {"retrieved", "answered", "unresolved", "error"}, "invalid trace status")
                _require(trace["answer_mode"] in {"extractive", "generated"}, "invalid answer mode")
                corpus, config = trace["corpus"], trace["config"]
                _require(isinstance(corpus, dict) and isinstance(config, dict), "invalid trace corpus/config")
                _require(corpus.get("snapshot_id") == snapshot["snapshot_id"], "trace snapshot mismatch")
                _require(corpus.get("members_sha256") == members_hash, "trace member hash mismatch")
                _require(corpus.get("kind") == snapshot["kind"], "trace snapshot kind mismatch")
                _require(Path(corpus.get("db_path", "")).resolve() == corpus_db.resolve(), "trace corpus DB path mismatch")
                _require(sorted(corpus.get("version_ids", [])) == version_ids, "trace snapshot members mismatch")
                as_of = _iso(corpus.get("as_of"), "trace.as_of")
                if dates:
                    _require(dates.get(row["id"]) == as_of, "declared per-case date mismatch")
                elif "as_of" in retrieval_config:
                    _require(retrieval_config["as_of"] == as_of, "declared date mismatch")
                include_undated = corpus.get("include_undated_research", False)
                _require(type(include_undated) is bool, "invalid include-undated policy")
                _require(not include_undated or snapshot["kind"] == "research", "undated policy only permitted for research")
                if snapshot["kind"] != "trusted":
                    _require(config.get("allow_nontrusted", retrieval_config.get("allow_nontrusted")) is True,
                             "non-trusted evidence lacks explicit policy")
                for name in ("top_k", "generate_requested", "include_undated_research", "allow_nontrusted"):
                    if name in config and name in retrieval_config:
                        _require(config[name] == retrieval_config[name], f"trace/envelope {name} mismatch")
                if "strategy_trace" not in trace:
                    _require(config.get("retrieval_strategy", "bm25") == "bm25"
                             and retrieval_config.get("retrieval_strategy", "bm25") == "bm25",
                             "non-legacy retrieval strategy lacks a strategy trace")
                requested_docs = config.get("doc_ids")
                requested_versions = config.get("version_ids")
                if requested_docs is not None:
                    _list_ids(requested_docs, "trace.doc_ids")
                if requested_versions is not None:
                    _list_ids(requested_versions, "trace.version_ids")
                declared_scope = scope_by_id.get(row["id"])
                if declared_scope:
                    for name in ("entity_iri", "doc_ids", "version_ids"):
                        if name in declared_scope:
                            _require(config.get(name) == declared_scope[name],
                                     f"declared {name} differs from trace")
                    _require(declared_scope.get("as_of") == as_of, "declared scope date mismatch")
                if questions is not None:
                    question = next(item for item in questions if item["id"] == row["id"])
                    _require(question["question"] == row["user_input"], "question text differs from actual")
                    _require(question["as_of"] == as_of, "question date differs from trace")
                    for name in ("doc_ids", "version_ids", "entity_iri"):
                        _require(question.get(name) == config.get(name),
                                 f"question {name} differs from trace")
                eligible_versions = {identifier for identifier, member in versions.items()
                                     if _eligible(member, as_of, include_undated)}
                evidence = trace["evidence"]
                _require(isinstance(evidence, list) and len(evidence) == len(row["retrieved_contexts"]),
                         "evidence/context count mismatch")
                _require((requested_docs != [] and requested_versions != []) or not evidence,
                         "explicit empty document/version scope carries evidence")
                evidence_ids, chunk_ids = set(), set()
                verified_evidence = []
                for position, item in enumerate(evidence):
                    _obj(item, EVIDENCE_REQUIRED, {"text_sha256"}, "evidence")
                    _require(item["evidence_id"] not in evidence_ids and item["chunk_id"] not in chunk_ids,
                             "duplicate evidence/chunk ID")
                    evidence_ids.add(item["evidence_id"])
                    chunk_ids.add(item["chunk_id"])
                    chunk = chunks.get(item["chunk_id"])
                    _require(chunk is not None, "evidence chunk outside selected snapshot")
                    member = versions[chunk["version_id"]]
                    _require(chunk["version_id"] in eligible_versions, "evidence outside as_of date eligibility")
                    _require(item["version_id"] == chunk["version_id"] and item["doc_id"] == member["document_id"],
                             "evidence version/document mismatch")
                    _require(requested_docs is None or item["doc_id"] in requested_docs, "evidence outside requested document scope")
                    _require(requested_versions is None or item["version_id"] in requested_versions, "evidence outside requested version scope")
                    _require(item["text"] == chunk["text"] == row["retrieved_contexts"][position],
                             "evidence/context/stored text mismatch")
                    _require(_sha(chunk["text"].encode("utf-8")) == chunk["text_sha256"], "stored chunk text hash mismatch")
                    _require(item["sha256"] == member["sha256"], "evidence original hash mismatch")
                    original = texts[chunk["version_id"]]
                    _require(type(chunk["char_start"]) is int and type(chunk["char_end"]) is int
                             and 0 <= chunk["char_start"] < chunk["char_end"] <= len(original),
                             "invalid chunk char range")
                    _require(original[chunk["char_start"]:chunk["char_end"]] == chunk["text"],
                             "chunk text not equal stored original char slice")
                    _require(chunk["section_version"] == chunk["version_id"]
                             and chunk["section_start"] <= chunk["char_start"] < chunk["char_end"] <= chunk["section_end"]
                             and original[chunk["section_start"]:chunk["section_end"]] == chunk["section_text"],
                             "invalid section/chunk containment")
                    locator = _parse(chunk["locator_json"])
                    locator.update({"source_uri": member["source_uri"], "source_path": member["source_path"],
                                    "sha256": member["sha256"], "version_id": member["version_id"],
                                    "original_storage": "sqlite:document_versions.original_bytes"})
                    _require(item["locator"] == locator, "evidence locator differs from stored locator")
                    _require(locator.get("char_start") == chunk["char_start"]
                             and locator.get("char_end") == chunk["char_end"], "locator char range mismatch")
                    complete_article = False
                    if locator.get("content_kind") == "legal_article":
                        _require(type(locator.get("article_number")) is int
                                 and locator["article_number"] > 0, "invalid legal article number")
                        if chunk["version_id"] not in article_ranges:
                            article_ranges[chunk["version_id"]] = _article_ranges(original)
                        expected_range = article_ranges[chunk["version_id"]].get(locator["article_number"])
                        _require(expected_range == (chunk["section_start"], chunk["section_end"]),
                                 "legal article section is not its exact original article boundary")
                        _require(locator.get("section_char_start") == chunk["section_start"]
                                 and locator.get("section_char_end") == chunk["section_end"],
                                 "legal article section locator range mismatch")
                        complete_article = chunk["char_start"] == chunk["section_start"] \
                            and chunk["char_end"] == chunk["section_end"]
                    for name in ("authority", "status", "issued_date", "effective_from", "withdrawn_date"):
                        _require(item[name] == member[name], f"evidence {name} differs from stored version")
                    _require(item["provenance"] == _parse(member["provenance_json"]), "evidence provenance mismatch")
                    links = [dict(link) for link in connection.execute(
                        "SELECT entity_id,method,confidence,review_status FROM entity_links WHERE chunk_id=? ORDER BY entity_id",
                        (chunk["chunk_id"],),
                    )]
                    _require(item["entity_links"] == links, "evidence entity links mismatch")
                    if config.get("entity_iri"):
                        _require(any(link["entity_id"] == config["entity_iri"]
                                     and link["review_status"] != "rejected" for link in links),
                                 "evidence outside entity scope")
                    _require(item["extraction_quality"] == chunk["extraction_quality"], "evidence extraction quality mismatch")
                    verified_evidence.append({
                        **item, "complete_article": complete_article,
                    })
                _require(trace["status"] != "error" or not evidence, "error trace carries retrieved evidence")
                _require(trace["status"] != "unresolved" or not evidence or trace["answer_mode"] == "generated",
                         "unresolved extractive trace carries retrieved evidence")
                _require(trace["status"] not in {"retrieved", "answered"} or bool(evidence),
                         "retrieved/answered trace lacks evidence")
                if "scope" in trace:
                    scope = trace["scope"]
                    _require(isinstance(scope, dict), "invalid resolved scope")
                    _require(scope.get("status") in {"resolved", "unresolved"}, "invalid scope status")
                    for field in ("doc_ids", "version_ids"):
                        _require(scope.get(f"requested_{field}") == config.get(field),
                                 f"scope requested {field} differs from trace config")
                    _require(scope.get("entity_iri") == config.get("entity_iri"), "scope entity differs from config")
                    selected_docs = _list_ids(scope.get("selected_doc_ids", []), "scope.selected_doc_ids")
                    selected_versions = _list_ids(scope.get("selected_version_ids", []), "scope.selected_version_ids")
                    _require(set(selected_versions) <= set(versions), "selected scope contains versions outside snapshot")
                    _require(set(selected_docs) <= {member["document_id"] for member in members},
                             "selected scope contains documents outside snapshot")
                    _require(requested_docs is None or set(selected_docs) <= set(requested_docs), "selected scope escapes requested documents")
                    _require(requested_versions is None or set(selected_versions) <= set(requested_versions),
                             "selected scope escapes requested versions")
                    eligible_ids = _list_ids(scope.get("eligible_chunk_ids", []), "scope.eligible_chunk_ids")
                    for identifier in eligible_ids:
                        _require(identifier in chunks and chunks[identifier]["version_id"] in eligible_versions,
                                 "scope eligible chunk not eligible in selected snapshot")
                        _require(chunks[identifier]["version_id"] in selected_versions, "eligible chunk escapes selected versions")
                        _require(versions[chunks[identifier]["version_id"]]["document_id"] in selected_docs,
                                 "eligible chunk escapes selected documents")
                    if requested_docs == [] or requested_versions == []:
                        _require(not eligible_ids and not selected_docs and not selected_versions,
                                 "explicit empty scope has selected documents/versions/chunks")
                    _require(chunk_ids <= set(eligible_ids), "retrieved chunks not in declared eligible scope")
                    for item in evidence:
                        _require(item["doc_id"] in selected_docs and item["version_id"] in selected_versions,
                                 "retrieved evidence escapes selected scope")
                if "retrieval_candidates" in trace:
                    candidates = trace["retrieval_candidates"]
                    _require(isinstance(candidates, list), "invalid retrieval candidates")
                    _require((requested_docs != [] and requested_versions != []) or not candidates,
                             "explicit empty scope has retrieval candidates")
                    candidate_ids = set()
                    selected_candidate_ids = []
                    last_score = None
                    for rank, candidate in enumerate(candidates, 1):
                        _obj(candidate, {"rank", "chunk_id", "doc_id", "version_id", "score", "selected"},
                             {"ranking"}, "retrieval_candidate")
                        identifier = candidate["chunk_id"]
                        _require(identifier not in candidate_ids and identifier in chunks, "duplicate or absent retrieval candidate")
                        candidate_ids.add(identifier)
                        candidate_chunk = chunks[identifier]
                        _require(candidate["rank"] == rank and type(candidate["selected"]) is bool,
                                 "invalid candidate rank/selection")
                        _require(type(config.get("top_k")) is int and config["top_k"] > 0
                                 and candidate["selected"] == (rank <= config["top_k"]),
                                 "candidate selection does not match top_k")
                        ranking = candidate.get("ranking", "bm25")
                        _require(ranking in {"bm25", "article_locator", "parent_bm25", "hybrid_rrf", "rerank"},
                                 "unsupported candidate ranking")
                        if ranking != "article_locator":
                            _score(candidate["score"], "candidate",
                                   positive=ranking in {"bm25", "parent_bm25", "hybrid_rrf"})
                            _require(ranking == "bm25" or "strategy_trace" in trace,
                                     "new ranking lacks independently audited strategy trace")
                            _require(last_score is None or candidate["score"] <= last_score, "candidate scores not descending")
                            last_score = candidate["score"]
                        else:
                            _require(candidate["score"] is None and "scope" in trace
                                     and bool(trace["scope"].get("article_numbers")),
                                     "article-locator ranking requires article scope and null score")
                        _require(candidate["version_id"] == candidate_chunk["version_id"]
                                 and candidate["doc_id"] == versions[candidate_chunk["version_id"]]["document_id"],
                                 "candidate document/version mismatch")
                        _require(candidate_chunk["version_id"] in eligible_versions, "candidate date ineligible")
                        if "scope" in trace:
                            _require(identifier in trace["scope"].get("eligible_chunk_ids", []), "candidate outside eligible scope")
                            if ranking == "article_locator":
                                candidate_locator = _parse(candidate_chunk["locator_json"])
                                _require(candidate_locator.get("article_number") in trace["scope"]["article_numbers"]
                                         and candidate_locator.get("content_kind") == "legal_article"
                                         and candidate_chunk["char_start"] == candidate_chunk["section_start"]
                                         and candidate_chunk["char_end"] == candidate_chunk["section_end"],
                                         "article-locator candidate is not a complete requested article")
                        if candidate["selected"]:
                            selected_candidate_ids.append(identifier)
                    _require(selected_candidate_ids == [item["chunk_id"] for item in evidence],
                             "selected candidates do not exactly match retrieved evidence order")
                    if "retrieval_debug" in trace:
                        debug = _obj(trace["retrieval_debug"], {
                            "ranking", "top_k", "candidate_count", "selected_count",
                            "budget_excluded_chunk_ids", "budget_excluded_articles",
                            "article_budget_sufficient",
                        }, set(), "retrieval_debug")
                        _require(debug["top_k"] == config["top_k"]
                                 and debug["candidate_count"] == len(candidates)
                                 and debug["selected_count"] == len(evidence),
                                 "retrieval debug counts disagree with candidates/evidence")
                        excluded = [candidate["chunk_id"] for candidate in candidates if not candidate["selected"]]
                        _require(debug["budget_excluded_chunk_ids"] == excluded,
                                 "retrieval debug excluded chunks disagree with selection")
                        _require(type(debug["article_budget_sufficient"]) is bool
                                 and debug["article_budget_sufficient"] == (not debug["budget_excluded_articles"]),
                                 "retrieval debug article budget flag mismatch")
                        if candidates:
                            _require(all(candidate.get("ranking", "bm25") == debug["ranking"] for candidate in candidates),
                                     "retrieval debug ranking disagrees with candidates")
                if "strategy_trace" in trace:
                    _require("retrieval_candidates" in trace and "retrieval_debug" in trace,
                             "strategy trace requires candidate/debug declarations")
                    _audit_strategy(trace, retrieval_config, chunks, texts)
                normalized.append({**trace, "evidence": verified_evidence})
    except (sqlite3.Error, UnicodeError, KeyError, TypeError) as exc:
        raise ArtifactAuditError(f"artifact audit unavailable ({type(exc).__name__}); details withheld") from exc
    return {
        "verified": True, "verification_kind": "local_artifact_consistency_only",
        "execution_origin": provenance["execution_origin"], "business_e2e": False,
        "source_authenticity_verified": False, "legal_currency_verified": False,
        "ranking_scores_independently_recomputed": False,
        "dense_and_rerank_scores_verification": "declared_only",
        "strategy_verification": "local_membership_offsets_channel_order_and_rrf_arithmetic",
        "input_file_sha256": _sha(input_path.read_bytes()), "trace_sha256": _sha(raw_trace),
        "corpus_db": str(corpus_db.resolve()), "snapshot_id": provenance["dataset_snapshot"],
        "snapshot_members_sha256": provenance["corpus_version"],
        "row_count": len(rows), "audit_implementation_sha256": _sha(Path(__file__).read_bytes()),
        "rows": normalized,
    }
