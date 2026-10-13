"""Independent input-cue and recorded retrieval search-scope diagnostics."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .artifact_audit import (
    _article_ranges, _eligible, _parse,
    audit_artifact, read_only_connection,
)
from .legal_retrieval import load_questions
from .ragas_runner import load_input


class SearchScopeError(ValueError):
    pass


_BOOK_TITLE = re.compile(r"《([^《》]+)》")
_LAW_NAME = re.compile(
    r"[\u4e00-\u9fff]{2,}(?:管理办法|管理条例|实施细则|监督条例|保护法|安全法|促进法)"
    r"|(?:证券|基金|公司|合同|劳动|民事诉讼|行政诉讼|刑事诉讼)法")
_ARTICLE = re.compile(r"第[零〇一二三四五六七八九十百千两0-9]+条")
_VERSION = re.compile(
    r"(?:[12][0-9]{3}(?:年(?:[0-9]{1,2}月(?:[0-9]{1,2}日)?)?"
    r"|-[0-9]{2}-[0-9]{2})?"
    r"(?:修订|修正|修改|发布|公布)?(?:版本|年版|版|修订|修正))"
    r"|(?:现行|旧|新修订|修订后|修订|修正|最新|原)(?:版本|版)"
    r"|(?:版本\s*ID|version[_ -]?id|证监会令\s*第[零〇一二三四五六七八九十百千两0-9]+号)",
    re.IGNORECASE,
)
_SCOPE_FIELDS = ("doc_ids", "version_ids", "entity_iri")
_CASE_FIELDS = {"id", "question", "as_of"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SearchScopeError(message)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_registry(path: Path) -> list[dict[str, Any]]:
    payload = _parse(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict) and payload.get("schema_version") == "1.0",
             "registry requires schema_version 1.0")
    sources = payload.get("sources")
    _require(isinstance(sources, list) and bool(sources), "registry.sources must be nonempty")
    identifiers = set()
    for source in sources:
        _require(isinstance(source, dict), "registry source must be an object")
        for name in ("doc_id", "title"):
            _require(isinstance(source.get(name), str) and bool(source[name].strip()),
                     f"registry source requires {name}")
        _require(source["doc_id"] not in identifiers, "duplicate registry doc_id")
        identifiers.add(source["doc_id"])
    return sources


def input_cues(case: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    question = case["question"]
    titles = sorted({source["title"] for source in sources if source["title"] in question})
    identifiers = sorted({source["doc_id"] for source in sources if source["doc_id"] in question})
    cues = {
        "scope_fields": {name: case[name] for name in _SCOPE_FIELDS if name in case},
        "registered_title_mentions": titles,
        "registered_document_id_mentions": identifiers,
        "book_title_mentions": [match.group(1) for match in _BOOK_TITLE.finditer(question)],
        "bare_law_name_mentions": sorted(set(_LAW_NAME.findall(question))),
        "version_mentions": sorted({match.group(0) for match in _VERSION.finditer(question)}),
        "article_mentions": sorted(set(_ARTICLE.findall(question))),
    }
    cues["has_source_cues"] = any(cues.values())
    return cues


def _metadata(chunk: dict[str, Any]) -> bool:
    locator = chunk["locator"]
    title = str(locator.get("title") or "").strip()
    section = str(locator.get("section") or "").strip()
    return locator.get("content_kind") == "metadata" or bool(
        title and section == title and chunk["text"].lstrip().startswith("#")
        and locator.get("char_start") == 0)


def _read_snapshot(corpus_db: Path, snapshot_id: str) -> tuple[dict, dict]:
    try:
        with closing(read_only_connection(corpus_db)) as connection:
            members = {
                record["version_id"]: dict(record) for record in connection.execute(
                    "SELECT v.* FROM document_versions v JOIN snapshot_members m "
                    "ON m.version_id=v.version_id WHERE m.snapshot_id=?", (snapshot_id,))
            }
            texts = {}
            for identifier, member in members.items():
                if member["extractor_version"] == "utf8-markdown-v1":
                    texts[identifier] = bytes(member["original_bytes"]).decode("utf-8")
                else:
                    extracted = connection.execute(
                        "SELECT normalized_text FROM document_extractions WHERE version_id=?",
                        (identifier,)).fetchone()
                    _require(extracted is not None, "snapshot lacks stored extraction")
                    texts[identifier] = extracted["normalized_text"]
            records = connection.execute(
                "SELECT c.*,s.char_start AS section_start,s.char_end AS section_end,"
                "s.text AS section_text,s.version_id AS section_version "
                "FROM chunks c JOIN sections s ON s.section_id=c.section_id "
                "JOIN snapshot_members m ON m.version_id=c.version_id WHERE m.snapshot_id=?",
                (snapshot_id,))
            chunks = {}
            ranges = {}
            for record in records:
                chunk = dict(record)
                identifier = chunk["chunk_id"]
                _require(identifier not in chunks, "duplicate snapshot chunk")
                text = texts[chunk["version_id"]]
                start, end = chunk["char_start"], chunk["char_end"]
                section_start, section_end = chunk["section_start"], chunk["section_end"]
                _require(all(type(value) is int for value in (start, end, section_start, section_end))
                         and 0 <= section_start <= start < end <= section_end <= len(text),
                         "snapshot chunk/section offsets invalid")
                _require(chunk["section_version"] == chunk["version_id"]
                         and text[start:end] == chunk["text"]
                         and text[section_start:section_end] == chunk["section_text"]
                         and hashlib.sha256(chunk["text"].encode()).hexdigest() == chunk["text_sha256"],
                         "snapshot chunk/section bytes differ")
                locator = _parse(chunk["locator_json"])
                _require(isinstance(locator, dict) and locator.get("char_start") == start
                         and locator.get("char_end") == end, "snapshot chunk locator offsets differ")
                chunk["locator"] = locator
                chunk["complete_article"] = False
                if locator.get("content_kind") == "legal_article":
                    version = chunk["version_id"]
                    if version not in ranges:
                        ranges[version] = _article_ranges(text)
                    number = locator.get("article_number")
                    _require(type(number) is int and number > 0
                             and ranges[version].get(number) == (section_start, section_end)
                             and locator.get("section_char_start") == section_start
                             and locator.get("section_char_end") == section_end,
                             "snapshot legal article boundary differs")
                    chunk["complete_article"] = start == section_start and end == section_end
                chunks[identifier] = chunk
            for identifier, member in members.items():
                if identifier not in ranges and re.search(
                        r"(?m)^第[一二三四五六七八九十百千零〇0-9]+条[ \t\u3000]+(?=\S)",
                        texts[identifier]):
                    ranges[identifier] = _article_ranges(texts[identifier])
                member["full_article_count"] = len(ranges.get(identifier, {}))
            return members, chunks
    except (sqlite3.Error, UnicodeError, KeyError, TypeError) as exc:
        raise SearchScopeError(f"snapshot diagnostic unavailable ({type(exc).__name__})") from exc


def _article_addresses(chunks: dict, identifiers: set[str]) -> set[tuple]:
    return {(chunks[identifier]["version_id"], chunks[identifier]["locator"]["article_number"])
            for identifier in identifiers if chunks[identifier]["complete_article"]}


def _execution_case(case: dict, trace: dict, members: dict, chunks: dict,
                    require_unscoped: bool) -> dict[str, Any]:
    scope = trace.get("scope")
    _require(isinstance(scope, dict), f"{case['id']}: execution diagnostic requires scope trace")
    for name in ("eligible_chunk_ids", "title_mentions", "article_numbers"):
        _require(isinstance(scope.get(name), list), f"{case['id']}: scope requires {name}")
    eligible = set(scope["eligible_chunk_ids"])
    _require(all(isinstance(identifier, str) for identifier in scope["eligible_chunk_ids"]),
             "invalid scope eligible ID")
    _require(len(eligible) == len(scope["eligible_chunk_ids"]), "duplicate scope eligible ID")
    available_versions = {
        identifier for identifier, member in members.items()
        if _eligible(member, case["as_of"], trace["corpus"].get("include_undated_research", False))
    }
    available = {identifier for identifier, chunk in chunks.items()
                 if chunk["version_id"] in available_versions and not _metadata(chunk)}
    _require(eligible <= set(chunks), "scope eligible IDs outside database")
    violations = []
    if eligible - available:
        violations.append("eligible_set_contains_metadata_or_date_ineligible_chunks")
    direct = bool(scope["article_numbers"] or scope.get("requested_articles")
                  or any(candidate.get("ranking") == "article_locator"
                         for candidate in trace.get("retrieval_candidates", []))
                  or trace.get("retrieval_debug", {}).get("ranking") == "article_locator"
                  or trace.get("strategy_trace", {}).get("effective_strategy") == "article_locator")
    if require_unscoped:
        if eligible != available:
            violations.append("eligible_set_differs_from_all_available_body_chunks")
        if scope["title_mentions"]:
            violations.append("runtime_title_scope_present")
        if direct:
            violations.append("direct_article_bypass_present")
        if any(trace["config"].get(name) is not None for name in _SCOPE_FIELDS):
            violations.append("runtime_explicit_scope_present")
    if "eligible_chunk_count" in scope and (
            type(scope["eligible_chunk_count"]) is not int or scope["eligible_chunk_count"] != len(eligible)):
        violations.append("declared_eligible_chunk_count_disagrees")
    searchable_docs = sorted({members[chunks[identifier]["version_id"]]["document_id"]
                              for identifier in eligible})
    return {
        "candidate_searchable_doc_ids": searchable_docs,
        "candidate_searchable_document_count": len(searchable_docs),
        "eligible_chunk_count": len(eligible),
        "available_body_document_count": len({
            members[chunks[identifier]["version_id"]]["document_id"] for identifier in available}),
        "available_body_chunk_count": len(available),
        "snapshot_full_article_count": sum(member["full_article_count"] for member in members.values()),
        "available_full_article_count": sum(
            members[identifier]["full_article_count"] for identifier in available_versions),
        "searchable_full_article_count": len(_article_addresses(chunks, eligible)),
        "missing_available_chunk_ids": sorted(available - eligible),
        "unexpected_eligible_chunk_ids": sorted(eligible - available),
        "runtime_title_mentions": scope["title_mentions"],
        "direct_article_bypass": direct,
        "violations": violations,
    }


def diagnose_search_scope(questions_path: Path, registry_path: Path, *,
                          actual_path: Path | None = None, corpus_db: Path | None = None,
                          require_unscoped: bool = False) -> dict[str, Any]:
    _require((actual_path is None) == (corpus_db is None), "--actual and --corpus-db must be paired")
    questions = load_questions(questions_path)
    sources = _load_registry(registry_path)
    report = {
        "schema_version": "1.0",
        "diagnostic_scope": "retrieval search-scope diagnostic only",
        "require_unscoped": require_unscoped,
        "questions_file_sha256": _hash_file(questions_path),
        "registry_file_sha256": _hash_file(registry_path),
        "heuristic_limitations": [
            "No detected cue is not proof of natural language or absence of source leakage; "
            "aliases, paraphrases and implicit source knowledge may evade these heuristics.",
            "Explicit legal citations are legitimate user inputs; require-unscoped is a benchmark input contract.",
        ],
        "claims_not_established": [
            "answer correctness", "question naturalness", "corpus scale or completeness",
            "original-source authenticity", "legal currency", "real execution certification",
        ],
        "execution_limitation": "Exact eligible-set equality checks the recorded search scope against "
                                "stored available body chunks; it does not certify that BM25 or any "
                                "retriever actually executed over every eligible chunk.",
        "execution_checked": actual_path is not None,
        "cases": [],
    }
    traces = {}
    members, chunks = {}, {}
    if actual_path is not None:
        audit = audit_artifact(actual_path, corpus_db, questions=questions)
        report["audit"] = {name: value for name, value in audit.items() if name != "rows"}
        traces = {row["id"]: row for row in audit["rows"]}
        members, chunks = _read_snapshot(corpus_db, audit["snapshot_id"])
    for case in questions:
        cues = input_cues(case, sources)
        violations = []
        if require_unscoped:
            if set(case) != _CASE_FIELDS:
                violations.append("case_fields_must_be_exactly_id_question_as_of")
            if cues["has_source_cues"]:
                violations.append("source_hint_or_explicit_scope_present")
        row = {"id": case["id"], "as_of": case["as_of"], "input_cues": cues}
        if actual_path is not None:
            row["execution"] = _execution_case(case, traces[case["id"]], members, chunks,
                                               require_unscoped)
            violations.extend(row["execution"]["violations"])
        row["violations"] = violations
        report["cases"].append(row)
    report["row_count"] = len(questions)
    report["cue_case_count"] = sum(row["input_cues"]["has_source_cues"] for row in report["cases"])
    report["nonpass_count"] = sum(bool(row["violations"]) for row in report["cases"])
    report["passed"] = report["nonpass_count"] == 0
    return report


def check_output_path(output: Path, inputs: list[Path], actual_path: Path | None = None) -> None:
    protected = list(inputs)
    if actual_path is not None:
        provenance, _rows = load_input(actual_path)
        trace_path = Path(provenance["trace_path"])
        if not trace_path.is_absolute():
            trace_path = actual_path.resolve().parent / trace_path
        protected.append(trace_path)
    for source in protected:
        _require(output.resolve() != source.resolve()
                 and not (output.exists() and source.exists() and output.samefile(source)),
                 "output must not overwrite questions, registry, actual, trace or corpus database")
