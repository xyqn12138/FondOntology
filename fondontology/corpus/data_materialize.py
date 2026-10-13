"""Offline restoration from explicit recovery manifests and conversion state."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .data_catalog import _FIELDS, _path, _receipt_url, _receipt_value, _url_equivalent, build_catalog_records
from .data_text import CHUNKER_VERSION, catalog_body_sections
from .pdf_extraction import load_extraction_json, parse_extraction, pdf_page_count


VERSION = "data-restoration-v1"
DEFAULT_SOURCES = (
    "_recovery/l0-l3-sources.json", "_recovery/l1-sources.json", "_recovery/l2-sources.json",
    "_recovery/l1-stock-connect-2022-sources.json",
)
DEFAULT_STATES = ("_converted/L1/state.json", "_converted/L2/state.json", "_converted/L3/state.json")
_BLOCK_TAGS = {"p", "div", "section", "article", "li", "ul", "ol", "h1", "h2", "h3",
               "h4", "h5", "h6", "br", "hr", "blockquote"}
_ARTICLE = re.compile(r"(?m)^[ \t]*(?:#{1,6}[ \t]+)?第[一二三四五六七八九十百千零〇0-9]+条[ \t\u3000]+(?=\S)")
_JOINED_ARTICLE = re.compile(r"(?m)^([ \t]*(?:#{1,6}[ \t]+)?第[一二三四五六七八九十百千零〇0-9]+条)(?=\S)")
_ISOLATED_ARTICLE = re.compile(
    r"(?m)^([ \t]*(?:#{1,6}[ \t]+)?第[一二三四五六七八九十百千零〇0-9]+条)"
    r"[ \t\u3000]*\r?\n(?:[ \t\u3000]*\r?\n)*[ \t\u3000]*"
    r"(?=(?!第[一二三四五六七八九十百千零〇0-9]+[条章节])\S)"
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _read_json(path: Path) -> object:
    return load_extraction_json(path.read_bytes())


def _documents(payload: object) -> list[dict]:
    documents = payload.get("documents") if isinstance(payload, dict) else payload
    if not isinstance(documents, list) or any(not isinstance(item, dict) for item in documents):
        raise ValueError("Recovery manifests require a documents array or a document array envelope")
    return documents


def _html_body(raw: bytes, selector: object, title_selector: object = None) -> tuple[str, dict]:
    try:
        from bs4 import BeautifulSoup, Comment, Declaration, Doctype, NavigableString, ProcessingInstruction
    except ImportError as error:
        raise ValueError("HTML restoration requires the existing beautifulsoup4 dependency") from error
    if not isinstance(selector, str) or not selector.strip():
        raise ValueError("HTML source requires an explicit body_selector")
    soup = BeautifulSoup(raw, "html.parser")
    matches = soup.select(selector)
    if len(matches) != 1:
        raise ValueError("HTML body_selector must match exactly one body")
    body = matches[0]
    title = None
    if title_selector is not None:
        if not isinstance(title_selector, str) or not title_selector.strip():
            raise ValueError("HTML title_selector must be nonempty text")
        titles = soup.select(title_selector)
        if len(titles) != 1:
            raise ValueError("HTML title_selector must match exactly one title")
        title = titles[0]
    for node in body.select("script,style,noscript,template"):
        node.decompose()
    for node in soup.find_all(string=lambda value: isinstance(
            value, (Comment, Declaration, Doctype, ProcessingInstruction))):
        node.extract()
    images = [node.get("src", "") for node in body.select("img")]
    tables = len(body.select("table"))

    def render(node) -> str:
        if isinstance(node, (Comment, Declaration, Doctype, ProcessingInstruction)):
            return ""
        if isinstance(node, NavigableString):
            return re.sub(r"\s+", " ", str(node).replace("\x00", ""))
        if node.name == "table":
            return "\n" + str(node) + "\n"
        if node.name == "img":
            return "\n" + str(node) + "\n"
        content = "".join(render(child) for child in node.children)
        return "\n" + content + "\n" if node.name in _BLOCK_TAGS else content

    text = "\n".join(line.strip() for line in render(body).splitlines() if line.strip()) + "\n"
    selected_title = None
    if title is not None:
        selected_title = " ".join(render(title).split())
        if not selected_title:
            raise ValueError("HTML title_selector matched an empty title")
        text = selected_title + "\n" + text
    unsupported = [{"kind": "html_table", "count": tables}] if tables else []
    if images:
        unsupported.append({"kind": "html_image_content_unreviewed", "count": len(images)})
    observations = {"body_selector": selector, "table_count": tables,
                    "image_references": images, "missing_images": images, "unsupported": unsupported}
    if title_selector is not None:
        observations.update({"title_selector": title_selector, "selected_title": selected_title})
    return text, observations


def _csrc_body(raw: bytes) -> tuple[str, dict]:
    payload = load_extraction_json(raw)
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError("Official body API must declare success")
    lawlist = payload.get("lawlist")
    if not isinstance(lawlist, dict) or not isinstance(lawlist.get("lawEntryVOs"), list):
        raise ValueError("Official body API requires lawlist.lawEntryVOs")
    law = lawlist.get("law")
    if not isinstance(law, dict):
        raise ValueError("Official body API requires a law identity object")
    parts = [law["secFutrsLawName"]]
    articles = 0
    ignored = 0

    def content(entry: dict) -> str:
        value = entry.get("cntnt") or ""
        nested = entry.get("itemList") or []
        if not isinstance(value, str) or not isinstance(nested, list):
            raise ValueError("Official body API has unsupported article structure")
        return "\n".join([value, *(content(item) for item in nested)]).strip()

    for entry in lawlist["lawEntryVOs"]:
        if entry.get("lawEntryStsCde") != "0" or not entry.get("title"):
            ignored += 1
            continue
        classification = entry.get("secFutrsLawEntryClsfCde")
        title = entry["title"]
        if classification == "4":
            title = re.sub(r"^(第[一二三四五六七八九十百千零〇0-9]+条)(?=\S)", r"\1 ", title)
            parts.append(title + " " + content(entry))
            articles += 1
        elif classification in {"2", "3"}:
            parts.append(title + " " + content(entry))
        elif content(entry):
            raise ValueError("Official body API has unknown substantive entry type")
    return "\n\n".join(parts) + "\n", {
        "api_law_version": law.get("secFutrsLawVersion"),
        "api_law_name": law.get("secFutrsLawName"),
        "active_article_count": articles, "ignored_inactive_or_empty_records": ignored,
        "annotations_policy": "annoList excludes editorial annotations; itemList preserves operative paragraphs",
        "missing_images": [], "unsupported": [],
    }


def _mineru_index(root: Path, state_paths: list[str]) -> dict[Path, tuple[Path, dict]]:
    result = {}
    for relative in state_paths:
        state_path = _path(root, relative, "MinerU state")
        state = _read_json(state_path)
        if not isinstance(state, dict) or not isinstance(state.get("files"), dict):
            raise ValueError("MinerU state requires files object")
        state_root = Path(state["data_root"]).resolve()
        if not state_root.is_relative_to(root):
            raise ValueError("MinerU data_root escapes data")
        for data_id, entry in state["files"].items():
            source = _path(state_root, entry["pdf"], "MinerU pdf")
            if entry.get("status") == "completed":
                output = _path(state_path.parent, "files/" + data_id, "MinerU output")
                if source in result:
                    raise ValueError("Multiple completed conversions for one source require explicit review")
                result[source] = (output, entry)
    return result


def _pdf_body(raw: bytes, raw_path: Path, conversion: tuple[Path, dict]) -> tuple[str, dict, dict[Path, bytes]]:
    directory, entry = conversion
    checksum = _sha(raw)
    if entry.get("sha256") != checksum:
        raise ValueError("MinerU state source hash mismatch")
    extraction_path = directory / "extraction.json"
    raw_extraction = extraction_path.read_bytes()
    if _sha(raw_extraction) != entry.get("sha256_extraction"):
        raise ValueError("MinerU extraction hash differs from completed state")
    artifact = load_extraction_json(raw_extraction)
    pages = pdf_page_count(raw)
    parsed = parse_extraction(artifact, source_sha256=checksum, page_count=pages)
    markdown = artifact["markdown"]
    full_path = directory / "full.md"
    full_raw = full_path.read_bytes()
    if full_raw.decode("utf-8") != markdown:
        raise ValueError("MinerU Markdown differs from bound extraction")
    recorded = entry.get("artifacts", {})
    if recorded.get("full.md") != _sha(full_raw):
        raise ValueError("MinerU full.md hash differs from completed state")
    coverage = sorted({block["page_idx"] + 1 for block in artifact["content_list"]})
    unsupported = [*parsed["unindexed_blocks"]]
    empty_text_blocks = [block for block in unsupported if block.get("reason") == "empty_text"]
    unsupported = [block for block in unsupported if block not in empty_text_blocks]
    merged_placeholders = [
        block for block in unsupported if block.get("reason") == "missing_table_body_placeholder"]
    accepted_merge_blocks = []
    if merged_placeholders:
        accepted_merge_blocks = [
            block for block in unsupported
            if block.get("reason") in {"missing_table_body_placeholder", "empty_text"}]
        unsupported = [block for block in unsupported if block not in accepted_merge_blocks]
    for ordinal, block in enumerate(artifact["content_list"]):
        if block["type"] in {"image", "chart"}:
            unsupported.append({"kind": "visual_or_formula_requires_review", "block": ordinal,
                                "type": block["type"], "page": block["page_idx"] + 1})
    references = re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", markdown)
    references += re.findall(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", markdown, flags=re.I)
    review_blocks = {block.get("block_index", block.get("block")) for block in unsupported}
    omitted_images = []
    for ordinal, block in enumerate(artifact["content_list"]):
        reference = block.get("img_path")
        if not reference:
            continue
        recognized_equation = block["type"] == "equation" and bool(block.get("text", "").strip())
        if reference in references or (ordinal in review_blocks and not recognized_equation):
            references.append(reference)
        else:
            omitted_images.append({"path": reference, "block_index": ordinal,
                                   "page": block["page_idx"] + 1, "type": block["type"],
                                   "reason": "structured_body_available"})
    assets = {}
    missing = []
    for reference in sorted(set(references)):
        decoded = unquote(reference).replace("\\", "/").split("#", 1)[0]
        if urlsplit(decoded).scheme or decoded.startswith("/"):
            missing.append(reference)
            continue
        image_path = _path(directory, decoded, "MinerU image")
        if not image_path.is_file():
            missing.append(reference)
            continue
        asset_bytes = image_path.read_bytes()
        relative = image_path.relative_to(directory)
        if recorded.get(relative.as_posix()) != _sha(asset_bytes):
            raise ValueError("MinerU image hash differs from completed state")
        assets[relative] = asset_bytes
    observations = {
        "page_count": pages, "page_coverage": coverage, "missing_images": missing,
        "unsupported": unsupported, "extraction_sha256": _sha(raw_extraction),
        "extraction_path": str(extraction_path), "page_scope": "mineru_reported_pages_unreviewed",
        "raw_pdf_path": str(raw_path), "extractor_model_version": artifact["extractor"]["model_version"],
        "retained_image_paths": sorted(relative.as_posix() for relative in assets),
        "omitted_recognition_images": omitted_images,
        "ignored_empty_text_blocks": empty_text_blocks,
        "pdf_acceptance_scope": "machine_structure_source_and_coverage_checks_not_verbatim_human_review",
    }
    if accepted_merge_blocks:
        observations["merged_table_acceptance"] = {
            "policy": "user-authorized-mineru-cross-page-merge-v1",
            "basis": "用户授权跨页表格合并占位不阻断ready；空文本占位一并忽略，其他图像、公式及实质空表问题继续阻断。",
            "accepted_blocks": accepted_merge_blocks,
        }
    return markdown, observations, assets


def _identity_matches(source: dict, text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    markers = source.get("source_identity_evidence", {}).get("identity_markers")
    if not markers:
        title = re.sub(r"[（(].*?[）)]", "", source.get("title", ""))
        markers = [title]
    return bool(markers) and all(re.sub(r"\s+", "", marker) in compact for marker in markers)


def _word_body(root: Path, word: dict, source: dict) -> tuple[str, dict, dict[Path, bytes]]:
    if word.get("source_sha256") != source["raw_sha256"]:
        raise ValueError("Word conversion source hash mismatch")
    word_path = _path(root, word["markdown_path"], "Word markdown_path")
    markdown_raw = word_path.read_bytes()
    observations = dict(word["observations"])
    if observations.get("markdown_sha256") != _sha(markdown_raw):
        raise ValueError("Word Markdown hash differs from conversion observations")
    text = markdown_raw.decode("utf-8")
    references = re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", text)
    references += re.findall(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", text, flags=re.I)
    recorded = observations.get("image_assets", {})
    assets = {}
    missing = list(observations.get("missing_images", []))
    for reference in sorted(set(references)):
        decoded = unquote(reference).replace("\\", "/").split("#", 1)[0]
        if urlsplit(decoded).scheme or decoded.startswith("/"):
            missing.append(reference)
            continue
        image_path = _path(word_path.parent, decoded, "Word image")
        if not image_path.is_file():
            missing.append(reference)
            continue
        image_raw = image_path.read_bytes()
        relative = image_path.relative_to(word_path.parent)
        if recorded.get(relative.as_posix()) != _sha(image_raw):
            raise ValueError("Word image hash differs from conversion observations")
        assets[relative] = image_raw
    observations["missing_images"] = sorted(set(missing))
    observations["word_converter_version"] = word["version"]
    return text, observations, assets


def _remove_title_headers(source: dict, text: str) -> tuple[str, list[str]]:
    first_article = _ARTICLE.search(text)
    if not first_article:
        return text, []
    title = source.get("title", "")
    titles = {re.sub(r"\s+", "", candidate)
              for candidate in (title, re.sub(r"[（(].*?[）)]", "", title))}
    prefix = text[:first_article.start()]
    removed = []
    preserved = []
    for line in prefix.splitlines(keepends=True):
        candidate = re.sub(r"^#{1,6}\s+", "", line.strip())
        if re.sub(r"\s+", "", candidate) in titles:
            removed.append(line.strip())
        else:
            preserved.append(line)
    return "".join(preserved) + text[first_article.start():], removed


def materialize_data(root: Path | str = "data", *, source_paths: list[str] | None = None,
                     state_paths: list[str] | None = None, write: bool = False) -> dict:
    """Produce a catalog and immutable full-text artifacts without replacing summaries."""
    root = Path(root).resolve()
    inputs = source_paths if source_paths is not None else list(DEFAULT_SOURCES)
    sources = []
    for relative in inputs:
        sources.extend(_documents(_read_json(_path(root, relative, "recovery manifest"))))
    index = _mineru_index(root, state_paths if state_paths is not None else list(DEFAULT_STATES))
    words = {}
    word_manifest = root / "_recovery" / "word-conversions.json"
    if word_manifest.is_file():
        words = {item["id"]: item for item in _documents(_read_json(word_manifest))}
    reviews = {}
    for name in ("fulltext-reviews.json", "source-page-reviews.json"):
        review_manifest = root / "_recovery" / name
        if review_manifest.is_file():
            for item in _documents(_read_json(review_manifest)):
                reviews[item["id"]] = {**reviews.get(item["id"], {}), **item}
    documents = []
    outputs = {}
    seen = set()
    for source in sources:
        source = {**source, **reviews.get(source.get("id"), {})}
        document_id = source.get("id")
        if (not isinstance(document_id, str) or ".." in document_id
                or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,120}", document_id)):
            raise ValueError("Recovery source ID must be a safe stable ID")
        if document_id in seen:
            raise ValueError(f"Duplicate recovery source ID: {document_id}")
        seen.add(document_id)
        document = {key: source.get(key) for key in _FIELDS if key not in {"verification"}}
        document.update({"markdown_path": None, "markdown_sha256": None, "status": "unresolved"})
        verification = {"identity": "not_checked", "completeness": "not_checked", "evidence": [],
                        "article_count": None, "page_count": None}
        document["verification"] = verification
        documents.append(document)
        raw_relative = source.get("raw_path")
        if not raw_relative:
            document["failure_reason"] = source.get("failure_reason") or "Official original not acquired"
            continue
        raw_path = _path(root, raw_relative, "raw_path")
        raw = raw_path.read_bytes()
        if _sha(raw) != source.get("raw_sha256"):
            raise ValueError(f"Recovery source hash mismatch: {document_id}")
        source_page_review = source.get("source_page_review")
        if source_page_review:
            page_raw = _path(root, source_page_review["path"], "reviewed source page").read_bytes()
            if (source_page_review["source_sha256"] != source["raw_sha256"]
                    or _sha(page_raw) != source_page_review["sha256"]):
                raise ValueError(f"Reviewed source page binding mismatch: {document_id}")
        document["status"] = "downloaded"
        receipt_relative = source.get("receipt_path") or (Path(raw_relative).parent / "receipt.json").as_posix()
        receipt_path = _path(root, receipt_relative, "receipt_path")
        if receipt_path.is_file():
            verification["acquisition"] = {"receipt_path": receipt_relative,
                                           "receipt_sha256": _sha(receipt_path.read_bytes())}
        try:
            assets = {}
            original_format = source["format"]
            if original_format == "html":
                text, observations = _html_body(raw, source.get("body_selector"), source.get("title_selector"))
                method = "selected-html-body"
            elif original_format == "json":
                text, observations = _csrc_body(raw)
                method = "official-structured-body-json"
            elif original_format == "pdf":
                if raw_path not in index:
                    raise ValueError("No completed MinerU conversion bound to this source")
                text, observations, assets = _pdf_body(raw, raw_path, index[raw_path])
                if source.get("conversion_issues"):
                    observations["unsupported"].extend(source["conversion_issues"])
                review = source.get("pdf_fidelity_review")
                if review:
                    if (not isinstance(review, dict)
                            or review.get("source_sha256") != source["raw_sha256"]
                            or review.get("markdown_sha256") != _sha(text.encode("utf-8"))
                            or not isinstance(review.get("basis"), str) or not review["basis"].strip()
                            or not isinstance(review.get("accepted_blocks"), list)):
                        raise ValueError("PDF fidelity review must bind source, Markdown and accepted blocks")
                    accepted = review["accepted_blocks"]
                    available = observations["unsupported"] + observations.get(
                        "merged_table_acceptance", {}).get("accepted_blocks", []) + observations.get(
                        "ignored_empty_text_blocks", [])
                    if any(block not in available for block in accepted):
                        raise ValueError("PDF fidelity review accepted blocks differ from extraction")
                    observations["unsupported"] = [
                        block for block in observations["unsupported"] if block not in accepted]
                    observations["pdf_fidelity_review"] = review
                method = "mineru-bound-content-list"
            elif original_format in {"doc", "docx"}:
                word = words.get(document_id)
                if not word:
                    raise ValueError("No source-bound Word conversion observation manifest")
                text, observations, assets = _word_body(root, word, source)
                method = word["method"]
            else:
                raise ValueError("Unsupported source format requires a reviewed conversion adapter")
            correction = source.get("reviewed_conversion")
            if correction:
                if (correction.get("source_sha256") != source["raw_sha256"]
                        or correction.get("input_markdown_sha256") != _sha(text.encode("utf-8"))
                        or not isinstance(correction.get("basis"), str) or not correction["basis"].strip()):
                    raise ValueError("Reviewed conversion must bind source and original conversion")
                for replacement in correction["replacements"]:
                    old = replacement.get("old")
                    if "block_index" in replacement:
                        extraction = _read_json(Path(observations["extraction_path"]))
                        old = extraction["content_list"][replacement["block_index"]]["text"]
                    if (not isinstance(old, str) or not old
                            or not isinstance(replacement.get("new"), str)
                            or text.count(old) != 1):
                        raise ValueError("Reviewed conversion replacement must match once")
                    text = text.replace(old, replacement["new"], 1)
                if _sha(text.encode("utf-8")) != correction.get("markdown_sha256"):
                    raise ValueError("Reviewed conversion Markdown hash mismatch")
                observations["reviewed_conversion"] = correction
            fulltext_review = source.get("fulltext_review")
            if fulltext_review:
                if (not isinstance(fulltext_review, dict)
                        or fulltext_review.get("source_sha256") != source["raw_sha256"]
                        or fulltext_review.get("markdown_sha256") != _sha(text.encode("utf-8"))
                        or fulltext_review.get("reviewer") not in {"human_user", "independent_model"}
                        or not isinstance(fulltext_review.get("basis"), str)
                        or not fulltext_review["basis"].strip()
                        or not isinstance(fulltext_review.get("accepted_blocks"), list)):
                    raise ValueError("Full-text review must bind source, Markdown, reviewer and accepted blocks")
                accepted = fulltext_review["accepted_blocks"]
                if any(block not in observations["unsupported"] for block in accepted):
                    raise ValueError("Full-text review accepted blocks differ from conversion")
                observations["unsupported"] = [
                    block for block in observations["unsupported"] if block not in accepted]
                accepted_images = fulltext_review.get("accepted_image_references", [])
                if any(image not in observations["missing_images"] for image in accepted_images):
                    raise ValueError("Full-text review accepted image references differ from conversion")
                observations["missing_images"] = [
                    image for image in observations["missing_images"] if image not in accepted_images]
                observations["fulltext_review"] = fulltext_review
            if not text.strip():
                raise ValueError("Converted full text is empty")
            identity_matches = _identity_matches(source, text)
            text, normalized_headings = _JOINED_ARTICLE.subn(r"\1 ", text)
            if normalized_headings:
                observations["article_heading_separator_insertions"] = normalized_headings
            text, joined_headings = _ISOLATED_ARTICLE.subn(r"\1 ", text)
            if joined_headings:
                observations["isolated_article_heading_line_joins"] = joined_headings
            text, removed_titles = _remove_title_headers(source, text)
            observations["excluded_title_headers"] = removed_titles
            page_count = observations.get("page_count")
            observations.update({"original_format": original_format, "page_count": page_count})
            observations.setdefault("page_coverage", [])
            observations.setdefault("missing_images", [])
            observations.setdefault("unsupported", [])
            article_count = None
            body_start = 1
            lines = text.splitlines()
            if lines and re.sub(r"^#{1,6}\s+", "", lines[0].strip()) == source.get("title"):
                body_start = 2
                while body_start <= len(lines) and not lines[body_start - 1].strip():
                    body_start += 1
            structural_error = None
            expected = source.get("expected_articles")
            if expected is not None:
                try:
                    config = {"strategy": CHUNKER_VERSION, "body_start_line": body_start,
                              "expected_articles": expected, "max_chars": 800, "overlap": 0}
                    sections = catalog_body_sections(text, config)
                    article_count = sum("article_number" in item for item in sections)
                    document["expected_articles"] = expected
                except ValueError as error:
                    structural_error = str(error)
            observations["article_count"] = article_count
            markdown_raw = text.encode("utf-8")
            directory = Path("_fulltext") / document_id / source["raw_sha256"][:12] / _sha(markdown_raw)[:12]
            markdown_relative = (directory / "full.md").as_posix()
            outputs[_path(root, markdown_relative, "generated Markdown")] = markdown_raw
            for relative, value in assets.items():
                outputs[_path(root, (directory / relative).as_posix(), "generated asset")] = value
            document.update({"markdown_path": markdown_relative, "markdown_sha256": _sha(markdown_raw),
                             "status": "converted_unverified"})
            conversion = {
                "schema_version": 1, "raw_path": raw_relative, "source_sha256": source["raw_sha256"],
                "markdown_path": markdown_relative, "markdown_sha256": _sha(markdown_raw),
                "method": method, "version": VERSION, "observations": observations,
                "identity_review": {"scope": "machine_conversion_and_structure_only", "human_reviewed": False},
            }
            record_raw = _json_bytes(conversion)
            record_relative = (directory / "conversions" / (_sha(record_raw) + ".json")).as_posix()
            outputs[_path(root, record_relative, "conversion record")] = record_raw
            verification.update({
                "identity": "verified" if identity_matches else "not_checked",
                "completeness": "complete" if not structural_error and not observations["unsupported"]
                and not observations["missing_images"] else "not_checked",
                "evidence": [source.get("version_basis") or "Explicit source recovery manifest",
                             "Bound machine conversion record; not human legal review"],
                "article_count": article_count, "page_count": page_count, "body_start_line": body_start,
                "conversion": {"record_path": record_relative, "record_sha256": _sha(record_raw)},
            })
            reasons = []
            if source_page_review:
                verification["evidence"].append(source_page_review)
            if observations.get("fulltext_review"):
                verification["evidence"].append(observations["fulltext_review"])
            if observations.get("merged_table_acceptance"):
                verification["evidence"].append(observations["merged_table_acceptance"])
            if observations.get("pdf_fidelity_review"):
                verification["evidence"].append({
                    "kind": "source_bound_pdf_fidelity_acceptance",
                    "basis": observations["pdf_fidelity_review"]["basis"],
                })
            if structural_error:
                reasons.append("Article structure check failed: " + structural_error)
            if verification["identity"] != "verified":
                reasons.append("Full text identity markers did not match recovered source identity")
            if not source.get("issued_date"):
                reasons.append("Source version issue date not independently established")
            if not source.get("source_page_url"):
                reasons.append("Source publication page not independently established")
            if observations["unsupported"] or observations["missing_images"]:
                reasons.append("Conversion contains unsupported or unreviewed visual/formula content")
            if source["origin_kind"] == "secondary":
                reasons.append("Secondary source cannot be authoritative")
            if original_format == "pdf":
                verification["evidence"].append({
                    "kind": "pdf_machine_acceptance_scope",
                    "scope": observations["pdf_acceptance_scope"],
                })
            if original_format in {"doc", "docx"} and not observations.get("fulltext_review"):
                reasons.append("Word full-text fidelity has not been independently verified")
                verification["completeness"] = "not_checked"
            if document_id == "amac-manager-registration-notice-2018":
                reasons.append("Historical registration notice repealed on 2023-05-01")
                verification["evidence"].append({
                    "status": "repealed", "repealed_on": "2023-05-01",
                    "source_document_id": "amac-private-fund-registration-2023",
                    "source_article": "第八十三条",
                    "basis": "《私募投资基金登记备案办法》自2023年5月1日起施行，登记须知同时废止。",
                })
            if source.get("failure_reason"):
                reasons.append(source["failure_reason"])
            if not reasons and verification.get("acquisition"):
                receipt = _read_json(receipt_path)
                byte_count = _receipt_value(receipt, ("bytes", "byte_count"))
                status = _receipt_value(receipt, ("http_status", "status_code"))
                if (not _url_equivalent(_receipt_url(receipt), source["download_url"])
                        or not _url_equivalent(receipt.get("final_url"), source["download_url"])
                        or _receipt_value(receipt, ("raw_sha256", "sha256")) != source["raw_sha256"]
                        or type(byte_count) is not int or byte_count != len(raw)
                        or type(status) is not int or status != 200):
                    reasons.append("Acquisition receipt differs from catalog source")
            elif not verification.get("acquisition"):
                reasons.append("Missing acquisition receipt")
            document["failure_reason"] = "; ".join(reasons) if reasons else None
            if not reasons:
                document["status"] = "ready"
        except (OSError, ValueError, KeyError, TypeError) as error:
            document["failure_reason"] = f"Offline materialization unavailable: {error}"
    payload = {"schema_version": 1, "documents": documents}
    if write:
        for path, raw in outputs.items():
            if path.is_file() and path.read_bytes() != raw:
                raise ValueError(f"Immutable generated full-text artifact changed: {path}")
        for path, raw in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(raw)
        catalog = root / "source_catalog.json"
        with tempfile.NamedTemporaryFile(dir=root, suffix=".catalog.json", delete=False) as staged:
            staged.write(_json_bytes(payload))
            staged_path = Path(staged.name)
        try:
            build_catalog_records(staged_path, data_root=root)
            staged_path.replace(catalog)
        finally:
            if staged_path.exists():
                staged_path.unlink()
    counts = {status: sum(document["status"] == status for document in documents)
              for status in ("ready", "converted_unverified", "downloaded", "unresolved")}
    return {"schema_version": 1, "write": write, "counts": counts, "documents": documents,
            "generated_files": len(outputs)}
