"""Fail-closed document scope decisions for the independent document pipeline."""

from __future__ import annotations

import re

from fondontology.corpus import CorpusError

from .store import ChunkStore


SCOPE_POLICY = "document-body-scope-v1"
_TITLES = re.compile(r"《([^《》]+)》")
_ARTICLE = re.compile(r"^\s*(?:的)?\s*第([零〇一二三四五六七八九十百千两\d]+)条")
_ARTICLE_NUMBER = re.compile(r"第([零〇一二三四五六七八九十百千两\d]+)条")
_ARTICLE_RANGE = re.compile(
    r"第[零〇一二三四五六七八九十百千两\d]+条\s*(?:至|到|[-~～—])")
_SCOPE_PREFIX = re.compile(
    r"(?:^|[，,；;。])\s*(?:请\s*)?(?:(?:仅仅|仅|只)\s*)?"
    r"(?:依据|根据|按照|依照|按)\s*"
    r"(?:入库的|所选的|现行的)?\s*$")
_DIRECT_REQUEST_PREFIX = re.compile(
    r"(?:^|[，,；;。])\s*(?:但是|但|不过)?\s*"
    r"(?:(?:请|麻烦|帮我|请帮我)\s*)?"
    r"(?:问(?:一下)?|查询|查看|解释(?:一下)?|介绍(?:一下)?|"
    r"告诉我|给我|提供|列出|展示|我想(?:查询|查看|了解)|"
    r"我要(?:的是|查看|查询)?|能否(?:告诉我|提供|查询|查看))\s*"
    r"(?:入库的|所选的)?\s*(?:[12]\d{3}(?:年)?版\s*)?$")
_REFERENCE_PREFIX = re.compile(
    r"(?:正文|原文|文中)?(?:引用|提到|援引)|例如|举例")
_CLAUSE_BREAK = re.compile(r"[，,；;。！？!?\r\n]")
_FILLER = re.compile(
    r"^(?:依据|根据|按照|依照|按)?(?:入库的|所选的|现行的)?"
    r"(?:的)?(?:内容|全文|正文)?(?:是|为)?(?:什么|如何)?$")


def validate_ids(value: list[str] | None, field: str) -> list[str] | None:
    if value is None:
        return None
    if (not isinstance(value, list)
            or any(not isinstance(item, str) or not item.strip() for item in value)):
        raise CorpusError(f"{field} must be null or a list of nonempty IDs")
    return list(dict.fromkeys(value))


def _number(value: str) -> int | None:
    if value.isascii() and value.isdigit():
        return int(value)
    digits = dict(zip("零〇一二三四五六七八九两", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2)))
    units = {"十": 10, "百": 100, "千": 1000}
    total = 0
    current = 0
    for character in value:
        if character in digits:
            current = digits[character]
        elif character in units:
            total += (current or 1) * units[character]
            current = 0
        else:
            return None
    return total + current


def _scope_titles(question: str) -> list:
    recognized = []
    for mention in _TITLES.finditer(question):
        prefix = question[:mention.start()].strip()
        direct_article = _ARTICLE.match(question[mention.end():])
        if (not prefix or _SCOPE_PREFIX.search(prefix)
                or (recognized and re.fullmatch(r"[、与及和\s]+", question[
                    recognized[-1].end():mention.start()]))
                or (recognized and re.fullmatch(
                    r"(?:的)?\s*第[零〇一二三四五六七八九十百千两\d]+条"
                    r"(?:\s*[、与及和]\s*第[零〇一二三四五六七八九十百千两\d]+条)*"
                    r"\s*[、与及和]\s*",
                    question[recognized[-1].end():mention.start()]))):
            recognized.append(mention)
        elif direct_article and _DIRECT_REQUEST_PREFIX.search(prefix):
            recognized.append(mention)
    return recognized


def _article_requests(text: str) -> tuple[list[int], str | None]:
    if _ARTICLE_RANGE.search(text):
        return [], "unsupported_article_range"
    numbers = []
    for article in _ARTICLE_NUMBER.finditer(text):
        number = _number(article.group(1))
        if number is None or number < 1:
            return [], "invalid_article_number"
        if number not in numbers:
            numbers.append(number)
    return numbers, None


def _is_metadata(chunk) -> bool:
    if chunk.locator.get("content_kind") == "metadata":
        return True
    title = str(chunk.locator.get("title") or "").strip()
    section = str(chunk.locator.get("section") or "").strip()
    return bool(title and section == title and chunk.text.lstrip().startswith("#")
                and chunk.locator.get("char_start") == 0)


def resolve_scope(question: str, store: ChunkStore, *, doc_ids: list[str] | None,
                  version_ids: list[str] | None, entity_iri: str | None) -> dict:
    documents = validate_ids(doc_ids, "doc_ids")
    versions = validate_ids(version_ids, "version_ids")
    directory = store.corpus_metadata.get("document_directory")
    if directory is None:
        directory = [{
            "doc_id": chunk.doc_id, "version_id": chunk.version_id,
            "title": chunk.locator.get("title", ""),
        } for chunk in store.chunks]
    catalog = {(item["doc_id"], item["version_id"]): item for item in directory}
    pairs = set(catalog)
    decision = {
        "policy": SCOPE_POLICY, "status": "resolved", "reason": None,
        "requested_doc_ids": documents, "requested_version_ids": versions,
        "entity_iri": entity_iri, "title_mentions": [], "title_candidates": [],
        "selected_doc_ids": [], "selected_version_ids": [],
        "eligible_chunk_ids": [], "article_numbers": [],
        "requested_articles": [], "missing_articles": [],
        "body_query": question, "metadata_excluded_ids": [],
    }

    def unresolved(reason: str) -> dict:
        decision["status"], decision["reason"] = "unresolved", reason
        return decision

    for requested, key in ((documents, "doc_id"), (versions, "version_id")):
        if requested is None:
            continue
        if not requested:
            return unresolved(f"empty_{key}_scope")
        known = {item[key] for item in catalog.values()}
        unknown = sorted(set(requested) - known)
        if unknown:
            decision["unknown_ids"] = unknown
            return unresolved(f"unknown_{key}")
        pairs = {pair for pair in pairs if catalog[pair][key] in requested}
        if not pairs:
            return unresolved("conflicting_document_version_scope")

    mentions = _scope_titles(question)
    decision["title_mentions"] = [mention.group(1).strip() for mention in mentions]
    if documents is not None or versions is not None:
        recognized_starts = {mention.start() for mention in mentions}
        for mention in _TITLES.finditer(question):
            if (mention.start() not in recognized_starts
                    and _ARTICLE.match(question[mention.end():])
                    and not _REFERENCE_PREFIX.search(
                        _CLAUSE_BREAK.split(question[:mention.start()])[-1])):
                return unresolved("unsupported_title_scope_syntax")
    body_query = question
    title_pairs = set()
    article_pairs = {}
    for mention_index, mention in enumerate(mentions):
        title = mention.group(1).strip()
        matches = {pair for pair in pairs if catalog[pair]["title"].strip() == title}
        all_matches = {pair for pair in catalog if catalog[pair]["title"].strip() == title}
        decision["title_candidates"].append({
            "title": title,
            "matches": [{"doc_id": pair[0], "version_id": pair[1]}
                        for pair in sorted(all_matches)],
            "after_explicit_scope": [{"doc_id": pair[0], "version_id": pair[1]}
                                     for pair in sorted(matches)],
        })
        if not all_matches:
            return unresolved("unknown_document_title")
        if not matches:
            return unresolved("conflicting_title_scope")
        if len(matches) != 1:
            return unresolved("ambiguous_document_title")
        title_pairs.update(matches)
        body_query = body_query.replace(mention.group(0), "", 1)
        article = _ARTICLE.match(question[mention.end():])
        if article:
            end = (mentions[mention_index + 1].start()
                   if mention_index + 1 < len(mentions) else len(question))
            numbers, reason = _article_requests(question[mention.end():end])
            if reason:
                return unresolved(reason)
            decision["article_numbers"].extend(
                number for number in numbers if number not in decision["article_numbers"])
            for pair in matches:
                article_pairs.setdefault(pair, set()).update(numbers)
    if mentions:
        pairs = title_pairs
    elif documents is not None or versions is not None:
        article = re.match(
            r"^\s*(?:请问|查询|查看|解释|介绍)?\s*第([零〇一二三四五六七八九十百千两\d]+)条",
            question)
        if article:
            numbers, reason = _article_requests(question)
            if reason:
                return unresolved(reason)
            if len(pairs) != 1:
                return unresolved("ambiguous_article_document_scope")
            decision["article_numbers"].extend(numbers)
            article_pairs = {pair: set(numbers) for pair in pairs}
    decision["requested_articles"] = [{
        "doc_id": pair[0], "version_id": pair[1], "article_number": number,
    } for pair in sorted(article_pairs) for number in sorted(article_pairs[pair])]
    decision["selected_doc_ids"] = sorted({pair[0] for pair in pairs})
    decision["selected_version_ids"] = sorted({pair[1] for pair in pairs if pair[1]})
    candidates = [chunk for chunk in store.chunks
                  if (chunk.doc_id, chunk.version_id) in pairs]
    if not candidates:
        return unresolved("no_documents_available_at_as_of")
    if entity_iri:
        candidates = [chunk for chunk in candidates if any(
            link.get("entity_id") == entity_iri and link.get("review_status") != "rejected"
            for link in chunk.entity_links)]
        if not candidates:
            return unresolved("empty_entity_intersection")
    metadata = [chunk.chunk_id for chunk in candidates if _is_metadata(chunk)]
    decision["metadata_excluded_ids"] = metadata
    metadata_ids = set(metadata)
    candidates = [chunk for chunk in candidates if chunk.chunk_id not in metadata_ids]
    if decision["article_numbers"]:
        candidates = [chunk for chunk in candidates if (
            type(chunk.locator.get("article_number")) is int
            and chunk.locator.get("content_kind") == "legal_article"
            and type(chunk.locator.get("char_start")) is int
            and type(chunk.locator.get("char_end")) is int
            and chunk.locator.get("char_start") == chunk.locator.get("section_char_start")
            and chunk.locator.get("char_end") == chunk.locator.get("section_char_end")
            and chunk.locator.get("article_number") in article_pairs.get(
                (chunk.doc_id, chunk.version_id), set()))]
        available_articles = {
            (chunk.doc_id, chunk.version_id, chunk.locator["article_number"])
            for chunk in candidates}
        decision["missing_articles"] = [
            requested for requested in decision["requested_articles"]
            if (requested["doc_id"], requested["version_id"],
                requested["article_number"]) not in available_articles]
        if decision["missing_articles"]:
            return unresolved("article_not_available")
    if not candidates:
        return unresolved("no_body_evidence")
    if mentions:
        body_query = re.sub(
            r"(?:依据|根据|按照|依照|按)\s*(?:入库的|所选的|现行的)?\s*", "", body_query, count=1)
        significant = re.sub(r"[\s，。？?：:、；;！!（）()]", "", body_query)
        if not significant or _FILLER.fullmatch(significant):
            return unresolved("empty_body_query")
    decision["body_query"] = body_query.strip(" \t\r\n，,:：")
    decision["eligible_chunk_ids"] = [chunk.chunk_id for chunk in candidates]
    return decision
