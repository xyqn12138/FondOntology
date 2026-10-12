"""Offline acquisition boundary tests; no public site is contacted."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fondontology.corpus.official_sources import load_registry, prepare_sources, verify_source


class OfficialSourcesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.raw = '<html><div id="body"><h3>测试法规</h3><p>2023年7月3日</p><p>第一条 范围。</p><p>第二条 例外。</p></div></html>'.encode()
        self.source = {
            "doc_id": "test-law", "title": "测试法规", "publisher": "测试发行机关",
            "url": "https://www.gov.cn/test-law.htm", "raw_sha256": hashlib.sha256(self.raw).hexdigest(),
            "extraction": {"kind": "official_html", "encoding": "utf-8",
                           "selector": {"tag": "div", "attribute": "id", "value": "body"}},
            "expected_articles": 2, "issued_date": "2023-07-03", "effective_from": None,
            "date_basis": "synthetic fixture", "required_text": ["2023年7月3日"],
            "validity_status": "not_checked_current",
        }
        self.receipt = {
            "schema_version": "1.0", "doc_id": "test-law", "requested_url": self.source["url"],
            "final_url": self.source["url"], "status_code": 200, "content_type": "text/html",
            "fetched_at": "2026-10-12T00:00:00+00:00", "raw_sha256": self.source["raw_sha256"],
            "byte_count": len(self.raw), "tls_policy": "default_certificate_verification",
            "redirects_allowed": False,
        }
        self.registry = self.root / "sources.json"
        self.registry.write_text(json.dumps({"schema_version": "1.0", "sources": [self.source]}), encoding="utf-8")

    def test_default_offline_does_not_fetch_or_create(self):
        with patch("fondontology.corpus.official_sources.download_source") as downloader:
            with self.assertRaises(ValueError):
                prepare_sources(self.registry, self.root / "cache")
            downloader.assert_not_called()
        self.assertFalse((self.root / "cache").exists())

    def test_explicit_acquisition_and_offline_replay(self):
        with patch("fondontology.corpus.official_sources.download_source", return_value=(self.raw, self.receipt)) as downloader:
            first = prepare_sources(self.registry, self.root / "cache", download=True)
            downloader.assert_called_once()
        with patch("fondontology.corpus.official_sources.download_source", side_effect=AssertionError("network forbidden")):
            replay = prepare_sources(self.registry, self.root / "cache")
        self.assertEqual(first, replay)
        self.assertEqual(first["report"][0]["article_count"], 2)
        self.assertEqual(first["records"][0]["provenance"]["source_verification"]["legal_validity"], "not_checked_current")
        self.assertEqual((self.root / "cache/test-law.html").read_bytes(), self.raw)

    def test_raw_tampering_and_receipt_mismatch_fail_closed(self):
        with self.assertRaises(ValueError):
            verify_source(self.source, self.raw + b"x", self.receipt)
        for field, value in [("final_url", "https://evil.example/"), ("status_code", 404),
                             ("raw_sha256", "0" * 64), ("byte_count", 2),
                             ("redirects_allowed", True), ("tls_policy", "disabled")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_source(self.source, self.raw, {**self.receipt, field: value})

    def test_source_identity_and_missing_tail_rejected(self):
        for changes in [{"title": "错误法规"}, {"required_text": ["2030年"]}, {"expected_articles": 3}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                verify_source({**self.source, **changes}, self.raw, self.receipt)

    def test_untrusted_urls_and_false_currency_rejected(self):
        for url in ["http://www.gov.cn/test.htm", "https://www.gov.cn.evil.example/test.htm",
                    "https://user:pass@www.gov.cn/test.htm", "https://www.gov.cn:8443/test.htm",
                    "https://www.gov.cn/test.htm?token=abc"]:
            source = {**self.source, "url": url}
            self.registry.write_text(json.dumps({"schema_version": "1.0", "sources": [source]}))
            with self.subTest(url=url), self.assertRaises(ValueError):
                load_registry(self.registry)
        self.registry.write_text(json.dumps({"schema_version": "1.0", "sources": [{**self.source, "validity_status": "current"}]}))
        with self.assertRaises(ValueError):
            load_registry(self.registry)

    def test_duplicate_registry_keys_and_unknown_fields_rejected(self):
        self.registry.write_text('{"schema_version":"1.0","schema_version":"1.0","sources":[]}')
        with self.assertRaises(ValueError):
            load_registry(self.registry)
        source = deepcopy(self.source)
        source["silent_override"] = True
        self.registry.write_text(json.dumps({"schema_version": "1.0", "sources": [source]}))
        with self.assertRaises(ValueError):
            load_registry(self.registry)

    def test_existing_tampered_cache_never_overwritten(self):
        with patch("fondontology.corpus.official_sources.download_source", return_value=(self.raw, self.receipt)):
            prepare_sources(self.registry, self.root / "cache", download=True)
        target = self.root / "cache/test-law.html"
        target.write_bytes(b"tampered")
        with patch("fondontology.corpus.official_sources.download_source") as downloader:
            with self.assertRaises(ValueError):
                prepare_sources(self.registry, self.root / "cache", download=True)
            downloader.assert_not_called()
        self.assertEqual(target.read_bytes(), b"tampered")


if __name__ == "__main__":
    unittest.main()
