# -*- coding: utf-8 -*-
"""M7-R1：文本资产（季报/法规条文）与 A-BOX 交叉一致性回归。

数据管线：tools/gen_text_assets.py 从 SimModel 同源投影出
- artifacts/cnfo/abox/cnfo-sim-reports.ttl（报告/章节/条文实体）
- artifacts/cnfo/rag/chunks.jsonl（chunk 池）
- artifacts/cnfo/rag/reports/*.md（报告正文）

本测试独立从 cnfo-sim-abox.ttl（图事实）与文本资产两边取证比对：
季报文本中的经理名/风险等级/净值/持仓必须能在图上找到对应三元组；
条文正文必须等于图上 RegulationArticle 的 articleText。
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
ABOX_TTL = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
REPORTS_TTL = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-reports.ttl"
CHUNKS_JSONL = ROOT / "artifacts" / "cnfo" / "rag" / "chunks.jsonl"
REPORTS_MD_DIR = ROOT / "artifacts" / "cnfo" / "rag" / "reports"

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")

MIN_REPORTS = 60      # 40 基金 × 2 季度，扣除晚于季度末成立的
SECTIONS_PER_REPORT = 5


def _load_chunks() -> list[dict]:
    if not CHUNKS_JSONL.is_file():
        return []
    return [json.loads(line) for line in
            CHUNKS_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]


def _manager_names(abox: Graph) -> dict[str, set[str]]:
    """fund_code → {经理名}。经理自然人经 playsFundRole 挂到基金经理角色
    （rolePlayedBy 指向的是承担管理人职责的机构，勿混淆），名取 rdfs:label。"""
    out: dict[str, set[str]] = {}
    for fund, role in abox.subject_objects(CNFO.hasFundManagerRole):
        code = str(fund).rsplit("F", 1)[-1]
        for person in abox.subjects(CNFO.playsFundRole, role):
            label = next((str(o) for o in abox.objects(person, RDFS.label)), None)
            if label:
                out.setdefault(code, set()).add(label)
    return out


def _fund_risk_labels(abox: Graph, tbox: Graph) -> dict[str, str]:
    """fund_code → 风险等级代码（如 R4）。风险概念是 cnfc:FundRiskLevelRn，
    文本中写短码 Rn（与生成器 _risk_zh 的取码方式一致）。"""
    out = {}
    for fund, risk in abox.subject_objects(CNFO.hasFundRiskLevel):
        code = str(fund).rsplit("F", 1)[-1]
        local = str(risk).rsplit("/", 1)[-1]
        out[code] = local.replace("FundRiskLevel", "")
    return out


def _unit_navs(abox: Graph) -> dict[tuple[str, str], str]:
    """(fund_code, valuation_date) → 单位净值字符串（4 位小数）。
    NAV 记录主语 IRI 形如 NAV{fund_code}{date}（基金级），从 IRI 解析基金。"""
    out = {}
    for s, d, v in abox.triples((None, CNFO.fundUnitNetAssetValue, None)):
        local = str(s).rsplit("/", 1)[-1]
        if not local.startswith("NAVF"):
            continue
        rest = local[len("NAVF"):]
        # rest = fund_code + yyyymmdd（fund_code 为 6 位数字）
        if len(rest) < 14 or not rest[:6].isdigit() or not rest[6:].isdigit():
            continue
        code, ymd = rest[:6], rest[6:]
        date = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
        out.setdefault((code, date), f"{float(v):.4f}")
    return out


class TextAssetConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not REPORTS_TTL.is_file() or not CHUNKS_JSONL.is_file():
            raise unittest.SkipTest("文本资产未生成（先运行 tools/gen_text_assets.py）")
        cls.reports = Graph()
        cls.reports.parse(str(REPORTS_TTL), format="turtle")
        cls.abox = Graph()
        cls.abox.parse(str(ABOX_TTL), format="turtle")
        # 物化推理边（hasFundManager 链）在主 A-BOX 已显式存在，直接查询
        cls.tbox = Graph()
        cls.tbox.parse(str(ROOT / "artifacts" / "cnfo" / "cnfo-fund-tbox.ttl"), format="turtle")
        cls.chunks = _load_chunks()

    # ---- 结构契约 ----
    def test_report_entities_and_chunks_aligned(self) -> None:
        reports = list(self.reports.subjects(RDF.type, CNFO.FundQuarterlyReport))
        self.assertGreaterEqual(len(reports), MIN_REPORTS)
        report_chunks = [c for c in self.chunks if c["doc_type"] == "periodic_report"]
        self.assertEqual(len(report_chunks), len(reports) * SECTIONS_PER_REPORT)
        # 每份报告恰好 5 个章节 chunk，sectionOrder 连续
        by_doc: dict[str, list[dict]] = {}
        for c in report_chunks:
            by_doc.setdefault(c["doc_id"], []).append(c)
        for doc_id, secs in by_doc.items():
            self.assertEqual(len(secs), SECTIONS_PER_REPORT, f"{doc_id} 章节数不符")
            self.assertEqual({s["section"] for s in secs},
                             {"重要提示", "基金产品概况", "主要财务指标", "管理人报告", "投资组合"})

    def test_chunk_fund_code_matches_report_edge(self) -> None:
        """chunk 元数据 fund_code ↔ 图上 reportForFund 边一致（一级检索锚定主键）。"""
        for report in self.reports.subjects(RDF.type, CNFO.FundQuarterlyReport):
            fund = self.reports.value(report, CNFO.reportForFund)
            self.assertIsNotNone(fund, f"{report} 缺 reportForFund")
            code = str(fund).rsplit("F", 1)[-1]
            period = str(self.reports.value(report, CNFO.reportPeriod))
            doc_id = f"qtr-{period}-{code}"
            chunks = [c for c in self.chunks if c["doc_id"] == doc_id]
            self.assertTrue(chunks, f"{doc_id} 无 chunk")
            for c in chunks:
                self.assertEqual(c["fund_code"], code)

    # ---- 事实一致性（图 → 文本方向） ----
    def test_report_manager_names_match_graph(self) -> None:
        """季报文本中的基金经理名 ∈ 图上该基金的 hasFundManager 集合。"""
        managers = _manager_names(self.abox)
        checked = 0
        for c in self.chunks:
            if c["doc_type"] != "periodic_report" or c["section"] != "管理人报告":
                continue
            code = c["fund_code"]
            self.assertIn(code, managers, f"基金 {code} 图上无经理")
            # 文本中出现『基金经理X认为』形态
            import re
            m = re.search(r"基金经理(.+?)认为", c["text"])
            self.assertIsNotNone(m, f"{c['chunk_id']} 管理人报告未提及经理名")
            self.assertIn(m.group(1), managers[code],
                          f"{c['chunk_id']} 经理名 {m.group(1)} 不在图上 {managers[code]}")
            checked += 1
        self.assertGreater(checked, MIN_REPORTS)

    def test_report_risk_levels_match_graph(self) -> None:
        risk = _fund_risk_labels(self.abox, self.tbox)
        for c in self.chunks:
            if c["doc_type"] != "periodic_report" or c["section"] != "基金产品概况":
                continue
            import re
            m = re.search(r"风险等级为(.+?)。", c["text"])
            self.assertIsNotNone(m, f"{c['chunk_id']} 概况章节未写风险等级")
            self.assertEqual(m.group(1), risk.get(c["fund_code"]),
                             f"{c['chunk_id']} 风险等级与图不符")

    def test_report_nav_values_match_graph(self) -> None:
        """主要财务指标章节的单位净值能在图上同日找到相同值。"""
        navs = _unit_navs(self.abox)
        checked = 0
        for c in self.chunks:
            if c["doc_type"] != "periodic_report" or c["section"] != "主要财务指标":
                continue
            import re
            m = re.search(r"报告期末（(\d{4}-\d{2}-\d{2})），基金份额单位净值为 ([\d.]+) 元", c["text"])
            if not m:
                continue  # 无净值记录的报告
            date, value = m.groups()
            self.assertEqual(navs.get((c["fund_code"], date)), value,
                             f"{c['chunk_id']} 净值 {value}@{date} 与图不符")
            checked += 1
        self.assertGreater(checked, MIN_REPORTS * 0.5, "净值核验样本过少")

    # ---- 法规条文 ----
    def test_article_text_equals_graph(self) -> None:
        articles = list(self.reports.subjects(RDF.type, CNFO.RegulationArticle))
        self.assertGreaterEqual(len(articles), 5)
        # regulationCode 在主 A-BOX 的 Regulation 实体上
        reg_code_by_uri = {
            str(r): str(c) for r, c in self.abox.subject_objects(CNFO.regulationCode)}
        article_chunks = {c["chunk_id"]: c for c in self.chunks
                          if c["doc_type"] == "regulation_article"}
        for art in articles:
            number = str(self.reports.value(art, CNFO.articleNumber))
            reg = self.reports.value(art, CNFO.articleOf)
            self.assertIsNotNone(reg, f"{art} 缺 articleOf")
            reg_code = reg_code_by_uri[str(reg)]
            chunk_id = f"article-{reg_code}-{number}"
            self.assertIn(chunk_id, article_chunks, f"条文 {chunk_id} 无 chunk")
            self.assertEqual(article_chunks[chunk_id]["text"],
                             str(self.reports.value(art, CNFO.articleText)),
                             f"{chunk_id} 正文与图上 articleText 不一致")

    def test_articles_cite_risk_codes(self) -> None:
        """适当性条文引用 R1-R5 代码概念（articleCitesCode 边存在）。"""
        citing = [a for a in self.reports.subjects(CNFO.articleCitesCode, None)]
        self.assertTrue(citing, "无条文引用代码概念")
        cited = {str(o).rsplit("/", 1)[-1].replace("FundRiskLevel", "")
                 for a in citing for o in self.reports.objects(a, CNFO.articleCitesCode)}
        self.assertEqual({"R1", "R2", "R3", "R4", "R5"} & cited, {"R1", "R2", "R3", "R4", "R5"},
                         f"适当性条文应引用 R1-R5，实际 {cited}")

    # ---- 独立可复现性 ----
    def test_md_reports_match_chunks(self) -> None:
        """md 正文由 chunk 拼装：每份 md 的章节正文 == 对应 chunk 文本。"""
        mds = list(REPORTS_MD_DIR.glob("*.md"))
        self.assertGreaterEqual(len(mds), MIN_REPORTS)
        by_doc: dict[str, dict[str, dict]] = {}
        for c in self.chunks:
            if c["doc_type"] == "periodic_report":
                by_doc.setdefault(c["doc_id"], {})[c["section"]] = c
        for md in mds[:10]:  # 抽 10 份全量比对成本过高
            doc_id = md.stem
            secs = by_doc.get(doc_id)
            self.assertIsNotNone(secs, f"{doc_id} md 无对应 chunk")
            body = md.read_text(encoding="utf-8")
            for title, c in secs.items():
                self.assertIn(c["text"], body, f"{doc_id} md 中 {title} 正文与 chunk 不一致")


if __name__ == "__main__":
    unittest.main()
