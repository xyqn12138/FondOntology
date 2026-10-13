"""Acquire explicitly selected originals; downloading does not certify legal validity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.corpus.markdown_inventory import inventory_markdown


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def local_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("Output must remain within the data directory")
    return path


def fetch(url: str) -> requests.Response:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("Source downloads require a public HTTPS URL")
    with requests.get(
        url, timeout=(15, 60), stream=True,
        headers={"User-Agent": "Mozilla/5.0 FondOntology-SourceAudit/1.0"},
    ) as response:
        response.raise_for_status()
        if urlsplit(response.url).scheme != "https":
            raise ValueError("Refused HTTPS downgrade")
        chunks = []
        size = 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 100_000_000:
                raise ValueError("Oversized original")
            chunks.append(chunk)
        if not size:
            raise ValueError("Empty original")
        response._content = b"".join(chunks)
    return response


def decode_html(response: requests.Response) -> str:
    raw = response.content
    encoding = re.search(br'<meta[^>]+charset\s*=\s*["\']?([\w-]+)', raw[:4096], re.I)
    if encoding:
        return raw.decode(encoding.group(1).decode(), errors="strict")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        detected = (response.apparent_encoding or "").lower()
        if detected not in {"gb2312", "gbk", "gb18030"}:
            raise
        return raw.decode(detected, errors="strict")


def attachments(response: requests.Response) -> list[dict]:
    soup = BeautifulSoup(decode_html(response), "html.parser")
    found = {}
    for anchor in soup.select("a[href]"):
        href = anchor["href"]
        if any(extension in urlsplit(href).path.lower() for extension in (".pdf", ".docx", ".doc")):
            url = urljoin(response.url, href).replace("http://", "https://", 1)
            found[url] = {"text": anchor.get_text(" ", strip=True), "url": url}
    return list(found.values())


def discover(root: Path, prefix: str) -> dict:
    documents = []
    for record in inventory_markdown(root)["records"]:
        if not record["path"].replace("\\", "/").startswith(prefix):
            continue
        urls = [item["url"] for item in record["source_candidates"]]
        identifier = "l1-" + digest(record["path"].replace("\\", "/").encode())[:12]
        document = {
            "id": identifier, "legacy_path": record["path"].replace("\\", "/"),
            "title": record["title"], "publisher": record["metadata"].get("发布机关"),
            "legacy_metadata": record["metadata"], "seed_urls": urls,
            "source_page_url": None, "download_url": None, "format": None,
            "origin_kind": "issuer_original", "issued_date": None, "effective_from": None,
            "expected_articles": None, "body_selector": None,
            "version_basis": "Not yet checked against downloaded original",
            "status": "unresolved", "failure_reason": None,
        }
        if not urls:
            document["failure_reason"] = "No declared source URL"
        else:
            try:
                response = fetch(urls[0].replace("http://", "https://", 1))
                document["seed_response_url"] = response.url
                if response.content.startswith(b"%PDF"):
                    document.update(download_url=response.url, format="pdf")
                else:
                    document["source_page_url"] = response.url
                    soup = BeautifulSoup(decode_html(response), "html.parser")
                    document["page_title"] = soup.title.get_text(strip=True) if soup.title else None
                    document["attachments"] = attachments(response)
            except (OSError, ValueError, requests.RequestException) as error:
                document["failure_reason"] = str(error)
        documents.append(document)
    return {"schema_version": 1, "documents": documents}


def acquire(document: dict, root: Path, group: str) -> dict:
    document = dict(document)
    try:
        identifier = document["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,90}", identifier):
            raise ValueError("Invalid document id")
        response = fetch(document["download_url"])
        format_name = document["format"]
        raw = response.content
        if format_name == "pdf" and not raw.startswith(b"%PDF"):
            raise ValueError("PDF URL returned a non-PDF response")
        if format_name == "docx" and not raw.startswith(b"PK"):
            raise ValueError("DOCX URL returned a non-ZIP response")
        if format_name == "html":
            decode_html(response)
        if format_name not in {"pdf", "docx", "doc", "html"}:
            raise ValueError("Unsupported original format")
        directory = local_path(root, f"_sources/{group}/{identifier}")
        directory.mkdir(parents=True, exist_ok=True)
        raw_path = directory / f"original.{format_name}"
        raw_path.write_bytes(raw)
        receipt = {
            "schema_version": 1, "id": identifier,
            "requested_url": document["download_url"], "final_url": response.url,
            "redirects": [item.url for item in response.history],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status_code": response.status_code, "content_type": response.headers.get("Content-Type"),
            "bytes": len(raw), "raw_sha256": digest(raw),
            "tls_policy": "default_certificate_verification",
            "identity_basis": document["version_basis"],
            "legal_validity": "not_checked_current",
        }
        if document.get("source_page_url") and document["source_page_url"] != response.url:
            page = fetch(document["source_page_url"])
            page_path = directory / "source-page.html"
            page_path.write_bytes(page.content)
            receipt["source_page"] = {
                "requested_url": document["source_page_url"], "final_url": page.url,
                "raw_path": page_path.relative_to(root).as_posix(),
                "sha256": digest(page.content), "bytes": len(page.content),
            }
        receipt_path = directory / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        document.update(
            raw_path=raw_path.relative_to(root).as_posix(), raw_sha256=digest(raw),
            receipt_path=receipt_path.relative_to(root).as_posix(),
            download_url=response.url, status="downloaded", failure_reason=None,
        )
        (directory / "selection.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    except (OSError, KeyError, TypeError, ValueError, requests.RequestException) as error:
        document.update(status="unresolved", failure_reason=f"{type(error).__name__}: {error}")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data")
    parser.add_argument("--discover-prefix")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--group", default="L1")
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.out.resolve().is_relative_to(root / "_recovery"):
        parser.error("--out must be under data/_recovery")
    if not re.fullmatch(r"L[0-3]", args.group):
        parser.error("--group must be L0..L3")
    if args.discover_prefix:
        result = discover(root, args.discover_prefix)
    elif args.plan:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        with ThreadPoolExecutor(max_workers=5) as pool:
            documents = list(pool.map(lambda item: acquire(item, root, args.group), plan["documents"]))
        result = {"schema_version": 1, "documents": documents}
    else:
        parser.error("Specify --discover-prefix or --plan")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "documents": len(result["documents"]),
        "downloaded": sum(item["status"] == "downloaded" for item in result["documents"]),
        "report": str(args.out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
