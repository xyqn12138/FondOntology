"""MinerU v4 batch ingestion with offline-first, resumable state."""

from __future__ import annotations

import argparse
import hashlib
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import sys
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

BASE_URL = "https://mineru.net"
CONFIG = {
    "model_version": "pipeline",
    "enable_table": True,
    "enable_formula": True,
    "language": "ch",
    "is_ocr": True,
}
MAX_FILES_PER_BATCH = 50
MAX_ZIP_FILES = 20_000
MAX_ZIP_BYTES = 512 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
RETRY_COUNT = 4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def data_id_for(pdf: Path, data_root: Path, config: dict[str, Any] | None = None) -> str:
    rel = pdf.resolve().relative_to(data_root.resolve()).as_posix()
    pdf_hash = sha256_file(pdf)
    config_hash = hashlib.sha256(canonical_bytes(config or CONFIG)).hexdigest()
    digest = hashlib.sha256(f"{rel}\0{pdf_hash}\0{config_hash}".encode()).hexdigest()
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(rel).stem).strip("-")[:48] or "document"
    return f"{stem}-{digest}"[:128]


def collect_pdfs(data_root: Path) -> list[Path]:
    if not data_root.is_dir():
        raise MinerUError("data directory does not exist")
    return sorted((p for p in data_root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"),
                  key=lambda p: p.as_posix())


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, canonical_bytes(value) + b"\n")


class MinerUError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class _NoDefaultPutContentTypeHTTPHandler(urllib.request.HTTPHandler):
    def do_request_(self, request):
        had_content_type = request.has_header("Content-type")
        request = super().do_request_(request)
        if request.get_method() == "PUT" and not had_content_type:
            request.unredirected_hdrs.pop("Content-type", None)
        return request

    http_request = do_request_


class _NoDefaultPutContentTypeHTTPSHandler(urllib.request.HTTPSHandler):
    def do_request_(self, request):
        had_content_type = request.has_header("Content-type")
        request = super().do_request_(request)
        if request.get_method() == "PUT" and not had_content_type:
            request.unredirected_hdrs.pop("Content-type", None)
        return request

    https_request = do_request_


class HTTPTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str] | None = None,
                body: bytes | None = None, timeout: float = 60.0) -> tuple[int, bytes]:
        request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        opener = urllib.request.build_opener(
            _NoRedirect(), _NoDefaultPutContentTypeHTTPHandler(),
            _NoDefaultPutContentTypeHTTPSHandler())
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_DOWNLOAD_BYTES + 1)
                if len(raw) > MAX_DOWNLOAD_BYTES:
                    raise MinerUError("HTTP response exceeds download size limit")
                return int(response.status), raw
        except urllib.error.HTTPError as error:
            return int(error.code), error.read(1024)


def _remaining(deadline: float, timeout: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise MinerUError("total deadline exceeded")
    return min(timeout, remaining)


def _sleep(duration: float, deadline: float) -> None:
    time.sleep(min(duration, _remaining(deadline, duration)))
    _remaining(deadline, duration)


def _https_url(value: Any) -> str:
    if not isinstance(value, str):
        raise MinerUError("invalid HTTPS resource URL")
    try:
        parsed = urllib.parse.urlsplit(value)
        if (any(ord(character) <= 32 or ord(character) == 127 for character in value)
                or "\\" in value
                or parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.port not in (None, 443)):
            raise ValueError
        if parsed.hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise ValueError
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError
    except ValueError as error:
        raise MinerUError("invalid HTTPS resource URL") from error
    return value


def _request(transport: HTTPTransport, method: str, url: str, *, deadline: float,
             timeout: float, headers: dict[str, str] | None = None,
             body: bytes | None = None, operation: str) -> bytes:
    _https_url(url)
    if headers and "Authorization" in headers:
        parsed = urllib.parse.urlsplit(url)
        if parsed.hostname != "mineru.net" or not parsed.path.startswith("/api/v4/"):
            raise MinerUError("authorization is restricted to MinerU API")
    for attempt in range(RETRY_COUNT):
        try:
            status, raw = transport.request(method, url, headers=headers, body=body,
                                            timeout=_remaining(deadline, timeout))
            if status == 429 or status >= 500:
                if attempt + 1 < RETRY_COUNT:
                    _sleep(0.5 * (attempt + 1), deadline)
                    continue
            if status < 200 or status >= 300:
                raise MinerUError(f"{operation} failed HTTP {status}")
            if len(raw) > MAX_DOWNLOAD_BYTES:
                raise MinerUError("HTTP response exceeds download size limit")
            return raw
        except (urllib.error.URLError, TimeoutError, OSError, socket.timeout) as error:
            if attempt + 1 == RETRY_COUNT:
                raise MinerUError(f"{operation} failed after retries") from None
            _sleep(0.5 * (attempt + 1), deadline)
    raise MinerUError(f"{operation} failed")


def _request_json(transport: HTTPTransport, method: str, url: str, token: str,
                  payload: Any | None, timeout: float, deadline: float) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = canonical_bytes(payload) if payload is not None else None
    raw = _request(transport, method, url, headers=headers, body=body,
                   timeout=timeout, deadline=deadline, operation="MinerU API request")
    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise MinerUError("MinerU returned invalid JSON") from error
    if not isinstance(result, dict) or type(result.get("code")) is not int or result["code"] != 0:
        raise MinerUError("MinerU API returned a non-success response")
    if not isinstance(result.get("data"), dict):
        raise MinerUError("MinerU API returned invalid data")
    return result["data"]


def _safe_member(name: str) -> str:
    normalized = name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    parts = normalized.rstrip("/").split("/")
    if (not parts or pure.is_absolute()
            or any(part in ("", ".", "..") or ":" in part or part.endswith((".", " "))
                   or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
                   for part in parts)):
        raise MinerUError("unsafe ZIP member")
    return pure.as_posix()


def extract_result_zip(zip_bytes: bytes, result_dir: Path) -> dict[str, Any]:
    if len(zip_bytes) > MAX_DOWNLOAD_BYTES:
        raise MinerUError("ZIP download size exceeds limit")
    if result_dir.exists() and any(result_dir.iterdir()):
        raise MinerUError("result destination must be empty")
    result_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_FILES:
            raise MinerUError("ZIP contains too many files")
        total = 0
        members: dict[str, zipfile.ZipInfo] = {}
        seen: set[str] = set()
        for info in infos:
            member = _safe_member(info.filename)
            if member.casefold() in seen:
                raise MinerUError("duplicate ZIP member mapping")
            seen.add(member.casefold())
            if info.is_dir():
                continue
            mode = (info.external_attr >> 16) & 0o170000
            if mode not in (0, 0o100000) or info.flag_bits & 1:
                raise MinerUError("unsupported ZIP file type or encrypted member")
            total += info.file_size
            if (total > MAX_ZIP_BYTES or info.file_size > MAX_ZIP_BYTES
                    or info.file_size > max(info.compress_size, 1) * 300):
                raise MinerUError("ZIP uncompressed size or compression ratio exceeds limit")
            members[member] = info
        full = [name for name in members if PurePosixPath(name).name == "full.md"]
        content = [name for name in members if PurePosixPath(name).name == "content_list.json" or PurePosixPath(name).name.endswith("_content_list.json")]
        if len(full) != 1:
            raise MinerUError(f"ZIP must contain exactly one full.md, found {len(full)}")
        if len(content) != 1:
            raise MinerUError(f"ZIP must contain exactly one content_list JSON, found {len(content)}")
        root = PurePosixPath(full[0]).parent
        if PurePosixPath(content[0]).parent != root:
            raise MinerUError("Markdown and content list must share one result root")
        mapped: set[str] = set()
        for member, info in members.items():
            try:
                relative = PurePosixPath(member).relative_to(root)
            except ValueError as error:
                raise MinerUError("ZIP contains multiple result roots") from error
            mapping = relative.as_posix()
            if mapping.casefold() in mapped or mapping == "result.zip":
                raise MinerUError("duplicate ZIP output mapping")
            mapped.add(mapping.casefold())
            target = result_dir / mapping
            if result_dir.resolve() not in target.resolve().parents:
                raise MinerUError("ZIP output escapes result directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
    (result_dir / "result.zip").write_bytes(zip_bytes)
    return {"full_md": result_dir / "full.md",
            "content_list": result_dir / PurePosixPath(content[0]).name}


def _verify_images(markdown_path: Path, result_dir: Path) -> None:
    text = markdown_path.read_text(encoding="utf-8")
    references = re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", text)
    references.extend(re.findall(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", text, re.I))
    content_paths = list(result_dir.glob("*_content_list.json"))
    if (result_dir / "content_list.json").is_file():
        content_paths.append(result_dir / "content_list.json")
    for content in content_paths:
        for block in _load_content(content):
            if isinstance(block, dict) and block.get("img_path"):
                references.append(block["img_path"])
    for raw in references:
        if not isinstance(raw, str) or urllib.parse.urlsplit(raw).scheme or raw.startswith(("/", "\\")):
            raise MinerUError("nonlocal image reference is not allowed")
        decoded = urllib.parse.unquote(raw).replace("\\", "/").split("#", 1)[0]
        target = (markdown_path.parent / decoded).resolve()
        if result_dir.resolve() not in target.parents and target != result_dir.resolve():
            raise MinerUError("image reference escapes result directory")
        if not target.is_file():
            raise MinerUError("missing image referenced by extraction")


def _load_content(path: Path) -> list[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MinerUError(f"invalid content list JSON: {path.name}") from error
    if not isinstance(value, list):
        raise MinerUError("content list must be a JSON array")
    return value


def write_artifacts(pdf: Path, result_dir: Path) -> dict[str, Any]:
    from .pdf_extraction import build_extraction, parse_extraction

    full_md = result_dir / "full.md"
    candidates = list(result_dir.rglob("full.md"))
    content_candidates = [p for p in result_dir.rglob("*")
                          if p.is_file() and (p.name == "content_list.json"
                                             or p.name.endswith("_content_list.json"))]
    if candidates != [full_md]:
        raise MinerUError("result must have one root full.md")
    if len(content_candidates) != 1:
        raise MinerUError("result must have exactly one content_list JSON")
    _verify_images(full_md, result_dir)
    _load_content(content_candidates[0])
    extraction = build_extraction(pdf, result_dir)
    parsed = parse_extraction(extraction, source_sha256=extraction["source_sha256"],
                              page_count=extraction["page_count"])
    extraction_bytes = canonical_bytes(extraction)
    extraction_path = result_dir / "extraction.json"
    _atomic_bytes(extraction_path, extraction_bytes + b"\n")
    quality = {
        "schema_version": 1,
        "source_sha256": extraction["source_sha256"],
        "page_count": extraction["page_count"],
        "content_blocks": len(extraction["content_list"]),
        "indexed_blocks": len(parsed["blocks"]),
        "indexed_reported_pages": sorted({block["locator"]["page"] for block in parsed["blocks"]}),
        "normalized_chars": len(parsed["text"]),
        "unindexed_blocks": parsed["unindexed_blocks"],
        "extraction_quality": "mineru_unreviewed",
        "page_scope": "mineru_reported_start_page_unreviewed",
    }
    _atomic_json(result_dir / "quality.json", quality)
    extraction_sha = hashlib.sha256(extraction_bytes + b"\n").hexdigest()
    return {"path": extraction_path, "sha256": extraction_sha}


def build_manifest(pdfs: list[Path], data_root: Path, output_root: Path,
                   completed: dict[str, dict[str, Any]], *,
                   source_verified: bool = False) -> Path:
    manifest = output_root / "corpus.jsonl"
    lines: list[str] = []
    for pdf in pdfs:
        data_id = data_id_for(pdf, data_root)
        item = completed.get(data_id)
        if not item:
            raise MinerUError(f"missing completed extraction: {data_id}")
        extraction = Path(item["extraction"])
        record = {
            "doc_id": "educational:" + hashlib.sha256(pdf.relative_to(data_root).as_posix().encode()).hexdigest(),
            "title": pdf.stem,
            "source_uri": pdf.resolve().as_uri(),
            "path": os.path.relpath(pdf, output_root).replace("\\", "/"),
            "sha256": sha256_file(pdf),
            "extraction": {
                "path": os.path.relpath(extraction, output_root).replace("\\", "/"),
                "sha256": item["sha256"],
            },
            "doc_type": "educational_reference",
            "authority": "research_note",
            "status": "verified" if source_verified else "unverified",
            "issued_date": None,
            "effective_from": None,
            "locator": {"source": "mineru", "data_id": data_id, "relative_path": pdf.relative_to(data_root).as_posix()},
            "provenance": (
                {"kind": "user_attested", "user_attestation": "Source verified by user; educational reference, not an official regulation.",
                 "extraction_review": "machine extraction; OCR not independently reviewed"}
                if source_verified else
                {"kind": "source_unverified",
                 "source_review": "Source not independently verified; educational reference, not an official regulation.",
                 "extraction_review": "machine extraction; OCR not independently reviewed"}
            ),
        }
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    _atomic_bytes(manifest, ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8"))
    return manifest


def _tree_hashes(directory: Path) -> dict[str, str]:
    if directory.is_symlink():
        raise MinerUError("symlinks are not allowed in result directories")
    hashes = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise MinerUError("symlinks are not allowed in result directories")
        if path.is_file():
            hashes[path.relative_to(directory).as_posix()] = sha256_file(path)
    return hashes


def _result_target(output_root: Path, data_id: str) -> Path:
    target = output_root / "files" / data_id
    if target.is_symlink() or target.parent.is_symlink() or output_root.resolve() not in target.resolve().parents:
        raise MinerUError("result directory escapes output root")
    return target


def _raw_target(output_root: Path, data_id: str) -> Path:
    target = output_root / "raw" / f"{data_id}.zip"
    if target.is_symlink() or target.parent.is_symlink() or output_root.resolve() not in target.resolve().parents:
        raise MinerUError("raw ZIP directory escapes output root")
    return target


def _install_zip(pdf: Path, raw_zip: Path, data_id: str, output_root: Path,
                 entry: dict[str, Any], state: dict[str, Any]) -> None:
    target = _result_target(output_root, data_id)
    with tempfile.TemporaryDirectory(prefix=".mineru-", dir=output_root) as temporary:
        staging = Path(temporary) / "result"
        extract_result_zip(raw_zip.read_bytes(), staging)
        write_artifacts(pdf, staging)
        if sha256_file(pdf) != entry["sha256"]:
            raise MinerUError("PDF changed during extraction")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staging), target)
    _finalize(pdf, target, entry, output_root, state)


def _complete(entry: dict[str, Any], output_root: Path) -> bool:
    if entry.get("status") != "completed" or not isinstance(entry.get("artifacts"), dict):
        return False
    try:
        result_dir = _result_target(output_root, entry["data_id"])
        if not result_dir.is_dir() or _tree_hashes(result_dir) != entry["artifacts"]:
            return False
        extraction = result_dir / "extraction.json"
        return (extraction.is_file() and (result_dir / "quality.json").is_file()
                and sha256_file(extraction) == entry.get("sha256_extraction"))
    except (OSError, MinerUError):
        return False


def _finalize(pdf: Path, result_dir: Path, entry: dict[str, Any], output_root: Path,
              state: dict[str, Any]) -> None:
    artifact = write_artifacts(pdf, result_dir)
    entry.update({"status": "completed", "sha256_extraction": artifact["sha256"],
                  "artifacts": _tree_hashes(result_dir)})
    _atomic_json(output_root / "state.json", state)


def _offline_result(results_dir: Path, pdf: Path, data_root: Path, data_id: str) -> Path:
    options = [results_dir / data_id, results_dir / pdf.relative_to(data_root).with_suffix("")]
    matches = list(dict.fromkeys(p.resolve() for p in options if p.is_dir()))
    if len(matches) != 1:
        raise MinerUError(f"offline result mapping is missing or ambiguous: {data_id}")
    source = matches[0]
    _tree_hashes(source)
    return source


def _download(transport: HTTPTransport, url: str, deadline: float, timeout: float) -> bytes:
    try:
        return _request(transport, "GET", url, deadline=deadline, timeout=timeout,
                        operation="result download")
    except MinerUError:
        executable = shutil.which("curl.exe") or shutil.which("curl")
        if type(transport) is not HTTPTransport or not executable:
            raise
        _https_url(url)
        with tempfile.TemporaryDirectory(prefix="mineru-download-") as directory:
            target = Path(directory) / "result.zip"
            config = f'url = "{url.replace(chr(34), "%22")}"\n'
            try:
                process = subprocess.run(
                    [executable, "--config", "-", "--silent", "--fail", "--proto", "=https",
                     "--max-time", str(_remaining(deadline, timeout)),
                     "--max-filesize", str(MAX_DOWNLOAD_BYTES), "--output", str(target)],
                    input=config, text=True, capture_output=True,
                    timeout=_remaining(deadline, timeout),
                )
            except (OSError, subprocess.TimeoutExpired):
                raise MinerUError("result download fallback failed") from None
            if process.returncode or not target.is_file() or target.stat().st_size > MAX_DOWNLOAD_BYTES:
                raise MinerUError("result download fallback failed")
            return target.read_bytes()


def run(data_root: Path, output_root: Path, *, execute: bool = False,
        poll_interval: float = 15.0, deadline_seconds: float = 1800.0,
        http_timeout: float = 60.0, results_dir: Path | None = None,
        transport: HTTPTransport | None = None,
        source_verified: bool = False) -> dict[str, Any]:
    if any(not 0 < number < 86400 for number in (poll_interval, deadline_seconds, http_timeout)):
        raise MinerUError("poll interval, deadline and HTTP timeout must be positive and below one day")
    data_root = data_root.resolve()
    output_root = output_root.resolve()
    pdfs = collect_pdfs(data_root)
    if not pdfs:
        raise MinerUError("no PDF inputs found")
    config_hash = hashlib.sha256(canonical_bytes(CONFIG)).hexdigest()
    state_path = output_root / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except (ValueError, OSError) as error:
        raise MinerUError("cannot read batch state") from error
    if state.get("config_hash") != config_hash or state.get("data_root") != str(data_root):
        state = {"schema_version": 1, "data_root": str(data_root), "config_hash": config_hash,
                 "files": {}, "batches": []}
    files = state.setdefault("files", {})
    if not isinstance(files, dict) or not isinstance(state.get("batches"), list):
        raise MinerUError("invalid batch state structure")
    requested: dict[str, Path] = {}
    for pdf in pdfs:
        if pdf.is_symlink() or data_root not in pdf.resolve().parents:
            raise MinerUError("PDF input must be within data directory and not a symlink")
        digest = sha256_file(pdf)
        data_id = data_id_for(pdf, data_root)
        requested[data_id] = pdf
        entry = files.setdefault(data_id, {"pdf": pdf.relative_to(data_root).as_posix(), "sha256": digest, "data_id": data_id})
        if not isinstance(entry, dict):
            raise MinerUError("invalid persisted file entry")
        if entry.get("sha256") != digest or entry.get("data_id") != data_id:
            entry.clear()
            entry.update({"pdf": pdf.relative_to(data_root).as_posix(), "sha256": digest, "data_id": data_id})
    pending_ids = [data_id for data_id in requested if not _complete(files[data_id], output_root)]
    if not execute and results_dir is None:
        return {"mode": "dry-run", "pdfs": [p.relative_to(data_root).as_posix() for p in pdfs],
                "data_ids": list(requested), "pending": pending_ids, "state": state_path}
    output_root.mkdir(parents=True, exist_ok=True)
    _atomic_json(state_path, state)
    manifest = output_root / "corpus.jsonl"
    manifest.unlink(missing_ok=True)
    if results_dir is not None:
        if execute:
            raise MinerUError("--results-dir cannot be combined with --execute")
        for data_id in pending_ids:
            pdf = requested[data_id]
            source = _offline_result(results_dir.resolve(), pdf, data_root, data_id)
            target = _result_target(output_root, data_id)
            if source != target.resolve():
                with tempfile.TemporaryDirectory(prefix=".mineru-", dir=output_root) as temporary:
                    staging = Path(temporary) / "result"
                    shutil.copytree(source, staging, symlinks=False)
                    write_artifacts(pdf, staging)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.move(str(staging), target)
            _finalize(pdf, target, files[data_id], output_root, state)
        completed = {data_id: {"extraction": str(output_root / "files" / data_id / "extraction.json"),
                              "sha256": files[data_id]["sha256_extraction"]} for data_id in requested}
        return {"mode": "offline", "manifest": build_manifest(
                    pdfs, data_root, output_root, completed, source_verified=source_verified),
                "state": state_path}
    for data_id in list(pending_ids):
        raw_zip = _raw_target(output_root, data_id)
        if (raw_zip.is_file() and files[data_id].get("download_sha256") == sha256_file(raw_zip)):
            _install_zip(requested[data_id], raw_zip, data_id, output_root, files[data_id], state)
            pending_ids.remove(data_id)
    token = os.getenv("MINERU_KEY") or os.getenv("MINERU_API_TOKEN")
    if pending_ids and not token:
        raise MinerUError("MINERU_KEY or MINERU_API_TOKEN is required with --execute")
    transport = transport or HTTPTransport()
    deadline = time.monotonic() + deadline_seconds
    remaining = set(pending_ids)
    resumable = []
    for previous in state["batches"]:
        batch_ids = previous.get("data_ids")
        if (not isinstance(batch_ids, list) or not batch_ids or not isinstance(previous.get("batch_id"), str)
                or len(batch_ids) != len(set(batch_ids)) or len(batch_ids) > MAX_FILES_PER_BATCH):
            raise MinerUError("invalid persisted batch mapping")
        wanted = set(batch_ids) & remaining
        if wanted and set(batch_ids).issubset(requested) and previous.get("uploaded") == batch_ids:
            resumable.append(previous)
            remaining -= wanted
    new_ids = [data_id for data_id in pending_ids if data_id in remaining]
    batches = [(item, False) for item in resumable]
    batches.extend(({"data_ids": new_ids[offset:offset + MAX_FILES_PER_BATCH]}, True)
                   for offset in range(0, len(new_ids), MAX_FILES_PER_BATCH))
    for batch_state, create in batches:
        batch_ids = batch_state["data_ids"]
        if create:
            payload = {key: value for key, value in CONFIG.items() if key != "is_ocr"}
            payload["files"] = [{"name": requested[data_id].name, "data_id": data_id,
                                 "is_ocr": CONFIG["is_ocr"]} for data_id in batch_ids]
            data = _request_json(transport, "POST", BASE_URL + "/api/v4/file-urls/batch",
                                 token, payload, http_timeout, deadline)
            urls = data.get("file_urls")
            batch_id = data.get("batch_id")
            if not isinstance(batch_id, str) or not batch_id or not isinstance(urls, list) or len(urls) != len(batch_ids):
                raise MinerUError("MinerU returned an invalid batch response")
            if any(not isinstance(url, str) for url in urls) or len(set(urls)) != len(urls):
                raise MinerUError("MinerU returned duplicate or invalid upload URLs")
            batch_state.update({"batch_id": batch_id, "uploaded": []})
            state["batches"].append(batch_state)
            _atomic_json(state_path, state)
            for data_id, upload_url in zip(batch_ids, urls):
                pdf = requested[data_id]
                if sha256_file(pdf) != files[data_id]["sha256"]:
                    raise MinerUError("PDF changed after batch planning")
                _request(transport, "PUT", upload_url, body=pdf.read_bytes(),
                         deadline=deadline, timeout=http_timeout, operation="PDF upload")
                batch_state["uploaded"].append(data_id)
                _atomic_json(state_path, state)
        batch_id = batch_state["batch_id"]
        while True:
            polled = _request_json(transport, "GET", f"{BASE_URL}/api/v4/extract-results/batch/{urllib.parse.quote(str(batch_id), safe='')}", token, None, http_timeout, deadline)
            results = polled.get("extract_result")
            if not isinstance(results, list):
                raise MinerUError("MinerU returned invalid result array")
            by_id: dict[str, Any] = {}
            for result in results:
                if (not isinstance(result, dict) or result.get("data_id") not in batch_ids
                        or result["data_id"] in by_id):
                    raise MinerUError("MinerU returned unknown or duplicate result ID")
                if result.get("state") not in {"waiting-file", "pending", "running", "converting", "done", "failed"}:
                    raise MinerUError("MinerU returned an unknown extraction state")
                by_id[result["data_id"]] = result
            if set(by_id) == set(batch_ids) and all(item["state"] in {"done", "failed"} for item in by_id.values()):
                break
            _sleep(poll_interval, deadline)
        failed = []
        for data_id in batch_ids:
            if _complete(files[data_id], output_root):
                continue
            pdf = requested[data_id]
            result = by_id[data_id]
            if result.get("state") != "done" or not result.get("full_zip_url"):
                files[data_id]["status"] = "failed"
                failed.append(data_id)
                _atomic_json(state_path, state)
                continue
            zip_bytes = _download(transport, _https_url(result["full_zip_url"]), deadline, http_timeout)
            raw_zip = _raw_target(output_root, data_id)
            _atomic_bytes(raw_zip, zip_bytes)
            files[data_id]["download_sha256"] = sha256_file(raw_zip)
            _atomic_json(state_path, state)
            _install_zip(pdf, raw_zip, data_id, output_root, files[data_id], state)
        if failed:
            raise MinerUError(f"MinerU failed {len(failed)} file(s); successful files remain resumable")
    if any(not _complete(files[data_id], output_root) for data_id in requested):
        raise MinerUError("not all PDF results are complete")
    completed = {data_id: {"extraction": str(output_root / "files" / data_id / "extraction.json"),
                          "sha256": files[data_id]["sha256_extraction"]} for data_id in requested}
    return {"mode": "execute", "manifest": build_manifest(
                pdfs, data_root, output_root, completed, source_verified=source_verified),
            "state": state_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline-first MinerU PDF batch conversion")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/mineru"))
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--source-verified", action="store_true",
                        help="record explicit user attestation of source verification")
    parser.add_argument("--dry-run", action="store_true", help="list planned IDs without network")
    parser.add_argument("--poll-interval", type=float, default=15.0)
    parser.add_argument("--deadline", type=float, default=1800.0)
    parser.add_argument("--http-timeout", type=float, default=60.0)
    args = parser.parse_args(argv)
    if args.execute and args.dry_run or args.dry_run and args.results_dir:
        parser.error("--dry-run cannot be combined with --execute or --results-dir")
    try:
        result = run(args.data_dir, args.output_dir, execute=args.execute and not args.dry_run,
                     poll_interval=args.poll_interval, deadline_seconds=args.deadline,
                     http_timeout=args.http_timeout, results_dir=args.results_dir,
                     source_verified=args.source_verified)
        print(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in result.items()}, ensure_ascii=False))
        return 0
    except MinerUError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        print(f"[FAIL] Invalid local PDF/result artifact ({type(error).__name__})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
