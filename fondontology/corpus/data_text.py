"""Explicit body boundaries for verified data catalog Markdown."""

from __future__ import annotations

import re

from .legal_text import legal_article_sections


CHUNKER_VERSION = "data-catalog-body-v1"
_PREFIX = re.compile(r"^([ \t]*(?:#{1,6}[ \t]+)?)(?=第)")
_ARTICLE = re.compile(r"(?m)^[ \t]*(?:#{1,6}[ \t]+)?第[一二三四五六七八九十百千零〇0-9]+条[ \t\u3000]+(?=\S)")


def catalog_body_sections(text: str, config: dict) -> list[dict]:
    """Keep offsets in the original Markdown while excluding its source header."""
    if (set(config) != {"strategy", "body_start_line", "expected_articles", "max_chars", "overlap"}
            or config["strategy"] != CHUNKER_VERSION
            or type(config["body_start_line"]) is not int or config["body_start_line"] < 1):
        raise ValueError("Data body config requires an explicit positive body_start_line")
    lines = text.splitlines(keepends=True)
    if config["body_start_line"] > len(lines):
        raise ValueError("body_start_line is outside the Markdown")
    start = sum(map(len, lines[:config["body_start_line"] - 1]))
    body = text[start:]
    expected = config["expected_articles"]
    if expected is not None:
        normalized_lines = []
        positions = []
        line_starts = {}
        original_offset = start
        normalized_offset = 0
        for line in body.splitlines(keepends=True):
            match = _PREFIX.match(line)
            removed = len(match.group(1)) if match else 0
            normalized_line = line[removed:]
            normalized_lines.append(normalized_line)
            line_starts[normalized_offset] = original_offset
            positions.extend(range(original_offset + removed, original_offset + len(line)))
            original_offset += len(line)
            normalized_offset += len(normalized_line)
        normalized = "".join(normalized_lines)
        sections = [{**section, "char_start": line_starts[section["char_start"]],
                     "char_end": positions[section["char_end"] - 1] + 1}
                    for section in legal_article_sections(normalized, expected_articles=expected)]
        appendix = re.search(r"(?m)^[ \t]*(?:#{1,6}[ \t]+)?附[件录](?:[ \t]*[:：]|[ \t]+|\r?$)", body)
        if appendix:
            appendix_start = start + appendix.start()
            for section in sections:
                if section["char_start"] < appendix_start < section["char_end"]:
                    section["char_end"] = appendix_start
        gaps = []
        cursor = start
        for section in sorted(sections, key=lambda item: item["char_start"]):
            if cursor < section["char_start"]:
                gaps.append((cursor, section["char_start"]))
            cursor = section["char_end"]
        if cursor < len(text):
            gaps.append((cursor, len(text)))
        chapter_heading = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+)?第[一二三四五六七八九十百千零〇0-9]+[章节][ \t\u3000]+\S")
        for gap_start, gap_end in gaps:
            substantive = []
            offset = gap_start
            for line in text[gap_start:gap_end].splitlines(keepends=True):
                if line.strip() and not chapter_heading.match(line):
                    substantive.append((offset, offset + len(line.rstrip("\r\n"))))
                offset += len(line)
            if substantive:
                supplemental_start, supplemental_end = substantive[0][0], substantive[-1][1]
                sections.append({"heading": "supplementary_body", "char_start": supplemental_start,
                                 "char_end": supplemental_end})
        return sorted(sections, key=lambda item: item["char_start"])
    if not body.strip():
        raise ValueError("Catalog body is empty")
    headings = list(re.finditer(r"(?m)^#{1,6}[ \t]+(.+)$", body))
    boundaries = [(heading.group(1).strip(), heading.start()) for heading in headings]
    if not boundaries or boundaries[0][1] > 0:
        boundaries.insert(0, ("document", 0))
    return [{"heading": heading, "char_start": start + offset,
             "char_end": start + (boundaries[ordinal + 1][1]
                                  if ordinal + 1 < len(boundaries) else len(body))}
            for ordinal, (heading, offset) in enumerate(boundaries)
            if body[offset:(boundaries[ordinal + 1][1]
                            if ordinal + 1 < len(boundaries) else len(body))].strip()]


def article_body_start_line(text: str) -> int:
    match = _ARTICLE.search(text)
    if match is None:
        raise ValueError("Ready legal Markdown has no complete article heading")
    return text.count("\n", 0, match.start()) + 1
