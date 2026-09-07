# -*- coding: utf-8 -*-
"""M6：Web UI（FastAPI + HTML）回归。

- 智能问数：/api/meta、/api/qa/suggestions、/api/qa/ask（JSON）、
  /api/qa/ask/stream（SSE 流式：phase → answer → done）
- 本体查看器模块：/viewer/ 独立页面 + /api/ontology/* 路由复用
- 统一入口 / 返回聊天壳页面

测试全部 use_llm=False（确定性模板，避免外部 LLM 的时延与抖动）。
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from fondontology.webui import create_web_app

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
VIEWER_TTL = ROOT / "artifacts" / "cnfo" / "cnfo-fund-tbox.ttl"

# 确定性路径实测可答的用例（无 LLM key 也可跑通）
FIND_Q = "货币市场基金有哪些？"
VERIFY_Q = "交易型开放式指数基金是不是开放式基金？"


class QaWebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_web_app(
            tbox_source=SOURCE,
            abox_ttl=ABOX,
            viewer_ttl=VIEWER_TTL,
            default_use_llm=False,
        )
        cls.client = TestClient(cls.app)

    # ---- 智能问数：入口与元信息 ----
    def test_index_page_serves_chat_shell(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("CNFO 智能问数", resp.text)
        self.assertIn("本体查看器", resp.text)

    def test_meta_endpoint(self) -> None:
        resp = self.client.get("/api/meta")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ontology"]["version"])
        self.assertGreater(data["ontology"]["class_count"], 0)
        self.assertGreater(data["data"]["entity_count"], 0)
        self.assertIn("llm", data)
        self.assertIn("configured", data["llm"])

    def test_suggestions_endpoint(self) -> None:
        resp = self.client.get("/api/qa/suggestions")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()["suggestions"]), 0)

    # ---- 智能问数：JSON 问答 ----
    def test_ask_verify_endpoint(self) -> None:
        resp = self.client.post("/api/qa/ask",
                                json={"question": VERIFY_Q, "use_llm": False})
        self.assertEqual(resp.status_code, 200)
        ans = resp.json()["answer"]
        self.assertEqual(ans["kind"], "verify")
        self.assertEqual(ans["verdict"], "ENTAILED")
        self.assertTrue(ans["text"])
        self.assertTrue(ans["report"]["claims"])

    def test_ask_find_endpoint_full_chain(self) -> None:
        resp = self.client.post("/api/qa/ask",
                                json={"question": FIND_Q, "use_llm": False})
        self.assertEqual(resp.status_code, 200)
        ans = resp.json()["answer"]
        self.assertEqual(ans["kind"], "find")
        self.assertEqual(ans["status"], "ok")
        self.assertTrue(ans["text"])
        self.assertTrue(ans["report"])
        # 证据合同：每条 claim 都有非空 evidence
        claims = ans["report"]["claims"]
        self.assertTrue(claims)
        for c in claims:
            self.assertTrue(c.get("evidence"), f"{c['claim_id']} 缺证据")
        # 表达层：模板模式 gate 标记
        self.assertEqual(ans["explanation"]["gate"], "template_nokey")

    def test_ask_empty_rejected(self) -> None:
        resp = self.client.post("/api/qa/ask", json={"question": "   "})
        self.assertEqual(resp.status_code, 400)

    # ---- 智能问数：SSE 流式 ----
    def test_ask_stream_sse_events(self) -> None:
        resp = self.client.get("/api/qa/ask/stream",
                               params={"q": VERIFY_Q, "use_llm": "false"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"].split(";")[0],
                         "text/event-stream")
        events: dict[str, list] = {"phase": [], "answer": [], "done": [], "error": []}
        for line in resp.text.splitlines():
            if line.startswith("event:"):
                current = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                payload = json.loads(line.split(":", 1)[1].strip())
                events.setdefault(current, []).append(payload)
        self.assertTrue(events["phase"], "应至少下发一个 phase 阶段事件")
        self.assertEqual(len(events["answer"]), 1, "应恰好一次 answer 事件")
        self.assertEqual(len(events["done"]), 1, "应以 done 事件结束")
        self.assertEqual(events["error"], [], "不应出现 error 事件")
        ans = events["answer"][0]["answer"]
        self.assertEqual(ans["verdict"], "ENTAILED")

    def test_ask_stream_empty_rejected(self) -> None:
        resp = self.client.get("/api/qa/ask/stream", params={"q": "  "})
        self.assertEqual(resp.status_code, 400)

    # ---- 本体查看器模块（侧边栏切换的目标页面与 API）----
    def test_viewer_page_served(self) -> None:
        for path in ("/viewer", "/viewer/"):
            resp = self.client.get(path, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("中国基金本体浏览器", resp.text)

    def test_viewer_api_reused(self) -> None:
        resp = self.client.get("/api/ontology/summary")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["class_count"], 143)

        resp = self.client.get("/api/ontology/search", params={"q": "ETF", "limit": 5})
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()["results"]), 0)


if __name__ == "__main__":
    unittest.main()
