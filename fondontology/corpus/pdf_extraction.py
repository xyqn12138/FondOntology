"""Strict, offline MinerU v1 extraction artifacts for PDF evidence."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
from pathlib import Path


EXTRACTOR_VERSION = "mineru-content-list-v1"
TEXT_BASIS = "mineru-content-list-v1-normalized"


class PDFExtractionError(ValueError):
    """A PDF or extraction artifact cannot be validated safely."""


def load_extraction_json(source: str | bytes) -> object:
    """Reject nonstandard constants and duplicate keys before artifact validation."""
    def reject_constant(value: str):
        raise PDFExtractionError(f"Nonstandard JSON constant: {value}")

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise PDFExtractionError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(source, parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PDFExtractionError(f"Invalid UTF-8 extraction JSON: {error}") from error


def pdf_page_count(source: bytes) -> int:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise PDFExtractionError("PDF validation requires the installed pypdf package") from error
    try:
        reader = PdfReader(io.BytesIO(source), strict=True)
        if reader.is_encrypted:
            raise PDFExtractionError("Encrypted PDF input is not supported")
        count = len(reader.pages)
    except PDFExtractionError:
        raise
    except Exception as error:
        raise PDFExtractionError(f"Cannot validate PDF pages: {error}") from error
    if count < 1:
        raise PDFExtractionError("PDF contains no pages")
    return count


def _fields(value: dict, allowed: set[str], required: set[str], label: str) -> None:
    if set(value) - allowed:
        raise PDFExtractionError(f"Unknown {label} fields: {sorted(set(value) - allowed)}")
    if required - set(value):
        raise PDFExtractionError(f"Missing {label} fields: {sorted(required - set(value))}")


def _strings(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value):
        raise PDFExtractionError(f"{label} must be a list of nonempty strings")
    if nonempty and not value:
        raise PDFExtractionError(f"{label} must not be empty")
    return value


def parse_extraction(artifact: dict, *, source_sha256: str, page_count: int) -> dict:
    """Validate every v1 block and derive reproducible, page-bounded text spans."""
    if not isinstance(artifact, dict):
        raise PDFExtractionError("Extraction artifact must be an object")
    fields = {"schema_version", "source_sha256", "page_count", "extractor",
              "markdown", "content_list"}
    _fields(artifact, fields, fields, "extraction")
    if type(artifact["schema_version"]) is not int or artifact["schema_version"] != 1:
        raise PDFExtractionError("Unsupported extraction schema_version")
    checksum = artifact["source_sha256"]
    if (not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum)
            or checksum != source_sha256):
        raise PDFExtractionError("Extraction source_sha256 mismatch or malformed hash")
    if type(artifact["page_count"]) is not int or artifact["page_count"] != page_count:
        raise PDFExtractionError("Extraction page_count differs from the original PDF")
    extractor = artifact["extractor"]
    if not isinstance(extractor, dict):
        raise PDFExtractionError("extractor must be an object")
    _fields(extractor, {"name", "version", "model_version"},
            {"name", "version", "model_version"}, "extractor")
    if extractor["name"] != "mineru" or extractor["version"] != EXTRACTOR_VERSION:
        raise PDFExtractionError("Unsupported extractor name/version")
    if not isinstance(extractor["model_version"], str) or not extractor["model_version"].strip():
        raise PDFExtractionError("extractor model_version must be a nonempty string")
    if not isinstance(artifact["markdown"], str) or not artifact["markdown"].strip():
        raise PDFExtractionError("Extraction markdown must be nonempty")
    content = artifact["content_list"]
    if not isinstance(content, list) or not content:
        raise PDFExtractionError("content_list must be a nonempty v1 array of objects")
    block_fields = {
        "text": {"text", "text_level"},
        "equation": {"text", "text_format", "img_path"},
        "table": {"img_path", "table_body", "table_caption", "table_footnote"},
        "image": {"img_path", "image_caption", "image_footnote"},
        "chart": {"img_path", "content", "chart_caption", "chart_footnote"},
        "list": {"list_items", "sub_type"},
        "discarded": {"text"},
        "header": {"text"},
        "footer": {"text"},
        "page_number": {"text"},
        "page_footnote": {"text"},
    }
    blocks = []
    unindexed_blocks = []
    text_parts = []
    position = 0
    previous_page = -1
    for index, block in enumerate(content):
        label = f"content_list block {index}"
        if not isinstance(block, dict):
            raise PDFExtractionError(f"{label} must be a v1 object, not a v2 page array")
        block_type = block.get("type")
        if not isinstance(block_type, str) or block_type not in block_fields:
            raise PDFExtractionError(f"Unsupported {label} type")
        _fields(block, {"type", "page_idx", "bbox"} | block_fields[block_type],
                {"type", "page_idx"}, label)
        page_index = block["page_idx"]
        if type(page_index) is not int or not 0 <= page_index < page_count:
            raise PDFExtractionError(f"{label} page_idx is outside the original PDF")
        if page_index < previous_page:
            raise PDFExtractionError("content_list pages must be in document order")
        previous_page = page_index
        bbox = block.get("bbox")
        if "bbox" in block:
            if (not isinstance(bbox, list) or len(bbox) != 4
                    or any(type(value) not in (int, float) or not math.isfinite(value)
                           or not 0 <= value <= 1000 for value in bbox)
                    or bbox[0] > bbox[2] or bbox[1] > bbox[3]):
                raise PDFExtractionError(f"{label} bbox must use ordered coordinates in 0..1000")
        if "img_path" in block and not isinstance(block["img_path"], str):
            raise PDFExtractionError(f"{label} img_path must be a string")
        for field in ("text_format", "sub_type"):
            if field in block and not isinstance(block[field], str):
                raise PDFExtractionError(f"{label} {field} must be a string")
        if "text_level" in block and (
                type(block["text_level"]) is not int or block["text_level"] < 0):
            raise PDFExtractionError(f"{label} text_level must be a nonnegative integer")
        if block_type in {"text", "equation", "discarded", "header", "footer",
                          "page_number", "page_footnote"}:
            text = block.get("text")
            if not isinstance(text, str):
                raise PDFExtractionError(f"{label} text must be a string")
            if text == "":
                if block_type in {"text", "equation"}:
                    unindexed_blocks.append({"block_index": index, "page": page_index + 1,
                                             "block_type": block_type,
                                             "reason": f"empty_{block_type}"})
                continue
            if not text.strip():
                raise PDFExtractionError(f"{label} text cannot be whitespace-only")
        elif block_type == "list":
            text = "\n".join(_strings(block.get("list_items"), f"{label} list_items", nonempty=True))
        elif block_type == "table":
            if "table_body" not in block:
                if (block.get("img_path") == ""
                        and all(isinstance(block.get(field), list)
                                and all(item == "" for item in block[field])
                                for field in ("table_caption", "table_footnote"))):
                    unindexed_blocks.append({
                        "block_index": index, "page": page_index + 1, "block_type": block_type,
                        "reason": "missing_table_body_placeholder",
                    })
                    continue
                raise PDFExtractionError(f"{label} table_body must be a string")
            body = block.get("table_body")
            if not isinstance(body, str):
                raise PDFExtractionError(f"{label} table_body must be a string")
            captions = _strings(block.get("table_caption", []), f"{label} table_caption")
            footnotes = _strings(block.get("table_footnote", []), f"{label} table_footnote")
            if body == "":
                unindexed_blocks.append({"block_index": index, "page": page_index + 1,
                                         "block_type": block_type, "reason": "empty_table_body"})
                continue
            if not body.strip():
                raise PDFExtractionError(f"{label} table_body cannot be whitespace-only")
            text = "\n".join([*captions, body, *footnotes])
        elif block_type == "chart":
            body = block.get("content")
            if not isinstance(body, str):
                raise PDFExtractionError(f"{label} chart content must be a string")
            captions = _strings(block.get("chart_caption", []), f"{label} chart_caption")
            footnotes = _strings(block.get("chart_footnote", []), f"{label} chart_footnote")
            text = "\n".join([*captions, *([body] if body else []), *footnotes])
            if not text:
                unindexed_blocks.append({"block_index": index, "page": page_index + 1,
                                         "block_type": block_type, "reason": "image_only_chart"})
                continue
        else:
            captions = _strings(block.get("image_caption", []), f"{label} image_caption")
            footnotes = _strings(block.get("image_footnote", []), f"{label} image_footnote")
            text = "\n".join([*captions, *footnotes])
        if not text:
            unindexed_blocks.append({"block_index": index, "page": page_index + 1,
                                     "block_type": block_type, "reason": "image_without_caption"})
            continue
        if block_type in {"discarded", "header", "footer", "page_number"}:
            continue
        if text_parts:
            position += 2
        start = position
        position += len(text)
        text_parts.append(text)
        locator = {"page": page_index + 1, "page_idx": page_index,
                   "block_index": index, "block_type": block_type, "text_basis": TEXT_BASIS,
                   "page_scope": "mineru_reported_start_page_unreviewed"}
        if bbox is not None:
            locator["bbox"] = bbox
        blocks.append({"heading": f"page {page_index + 1} block {index + 1}",
                       "char_start": start, "char_end": position, "locator": locator})
    if not text_parts:
        raise PDFExtractionError("Extraction contains no usable text blocks")
    return {"text": "\n\n".join(text_parts), "blocks": blocks,
            "unindexed_blocks": unindexed_blocks}


def build_extraction(pdf_path: Path, result_dir: Path, *, model_version: str = "pipeline") -> dict:
    """Read existing MinerU output; never run OCR or access the network."""
    source = Path(pdf_path).read_bytes()
    checksum = hashlib.sha256(source).hexdigest()
    page_count = pdf_page_count(source)
    directory = Path(result_dir)
    markdown_path = directory / "full.md"
    if not markdown_path.is_file():
        raise PDFExtractionError(f"Missing MinerU full.md: {directory}")
    content_paths = sorted(set(directory.glob("*_content_list.json"))
                           | ({directory / "content_list.json"}
                              if (directory / "content_list.json").is_file() else set()))
    if len(content_paths) != 1:
        raise PDFExtractionError("Expected exactly one MinerU *_content_list.json v1 file")
    try:
        artifact = {
            "schema_version": 1, "source_sha256": checksum, "page_count": page_count,
            "extractor": {"name": "mineru", "version": EXTRACTOR_VERSION,
                          "model_version": model_version},
            "markdown": markdown_path.read_text(encoding="utf-8"),
            "content_list": load_extraction_json(content_paths[0].read_bytes()),
        }
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PDFExtractionError(f"Invalid UTF-8 MinerU output: {error}") from error
    parse_extraction(artifact, source_sha256=checksum, page_count=page_count)
    return artifact
