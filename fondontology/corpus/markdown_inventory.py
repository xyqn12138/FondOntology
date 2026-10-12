"""Auditable inventory and selection helpers for local legal Markdown files."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


_METADATA_RE = re.compile(r"^\*\*(?P<key>[^*]+)\*\*\s*[:：]\s*(?P<value>.+?)\s*$")
_NUMBER = r"[一二三四五六七八九十百千万零〇0-9]+"
_ARTICLE_RE = re.compile(rf"^\s*(?:#{{1,6}}\s+)?第({_NUMBER})条(?!至)")
_RANGE_START_RE = re.compile(rf"^\s*(?:#{{1,6}}\s+)?第({_NUMBER})条?至第?({_NUMBER})条")
_INCOMPLETE_MARKERS = (
    "摘要",
    "摘录",
    "摘编",
    "核心条款整理",
    "核心制度内容",
    "非逐条全文",
    "未能直接抓取",
    "未完整获取",
    "暂未能",
    "暂未抓取",
    "需通过",
    "建议后续补充",
    "不属于全文",
)
_COMPLETE_RE = re.compile(r"(?:逐条全文|(?<!非)全文\s*(\d+)\s*条|(\d+)\s*条全文|(?<!非)全文收录)")
_OFFICIAL_HOST_HINTS = (
    "gov.cn",
    "csrc.gov.cn",
    "amac.org.cn",
    "sse.com.cn",
    "szse.cn",
    "chinaclear.cn",
    "pbc.gov.cn",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _split_metadata(text: str) -> tuple[str | None, dict[str, str]]:
    title = next((line[2:].strip() for line in text.splitlines()
                  if line.startswith("# ") and line[2:].strip()), None)
    metadata: dict[str, str] = {}
    for line in text.splitlines()[:40]:
        match = _METADATA_RE.match(line.strip())
        if match:
            metadata[match.group("key").strip()] = match.group("value").strip()
    return title, metadata


def _date_declarations(metadata: dict[str, str]) -> list[dict[str, str]]:
    dates: list[dict[str, str]] = []
    for key, value in metadata.items():
        if "日期" not in key and "时间" not in key:
            continue
        matches = re.finditer(r"((?:19|20)\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?", value)
        for match in matches:
            try:
                parsed = date(*map(int, match.groups()))
            except ValueError:
                continue
            dates.append({"field": key, "declared": match.group(), "iso": parsed.isoformat(),
                          "context": value})
    return dates


def _source_candidates(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, str]] = []
    for position, line in enumerate(text.splitlines(), 1):
        metadata = _METADATA_RE.match(line)
        key = metadata.group("key") if metadata else None
        for url in re.findall(r"https?://[^\s)）>]+", line):
            url = url.rstrip("，。；;")
            host = (urlparse(url).hostname or "").lower()
            candidates.append({
                "field": key,
                "line": position,
                "context": line,
                "url": url,
                "host": host,
                "official_host_hint": any(host == hint or host.endswith("." + hint)
                                          for hint in _OFFICIAL_HOST_HINTS),
                "verification_status": "not_checked",
            })
    return candidates


def _number(value: str) -> int:
    if value.isascii() and value.isdigit():
        return int(value)
    digits = dict(zip("零〇一二三四五六七八九", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9)))
    total = 0
    current = 0
    for character in value:
        if character in digits:
            current = digits[character]
        elif character in {"十", "百", "千"}:
            total += (current or 1) * {"十": 10, "百": 100, "千": 1000}[character]
            current = 0
        else:
            return 0
    return total + current


def inspect_markdown(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """Return a deterministic, non-authoritative audit record for one Markdown file."""
    path = path.resolve()
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    title, metadata = _split_metadata(text)
    source_candidates = _source_candidates(text)
    dates = _date_declarations(metadata)
    lines = text.splitlines()
    incomplete = [{"line": position, "marker": marker, "text": line}
                  for position, line in enumerate(lines, 1)
                  for marker in _INCOMPLETE_MARKERS if marker in line]
    complete = [{"line": position, "text": line, "article_count": int(match.group(1)
                 or match.group(2)) if match.group(1) or match.group(2) else None}
                for position, line in enumerate(lines, 1)
                if not any(marker in line for marker in _INCOMPLETE_MARKERS)
                for match in _COMPLETE_RE.finditer(line)]
    articles = [{"line": position, "number": _number(match.group(1))}
                for position, line in enumerate(lines, 1)
                if not _RANGE_START_RE.search(line)
                if (match := _ARTICLE_RE.match(line))]
    numbers = sorted({item["number"] for item in articles if item["number"] > 0})
    ranges = [{"line": position, "text": line} for position, line in enumerate(lines, 1)
              if _RANGE_START_RE.search(line)]
    expected = max((item["article_count"] or 0 for item in complete), default=0)
    upper_bound = max(expected, max(numbers, default=0))
    missing = [number for number in range(1, min(upper_bound, 10000) + 1)
               if number not in numbers]
    commentary = [{"line": position, "text": line} for position, line in enumerate(lines, 1)
                  if line.startswith("#") and ("本体设计" in line or "核心变化摘要" in line)]
    suspicious = bool(ranges or missing or commentary) or not numbers
    if incomplete or ranges or missing:
        completeness = "incomplete"
    elif complete and not suspicious:
        completeness = "explicit_full"
    elif complete or numbers:
        completeness = "uncertain"
    else:
        completeness = "unclassified"
    if completeness == "explicit_full":
        recommendation = "candidate_authoritative_original"
    else:
        recommendation = "research_note"
    relative = str(path.relative_to(root.resolve())) if root else str(path)
    return {
        "path": relative,
        "absolute_path": str(path),
        "sha256": _sha256(raw),
        "bytes": len(raw),
        "title": title,
        "metadata": metadata,
        "source_candidates": source_candidates,
        "source_status": "declared" if source_candidates else "missing",
        "source_verification_status": "not_checked",
        "date_declarations": dates,
        "date_statements": [{"field": key, "text": value} for key, value in metadata.items()
                            if any(marker in key for marker in ("日期", "时间", "修订", "通过", "版本"))],
        "article_marker_count": len(articles),
        "article_numbers": numbers,
        "missing_article_numbers": missing,
        "declared_article_count": expected or None,
        "article_range_marker_count": len(ranges),
        "completeness": completeness,
        "content_observation": "commentary_present" if commentary else "no_commentary_heading_detected",
        "completeness_evidence": {
            "explicit_full_markers": complete,
            "incomplete_markers": incomplete,
            "suspicious_range_markers": ranges[:10],
            "commentary_sections": commentary,
        },
        "authority_recommendation": recommendation,
        "status_recommendation": "unverified",
        "authority_basis": "Local hash/URLs do not verify legal authority or full-text fidelity.",
    }


def inventory_markdown(root: Path | str) -> dict[str, Any]:
    """Inventory all local Markdown files under ``root`` in stable path order."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Markdown root is not a directory: {root}")
    records = [
        inspect_markdown(path, root=root)
        for path in sorted(root.rglob("*.md"), key=lambda item: item.as_posix())
    ]
    return {
        "schema_version": 1,
        "root": str(root),
        "file_count": len(records),
        "records": records,
    }


def load_selection(path: Path | str) -> list[dict[str, Any]]:
    """Load an external JSON selection manifest without changing its decisions."""
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate selection JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite selection JSON number: {value}")

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"Non-finite selection JSON number: {value}")
        return parsed

    payload = json.loads(
        Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
        parse_constant=reject_constant, parse_float=finite_float,
    )
    if isinstance(payload, dict) and set(payload) != {"documents"}:
        raise ValueError("Selection envelope requires only the documents field")
    selections = payload.get("documents") if isinstance(payload, dict) else payload
    if not isinstance(selections, list) or not selections:
        raise ValueError("Selection manifest must contain a non-empty documents list")
    if any(not isinstance(item, dict) for item in selections):
        raise ValueError("Selection entries must be JSON objects")
    return selections


def build_repository_records(root: Path | str, selections: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build CorpusRepository JSONL records from explicitly selected files."""
    root = Path(root).resolve()
    records = []
    selected_paths: set[Path] = set()
    document_ids: set[str] = set()
    for selection in selections:
        allowed = {
            "path", "sha256", "doc_id", "source_uri", "source_verification", "authority",
            "status", "title", "doc_type", "publisher", "fund_code", "period", "issued_date",
            "effective_from", "withdrawn_date", "supersedes", "selection_basis", "license",
            "chunker_config", "entity_links",
        }
        if set(selection) - allowed:
            raise ValueError(f"Unknown selection fields: {', '.join(sorted(set(selection) - allowed))}")
        relative = selection.get("path")
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError("Selection path must be a non-empty string")
        selected_path = (root / relative).resolve()
        if not selected_path.is_relative_to(root) or selected_path.suffix.lower() != ".md":
            raise ValueError("Selection paths must be Markdown files inside root")
        if selected_path in selected_paths:
            raise ValueError(f"Duplicate selection path: {relative}")
        selected_paths.add(selected_path)
        inspected = inspect_markdown(selected_path, root=root)
        checksum = selection.get("sha256")
        if checksum != inspected["sha256"]:
            raise ValueError(f"Selection sha256 mismatch or missing: {relative}")
        authority = selection.get("authority")
        status = selection.get("status")
        if authority not in {"authoritative_original", "research_note"}:
            raise ValueError("Selection authority must be authoritative_original or research_note")
        if status not in {"verified", "unverified", "quarantined"}:
            raise ValueError("Selection status must be verified, unverified, or quarantined")
        source_verification = selection.get("source_verification")
        if not isinstance(source_verification, dict):
            raise ValueError("Selection must declare a source_verification object")
        verification_status = source_verification.get("status")
        if verification_status not in {"verified", "not_checked", "failed"}:
            raise ValueError("source_verification status must be verified, not_checked, or failed")
        if status == "verified" and (verification_status != "verified"
                                     or not source_verification.get("basis")
                                     or not source_verification.get("reviewed_by")):
            raise ValueError("verified selections require upstream source basis and reviewer")
        if authority == "authoritative_original" and inspected["completeness"] != "explicit_full":
            raise ValueError("authoritative_original requires explicit full text without detected gaps")
        metadata = inspected["metadata"]
        source_uri = selection.get("source_uri")
        if not source_uri:
            raise ValueError(f"Selection has no source_uri: {relative}")
        if not isinstance(source_uri, str) or not source_uri.strip():
            raise ValueError("Selection source_uri must be a non-empty string")
        title = selection.get("title") or inspected["title"]
        if not title:
            raise ValueError(f"Selection has no title: {relative}")
        doc_id = selection.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ValueError("Selection requires a stable doc_id")
        if doc_id in document_ids:
            raise ValueError(f"Duplicate selected doc_id: {doc_id}")
        document_ids.add(doc_id)
        for field in ("issued_date", "effective_from", "withdrawn_date"):
            value = selection.get(field)
            if value is not None:
                try:
                    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                        raise ValueError
                except ValueError as error:
                    raise ValueError(f"{field} must be YYYY-MM-DD or null") from error
        effective = selection.get("effective_from")
        withdrawn = selection.get("withdrawn_date")
        if effective and withdrawn and withdrawn <= effective:
            raise ValueError("withdrawn_date must be after effective_from")
        records.append({
            "doc_id": doc_id,
            "title": title,
            "doc_type": selection.get("doc_type") or "legal_markdown",
            "publisher": selection.get("publisher") or metadata.get("发布机关"),
            "fund_code": selection.get("fund_code"),
            "period": selection.get("period"),
            "source_uri": source_uri,
            "path": str(selected_path),
            "sha256": inspected["sha256"],
            "issued_date": selection.get("issued_date"),
            "effective_from": selection.get("effective_from"),
            "withdrawn_date": selection.get("withdrawn_date"),
            "supersedes": selection.get("supersedes"),
            "authority": authority,
            "status": status,
            "provenance": {
                "inventory_schema": 1,
                "inventory_completeness": inspected["completeness"],
                "source_status": inspected["source_status"],
                "source_verification": source_verification,
                "selection_basis": selection.get("selection_basis", "human-selected"),
                "source_candidates": inspected["source_candidates"],
                "date_declarations": inspected["date_declarations"],
                "date_statements": inspected["date_statements"],
                "inventory_evidence": inspected["completeness_evidence"],
            },
            "locator": {
                "kind": "markdown",
                "path": relative,
                "title": title,
                "text_basis": "utf8-markdown-v1",
            },
            "license": selection.get("license"),
            "chunker_config": selection.get("chunker_config", {"max_chars": 800, "overlap": 0}),
            "entity_links": selection.get("entity_links", []),
        })
    return records
