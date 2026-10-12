"""Pinned official-source acquisition, separate from offline corpus storage."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlsplit

from .legal_text import extract_official_html, legal_article_sections, validate_html_reference


OFFICIAL_HOSTS = {"www.csrc.gov.cn", "www.gov.cn"}
MAX_BYTES = 5_000_000


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON number: {value}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=_reject_constant)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_registry(path: Path) -> list[dict]:
    payload = _read_json(path)
    if (not isinstance(payload, dict) or set(payload) != {"schema_version", "sources"}
            or payload["schema_version"] != "1.0"
            or not isinstance(payload["sources"], list) or not payload["sources"]):
        raise ValueError("Registry requires schema_version=1.0 and nonempty sources")
    seen = set()
    required = {"doc_id", "title", "publisher", "url", "raw_sha256", "extraction",
                "expected_articles", "issued_date", "effective_from", "date_basis",
                "required_text", "validity_status"}
    for source in payload["sources"]:
        if not isinstance(source, dict) or set(source) != required:
            raise ValueError("Unknown or missing source registry fields")
        for key in ("doc_id", "title", "publisher", "url", "date_basis"):
            if not isinstance(source[key], str) or not source[key].strip():
                raise ValueError(f"Source {key} must be nonempty text")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,100}", source["doc_id"]):
            raise ValueError("Unsafe source doc_id")
        if source["doc_id"] in seen:
            raise ValueError("Duplicate source doc_id")
        seen.add(source["doc_id"])
        parsed = urlsplit(source["url"])
        if (parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS
                or parsed.username or parsed.password or parsed.port or parsed.fragment
                or parsed.query):
            raise ValueError("Source must use a pinned HTTPS official-host URL without credentials")
        if not isinstance(source["raw_sha256"], str) or not re.fullmatch(
                r"[a-f0-9]{64}", source["raw_sha256"]):
            raise ValueError("Source raw_sha256 must be a pinned lowercase hash")
        if type(source["expected_articles"]) is not int or not 1 <= source["expected_articles"] <= 10000:
            raise ValueError("Invalid expected_articles")
        validate_html_reference(source["extraction"])
        for key in ("issued_date", "effective_from"):
            value = source[key]
            if value is not None and (not isinstance(value, str)
                                      or date.fromisoformat(value).isoformat() != value):
                raise ValueError(f"Invalid {key}")
        if source["issued_date"] is None:
            raise ValueError("An official source version requires an explicit issue date")
        if source["validity_status"] != "not_checked_current":
            raise ValueError("Acquisition must not imply current legal validity")
        if (not isinstance(source["required_text"], list) or not source["required_text"]
                or any(not isinstance(item, str) or not item.strip()
                       for item in source["required_text"])):
            raise ValueError("required_text must contain explicit source identity/date anchors")
    return payload["sources"]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        raise ValueError("Official-source redirect refused; review and repin the final URL")


def download_source(source: dict) -> tuple[bytes, dict]:
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(source["url"], headers={
        "User-Agent": "Mozilla/5.0 FondOntology-SourceAudit/1.0",
        "Accept": "text/html", "Accept-Encoding": "identity",
    })
    with opener.open(request, timeout=30) as response:
        if response.status != 200 or response.url != source["url"]:
            raise ValueError("Official source must return HTTP 200 at the pinned URL")
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("Official source is not HTML")
        raw = response.read(MAX_BYTES + 1)
        if not raw or len(raw) > MAX_BYTES:
            raise ValueError("Official source exceeds the byte budget or is empty")
        receipt = {
            "schema_version": "1.0", "doc_id": source["doc_id"],
            "requested_url": source["url"], "final_url": response.url,
            "status_code": response.status, "content_type": content_type,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "raw_sha256": _sha(raw), "byte_count": len(raw),
            "tls_policy": "default_certificate_verification", "redirects_allowed": False,
        }
    if _sha(raw) != source["raw_sha256"]:
        raise ValueError("Official HTML changed from pinned bytes; review before replacing the source")
    return raw, receipt


def verify_source(source: dict, raw: bytes, receipt: dict) -> dict:
    if _sha(raw) != source["raw_sha256"]:
        raise ValueError("Official source hash mismatch")
    if (receipt.get("doc_id") != source["doc_id"]
            or receipt.get("raw_sha256") != _sha(raw)
            or receipt.get("byte_count") != len(raw)
            or receipt.get("requested_url") != source["url"]
            or receipt.get("final_url") != source["url"]
            or receipt.get("status_code") != 200
            or receipt.get("content_type") not in {"text/html", "application/xhtml+xml"}
            or receipt.get("redirects_allowed") is not False
            or receipt.get("tls_policy") != "default_certificate_verification"):
        raise ValueError("Acquisition receipt is inconsistent with the pinned source")
    acquired = datetime.fromisoformat(receipt.get("fetched_at", ""))
    if acquired.tzinfo is None:
        raise ValueError("Acquisition timestamp requires a timezone")
    extracted = extract_official_html(raw, source["extraction"])
    normalized = _compact(extracted["text"])
    if any(_compact(anchor) not in normalized for anchor in [source["title"], *source["required_text"]]):
        raise ValueError("Official body is missing a pinned title/date/identity anchor")
    sections = legal_article_sections(extracted["text"], expected_articles=source["expected_articles"])
    return {**extracted, "article_count": len(sections)}


def prepare_sources(registry_path: Path, output_dir: Path, *, download: bool = False) -> dict:
    sources = load_registry(registry_path)
    output_dir = output_dir.resolve()
    if registry_path.resolve().is_relative_to(output_dir):
        raise ValueError("Output directory must not contain the source registry")
    if download:
        output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    report = []
    registry_sha = _sha(registry_path.read_bytes())
    for source in sources:
        raw_path = output_dir / f"{source['doc_id']}.html"
        receipt_path = output_dir / f"{source['doc_id']}.receipt.json"
        for path in (raw_path, receipt_path):
            if path.resolve().parent != output_dir:
                raise ValueError("Source output path escapes its directory")
        if raw_path.exists() or receipt_path.exists():
            if not raw_path.is_file() or not receipt_path.is_file():
                raise ValueError("Incomplete cached source/receipt pair; inspect before continuing")
            raw, receipt = raw_path.read_bytes(), _read_json(receipt_path)
        elif download:
            raw, receipt = download_source(source)
            with raw_path.open("xb") as stream:
                stream.write(raw)
            with receipt_path.open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        else:
            raise ValueError("Missing cached source; --download is required for network acquisition")
        extracted = verify_source(source, raw, receipt)
        report.append({"doc_id": source["doc_id"], "raw_sha256": _sha(raw),
                       "normalized_text_sha256": extracted["normalized_text_sha256"],
                       "article_count": extracted["article_count"], "chars": len(extracted["text"]),
                       "origin_check": "pinned_official_response",
                       "legal_validity": source["validity_status"]})
        records.append({
            "doc_id": source["doc_id"], "title": source["title"], "doc_type": "official_legal_html",
            "publisher": source["publisher"], "source_uri": source["url"],
            "path": str(raw_path), "sha256": _sha(raw),
            "issued_date": source["issued_date"], "effective_from": source["effective_from"],
            "authority": "authoritative_original", "status": "verified",
            "extraction": source["extraction"],
            "chunker_config": {"strategy": "legal-article-v1", "max_chars": 800,
                               "overlap": 0, "expected_articles": source["expected_articles"]},
            "provenance": {
                "source_verification": {"status": "verified", "scope": "official_origin_and_pinned_bytes",
                                        "basis": "curated HTTPS URL, byte hash, unique body, title/date anchors and article sequence",
                                        "reviewed_by": "source-acquisition-review-20261012",
                                        "legal_validity": source["validity_status"]},
                "acquisition": receipt, "acquisition_receipt_sha256": _sha(receipt_path.read_bytes()),
                "registry_sha256": registry_sha, "date_basis": source["date_basis"],
                "normalized_text_sha256": extracted["normalized_text_sha256"],
                "extraction_review": "deterministic_structure_checks_not_full_human_legal_review",
            },
            "locator": {"kind": "official_html", "title": source["title"],
                        "source_uri": source["url"], "text_basis": "official-html-v1-normalized"},
        })
    return {"records": records, "report": report, "registry_sha256": registry_sha}
