"""Deterministic local HTML extraction and complete legal-article boundaries."""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser


EXTRACTOR_VERSION = "official-html-v1"
TEXT_BASIS = "official-html-v1-normalized"
CHUNKER_VERSION = "legal-article-v1"
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
         "meta", "param", "source", "track", "wbr"}
_BLOCK = {"p", "div", "section", "article", "header", "footer", "li", "ul",
          "ol", "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}
_EXCLUDED = {"script", "style", "noscript", "template"}
_NUMBER = r"[一二三四五六七八九十百千零〇0-9]+"
_ARTICLE = re.compile(rf"^第({_NUMBER})条[ \t\u3000]+(?=\S)")
_CHAPTER = re.compile(rf"^第{_NUMBER}[章节][ \t\u3000]+\S")


def _number(value: str) -> int:
    if value.isascii() and value.isdigit():
        return int(value)
    digits = dict(zip("零〇一二三四五六七八九", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9)))
    total = 0
    current = 0
    for character in value:
        if character in digits:
            current = digits[character]
        else:
            total += (current or 1) * {"十": 10, "百": 100, "千": 1000}[character]
            current = 0
    return total + current


def validate_html_reference(reference: object) -> dict:
    if not isinstance(reference, dict) or set(reference) != {"kind", "selector", "encoding"}:
        raise ValueError("HTML extraction requires only kind, selector and encoding")
    if reference["kind"] != "official_html" or reference["encoding"] != "utf-8":
        raise ValueError("HTML extraction requires official_html and explicit utf-8")
    selector = reference["selector"]
    if not isinstance(selector, dict) or set(selector) != {"tag", "attribute", "value"}:
        raise ValueError("HTML selector requires only tag, attribute and value")
    if any(not isinstance(value, str) or not value.strip() for value in selector.values()):
        raise ValueError("HTML selector values must be nonempty strings")
    if (not re.fullmatch(r"[a-z][a-z0-9]*", selector["tag"])
            or selector["tag"] in _VOID | _EXCLUDED
            or not re.fullmatch(r"[a-z][a-z0-9_-]*", selector["attribute"])):
        raise ValueError("Invalid HTML selector tag or attribute")
    if selector["attribute"] == "class" and len(selector["value"].split()) != 1:
        raise ValueError("HTML class selector requires one class token")
    return reference


class _BodyParser(HTMLParser):
    def __init__(self, selector: dict):
        super().__init__(convert_charrefs=True)
        self.selector = selector
        self.stack: list[dict] = []
        self.root_counts: dict[str, int] = {}
        self.parts: list[str] = []
        self.matches = 0
        self.selected_depth: int | None = None
        self.dom_locator: dict | None = None
        self.closed = False
        self.removed_nul_count = 0

    def _active(self) -> bool:
        return self.selected_depth is not None and not any(
            frame["tag"] in _EXCLUDED for frame in self.stack[self.selected_depth - 1:]
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._active() and tag in _BLOCK:
            self.parts.append("\n")
        counts = self.stack[-1]["counts"] if self.stack else self.root_counts
        counts[tag] = counts.get(tag, 0) + 1
        path = (self.stack[-1]["path"] if self.stack else "") + f"/{tag}[{counts[tag]}]"
        values = [value for key, value in attrs if key == self.selector["attribute"]]
        if len(values) > 1:
            raise ValueError("Duplicate HTML selector attribute")
        value = values[0] if values else None
        matches = tag == self.selector["tag"] and value is not None and (
            self.selector["value"] in value.split() if self.selector["attribute"] == "class"
            else value == self.selector["value"]
        )
        if matches:
            self.matches += 1
            if self.matches > 1:
                raise ValueError("HTML body selector must match exactly one element")
            self.selected_depth = len(self.stack) + 1
            self.dom_locator = {"selector": self.selector, "path": path,
                                "html_line": self.getpos()[0]}
        if tag not in _VOID:
            self.stack.append({"tag": tag, "path": path, "counts": {}})

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID:
            return
        if not self.stack or self.stack[-1]["tag"] != tag:
            if self.selected_depth is not None:
                raise ValueError("Unbalanced HTML inside selected body")
            return
        if self._active() and tag in _BLOCK:
            self.parts.append("\n")
        if self.selected_depth == len(self.stack):
            self.selected_depth = None
            self.closed = True
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self._active():
            if any(ord(character) < 32 and not character.isspace() and character != "\x00"
                   for character in data):
                raise ValueError("Unsupported control character in selected HTML body")
            self.removed_nul_count += data.count("\x00")
            self.parts.append(re.sub(r"\s+", " ", data.replace("\x00", "")))


def extract_official_html(raw: bytes, reference: object) -> dict:
    """Select one DOM container, exclude executable content, normalize paragraphs."""
    reference = validate_html_reference(reference)
    parser = _BodyParser(reference["selector"])
    parser.feed(raw.decode(reference["encoding"], errors="strict"))
    parser.close()
    if parser.matches != 1 or not parser.closed:
        raise ValueError("HTML body selector must match exactly one closed element")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip()
             for line in "".join(parser.parts).splitlines()]
    text = "\n".join(line for line in lines if line)
    if not text:
        raise ValueError("Selected HTML body is empty")
    return {"text": text, "dom_locator": parser.dom_locator,
            "removed_nul_count": parser.removed_nul_count,
            "normalized_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def legal_article_sections(text: str, *, expected_articles: int | None = None) -> list[dict]:
    """Require ordered 1..N article starts; chapters and preamble are not sections."""
    if expected_articles is not None and (
        type(expected_articles) is not int or not 1 <= expected_articles <= 10000
    ):
        raise ValueError("expected_articles must be a positive integer at most 10000")
    sections = []
    chapter = None
    position = 0
    previous = None
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if _CHAPTER.match(content):
            if previous is not None:
                previous["char_end"] = position
                previous = None
            chapter = content.strip()
        match = _ARTICLE.match(content)
        if match:
            if previous is not None:
                previous["char_end"] = position
            number = _number(match.group(1))
            section = {
                "heading": f"第{match.group(1)}条",
                "article_number": number,
                "chapter": chapter,
                "char_start": position,
                "char_end": len(text),
            }
            sections.append(section)
            previous = section
        position += len(line)
    numbers = [section["article_number"] for section in sections]
    total = expected_articles if expected_articles is not None else len(sections)
    if not numbers or numbers != list(range(1, total + 1)):
        raise ValueError(f"Legal article sequence must be consecutive 1..{total}: {numbers}")
    for section in sections:
        end = section["char_end"]
        while end > section["char_start"] and text[end - 1].isspace():
            end -= 1
        section["char_end"] = end
    return sections
