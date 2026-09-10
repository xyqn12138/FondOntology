# -*- coding: utf-8 -*-
"""M7-R4：向量检索与 RRF 融合回归（mock 向量，CI 无网络）。

覆盖：
- VectorIndex：归一化点积检索、top-k 截断；
- get_vector_index 降级：embedding 未配置/文件缺失 → None（BM25-only）；
- _rrf_select：锚定强先验、dense 加权、BM25 兜底、top_k 截断；
- retrieve 集成：向量不可用时静默降级（channels 无 dense）。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from fondontology.qa.rag import retrieve as rt
from fondontology.qa.rag.embedder import VectorIndex
from fondontology.qa.rag.retrieve import _rrf_select
from fondontology.qa.rag.store import ChunkStore, RagChunk, get_store

ROOT = Path(__file__).resolve().parents[1]


def _chunk(cid: str, fund: str = "006494", section: str = "管理人报告",
           doc_type: str = "periodic_report") -> RagChunk:
    return RagChunk(chunk_id=cid, doc_id=f"doc-{fund}", fund_code=fund,
                    doc_type=doc_type, period="2026-Q1", section=section,
                    text=f"text of {cid}", locator={})


class VectorIndexTest(unittest.TestCase):
    def test_cosine_search_and_topk(self) -> None:
        # 三个向量，查询与第一/二个同向分量（第三个正交得 0 被过滤）
        matrix = np.array([[1, 0, 0], [0.9, 0.1, 0], [0, 0, 1]], dtype=np.float32)
        idx = VectorIndex(matrix, ["a", "b", "c"])
        hits = idx.search([1.0, 0, 0], k=2)
        self.assertEqual(hits[0][0], "a")
        self.assertGreater(hits[0][1], 0.99)
        self.assertEqual(len(hits), 2)   # 正交的 c 得分 0 不返回

    def test_zero_query_returns_empty(self) -> None:
        idx = VectorIndex(np.eye(3, dtype=np.float32), ["a", "b", "c"])
        self.assertEqual(idx.search([0, 0, 0], k=3), [])


class DegradationTest(unittest.TestCase):
    def test_vector_index_none_when_unconfigured(self) -> None:
        import fondontology.qa.rag.embedder as ed
        with mock.patch.object(ed, "embedding_configured", return_value=False):
            # 单例已加载的进程内重置
            ed._INDEX_SINGLETON = None
            ed._INDEX_LOADED = False
            self.assertIsNone(ed.get_vector_index())
        ed._INDEX_SINGLETON = None
        ed._INDEX_LOADED = False

    def test_retrieve_degrades_to_bm25(self) -> None:
        """向量通道不可用时 retrieve 静默降级，不抛异常。"""
        import importlib
        rt_mod = importlib.import_module("fondontology.qa.rag.retrieve")
        store = get_store()
        with mock.patch.object(rt_mod, "_vector_index_if_ready", return_value=None):
            r = rt_mod.retrieve("管理人报告", store=store)
        self.assertTrue(r.chunks)
        self.assertIn("bm25", "".join(r.channels.keys()))
        self.assertNotIn("dense", "".join(r.channels.keys()))


class RrfSelectTest(unittest.TestCase):
    def _store(self, *chunks):
        return ChunkStore(list(chunks))

    def test_anchor_is_strong_prior(self) -> None:
        """锚定通道命中的 chunk 必在结果内（防串台的强先验）。"""
        store = self._store(_chunk("x1", section="管理人报告"),
                            _chunk("x2", section="投资组合"),
                            _chunk("x3", section="基金产品概况"))
        out = _rrf_select(anchor_ids=["x1"],
                          bm25_ranked=[("x2", 9.9), ("x3", 9.0)],
                          dense_rank={"x2": 1, "x3": 2},
                          store=store, top_k=2)
        self.assertEqual([c.chunk_id for c in out][0], "x1")

    def test_dense_weight_overrides_bm25_on_rewrite(self) -> None:
        """dense 加权（1.2）在语义改写场景应压过 BM25 词频优势（0.8）。"""
        store = self._store(_chunk("bm_hit", section="基金产品概况"),
                            _chunk("dense_hit", section="管理人报告"))
        out = _rrf_select(anchor_ids=[],
                          bm25_ranked=[("bm_hit", 9.9)],
                          dense_rank={"dense_hit": 1},
                          store=store, top_k=1)
        self.assertEqual(out[0].chunk_id, "dense_hit")

    def test_topk_truncation(self) -> None:
        store = self._store(*[_chunk(f"c{i}") for i in range(10)])
        out = _rrf_select(anchor_ids=[],
                          bm25_ranked=[(f"c{i}", 1.0) for i in range(10)],
                          dense_rank={}, store=store, top_k=3)
        self.assertEqual(len(out), 3)


class RerankTest(unittest.TestCase):
    """rerank 精排：失败降级保持 RRF 序、小集合跳过、成功时按服务端分数重排。"""

    def _chunks(self, n):
        return [_chunk(f"c{i}", section=f"节{i}") for i in range(n)]

    def _rt(self):
        import importlib
        return importlib.import_module("fondontology.qa.rag.retrieve")

    def test_unconfigured_returns_none(self) -> None:
        import fondontology.qa.rag.reranker as rr
        with mock.patch.object(rr, "rerank_configured", return_value=False):
            self.assertIsNone(rr.rerank("q", ["a", "b"]))

    def test_small_collection_skipped_in_maybe_rerank(self) -> None:
        """≤5 条候选不发起 rerank（收益低于网络往返），直接截断。"""
        rt = self._rt()
        chunks = self._chunks(4)
        with mock.patch.object(rt, "_rerank_call", side_effect=AssertionError):
            out = rt._maybe_rerank("q", chunks, top_k=3)
        self.assertEqual(len(out), 3)
        self.assertEqual([c.chunk_id for c in out], ["c0", "c1", "c2"])

    def test_rerank_reorders_by_server_score(self) -> None:
        rt = self._rt()
        chunks = self._chunks(8)
        with mock.patch.object(rt, "_rerank_call",
                               return_value=[(5, 0.9), (0, 0.8), (3, 0.7)]):
            out = rt._maybe_rerank("q", chunks, top_k=3)
        self.assertEqual([c.chunk_id for c in out], ["c5", "c0", "c3"])

    def test_rerank_failure_keeps_rrf_order(self) -> None:
        rt = self._rt()
        chunks = self._chunks(8)
        with mock.patch.object(rt, "_rerank_call", return_value=None):
            out = rt._maybe_rerank("q", chunks, top_k=3)
        self.assertEqual([c.chunk_id for c in out], ["c0", "c1", "c2"])


if __name__ == "__main__":
    unittest.main()
