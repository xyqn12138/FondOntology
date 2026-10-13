"""Fail-closed offline import selection from the authoritative data catalog."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .data_text import CHUNKER_VERSION, article_body_start_line, catalog_body_sections


_STATUSES = {"ready", "unresolved", "downloaded", "converted_unverified"}
_ORIGINS = {"issuer_original", "official_republication", "secondary"}
_FIELDS = {
    "id", "legacy_path", "title", "publisher", "seed_urls", "source_page_url", "download_url",
    "format", "issued_date", "effective_from", "expected_articles", "origin_kind",
    "raw_path", "raw_sha256", "markdown_path", "markdown_sha256", "status", "verification",
    "failure_reason",
}


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"Duplicate catalog JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Invalid catalog JSON number: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"Invalid catalog JSON number: {value}")
    return parsed


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Catalog {field} requires nonempty text")
    return value


def _path(root: Path, value: object, field: str) -> Path:
    relative = Path(_text(value, field))
    if relative.is_absolute() or relative.drive or ".." in relative.parts or ":" in str(relative):
        raise ValueError(f"Catalog {field} must be relative to data without traversal")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Catalog {field} escapes data")
    return target


def _source_url(value: object, field: str) -> str:
    value = _text(value, field)
    parsed = urlsplit(value)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname
            or parsed.username or parsed.password
            or any(character.isspace() or ord(character) < 32 for character in value)):
        raise ValueError(f"Catalog {field} requires a public source URL without credentials")
    return value


def _url_component(value: str) -> str:
    def normalize(match: re.Match) -> str:
        encoded = bytes.fromhex(match.group().replace("%", ""))
        parts = []
        position = 0
        while position < len(encoded):
            byte = encoded[position]
            if byte < 128:
                character = chr(byte)
                parts.append(character if character.isalnum() or character in "-._~"
                             else f"%{byte:02X}")
                position += 1
            else:
                end = position + 1
                while end < len(encoded) and encoded[end] >= 128:
                    end += 1
                fragment = encoded[position:end]
                try:
                    parts.append(fragment.decode("utf-8", errors="strict"))
                except UnicodeDecodeError:
                    parts.append("".join(f"%{item:02X}" for item in fragment))
                position = end
        return "".join(parts)

    return re.sub(r"(?:%[0-9A-Fa-f]{2})+", normalize, value)


def _url_key(value: object) -> tuple[str, ...]:
    parsed = urlsplit(_source_url(value, "acquisition URL"))
    return (parsed.scheme.lower(), parsed.netloc.lower(), _url_component(parsed.path),
            _url_component(parsed.query), _url_component(parsed.fragment))


def _url_equivalent(first: object, second: object) -> bool:
    return _url_key(first) == _url_key(second)


def _receipt_url(receipt: dict) -> object:
    values = [receipt[field] for field in ("requested_url", "actual_url") if field in receipt]
    if not values or any(not _url_equivalent(value, values[0]) for value in values):
        raise ValueError("Acquisition receipt requires consistent requested_url/actual_url")
    _url_key(values[0])
    return values[0]


def _verify_file(root: Path, document: dict, field: str) -> Path | None:
    value = document.get(field + "_path")
    checksum = document.get(field + "_sha256")
    if value is None:
        if checksum is not None:
            raise ValueError(f"{field}_sha256 has no matching path")
        return None
    target = _path(root, value, field + "_path")
    if (not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum)
            or hashlib.sha256(target.read_bytes()).hexdigest() != checksum):
        raise ValueError(f"Catalog {field} sha256 mismatch or missing: {document['id']}")
    if field == "markdown" and target.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Catalog markdown_path must be Markdown")
    return target


def _verified_json(root: Path, reference: object, path_field: str, hash_field: str) -> dict:
    if not isinstance(reference, dict) or set(reference) != {path_field, hash_field}:
        raise ValueError(f"Verification reference requires only {path_field} and {hash_field}")
    path = _path(root, reference[path_field], path_field)
    raw = path.read_bytes()
    checksum = reference[hash_field]
    if (not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum)
            or hashlib.sha256(raw).hexdigest() != checksum):
        raise ValueError(f"Verification {hash_field} mismatch or malformed")
    payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_constant=_reject_constant, parse_float=_finite_float)
    if not isinstance(payload, dict):
        raise ValueError("Verification record must be a JSON object")
    return payload


def _receipt_value(receipt: dict, fields: tuple[str, ...]) -> object:
    values = [receipt[field] for field in fields if field in receipt]
    if not values or any(value != values[0] or type(value) is not type(values[0])
                         for value in values):
        raise ValueError(f"Acquisition receipt requires consistent {'/'.join(fields)}")
    return values[0]


def _verify_ready_records(root: Path, document: dict, raw_path: Path,
                          verification: dict) -> None:
    receipt = _verified_json(root, verification.get("acquisition"),
                             "receipt_path", "receipt_sha256")
    download_url = _source_url(document.get("download_url"), "download_url")
    requested = _receipt_url(receipt)
    final = receipt.get("final_url")
    raw_sha = _receipt_value(receipt, ("raw_sha256", "sha256"))
    byte_count = _receipt_value(receipt, ("bytes", "byte_count"))
    status = _receipt_value(receipt, ("status_code", "http_status"))
    if (not _url_equivalent(requested, download_url) or not _url_equivalent(final, download_url)
            or raw_sha != document["raw_sha256"]
            or type(byte_count) is not int or byte_count != raw_path.stat().st_size
            or type(status) is not int or status != 200):
        raise ValueError(f"Acquisition receipt does not bind the catalog source: {document['id']}")
    conversion = _verified_json(root, verification.get("conversion"),
                                "record_path", "record_sha256")
    required = {"schema_version", "raw_path", "source_sha256", "markdown_path",
                "markdown_sha256", "method", "version", "observations", "identity_review"}
    if (set(conversion) != required or type(conversion.get("schema_version")) is not int
            or conversion["schema_version"] != 1
            or conversion["raw_path"] != document["raw_path"]
            or conversion["source_sha256"] != document["raw_sha256"]
            or conversion["markdown_path"] != document["markdown_path"]
            or conversion["markdown_sha256"] != document["markdown_sha256"]):
        raise ValueError(f"Conversion record does not bind source and Markdown: {document['id']}")
    _text(conversion["method"], "conversion.method")
    _text(conversion["version"], "conversion.version")
    review = conversion["identity_review"]
    if (not isinstance(review, dict) or set(review) != {"scope", "human_reviewed"}
            or review["scope"] != "machine_conversion_and_structure_only"
            or review["human_reviewed"] is not False):
        raise ValueError("Conversion identity_review must explicitly limit machine review scope")
    observations = conversion["observations"]
    original_format = _text(document.get("format"), "format")
    required_observations = {"original_format", "page_count", "page_coverage", "article_count",
                             "missing_images", "unsupported"}
    if (not isinstance(observations, dict) or not required_observations.issubset(observations)
            or observations["original_format"] != original_format
            or observations["article_count"] != verification.get("article_count")
            or type(observations["article_count"]) is not type(verification.get("article_count"))
            or observations["missing_images"] != [] or observations["unsupported"] != []):
        raise ValueError("Ready conversion observations are missing or identify omitted content")
    page_count = verification.get("page_count")
    if page_count is not None and (type(page_count) is not int or not 1 <= page_count <= 10000):
        raise ValueError("verification.page_count must be a positive bounded count or null")
    coverage = list(range(1, page_count + 1)) if page_count is not None else []
    if (type(observations["page_count"]) is not type(page_count)
            or observations["page_count"] != page_count or observations["page_coverage"] != coverage
            or any(type(page) is not int for page in observations["page_coverage"])):
        raise ValueError("Ready conversion must record complete page coverage")
    if str(document.get("format", "")).lower() == "pdf" and page_count is None:
        raise ValueError("Ready PDF conversion requires explicit page count and coverage")


def verify_source_freeze(root: Path, catalog_raw: bytes) -> dict | None:
    lock_path = root / "rag_source_lock.json"
    if not lock_path.is_file():
        return None
    lock = json.loads(lock_path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    if (lock.get("schema_version") != 1 or lock.get("catalog_path") != "source_catalog.json"
            or lock.get("catalog_sha256") != hashlib.sha256(catalog_raw).hexdigest()):
        raise ValueError("Frozen RAG source catalog hash mismatch; publish a new source version")
    documents = json.loads(catalog_raw.decode("utf-8"))["documents"]
    ready_ids = [document["id"] for document in documents if document["status"] == "ready"]
    if (lock.get("document_ids") != ready_ids or lock.get("document_count") != len(ready_ids)):
        raise ValueError("Frozen RAG source membership mismatch")
    for relative, digest in lock.get("image_sha256", {}).items():
        if hashlib.sha256(_path(root, relative, "frozen image").read_bytes()).hexdigest() != digest:
            raise ValueError(f"Frozen RAG source image hash mismatch: {relative}")
    return lock


def build_catalog_records(catalog_path: Path | str, *, data_root: Path | str = "data",
                          document_ids: list[str] | None = None) -> dict:
    """Validate all catalog references; select only explicitly ready full texts."""
    root = Path(data_root).resolve()
    catalog = Path(catalog_path).resolve()
    if not root.is_dir() or not catalog.is_relative_to(root):
        raise ValueError("Catalog must be a file inside the data root")
    raw_catalog = catalog.read_bytes()
    if catalog == root / "source_catalog.json":
        verify_source_freeze(root, raw_catalog)
    payload = json.loads(raw_catalog.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_constant=_reject_constant, parse_float=_finite_float)
    if (not isinstance(payload, dict) or set(payload) != {"schema_version", "documents"}
            or type(payload["schema_version"]) is not int or payload["schema_version"] != 1
            or not isinstance(payload["documents"], list)):
        raise ValueError("Catalog requires schema_version=1 and a documents list")
    records = []
    skipped = []
    seen = set()
    if document_ids is not None and (not isinstance(document_ids, list)
                                     or any(not isinstance(item, str) or not item.strip()
                                            for item in document_ids)):
        raise ValueError("Document selection must be a list of nonempty IDs")
    requested = set(document_ids) if document_ids is not None else None
    if requested is not None and (not requested or len(requested) != len(document_ids)):
        raise ValueError("Document selection must contain unique IDs")
    catalog_sha = hashlib.sha256(raw_catalog).hexdigest()
    for document in payload["documents"]:
        if not isinstance(document, dict) or set(document) - _FIELDS:
            raise ValueError("Unknown catalog document fields")
        document_id = _text(document.get("id"), "id")
        if document_id in seen:
            raise ValueError(f"Duplicate catalog document ID: {document_id}")
        seen.add(document_id)
        unresolved_origin = document.get("status") == "unresolved" and document.get("origin_kind") is None
        if (document.get("status") not in _STATUSES
                or document.get("origin_kind") not in _ORIGINS and not unresolved_origin):
            raise ValueError(f"Invalid catalog status or origin_kind: {document_id}")
        if document.get("legacy_path") is not None:
            _path(root, document["legacy_path"], "legacy_path")
        raw_path = _verify_file(root, document, "raw")
        markdown_path = _verify_file(root, document, "markdown")
        for field in ("issued_date", "effective_from"):
            value = document.get(field)
            if value is not None and (not isinstance(value, str)
                                      or date.fromisoformat(value).isoformat() != value):
                raise ValueError(f"Catalog {field} must be YYYY-MM-DD or null")
        selected = requested is None or document_id in requested
        if document["status"] != "ready":
            if requested is not None and selected:
                raise ValueError(f"Selected catalog document is not ready: {document_id}")
            if selected:
                skipped.append({"id": document_id, "status": document["status"],
                                "failure_reason": document.get("failure_reason")})
            continue
        verification = document.get("verification")
        evidence = verification.get("evidence") if isinstance(verification, dict) else None
        has_evidence = (isinstance(evidence, str) and bool(evidence.strip())
                        or isinstance(evidence, list) and bool(evidence)
                        and all(isinstance(item, (str, dict)) and bool(item) for item in evidence))
        if (document["origin_kind"] == "secondary" or raw_path is None or markdown_path is None
                or not isinstance(verification, dict)
                or verification.get("identity") != "verified"
                or verification.get("completeness") != "complete"
                or not has_evidence or not document.get("issued_date")):
            raise ValueError(f"Ready catalog entry lacks verified official complete text: {document_id}")
        _verify_ready_records(root, document, raw_path, verification)
        title = _text(document.get("title"), "title")
        publisher = _text(document.get("publisher"), "publisher")
        source_uri = _source_url(document.get("source_page_url"), "source_page_url")
        if document.get("download_url") is not None:
            _source_url(document["download_url"], "download_url")
        expected = document.get("expected_articles")
        if expected is not None and (type(expected) is not int or not 1 <= expected <= 10000):
            raise ValueError("expected_articles must be a positive bounded count or null")
        article_count = verification.get("article_count")
        if expected is not None and (type(article_count) is not int or article_count != expected):
            raise ValueError(f"Catalog article count differs from expected count: {document_id}")
        text = markdown_path.read_bytes().decode("utf-8", errors="strict")
        start = verification.get("body_start_line")
        if start is None and expected is not None:
            start = article_body_start_line(text)
        if type(start) is int and 1 <= start <= len(text.splitlines()):
            first_body_line = text.splitlines()[start - 1].strip()
            if (re.sub(r"^#{1,6}\s+", "", first_body_line) == title
                    or re.match(r"^\*\*(?:Source|来源|原始来源|源文件|发布日期|发布机关|发布机构)\*\*",
                                first_body_line, flags=re.IGNORECASE)):
                raise ValueError(f"Catalog body_start_line points to a source/title header: {document_id}")
        config = {"strategy": CHUNKER_VERSION, "body_start_line": start,
                  "expected_articles": expected, "max_chars": 800, "overlap": 0}
        sections = catalog_body_sections(text, config)
        if expected is not None and sum("article_number" in section for section in sections) != expected:
            raise ValueError(f"Catalog legal article completeness mismatch: {document_id}")
        if not selected:
            continue
        records.append({
            "doc_id": document_id, "title": title, "publisher": publisher,
            "doc_type": "data_legal_markdown" if expected is not None else "data_technical_markdown",
            "source_uri": source_uri, "path": str(markdown_path),
            "sha256": document["markdown_sha256"], "issued_date": document["issued_date"],
            "effective_from": document.get("effective_from"),
            "authority": "authoritative_original", "status": "verified",
            "provenance": {
                "catalog_schema": 1, "catalog_sha256": catalog_sha,
                "origin_kind": document["origin_kind"],
                "raw_path": document["raw_path"], "raw_sha256": document["raw_sha256"],
                "download_url": document.get("download_url"),
                "source_verification": verification,
                "legal_validity": "not_checked_current",
            },
            "locator": {"kind": "data_catalog_markdown", "path": document["markdown_path"],
                        "raw_path": document["raw_path"], "raw_sha256": document["raw_sha256"],
                        "title": title, "text_basis": "utf8-markdown-v1"},
            "chunker_config": config,
        })
    if requested is not None and requested - seen:
        raise ValueError(f"Unknown catalog document IDs: {', '.join(sorted(requested - seen))}")
    return {"catalog_sha256": catalog_sha, "records": records, "skipped": skipped}


def artifact_output(path: Path | str, *, artifacts_root: Path | str = "artifacts",
                    data_root: Path | str = "data") -> Path:
    target = Path(path).resolve()
    if (not target.is_relative_to(Path(artifacts_root).resolve())
            or target.is_relative_to(Path(data_root).resolve())):
        raise ValueError("Derived databases and manifests must be inside artifacts and outside data")
    return target
