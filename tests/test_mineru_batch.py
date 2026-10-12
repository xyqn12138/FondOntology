"""Offline tests for MinerU batches; no hosted API is contacted."""

from __future__ import annotations

import io
import json
import os
import threading
import tempfile
import time
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from fondontology.corpus import CorpusRepository
from fondontology.corpus import mineru_batch as mineru


class FakeTransport:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def api(data, code=0):
    return 200, json.dumps({"code": code, "data": data}).encode()


def zip_bytes(members=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in (members or {
            "document/full.md": "# Synthetic PDF\n\nText fixture.",
            "document/document_content_list.json": json.dumps([
                {"type": "text", "text": "Text fixture.", "page_idx": 0}
            ]),
            "document/document_content_list_v2.json": "[]",
        }).items():
            archive.writestr(name, value)
    return stream.getvalue()


class MinerUBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.output = self.root / "artifacts"
        self.data.mkdir()
        self.pdf = self.make_pdf("textbook.pdf")
        self.data_id = mineru.data_id_for(self.pdf, self.data)
        self.env = patch.dict(os.environ, {"MINERU_KEY": "private-token-fixture"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_pdf(self, name, width=72):
        path = self.data / name
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        writer.add_blank_page(width=width, height=72)
        with path.open("wb") as output:
            writer.write(output)
        return path

    def transport(self, pdfs=None, results=None, archives=None):
        pdfs = pdfs or [self.pdf]
        ids = [mineru.data_id_for(pdf, self.data) for pdf in pdfs]
        replies = [api({"batch_id": "batch-one", "file_urls": [
            f"https://uploads.example.com/{index}?signature=secret" for index in range(len(pdfs))
        ]})]
        replies.extend((200, b"") for unused in pdfs)
        replies.append(api({"extract_result": results if results is not None else [
            {"data_id": data_id, "state": "done",
             "full_zip_url": f"https://cdn.example.com/{index}?signature=secret"}
            for index, data_id in enumerate(ids)
        ]}))
        replies.extend((200, value) for value in (archives or [zip_bytes() for unused in pdfs]))
        return FakeTransport(replies)

    def execute(self, transport, **kwargs):
        return mineru.run(self.data, self.output, execute=True, transport=transport, **kwargs)

    def test_default_dry_run_needs_no_token_network_or_output(self):
        with patch.dict(os.environ, {"MINERU_KEY": "", "MINERU_API_TOKEN": ""}):
            result = mineru.run(self.data, self.output)
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["data_ids"], [self.data_id])
        self.assertFalse(self.output.exists())

    def test_ids_are_ascii_distinguish_same_filename_content_and_config(self):
        nested = self.make_pdf("other/textbook.pdf")
        changed = self.make_pdf("third/textbook.pdf", width=80)
        ids = [mineru.data_id_for(pdf, self.data) for pdf in (self.pdf, nested, changed)]
        self.assertEqual(len(set(ids)), 3)
        self.assertNotEqual(ids[0], mineru.data_id_for(self.pdf, self.data, {"model_version": "different"}))
        self.assertTrue(all(value.isascii() and len(value) <= 128 for value in ids))

    def test_execute_generates_importable_manifest_and_credentials_stay_on_api(self):
        transport = self.transport()
        result = self.execute(transport, source_verified=True)
        record = json.loads(result["manifest"].read_text())
        self.assertEqual(record["authority"], "research_note")
        self.assertEqual(record["provenance"]["kind"], "user_attested")
        self.assertIsNone(record["issued_date"])
        self.assertIsNone(record["effective_from"])
        self.assertEqual(record["sha256"], mineru.sha256_file(self.pdf))
        self.assertTrue((self.output / record["extraction"]["path"]).is_file())
        imported = CorpusRepository(self.root / "corpus.sqlite").import_manifest(result["manifest"])
        self.assertEqual(imported["inserted"], 1)
        for method, url, kwargs in transport.requests:
            if url.startswith(mineru.BASE_URL + "/api/v4/"):
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer private-token-fixture")
            else:
                self.assertNotIn("Authorization", kwargs.get("headers") or {})
        saved = (self.output / "state.json").read_text()
        self.assertNotIn("private-token-fixture", saved)
        self.assertNotIn("signature=secret", saved)

    def test_source_verification_defaults_unverified_and_does_not_change_cache_identity(self):
        self.execute(self.transport())
        default_record = json.loads((self.output / "corpus.jsonl").read_text())
        original_state = (self.output / "state.json").read_bytes()
        self.assertEqual(default_record["status"], "unverified")
        self.assertEqual(default_record["provenance"]["kind"], "source_unverified")
        self.assertNotIn("user_attestation", default_record["provenance"])
        self.assertIn("not independently verified", default_record["provenance"]["source_review"])
        transport = FakeTransport([])
        self.execute(transport, source_verified=True)
        verified_record = json.loads((self.output / "corpus.jsonl").read_text())
        self.assertEqual(transport.requests, [])
        self.assertEqual((self.output / "state.json").read_bytes(), original_state)
        self.assertEqual(verified_record["status"], "verified")
        self.assertEqual(verified_record["provenance"], {
            "kind": "user_attested",
            "user_attestation": "Source verified by user; educational reference, not an official regulation.",
            "extraction_review": "machine extraction; OCR not independently reviewed",
        })
        self.assertEqual(verified_record["extraction"], default_record["extraction"])
        self.assertEqual(verified_record["locator"]["data_id"], default_record["locator"]["data_id"])
        self.execute(FakeTransport([]))
        reset_record = json.loads((self.output / "corpus.jsonl").read_text())
        self.assertEqual(reset_record["status"], "unverified")
        self.assertNotIn("user_attestation", reset_record["provenance"])

    def test_cli_forwards_explicit_source_verification_without_changing_dry_run(self):
        with patch.object(mineru, "run", return_value={"mode": "dry-run"}) as runner:
            self.assertEqual(mineru.main(["--source-verified", "--dry-run"]), 0)
        self.assertTrue(runner.call_args.kwargs["source_verified"])
        self.assertFalse(runner.call_args.kwargs["execute"])
        with patch.object(mineru, "run", return_value={"mode": "dry-run"}) as runner:
            self.assertEqual(mineru.main(["--dry-run"]), 0)
        self.assertFalse(runner.call_args.kwargs["source_verified"])

    def test_completed_files_skip_only_with_valid_artifact_hashes(self):
        self.execute(self.transport())
        empty = FakeTransport([])
        self.execute(empty)
        self.assertEqual(empty.requests, [])
        full_md = self.output / "files" / self.data_id / "full.md"
        full_md.write_text("tampered", encoding="utf-8")
        resume = FakeTransport([
            api({"extract_result": [{"data_id": self.data_id, "state": "done",
                                      "full_zip_url": "https://cdn.example.com/result"}]}),
            (200, zip_bytes()),
        ])
        self.execute(resume)
        self.assertEqual(resume.requests, [])
        self.assertIn("Text fixture.", full_md.read_text())

    def test_missing_artifact_resumes_completed_upload_batch(self):
        self.execute(self.transport())
        (self.output / "files" / self.data_id / "extraction.json").unlink()
        transport = FakeTransport([
            api({"extract_result": [{"data_id": self.data_id, "state": "done",
                                      "full_zip_url": "https://cdn.example.com/result"}]}),
            (200, zip_bytes()),
        ])
        self.execute(transport)
        self.assertEqual(transport.requests, [])

    def test_quality_report_is_reproducible_and_reports_unindexed_blocks(self):
        transport = self.transport(archives=[zip_bytes({
            "full.md": "text fixture",
            "content_list.json": json.dumps([
                {"type": "header", "text": "header", "page_idx": 0},
                {"type": "text", "text": "text fixture", "page_idx": 0},
                {"type": "image", "image_caption": [], "image_footnote": [], "page_idx": 0},
            ]),
        })])
        self.execute(transport)
        directory = self.output / "files" / self.data_id
        original = (directory / "quality.json").read_bytes()
        quality = json.loads(original)
        self.assertEqual(quality["page_count"], 1)
        self.assertEqual(quality["content_blocks"], 3)
        self.assertEqual(quality["indexed_blocks"], 1)
        self.assertEqual(quality["indexed_reported_pages"], [1])
        self.assertEqual(quality["normalized_chars"], len("text fixture"))
        self.assertEqual(quality["unindexed_blocks"], [
            {"block_index": 2, "block_type": "image", "page": 1, "reason": "image_without_caption"}
        ])
        self.assertEqual(quality["extraction_quality"], "mineru_unreviewed")
        self.assertEqual(quality["page_scope"], "mineru_reported_start_page_unreviewed")
        mineru.write_artifacts(self.pdf, directory)
        self.assertEqual((directory / "quality.json").read_bytes(), original)

    def test_legacy_cache_without_quality_is_rebuilt_from_raw(self):
        self.execute(self.transport())
        directory = self.output / "files" / self.data_id
        (directory / "quality.json").unlink()
        state_path = self.output / "state.json"
        state = json.loads(state_path.read_text())
        state["files"][self.data_id]["artifacts"].pop("quality.json")
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assertFalse(mineru._complete(state["files"][self.data_id], self.output))
        transport = FakeTransport([])
        self.execute(transport)
        self.assertEqual(transport.requests, [])
        self.assertTrue((directory / "quality.json").is_file())
        current_state = json.loads(state_path.read_text())
        self.assertIn("quality.json", current_state["files"][self.data_id]["artifacts"])

    def test_added_pdf_does_not_disappear_on_resume(self):
        self.execute(self.transport())
        added = self.make_pdf("new.pdf")
        self.execute(self.transport([added]))
        records = self.output.joinpath("corpus.jsonl").read_text().splitlines()
        self.assertEqual(len(records), 2)

    def test_changed_source_gets_new_result_id(self):
        self.execute(self.transport())
        self.make_pdf("textbook.pdf", width=90)
        self.assertNotEqual(self.data_id, mineru.data_id_for(self.pdf, self.data))
        self.execute(self.transport())
        self.assertEqual(len(self.output.joinpath("corpus.jsonl").read_text().splitlines()), 1)

    def test_empty_partial_results_cannot_succeed_and_deadline_is_finite(self):
        for results in ([], [{"data_id": self.data_id, "state": "running"}]):
            with self.subTest(results=results):
                output = self.root / ("empty" if not results else "running")
                transport = self.transport(results=results)
                with self.assertRaisesRegex(mineru.MinerUError, "deadline"):
                    mineru.run(self.data, output, execute=True, transport=transport,
                               deadline_seconds=0.01, poll_interval=0.1)
                self.assertFalse((output / "corpus.jsonl").exists())

    def test_unknown_and_duplicate_result_ids_are_rejected(self):
        for results in (
            [{"data_id": "unknown", "state": "done"}],
            [{"data_id": self.data_id, "state": "done"}] * 2,
        ):
            with self.subTest(results=results):
                output = self.root / ("unknown-result" if len(results) == 1 else "duplicate-result")
                with self.assertRaisesRegex(mineru.MinerUError, "unknown or duplicate"):
                    mineru.run(self.data, output, execute=True, transport=self.transport(results=results))

    def test_failed_member_preserves_successful_result_but_no_complete_manifest(self):
        other = self.make_pdf("second.pdf")
        ids = [mineru.data_id_for(pdf, self.data) for pdf in [other, self.pdf]]
        transport = self.transport([other, self.pdf], results=[
            {"data_id": ids[0], "state": "failed", "err_msg": "secret should never print"},
            {"data_id": ids[1], "state": "done", "full_zip_url": "https://cdn.example.com/file"},
        ])
        with self.assertRaisesRegex(mineru.MinerUError, "failed 1"):
            self.execute(transport)
        self.assertTrue((self.output / "files" / self.data_id / "extraction.json").is_file())
        self.assertFalse((self.output / "corpus.jsonl").exists())

    def test_api_code_must_be_zero_and_error_bodies_never_leak(self):
        for reply in ((401, b"private-token-fixture https://cdn.example.com/?signature=secret"),
                      api({}, code=100), api({}, code=False), (200, b'{"data":{}}')):
            with self.subTest(reply=reply):
                with self.assertRaises(mineru.MinerUError) as caught:
                    self.execute(FakeTransport([reply]))
                self.assertNotIn("private-token-fixture", str(caught.exception))
                self.assertNotIn("signature", str(caught.exception))

    def test_retry_has_bounded_timeout_and_does_not_print_transport_exception(self):
        transport = FakeTransport([(429, b"token"), (200, b"ok")])
        with patch.object(mineru.time, "sleep"):
            result = mineru._request(transport, "GET", "https://cdn.example.com/file",
                                    deadline=time.monotonic() + 3, timeout=2, operation="download")
        self.assertEqual(result, b"ok")
        self.assertTrue(all(request[2]["timeout"] <= 2 for request in transport.requests))
        errors = FakeTransport([OSError("private-token-fixture signature=secret")] * mineru.RETRY_COUNT)
        with patch.object(mineru.time, "sleep"):
            with self.assertRaises(mineru.MinerUError) as caught:
                mineru._request(errors, "GET", "https://cdn.example.com/file",
                                deadline=time.monotonic() + 3, timeout=2, operation="download")
        self.assertNotIn("private-token-fixture", str(caught.exception))

    def test_offline_results_need_no_token_and_reject_ambiguous_mapping(self):
        results = self.root / "offline"
        target = results / self.data_id
        mineru.extract_result_zip(zip_bytes(), target)
        with patch.dict(os.environ, {"MINERU_KEY": "", "MINERU_API_TOKEN": ""}):
            result = mineru.run(self.data, self.output, results_dir=results)
        self.assertEqual(result["mode"], "offline")
        self.assertTrue(result["manifest"].is_file())
        self.assertEqual(json.loads(result["manifest"].read_text())["status"], "unverified")
        verified = mineru.run(self.data, self.output, results_dir=results, source_verified=True)
        self.assertEqual(json.loads(verified["manifest"].read_text())["status"], "verified")
        (results / "textbook").mkdir()
        with self.assertRaisesRegex(mineru.MinerUError, "ambiguous"):
            mineru._offline_result(results, self.pdf, self.data, self.data_id)

    def test_zip_rejects_traversal_ads_drive_and_reserved_names(self):
        for bad_name in ("../evil", "nested/../../evil", "C:/evil", "file:ads", "/evil",
                         "images/CON.png", "images/photo. ", "nested\\..\\evil"):
            with self.subTest(name=bad_name):
                raw = zip_bytes({"full.md": "text", "content_list.json": "[]", bad_name: "evil"})
                with self.assertRaises(mineru.MinerUError):
                    mineru.extract_result_zip(raw, self.root / "malicious")
                for child in (self.root / "malicious").glob("*"):
                    self.assertEqual(child.name, "result.zip")

    def test_zip_rejects_duplicate_case_mapping_symlink_and_bomb(self):
        for kind in ("duplicate", "symlink", "bomb"):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("full.md", "text")
                archive.writestr("content_list.json", "[]")
                if kind == "duplicate":
                    archive.writestr("FULL.MD", "other")
                elif kind == "symlink":
                    info = zipfile.ZipInfo("images/link")
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, "/outside")
                else:
                    archive.writestr("images/bomb", b"x" * 100_000)
            with self.assertRaises(mineru.MinerUError):
                mineru.extract_result_zip(stream.getvalue(), self.root / kind)

    def test_zip_requires_unique_matching_v1_root_and_preserves_v2(self):
        target = self.root / "valid"
        mineru.extract_result_zip(zip_bytes(), target)
        self.assertTrue((target / "full.md").is_file())
        self.assertTrue((target / "document_content_list_v2.json").is_file())
        for members in (
            {"full.md": "text", "second/full.md": "text", "content_list.json": "[]"},
            {"full.md": "text", "content_list.json": "[]", "other_content_list.json": "[]"},
            {"full.md": "text", "second/content_list.json": "[]"},
            {"full.md": "text", "content_list_v2.json": "[]"},
        ):
            with self.subTest(members=members):
                with self.assertRaises(mineru.MinerUError):
                    mineru.extract_result_zip(zip_bytes(members), self.root / "invalid")

    def test_images_are_validated_and_kept_per_file(self):
        raw = zip_bytes({
            "full.md": "![figure](images/figure.png)\n\ntext",
            "content_list.json": json.dumps([{"type": "text", "text": "text", "page_idx": 0}]),
            "images/figure.png": b"synthetic-image-fixture",
        })
        target = self.root / "image-result"
        mineru.extract_result_zip(raw, target)
        mineru.write_artifacts(self.pdf, target)
        self.assertEqual((target / "images" / "figure.png").read_bytes(), b"synthetic-image-fixture")
        for reference in ("../outside.png", "images/missing.png", "https://remote.example/image.png"):
            (target / "full.md").write_text(f"![figure]({reference})", encoding="utf-8")
            with self.assertRaises(mineru.MinerUError):
                mineru.write_artifacts(self.pdf, target)

    def test_maximum_batch_size_is_fifty(self):
        for index in range(50):
            self.make_pdf(f"book-{index:02}.pdf")
        pdfs = mineru.collect_pdfs(self.data)
        first = self.transport(pdfs[:50])
        second = self.transport(pdfs[50:])
        transport = FakeTransport(first.replies + second.replies)
        self.execute(transport)
        sizes = [len(json.loads(kwargs["body"])["files"])
                 for method, url, kwargs in transport.requests if method == "POST"]
        self.assertEqual(sizes, [50, 1])
        self.assertEqual(len(self.output.joinpath("corpus.jsonl").read_text().splitlines()), 51)

    def test_authorization_domain_and_redirect_policy(self):
        with self.assertRaisesRegex(mineru.MinerUError, "restricted"):
            mineru._request(FakeTransport([]), "GET", "https://cdn.example.com/",
                            headers={"Authorization": "Bearer private"}, deadline=time.monotonic() + 3,
                            timeout=2, operation="API")
        self.assertIsNone(mineru._NoRedirect().redirect_request(None, None, 302, "", {}, "https://cdn.example.com/"))

    def test_real_transport_put_omits_urllib_default_content_type(self):
        observed = {}

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self):
                observed.update(self.headers)
                size = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(size)
                self.send_response(200)
                self.end_headers()

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        status, body = mineru.HTTPTransport().request(
            "PUT", f"http://127.0.0.1:{server.server_port}/signed", body=b"%PDF-fixture")
        self.assertEqual((status, body), (200, b""))
        self.assertNotIn("Content-Type", observed)
        self.assertNotIn("Authorization", observed)

    def test_curl_configuration_rejects_control_characters_and_backslash(self):
        for url in ("https://cdn.example.com/x\noutput=evil", "https://cdn.example.com/x\r",
                    "https://cdn.example.com/\\\""):
            with self.subTest(url=url):
                with self.assertRaises(mineru.MinerUError):
                    mineru._https_url(url)

    def test_invalid_extraction_keeps_raw_zip_and_can_retry_without_network(self):
        invalid = zip_bytes({"full.md": "text", "content_list.json": "[]"})
        with self.assertRaises(ValueError):
            self.execute(self.transport(archives=[invalid]))
        raw_zip = self.output / "raw" / f"{self.data_id}.zip"
        self.assertEqual(raw_zip.read_bytes(), invalid)
        retry = FakeTransport([])
        with self.assertRaises(ValueError):
            self.execute(retry)
        self.assertEqual(retry.requests, [])


if __name__ == "__main__":
    unittest.main()
