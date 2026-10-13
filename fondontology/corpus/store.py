"""Offline document ingestion and immutable SQLite corpus snapshots."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

from .pdf_extraction import EXTRACTOR_VERSION as PDF_EXTRACTOR_VERSION
from .pdf_extraction import load_extraction_json, parse_extraction, pdf_page_count
from .data_text import CHUNKER_VERSION as DATA_CHUNKER_VERSION
from .data_text import catalog_body_sections
from .legal_text import (
    CHUNKER_VERSION as LEGAL_CHUNKER_VERSION,
    EXTRACTOR_VERSION as LEGAL_EXTRACTOR_VERSION,
    TEXT_BASIS as LEGAL_TEXT_BASIS,
    extract_official_html,
    legal_article_sections,
)


class CorpusError(ValueError):
    """An invalid input or an unavailable corpus snapshot."""


SCHEMA_VERSION = 2
EXTRACTOR_VERSION = "utf8-markdown-v1"
CHUNKER_VERSION = "char-window-v1"
_AUTHORITIES = {"authoritative_original", "research_note", "synthetic"}
_STATUSES = {"verified", "unverified", "quarantined"}
_EXTRACTION_SCHEMA = """
CREATE TABLE document_extractions (
    version_id TEXT PRIMARY KEY REFERENCES document_versions(version_id),
    artifact_sha256 TEXT NOT NULL,
    artifact_bytes BLOB NOT NULL,
    artifact_path TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    text_basis TEXT NOT NULL,
    normalized_text TEXT NOT NULL
);
CREATE TRIGGER immutable_document_extractions_update
BEFORE UPDATE ON document_extractions BEGIN
SELECT RAISE(ABORT, 'immutable corpus record'); END;
CREATE TRIGGER immutable_document_extractions_delete
BEFORE DELETE ON document_extractions BEGIN
SELECT RAISE(ABORT, 'immutable corpus record'); END;
"""
_SCHEMA = """
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY
);
CREATE TABLE ingestion_runs (
    run_id TEXT PRIMARY KEY,
    manifest_path TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('completed', 'failed')),
    inserted_count INTEGER NOT NULL,
    reused_count INTEGER NOT NULL,
    error TEXT
);
CREATE TABLE document_versions (
    version_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    publisher TEXT,
    fund_code TEXT,
    period TEXT,
    source_uri TEXT NOT NULL,
    source_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    original_bytes BLOB NOT NULL,
    issued_date TEXT,
    effective_from TEXT,
    withdrawn_date TEXT,
    acquired_at TEXT NOT NULL,
    supersedes TEXT REFERENCES document_versions(version_id),
    authority TEXT NOT NULL,
    status TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    locator_json TEXT NOT NULL,
    license TEXT,
    extractor_version TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    chunker_config_json TEXT NOT NULL,
    identity_json TEXT NOT NULL,
    ingestion_run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id)
);
CREATE TABLE sections (
    section_id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL REFERENCES document_versions(version_id),
    ordinal INTEGER NOT NULL,
    heading TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    text TEXT NOT NULL,
    locator_json TEXT NOT NULL,
    extraction_quality TEXT NOT NULL,
    UNIQUE(version_id, ordinal)
);
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL REFERENCES document_versions(version_id),
    section_id TEXT NOT NULL REFERENCES sections(section_id),
    ordinal INTEGER NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    text TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    locator_json TEXT NOT NULL,
    UNIQUE(section_id, ordinal)
);
CREATE TABLE entity_links (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
    entity_id TEXT NOT NULL,
    method TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    review_status TEXT NOT NULL,
    PRIMARY KEY(chunk_id, entity_id)
);
CREATE TABLE corpus_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('trusted', 'research', 'regression')),
    index_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    members_sha256 TEXT NOT NULL
);
CREATE TABLE snapshot_members (
    snapshot_id TEXT NOT NULL REFERENCES corpus_snapshots(snapshot_id),
    version_id TEXT NOT NULL REFERENCES document_versions(version_id),
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    PRIMARY KEY(snapshot_id, version_id),
    UNIQUE(snapshot_id, document_id)
);
CREATE INDEX chunks_version ON chunks(version_id);
CREATE INDEX sections_version ON sections(version_id);
CREATE INDEX versions_document ON document_versions(document_id);
"""


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _id(prefix: str, value: object) -> str:
    return prefix + _sha(_json(value).encode("utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CorpusError(f"{field} must be an ISO date or null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise CorpusError(f"Invalid {field}: {value}") from error
    if parsed.isoformat() != value:
        raise CorpusError(f"{field} must use YYYY-MM-DD")
    return value


def _text(record: dict, field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CorpusError(f"Missing nonempty string: {field}")
    return value


class CorpusRepository:
    """A connection-per-operation repository; constructing it runs migrations."""

    def __init__(self, db_path: Path | str, *, _allow_create: bool = True):
        self.db_path = Path(db_path).resolve()
        self._allow_create = _allow_create
        if not _allow_create and not self.db_path.is_file():
            raise CorpusError(f"Corpus database does not exist: {self.db_path}")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @classmethod
    def open_existing(cls, db_path: Path | str) -> "CorpusRepository":
        """Open a corpus without creating a missing path."""
        return cls(db_path, _allow_create=False)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = (sqlite3.connect(self.db_path, timeout=30) if self._allow_create
                      else sqlite3.connect(self.db_path.as_uri() + "?mode=rw", uri=True, timeout=30))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self._connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise CorpusError(f"Unsupported corpus schema version: {version}")
            if version == SCHEMA_VERSION:
                return
            if version == 1:
                connection.executescript(
                    "BEGIN IMMEDIATE;\n" + _EXTRACTION_SCHEMA
                    + f"\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
                )
                return
            if not self._allow_create:
                raise CorpusError("Not an initialized corpus database; run init explicitly")
            triggers = []
            for table in ("documents", "document_versions", "sections", "chunks",
                          "entity_links", "corpus_snapshots", "snapshot_members"):
                for operation in ("UPDATE", "DELETE"):
                    triggers.append(
                        f"CREATE TRIGGER immutable_{table}_{operation.lower()} "
                        f"BEFORE {operation} ON {table} BEGIN "
                        "SELECT RAISE(ABORT, 'immutable corpus record'); END;"
                    )
            connection.executescript(
                "BEGIN IMMEDIATE;\n" + _SCHEMA + _EXTRACTION_SCHEMA + "\n".join(triggers)
                + f"\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
            )

    def import_manifest(self, path: Path | str) -> dict:
        """Import every JSONL entry atomically; record a failed run after rollback."""
        manifest_path = Path(path).resolve()
        run_id = "ingest_" + uuid.uuid4().hex
        started_at = _now()
        raw_manifest = b""
        inserted = 0
        reused = 0
        version_ids = []
        extractor_versions = set()
        chunker_versions = set()
        try:
            raw_manifest = manifest_path.read_bytes()
            manifest_text = raw_manifest.decode("utf-8", errors="strict")
            with self._connection() as connection:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    self._record_run(connection, run_id, manifest_path, raw_manifest,
                                     started_at, "completed", 0, 0, None)
                    for line_number, line in enumerate(manifest_text.splitlines(), 1):
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            if not isinstance(record, dict):
                                raise CorpusError("Manifest entries must be JSON objects")
                            version_id, was_inserted = self._import_record(
                                connection, record, manifest_path.parent, run_id
                            )
                        except (ValueError, OSError, sqlite3.Error) as error:
                            raise CorpusError(f"Manifest line {line_number}: {error}") from error
                        version_ids.append(version_id)
                        extractor_versions.add(connection.execute(
                            "SELECT extractor_version FROM document_versions WHERE version_id=?",
                            (version_id,),
                        ).fetchone()["extractor_version"])
                        chunker_versions.add(connection.execute(
                            "SELECT chunker_version FROM document_versions WHERE version_id=?",
                            (version_id,),
                        ).fetchone()["chunker_version"])
                        inserted += int(was_inserted)
                        reused += int(not was_inserted)
                    if not version_ids:
                        raise CorpusError("Manifest contains no documents")
                    connection.execute(
                        "UPDATE ingestion_runs SET completed_at=?, inserted_count=?, "
                        "reused_count=?, extractor_version=?, chunker_version=? WHERE run_id=?",
                        (_now(), inserted, reused,
                         next(iter(extractor_versions)) if len(extractor_versions) == 1
                         else "mixed", next(iter(chunker_versions)) if len(chunker_versions) == 1
                         else "mixed", run_id),
                    )
        except (ValueError, OSError, sqlite3.Error) as error:
            with self._connection() as connection:
                with connection:
                    self._record_run(connection, run_id, manifest_path, raw_manifest,
                                     started_at, "failed", 0, 0, str(error))
            raise CorpusError(str(error)) from error
        return {"run_id": run_id, "version_ids": list(dict.fromkeys(version_ids)),
                "inserted": inserted, "reused": reused}

    @staticmethod
    def _record_run(connection, run_id, manifest_path, raw_manifest, started_at,
                    status, inserted, reused, error):
        connection.execute(
            "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, str(manifest_path), _sha(raw_manifest),
             "unknown" if status == "failed" else "pending",
             CHUNKER_VERSION, started_at, _now(), status, inserted, reused, error),
        )

    def _import_record(self, connection, record, base_path, run_id):
        allowed = {
            "doc_id", "title", "doc_type", "publisher", "fund_code", "period",
            "source_uri", "path", "sha256", "issued_date", "effective_from",
            "withdrawn_date", "supersedes", "authority", "status", "provenance",
            "locator", "license", "chunker_config", "entity_links",
            "extraction",
        }
        unknown = set(record) - allowed
        if unknown:
            raise CorpusError(f"Unknown manifest fields: {', '.join(sorted(unknown))}")
        document_id = _text(record, "doc_id")
        document = {
            "document_id": document_id,
            "title": _text(record, "title"),
            "doc_type": _text(record, "doc_type"),
            "publisher": record.get("publisher"),
            "fund_code": record.get("fund_code"),
            "period": record.get("period"),
        }
        for field in ("publisher", "fund_code", "period"):
            if document[field] is not None and not isinstance(document[field], str):
                raise CorpusError(f"{field} must be a string or null")
        source_uri = _text(record, "source_uri")
        source_path = (base_path / _text(record, "path")).resolve()
        is_pdf = source_path.suffix.lower() == ".pdf"
        is_html = source_path.suffix.lower() in {".html", ".htm"}
        if source_path.suffix.lower() not in {".md", ".txt", ".markdown", ".pdf", ".html", ".htm"}:
            raise CorpusError("Only local PDF, UTF-8 text/Markdown, or HTML input is supported")
        raw_source = source_path.read_bytes()
        checksum = _text(record, "sha256").lower()
        if not re.fullmatch(r"[a-f0-9]{64}", checksum) or _sha(raw_source) != checksum:
            raise CorpusError("Source sha256 mismatch or malformed sha256")
        extraction = None
        extractor_version = EXTRACTOR_VERSION
        if is_pdf:
            extraction = self._load_pdf_extraction(record.get("extraction"), base_path,
                                                   raw_source, checksum)
            text = extraction["parsed"]["text"]
            extractor_version = PDF_EXTRACTOR_VERSION
        elif is_html:
            extraction = self._load_html_extraction(record.get("extraction"), raw_source, checksum)
            text = extraction["parsed"]["text"]
            extractor_version = LEGAL_EXTRACTOR_VERSION
        else:
            if "extraction" in record:
                raise CorpusError("extraction is only supported for PDF or HTML input")
            text = raw_source.decode("utf-8", errors="strict")
            if not text.strip():
                raise CorpusError("Document text is empty")
        authority = _text(record, "authority")
        status = _text(record, "status")
        if authority not in _AUTHORITIES or status not in _STATUSES:
            raise CorpusError("Unsupported authority/status classification")
        provenance = record.get("provenance")
        locator = record.get("locator")
        if not isinstance(provenance, dict) or not provenance:
            raise CorpusError("provenance must be a nonempty object")
        if not isinstance(locator, dict) or not locator:
            raise CorpusError("locator must be a nonempty object")
        issued_date = _date(record.get("issued_date"), "issued_date")
        effective_from = _date(record.get("effective_from"), "effective_from")
        withdrawn_date = _date(record.get("withdrawn_date"), "withdrawn_date")
        if effective_from and withdrawn_date and withdrawn_date <= effective_from:
            raise CorpusError("withdrawn_date must be after effective_from")
        supersedes = record.get("supersedes")
        if supersedes is not None:
            if not isinstance(supersedes, str):
                raise CorpusError("supersedes must be a version ID or null")
            previous = connection.execute(
                "SELECT document_id FROM document_versions WHERE version_id=?", (supersedes,)
            ).fetchone()
            if previous is None or previous["document_id"] != document_id:
                raise CorpusError("supersedes must reference a version of the same document")
        config = record.get("chunker_config", {"max_chars": 800, "overlap": 0})
        is_catalog = isinstance(config, dict) and config.get("strategy") == DATA_CHUNKER_VERSION
        is_legal = isinstance(config, dict) and config.get("strategy") == LEGAL_CHUNKER_VERSION
        if is_catalog:
            if is_pdf or is_html:
                raise CorpusError("Data catalog body chunking requires UTF-8 Markdown")
            catalog_sections = catalog_body_sections(text, config)
        elif is_legal:
            if (not isinstance(config, dict)
                    or set(config) != {"strategy", "max_chars", "overlap", "expected_articles"}
                    or type(config.get("expected_articles")) is not int):
                raise CorpusError(
                    "Legal chunker_config requires strategy, max_chars, overlap, expected_articles"
                )
        elif not isinstance(config, dict) or set(config) != {"max_chars", "overlap"}:
            raise CorpusError("chunker_config requires only max_chars and overlap")
        if is_html and not is_legal:
            raise CorpusError("HTML requires explicit legal-article-v1 chunking")
        if is_pdf and is_legal:
            raise CorpusError("Legal article chunking is not supported for PDF extraction")
        max_chars, overlap = config["max_chars"], config["overlap"]
        if (type(max_chars) is not int or type(overlap) is not int
                or max_chars <= 0 or overlap < 0 or overlap >= max_chars):
            raise CorpusError("Invalid chunk sizes")
        if (is_legal or is_catalog) and overlap != 0:
            raise CorpusError("Legal article chunking requires overlap=0")
        legal_sections = (legal_article_sections(text, expected_articles=config["expected_articles"])
                          if is_legal else None)
        chunker_version = (DATA_CHUNKER_VERSION if is_catalog else
                           LEGAL_CHUNKER_VERSION if is_legal else CHUNKER_VERSION)
        links = record.get("entity_links", [])
        if not isinstance(links, list):
            raise CorpusError("entity_links must be a list")
        normalized_links = []
        for link in links:
            if not isinstance(link, dict):
                raise CorpusError("entity link must be an object")
            confidence = link.get("confidence")
            if (type(confidence) not in (int, float) or not 0 <= confidence <= 1):
                raise CorpusError("entity link confidence must be between 0 and 1")
            normalized_links.append({
                "entity_id": _text(link, "entity_id"), "method": _text(link, "method"),
                "confidence": confidence, "review_status": _text(link, "review_status"),
            })
        if len({link["entity_id"] for link in normalized_links}) != len(normalized_links):
            raise CorpusError("Duplicate entity links")
        normalized_links.sort(key=lambda link: link["entity_id"])
        identity = {
            "document": document, "source_uri": source_uri, "sha256": checksum,
            "issued_date": issued_date, "effective_from": effective_from,
            "withdrawn_date": withdrawn_date, "supersedes": supersedes,
            "authority": authority, "status": status, "provenance": provenance,
            "locator": locator, "license": record.get("license"),
            "extractor_version": extractor_version,
            "chunker_version": chunker_version,
            "chunker_config": config, "entity_links": normalized_links,
        }
        if extraction is not None:
            identity["extraction_sha256"] = extraction["sha256"]
            if is_html:
                identity["normalized_text_sha256"] = extraction["parsed"]["normalized_text_sha256"]
                identity["html_extraction"] = extraction["reference"]
        if identity["license"] is not None and not isinstance(identity["license"], str):
            raise CorpusError("license must be a string or null")
        version_id = _id("version_", identity)
        existing = connection.execute(
            "SELECT * FROM documents WHERE document_id=?", (document_id,)
        ).fetchone()
        if existing is None:
            connection.execute("INSERT INTO documents VALUES (?)", (document_id,))
        if connection.execute(
            "SELECT 1 FROM document_versions WHERE version_id=?", (version_id,)
        ).fetchone():
            return version_id, False
        connection.execute(
            "INSERT INTO document_versions VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (version_id, document_id, document["title"], document["doc_type"],
             document["publisher"], document["fund_code"], document["period"],
             source_uri, str(source_path), checksum, raw_source,
             issued_date, effective_from, withdrawn_date, _now(), supersedes, authority,
             status, _json(provenance), _json(locator), identity["license"],
             extractor_version, chunker_version, _json(config), _json(identity), run_id),
        )
        if extraction is not None:
            connection.execute(
                "INSERT INTO document_extractions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (version_id, extraction["sha256"], extraction["bytes"],
                 str(extraction.get("path", source_path)),
                 extraction["artifact"].get("page_count", 0),
                 LEGAL_TEXT_BASIS if is_html else
                 extraction["parsed"]["blocks"][0]["locator"]["text_basis"],
                 text),
            )
            if is_html:
                sections = [
                    (section["heading"], section["char_start"], section["char_end"], section)
                    for section in legal_sections
                ]
            else:
                sections = [
                    (block["heading"], block["char_start"], block["char_end"], block["locator"])
                    for block in extraction["parsed"]["blocks"]
                ]
        else:
            sections = [(heading, start, end, {}) for heading, start, end in self._sections(text)]
            if is_legal:
                sections = [(section["heading"], section["char_start"], section["char_end"], section)
                            for section in legal_sections]
            elif is_catalog:
                sections = [(section["heading"], section["char_start"], section["char_end"], section)
                            for section in catalog_sections]
        for ordinal, (heading, start, end, block_locator) in enumerate(sections):
            section_id = _id("section_", [version_id, ordinal, start, end, heading])
            section_locator = {**locator, **block_locator, "section": heading, "char_start": start,
                               "char_end": end}
            if extraction is not None:
                section_locator.update({"extraction_sha256": extraction["sha256"]})
                if is_pdf:
                    section_locator["pdf_sha256"] = checksum
            if is_legal:
                section_locator.update({
                    "article_number": block_locator["article_number"],
                    "content_kind": "legal_article",
                    "title": document["title"],
                    "chapter": block_locator["chapter"],
                    "max_chars_semantics": "soft_target",
                    "section_char_start": start,
                    "section_char_end": end,
                })
            elif is_catalog:
                section_locator.update({
                    "content_kind": ("legal_article" if "article_number" in block_locator
                                     else "supplementary_body" if config["expected_articles"] is not None
                                     else "technical_body"),
                    "title": document["title"], "body_start_line": config["body_start_line"],
                    "section_char_start": start, "section_char_end": end,
                })
            if is_html:
                section_locator.update({
                    "raw_html_sha256": checksum,
                    "normalized_text_sha256": extraction["parsed"]["normalized_text_sha256"],
                    "dom_locator": extraction["parsed"]["dom_locator"],
                    "text_basis": LEGAL_TEXT_BASIS,
                })
            connection.execute(
                "INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (section_id, version_id, ordinal, heading, start, end, text[start:end],
                 _json(section_locator), ("unreviewed" if is_pdf
                                          else "utf8_text_not_independently_verified")),
            )
            if is_legal or is_catalog and "article_number" in block_locator:
                chunk_ranges = [(0, start, end)]
            else:
                chunk_ranges = (
                    (chunk_ordinal, chunk_start, min(chunk_start + max_chars, end))
                    for chunk_ordinal, chunk_start in enumerate(range(start, end, max_chars - overlap))
                )
            for chunk_ordinal, chunk_start, chunk_end in chunk_ranges:
                chunk_text = text[chunk_start:chunk_end]
                chunk_id = _id("chunk_", [version_id, section_id, chunk_ordinal,
                                          chunk_start, chunk_end,
                                          chunker_version, config])
                chunk_locator = {**section_locator, "char_start": chunk_start,
                                 "char_end": chunk_end}
                if is_legal or is_catalog and "article_number" in block_locator:
                    chunk_locator["oversized"] = len(chunk_text) > max_chars
                connection.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (chunk_id, version_id, section_id, chunk_ordinal, chunk_start,
                     chunk_end, chunk_text, _sha(chunk_text.encode("utf-8")),
                     chunker_version, _json(chunk_locator)),
                )
                connection.executemany(
                    "INSERT INTO entity_links VALUES (?, ?, ?, ?, ?)",
                    [(chunk_id, link["entity_id"], link["method"], link["confidence"],
                      link["review_status"]) for link in normalized_links],
                )
                if chunk_end == end:
                    break
        return version_id, True

    @staticmethod
    def _load_pdf_extraction(reference, base_path, raw_source, checksum):
        if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
            raise CorpusError("PDF extraction requires only path and sha256")
        path = (base_path / _text(reference, "path")).resolve()
        artifact_bytes = path.read_bytes()
        artifact_checksum = _text(reference, "sha256").lower()
        if (not re.fullmatch(r"[a-f0-9]{64}", artifact_checksum)
                or _sha(artifact_bytes) != artifact_checksum):
            raise CorpusError("Extraction sha256 mismatch or malformed sha256")
        try:
            artifact = load_extraction_json(artifact_bytes)
            parsed = parse_extraction(artifact, source_sha256=checksum,
                                      page_count=pdf_page_count(raw_source))
        except (ValueError, UnicodeDecodeError) as error:
            raise CorpusError(str(error)) from error
        return {"path": path, "bytes": artifact_bytes, "sha256": artifact_checksum,
                "artifact": artifact, "parsed": parsed}

    @staticmethod
    def _load_html_extraction(reference, raw_source, checksum):
        try:
            parsed = extract_official_html(raw_source, reference)
        except (ValueError, UnicodeDecodeError) as error:
            raise CorpusError(str(error)) from error
        artifact = {
            "schema_version": 1,
            "kind": reference["kind"],
            "source_sha256": checksum,
            "reference": reference,
            "dom_locator": parsed["dom_locator"],
            "removed_nul_count": parsed["removed_nul_count"],
            "text_basis": LEGAL_TEXT_BASIS,
            "normalized_text_sha256": parsed["normalized_text_sha256"],
            "normalized_text": parsed["text"],
            "page_count": 0,
        }
        artifact_bytes = _json(artifact).encode("utf-8")
        return {
            "reference": reference,
            "path": "sqlite:document_extractions.artifact_bytes",
            "bytes": artifact_bytes,
            "sha256": _sha(artifact_bytes),
            "artifact": artifact,
            "parsed": {**parsed, "text_basis": LEGAL_TEXT_BASIS},
        }

    @staticmethod
    def _sections(text: str) -> list[tuple[str, int, int]]:
        headings = list(re.finditer(r"(?m)^#{1,6}[ \t]+(.+)$", text))
        sections = []
        if not headings:
            return [("document", 0, len(text))]
        if headings[0].start() > 0:
            sections.append(("preamble", 0, headings[0].start()))
        for ordinal, heading in enumerate(headings):
            end = headings[ordinal + 1].start() if ordinal + 1 < len(headings) else len(text)
            sections.append((heading.group(1).strip(), heading.start(), end))
        return sections

    def publish_snapshot(self, snapshot_id: str, version_ids: list[str], *,
                         kind: str = "trusted", index_version: str = "bm25-2gram-v1") -> dict:
        """Publish an explicit, immutable membership set in one transaction."""
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise CorpusError("snapshot_id must be a nonempty string")
        if kind not in {"trusted", "research", "regression"}:
            raise CorpusError("Unknown snapshot kind")
        if not isinstance(index_version, str) or not index_version.strip():
            raise CorpusError("index_version must be a nonempty string")
        if (not isinstance(version_ids, list) or not version_ids
                or any(not isinstance(version_id, str) for version_id in version_ids)):
            raise CorpusError("version_ids must be a nonempty list of IDs")
        members = sorted(set(version_ids))
        fingerprint = _sha(_json(members).encode("utf-8"))
        with self._connection() as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT * FROM corpus_snapshots WHERE snapshot_id=?", (snapshot_id,)
                ).fetchone()
                if existing is not None:
                    if (existing["kind"], existing["index_version"], existing["members_sha256"]) != (
                            kind, index_version, fingerprint):
                        raise CorpusError("Snapshot ID already has different immutable membership")
                    return {**dict(existing), "version_ids": members}
                selected = []
                for version_id in members:
                    version = connection.execute(
                        "SELECT * FROM document_versions WHERE version_id=?", (version_id,)
                    ).fetchone()
                    if version is None:
                        raise CorpusError(f"Unknown version: {version_id}")
                    if kind == "trusted":
                        if (version["authority"] != "authoritative_original"
                                or version["status"] != "verified"
                                or not version["issued_date"]):
                            raise CorpusError("Trusted publication needs verified originals and issued date")
                    elif kind == "regression":
                        if (version["authority"] != "synthetic"
                                or version["status"] == "quarantined"):
                            raise CorpusError("Regression snapshots contain non-quarantined synthetic data only")
                    elif version["authority"] != "research_note" or version["status"] == "quarantined":
                        raise CorpusError("Research snapshots contain non-quarantined research notes only")
                    selected.append(version)
                if len({version["document_id"] for version in selected}) != len(selected):
                    raise CorpusError("A snapshot may select only one version per document")
                metadata = {"snapshot_id": snapshot_id, "kind": kind,
                            "index_version": index_version, "created_at": _now(),
                            "members_sha256": fingerprint}
                connection.execute("INSERT INTO corpus_snapshots VALUES (?, ?, ?, ?, ?)",
                                   tuple(metadata.values()))
                connection.executemany(
                    "INSERT INTO snapshot_members VALUES (?, ?, ?)",
                    [(snapshot_id, version["version_id"], version["document_id"])
                     for version in selected],
                )
        return {**metadata, "version_ids": members}

    def get_snapshot(self, snapshot_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM corpus_snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
            if row is None:
                raise CorpusError(f"Unknown snapshot: {snapshot_id}")
            versions = connection.execute(
                "SELECT version_id FROM snapshot_members WHERE snapshot_id=? ORDER BY version_id",
                (snapshot_id,),
            ).fetchall()
            return {**dict(row), "version_ids": [version["version_id"] for version in versions]}

    def list_snapshots(self) -> list[dict]:
        with self._connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM corpus_snapshots ORDER BY created_at, snapshot_id"
            )]

    def list_versions(self) -> list[dict]:
        with self._connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT version_id, document_id AS doc_id, title, doc_type, source_uri, sha256, authority, "
                "status, issued_date, effective_from, withdrawn_date, supersedes "
                "FROM document_versions ORDER BY document_id, acquired_at, version_id"
            )]

    def get_chunks(self, snapshot_id: str, *, as_of: str | None = None,
                   include_undated: bool = False) -> list[dict]:
        """Read only selected versions; date filtering never falls back to other versions."""
        snapshot = self.get_snapshot(snapshot_id)
        if type(include_undated) is not bool:
            raise CorpusError("include_undated must be a boolean")
        if include_undated and snapshot["kind"] != "research":
            raise CorpusError("include_undated is only supported for research snapshots")
        as_of = _date(as_of, "as_of")
        sql = (
            "SELECT c.*, s.heading, d.document_id, v.title, v.doc_type, v.fund_code, v.period, "
            "v.source_uri, v.source_path, v.sha256, v.authority, v.status, "
            "v.provenance_json, v.issued_date, v.effective_from, v.withdrawn_date, "
            "s.extraction_quality FROM snapshot_members m "
            "JOIN document_versions v ON v.version_id=m.version_id "
            "JOIN documents d ON d.document_id=v.document_id "
            "JOIN chunks c ON c.version_id=v.version_id "
            "JOIN sections s ON s.section_id=c.section_id WHERE m.snapshot_id=? "
        )
        parameters = [snapshot_id]
        if as_of is not None:
            sql += (
                "AND (v.issued_date<=? OR (? AND v.issued_date IS NULL)) "
                "AND (v.effective_from IS NULL OR v.effective_from<=?) "
                "AND (v.withdrawn_date IS NULL OR v.withdrawn_date>?) "
            )
            parameters.extend([as_of, include_undated, as_of, as_of])
        sql += "ORDER BY d.document_id, s.ordinal, c.ordinal"
        with self._connection() as connection:
            chunks = []
            for row in connection.execute(sql, parameters):
                locator = json.loads(row["locator_json"])
                locator.update({"source_uri": row["source_uri"], "source_path": row["source_path"],
                                "sha256": row["sha256"], "version_id": row["version_id"],
                                "original_storage": "sqlite:document_versions.original_bytes"})
                links = [dict(link) for link in connection.execute(
                    "SELECT entity_id, method, confidence, review_status FROM entity_links "
                    "WHERE chunk_id=? ORDER BY entity_id", (row["chunk_id"],)
                )]
                chunks.append({
                    "chunk_id": row["chunk_id"], "doc_id": row["document_id"],
                    "title": row["title"],
                    "version_id": row["version_id"], "doc_type": row["doc_type"],
                    "section": row["heading"], "text": row["text"], "locator": locator,
                    "fund_code": row["fund_code"], "period": row["period"],
                    "entity_links": links, "authority": row["authority"], "status": row["status"],
                    "provenance": json.loads(row["provenance_json"]),
                    "extraction_quality": row["extraction_quality"],
                    "issued_date": row["issued_date"], "effective_from": row["effective_from"],
                    "withdrawn_date": row["withdrawn_date"],
                })
            return chunks

    def get_original(self, version_id: str) -> bytes:
        """Restore exact imported bytes even if the external source path disappeared."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT original_bytes FROM document_versions WHERE version_id=?", (version_id,)
            ).fetchone()
            if row is None:
                raise CorpusError(f"Unknown version: {version_id}")
            return bytes(row["original_bytes"])

    def get_extraction(self, version_id: str) -> bytes:
        """Restore the exact hashed extraction receipt, independent of external files."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT artifact_bytes FROM document_extractions WHERE version_id=?", (version_id,)
            ).fetchone()
            if row is None:
                raise CorpusError(f"No extraction for version: {version_id}")
            return bytes(row["artifact_bytes"])

    def get_normalized_text(self, version_id: str) -> str:
        """Restore normalized text; offsets of HTML/PDF evidence use this text."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT v.original_bytes, v.extractor_version, e.normalized_text "
                "FROM document_versions v LEFT JOIN document_extractions e "
                "ON e.version_id=v.version_id WHERE v.version_id=?", (version_id,),
            ).fetchone()
            if row is None:
                raise CorpusError(f"Unknown version: {version_id}")
            if row["normalized_text"] is not None:
                return row["normalized_text"]
            return bytes(row["original_bytes"]).decode("utf-8", errors="strict")

    def verify_snapshot(self, snapshot_id: str) -> dict:
        """Verify stored originals and chunk spans, not legal authority or factual truth."""
        snapshot = self.get_snapshot(snapshot_id)
        errors = []
        if _sha(_json(snapshot["version_ids"]).encode("utf-8")) != snapshot["members_sha256"]:
            errors.append("Snapshot membership hash mismatch")
        with self._connection() as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                errors.append("SQLite integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                errors.append("Foreign key check failed")
            for version_id in snapshot["version_ids"]:
                version = connection.execute(
                    "SELECT * FROM document_versions WHERE version_id=?", (version_id,)
                ).fetchone()
                raw_source = bytes(version["original_bytes"])
                if _sha(raw_source) != version["sha256"]:
                    errors.append(f"Original hash mismatch: {version_id}")
                identity = json.loads(version["identity_json"])
                if _id("version_", identity) != version_id:
                    errors.append(f"Version identity mismatch: {version_id}")
                pdf_blocks = None
                legal_sections = None
                if version["extractor_version"] == PDF_EXTRACTOR_VERSION:
                    extraction = connection.execute(
                        "SELECT * FROM document_extractions WHERE version_id=?", (version_id,)
                    ).fetchone()
                    if extraction is None:
                        errors.append(f"Missing PDF extraction: {version_id}")
                        continue
                    artifact_bytes = bytes(extraction["artifact_bytes"])
                    artifact_sha256 = _sha(artifact_bytes)
                    if (artifact_sha256 != extraction["artifact_sha256"]
                            or artifact_sha256 != identity.get("extraction_sha256")):
                        errors.append(f"Extraction hash mismatch: {version_id}")
                    try:
                        artifact = load_extraction_json(artifact_bytes)
                        parsed = parse_extraction(artifact, source_sha256=version["sha256"],
                                                  page_count=pdf_page_count(raw_source))
                    except (ValueError, UnicodeDecodeError) as error:
                        errors.append(f"Invalid stored PDF extraction: {version_id}: {error}")
                        continue
                    original = parsed["text"]
                    pdf_blocks = parsed["blocks"]
                    if (original != extraction["normalized_text"]
                            or artifact["page_count"] != extraction["page_count"]
                            or extraction["text_basis"] != pdf_blocks[0]["locator"]["text_basis"]):
                        errors.append(f"Extraction normalized metadata mismatch: {version_id}")
                    sections = connection.execute(
                        "SELECT * FROM sections WHERE version_id=? ORDER BY ordinal", (version_id,)
                    ).fetchall()
                    if len(sections) != len(pdf_blocks):
                        errors.append(f"PDF section count mismatch: {version_id}")
                    for section, block in zip(sections, pdf_blocks):
                        expected_locator = {
                            **block["locator"], "char_start": block["char_start"],
                            "char_end": block["char_end"], "extraction_sha256": artifact_sha256,
                            "pdf_sha256": version["sha256"],
                        }
                        try:
                            section_locator = json.loads(section["locator_json"])
                        except (ValueError, TypeError):
                            errors.append(f"Invalid PDF section locator: {section['section_id']}")
                            continue
                        if (section["heading"] != block["heading"]
                                or section["char_start"] != block["char_start"]
                                or section["char_end"] != block["char_end"]
                                or section["text"] != original[block["char_start"]:block["char_end"]]
                                or section["extraction_quality"] != "unreviewed"
                                or not isinstance(section_locator, dict)
                                or any(section_locator.get(key) != value
                                       for key, value in expected_locator.items())):
                            errors.append(f"PDF section locator mismatch: {section['section_id']}")
                        config = json.loads(version["chunker_config_json"])
                        expected_chunks = []
                        for chunk_start in range(block["char_start"], block["char_end"],
                                                 config["max_chars"] - config["overlap"]):
                            chunk_end = min(chunk_start + config["max_chars"], block["char_end"])
                            expected_chunks.append((chunk_start, chunk_end))
                            if chunk_end == block["char_end"]:
                                break
                        stored_chunks = connection.execute(
                            "SELECT ordinal, char_start, char_end FROM chunks "
                            "WHERE section_id=? ORDER BY ordinal", (section["section_id"],)
                        ).fetchall()
                        if [(row["ordinal"], row["char_start"], row["char_end"])
                            for row in stored_chunks] != [
                                (ordinal, start, end)
                                for ordinal, (start, end) in enumerate(expected_chunks)]:
                            errors.append(f"PDF chunk coverage mismatch: {section['section_id']}")
                elif version["extractor_version"] == LEGAL_EXTRACTOR_VERSION:
                    extraction = connection.execute(
                        "SELECT * FROM document_extractions WHERE version_id=?", (version_id,)
                    ).fetchone()
                    if extraction is None:
                        errors.append(f"Missing HTML extraction: {version_id}")
                        continue
                    artifact_bytes = bytes(extraction["artifact_bytes"])
                    artifact_sha256 = _sha(artifact_bytes)
                    identity = json.loads(version["identity_json"])
                    if (artifact_sha256 != extraction["artifact_sha256"]
                            or artifact_sha256 != identity.get("extraction_sha256")):
                        errors.append(f"HTML extraction hash mismatch: {version_id}")
                    try:
                        artifact = json.loads(artifact_bytes.decode("utf-8"))
                        reference = artifact["reference"]
                        parsed = extract_official_html(raw_source, reference)
                    except (ValueError, UnicodeDecodeError, KeyError, json.JSONDecodeError) as error:
                        errors.append(f"Invalid stored HTML extraction: {version_id}: {error}")
                        continue
                    original = parsed["text"]
                    rebuilt = self._load_html_extraction(reference, raw_source, version["sha256"])
                    if (
                        extraction["normalized_text"] != original
                        or artifact.get("normalized_text") != original
                        or artifact.get("normalized_text_sha256") != parsed["normalized_text_sha256"]
                        or artifact.get("removed_nul_count") != parsed["removed_nul_count"]
                        or identity.get("normalized_text_sha256") != parsed["normalized_text_sha256"]
                        or extraction["text_basis"] != LEGAL_TEXT_BASIS
                        or artifact_bytes != rebuilt["bytes"]
                        or identity.get("html_extraction") != reference
                        or extraction["page_count"] != 0
                    ):
                        errors.append(f"HTML normalized metadata mismatch: {version_id}")
                    try:
                        config = json.loads(version["chunker_config_json"])
                        legal_sections = legal_article_sections(
                            original, expected_articles=config["expected_articles"]
                        )
                    except (ValueError, KeyError, TypeError) as error:
                        errors.append(f"Invalid legal article sections: {version_id}: {error}")
                        continue
                    sections = connection.execute(
                        "SELECT * FROM sections WHERE version_id=? ORDER BY ordinal", (version_id,)
                    ).fetchall()
                    if len(sections) != len(legal_sections):
                        errors.append(f"HTML section count mismatch: {version_id}")
                    for section, expected in zip(sections, legal_sections):
                        try:
                            locator = json.loads(section["locator_json"])
                        except (ValueError, TypeError):
                            errors.append(f"Invalid HTML section locator: {section['section_id']}")
                            continue
                        if (
                            section["heading"] != expected["heading"]
                            or section["char_start"] != expected["char_start"]
                            or section["char_end"] != expected["char_end"]
                            or section["text"] != original[expected["char_start"]:expected["char_end"]]
                            or locator.get("article_number") != expected["article_number"]
                            or locator.get("content_kind") != "legal_article"
                            or locator.get("raw_html_sha256") != version["sha256"]
                            or locator.get("dom_locator") != parsed["dom_locator"]
                            or locator.get("normalized_text_sha256") != parsed["normalized_text_sha256"]
                            or locator.get("chapter") != expected["chapter"]
                            or locator.get("title") != version["title"]
                            or locator.get("char_start") != expected["char_start"]
                            or locator.get("char_end") != expected["char_end"]
                        ):
                            errors.append(f"HTML section locator mismatch: {section['section_id']}")
                else:
                    try:
                        original = raw_source.decode("utf-8", errors="strict")
                    except UnicodeDecodeError:
                        errors.append(f"Invalid stored UTF-8: {version_id}")
                        continue
                if version["chunker_version"] == DATA_CHUNKER_VERSION:
                    errors.extend(self._verify_catalog_body(connection, version, original))
                if (version["chunker_version"] == LEGAL_CHUNKER_VERSION
                        and legal_sections is None):
                    try:
                        config = json.loads(version["chunker_config_json"])
                        legal_sections = legal_article_sections(
                            original, expected_articles=config["expected_articles"]
                        )
                    except (ValueError, KeyError, TypeError) as error:
                        errors.append(f"Invalid legal article sections: {version_id}: {error}")
                        continue
                if legal_sections is not None:
                    if (version["chunker_version"] != LEGAL_CHUNKER_VERSION
                            or config.get("strategy") != LEGAL_CHUNKER_VERSION
                            or config.get("overlap") != 0
                            or type(config.get("max_chars")) is not int
                            or config["max_chars"] <= 0):
                        errors.append(f"Legal chunker configuration mismatch: {version_id}")
                    stored_sections = connection.execute(
                        "SELECT * FROM sections WHERE version_id=? ORDER BY ordinal", (version_id,)
                    ).fetchall()
                    stored_chunks = connection.execute(
                        "SELECT * FROM chunks WHERE version_id=? ORDER BY ordinal", (version_id,)
                    ).fetchall()
                    if (len(stored_sections) != len(legal_sections)
                            or len(stored_chunks) != len(legal_sections)):
                        errors.append(f"Legal article coverage mismatch: {version_id}")
                    for section, expected in zip(stored_sections, legal_sections):
                        base_locator = json.loads(version["locator_json"])
                        expected_locator = {
                            **base_locator, **expected, "section": expected["heading"],
                            "char_start": expected["char_start"], "char_end": expected["char_end"],
                            "article_number": expected["article_number"], "content_kind": "legal_article",
                            "title": version["title"], "chapter": expected["chapter"],
                            "max_chars_semantics": "soft_target",
                            "section_char_start": expected["char_start"],
                            "section_char_end": expected["char_end"],
                        }
                        if version["extractor_version"] == LEGAL_EXTRACTOR_VERSION:
                            expected_locator.update({
                                "extraction_sha256": artifact_sha256,
                                "raw_html_sha256": version["sha256"],
                                "normalized_text_sha256": parsed["normalized_text_sha256"],
                                "dom_locator": parsed["dom_locator"],
                                "text_basis": LEGAL_TEXT_BASIS,
                            })
                        try:
                            section_locator = json.loads(section["locator_json"])
                        except (ValueError, TypeError):
                            errors.append(f"Invalid legal section locator: {section['section_id']}")
                            continue
                        expected_section_id = _id(
                            "section_", [version_id, section["ordinal"], expected["char_start"],
                                         expected["char_end"], expected["heading"]]
                        )
                        if (section["ordinal"] != expected["article_number"] - 1
                                or section["char_start"] != expected["char_start"]
                                or section["char_end"] != expected["char_end"]
                                or section["text"] != original[expected["char_start"]:expected["char_end"]]
                                or section["section_id"] != expected_section_id
                                or section_locator != expected_locator
                                or section["extraction_quality"] != "utf8_text_not_independently_verified"):
                            errors.append(f"Legal article section mismatch: {section['section_id']}")
                        count = connection.execute(
                            "SELECT COUNT(*) FROM chunks WHERE section_id=?", (section["section_id"],)
                        ).fetchone()[0]
                        if count != 1:
                            errors.append(f"Legal article chunk count mismatch: {section['section_id']}")
                for chunk in connection.execute(
                    "SELECT * FROM chunks WHERE version_id=?", (version_id,)
                ):
                    if (not 0 <= chunk["char_start"] < chunk["char_end"] <= len(original)
                            or original[chunk["char_start"]:chunk["char_end"]] != chunk["text"]):
                        errors.append(f"Chunk locator mismatch: {chunk['chunk_id']}")
                    if _sha(chunk["text"].encode("utf-8")) != chunk["text_sha256"]:
                        errors.append(f"Chunk hash mismatch: {chunk['chunk_id']}")
                    if pdf_blocks is not None:
                        section = connection.execute(
                            "SELECT * FROM sections WHERE section_id=?", (chunk["section_id"],)
                        ).fetchone()
                        try:
                            chunk_locator = json.loads(chunk["locator_json"])
                            section_locator = json.loads(section["locator_json"])
                            if not isinstance(chunk_locator, dict) or not isinstance(section_locator, dict):
                                raise ValueError("PDF locators must be objects")
                        except (ValueError, TypeError):
                            errors.append(f"Invalid PDF chunk locator: {chunk['chunk_id']}")
                            continue
                        expected = {**section_locator, "char_start": chunk["char_start"],
                                    "char_end": chunk["char_end"]}
                        if (section["version_id"] != version_id
                                or not section["char_start"] <= chunk["char_start"]
                                < chunk["char_end"] <= section["char_end"]
                                or chunk_locator != expected):
                            errors.append(f"PDF chunk page/span mismatch: {chunk['chunk_id']}")
                    elif legal_sections is not None:
                        section = connection.execute(
                            "SELECT * FROM sections WHERE section_id=?", (chunk["section_id"],)
                        ).fetchone()
                        try:
                            chunk_locator = json.loads(chunk["locator_json"])
                            section_locator = json.loads(section["locator_json"])
                        except (ValueError, TypeError):
                            errors.append(f"Invalid HTML chunk locator: {chunk['chunk_id']}")
                            continue
                        expected = {**section_locator, "char_start": chunk["char_start"],
                                    "char_end": chunk["char_end"], "oversized":
                                    len(chunk["text"]) > json.loads(
                                        version["chunker_config_json"])["max_chars"]}
                        expected_chunk_id = _id(
                            "chunk_", [version_id, section["section_id"], 0,
                                       section["char_start"], section["char_end"],
                                       LEGAL_CHUNKER_VERSION, config]
                        )
                        if (
                            section["version_id"] != version_id
                            or chunk["chunker_version"] != LEGAL_CHUNKER_VERSION
                            or chunk_locator != expected
                            or chunk["ordinal"] != 0
                            or chunk["char_start"] != section["char_start"]
                            or chunk["char_end"] != section["char_end"]
                            or chunk["chunk_id"] != expected_chunk_id
                        ):
                            errors.append(f"HTML chunk locator mismatch: {chunk['chunk_id']}")
            chunk_count = connection.execute(
                "SELECT COUNT(*) FROM chunks c JOIN snapshot_members m "
                "ON m.version_id=c.version_id WHERE m.snapshot_id=?", (snapshot_id,)
            ).fetchone()[0]
        return {"snapshot_id": snapshot_id, "ok": not errors, "errors": errors,
                "versions": len(snapshot["version_ids"]),
                "chunks": chunk_count}

    @staticmethod
    def _verify_catalog_body(connection, version, original):
        errors = []
        version_id = version["version_id"]
        try:
            config = json.loads(version["chunker_config_json"])
            if (type(config["max_chars"]) is not int or config["max_chars"] <= 0
                    or config["overlap"] != 0):
                raise ValueError("Invalid data body chunk sizes")
            expected_sections = catalog_body_sections(original, config)
            base_locator = json.loads(version["locator_json"])
        except (ValueError, KeyError, TypeError) as error:
            return [f"Invalid data body configuration: {version_id}: {error}"]
        sections = connection.execute(
            "SELECT * FROM sections WHERE version_id=? ORDER BY ordinal", (version_id,)
        ).fetchall()
        if len(sections) != len(expected_sections):
            errors.append(f"Data body section coverage mismatch: {version_id}")
        for ordinal, (section, expected) in enumerate(zip(sections, expected_sections)):
            start, end = expected["char_start"], expected["char_end"]
            section_id = _id("section_", [version_id, ordinal, start, end, expected["heading"]])
            locator = {
                **base_locator, **expected, "section": expected["heading"],
                "char_start": start, "char_end": end,
                "content_kind": ("legal_article" if "article_number" in expected
                                 else "supplementary_body" if config["expected_articles"] is not None
                                 else "technical_body"),
                "title": version["title"], "body_start_line": config["body_start_line"],
                "section_char_start": start, "section_char_end": end,
            }
            if (section["section_id"] != section_id or section["ordinal"] != ordinal
                    or section["heading"] != expected["heading"]
                    or section["char_start"] != start or section["char_end"] != end
                    or section["text"] != original[start:end]
                    or json.loads(section["locator_json"]) != locator):
                errors.append(f"Data body section mismatch: {section['section_id']}")
            ranges = [(start, end)] if "article_number" in expected else []
            if not ranges:
                for chunk_start in range(start, end, config["max_chars"]):
                    chunk_end = min(chunk_start + config["max_chars"], end)
                    ranges.append((chunk_start, chunk_end))
            chunks = connection.execute(
                "SELECT * FROM chunks WHERE section_id=? ORDER BY ordinal", (section["section_id"],)
            ).fetchall()
            if len(chunks) != len(ranges):
                errors.append(f"Data body chunk coverage mismatch: {section['section_id']}")
            for chunk_ordinal, (chunk, span) in enumerate(zip(chunks, ranges)):
                chunk_start, chunk_end = span
                chunk_locator = {**locator, "char_start": chunk_start, "char_end": chunk_end}
                if "article_number" in expected:
                    chunk_locator["oversized"] = chunk_end - chunk_start > config["max_chars"]
                chunk_id = _id("chunk_", [version_id, section_id, chunk_ordinal,
                                          chunk_start, chunk_end, DATA_CHUNKER_VERSION, config])
                if (chunk["chunk_id"] != chunk_id or chunk["ordinal"] != chunk_ordinal
                        or chunk["chunker_version"] != DATA_CHUNKER_VERSION
                        or chunk["char_start"] != chunk_start or chunk["char_end"] != chunk_end
                        or json.loads(chunk["locator_json"]) != chunk_locator):
                    errors.append(f"Data body chunk mismatch: {chunk['chunk_id']}")
        return errors
