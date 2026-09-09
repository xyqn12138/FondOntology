# -*- coding: utf-8 -*-
"""CNFO 文本资产生成器（M7-R1）：从仿真数据源同源生成季报文本与法规条文。

同源生成原则（RAG V2 设计 §4.1）：
- 季报与 A-BOX 由同一个 SimModel 投影——季报文本中的基金经理名、基金类型、
  规模数字、重仓持仓均等于图上的三元组，交叉一致性是生成方式的数学性质，
  不是概率结果；
- 法规条文从图上已有的仿真 Regulation 及其关联约束反向生成——图上 120 条
  governedByRegulation 边、投资比例约束被渲染成条文正文，条文引用的代码
  概念经 articleCitesCode 挂到 cnfc 代码表；
- 生成器复用 gen_sim_abox 的 generate()（同 seed 同数据），保证与既有
  cnfo-sim-abox.ttl 完全一致。

产出：
- Turtle A-BOX artifacts/cnfo/abox/cnfo-sim-reports.ttl
  （FundQuarterlyReport / ReportSection / RegulationArticle 实例；
  独立文件便于报告语料单独重建，与 cnfo-sim-abox.ttl 同命名空间）
- 报告正文 artifacts/cnfo/rag/reports/{doc_id}.md（80 份，章节对齐真实季报）
- chunk 池 artifacts/cnfo/rag/chunks.jsonl（doc_id/fund_code/period/section 元数据）
- 交叉一致性清单 artifacts/cnfo/rag/consistency.json
  （每个文本事实 ↔ 图三元组的映射，CI 断言依据）

用法：
    .venv\\Scripts\\python.exe tools\\gen_text_assets.py [--seed 20260826]
        [--quarters 2] [--no-reports] [--no-articles] [--no-md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from fondontology.ontology_loader import load_ontology_graph
from tools.gen_sim_abox import (
    CNFO, CNFC, CNFOA, ROOT, TBOX_ENTRY, OntologyVocabulary, generate,
    local, zh_label,
)

ABOX_DIR = ROOT / "artifacts" / "cnfo" / "abox"
RAG_DIR = ROOT / "artifacts" / "cnfo" / "rag"
REPORTS_TTL = ABOX_DIR / "cnfo-sim-reports.ttl"
REPORTS_MD_DIR = RAG_DIR / "reports"
CHUNKS_JSONL = RAG_DIR / "chunks.jsonl"
CONSISTENCY_JSON = RAG_DIR / "consistency.json"

TODAY = dt.date(2026, 8, 26)
SEED_DEFAULT = 20260826

# 季报章节结构：对齐真实季报（章节标题为行业惯例固定结构）。
# 每章节一个渲染函数：SimModel → (正文段落列表, 文本事实清单)。
SECTION_TITLES = [
    "重要提示",
    "基金产品概况",
    "主要财务指标",
    "管理人报告",
    "投资组合",
]


# ---------------------------------------------------------------------------
# 季报正文渲染（SimModel → 段落文本 + 事实指纹）
# ---------------------------------------------------------------------------
class ReportFacts:
    """一份季报的文本事实清单（供一致性清单与 CI 断言）。"""

    def __init__(self, doc_id: str, fund_code: str):
        self.doc_id = doc_id
        self.fund_code = fund_code
        self.facts: list[dict] = []   # {section, kind, text, graph}

    def add(self, section: str, kind: str, text: str, graph: str) -> None:
        self.facts.append({"section": section, "kind": kind,
                           "text": text, "graph": graph})


def _fund_display(f: dict) -> str:
    return f["fund_name"]


def _risk_zh(vocab: OntologyVocabulary, risk_level_local: str) -> str:
    # risk_level 形如 "FundRiskLevelR3"；代码概念在 cnfc 词表里有中文标签
    code = risk_level_local.replace("FundRiskLevel", "")
    scheme, label = vocab.code_concepts.get(code, ("", code))
    return label


def _op_mode_zh(f: dict) -> str:
    return "开放式" if f["is_open_ended"] else "封闭式"


def render_section_notice(f: dict, depositary_name: str) -> list[str]:
    text = (f"基金管理人的董事会及董事保证本报告所载资料不存在虚假记载、"
            f"误导性陈述或重大遗漏，并对其内容的真实性、准确性和完整性承担"
            f"个别及连带责任。")
    text2 = (f"基金托管人{depositary_name}已复核了本报告中的财务指标、"
             f"净值表现和投资组合报告等内容，保证复核内容不存在虚假记载、"
             f"误导性陈述或者重大遗漏。")
    return [text, text2]


def render_section_overview(f: dict, manager_name: str, company_name: str,
                            vocab: OntologyVocabulary, facts: ReportFacts) -> list[str]:
    risk_zh = _risk_zh(vocab, f["risk_level"])
    paras = [
        (f"{_fund_display(f)}（基金代码：{f['fund_code']}，简称：{f['fund_short_name']}）"
         f"为{_op_mode_zh(f)}基金，基金管理人为{company_name}，"
         f"基金经理为{manager_name}，风险等级为{risk_zh}。"),
    ]
    facts.add("基金产品概况", "manager", manager_name,
              f"hasFundManager → {manager_name}")
    facts.add("基金产品概况", "risk_level", risk_zh, f"hasFundRiskLevel → {f['risk_level']}")
    facts.add("基金产品概况", "operation_mode", _op_mode_zh(f), f"基金运作方式 → {f['operation_mode']}")
    return paras


def render_section_financial(model, f: dict, quarter_end: dt.date,
                             facts: ReportFacts) -> list[str]:
    # 期末净值：取该基金最新估值日（≤ 季度末）的首个份额单位净值
    nav = _latest_nav(model, f["fund_code"], quarter_end)
    if nav is None:
        return ["报告期内无净值记录。"]
    date_s, unit_nav, acc_nav = nav
    text = (f"报告期末（{date_s}），基金份额单位净值为 {unit_nav} 元，"
            f"累计单位净值为 {acc_nav} 元。")
    facts.add("主要财务指标", "unit_nav", f"{unit_nav}",
              f"fundUnitNetAssetValue → {unit_nav} @ {date_s}")
    facts.add("主要财务指标", "acc_nav", f"{acc_nav}",
              f"accumulatedUnitNetAssetValue → {acc_nav} @ {date_s}")
    return [text]


def render_section_manager(f: dict, manager_name: str, quarter_label: str,
                           style_hint: str, facts: ReportFacts) -> list[str]:
    # 运作回顾 + 未来展望：观点文本按风格参数化；经理名与基金名与图一致
    review = (f"{quarter_label}，本基金管理人坚持既定的投资策略与风险控制原则，"
              f"围绕{style_hint}进行组合管理，保持了基金合同的约定运作。")
    outlook = (f"展望后市，基金经理{manager_name}认为市场结构性机会与波动并存，"
               f"本基金将继续在严格控制风险的前提下，动态优化{style_hint}方向的"
               f"组合配置，力争为基金份额持有人创造长期稳健回报。")
    facts.add("管理人报告", "manager", manager_name,
              f"hasFundManager → {manager_name}")
    return [review, outlook]


def render_section_portfolio(model, f: dict, facts: ReportFacts) -> list[str]:
    # 投资组合：模拟数据的持仓快照是单一时点（as_of_date），如实标注该时点，
    # 不冒充报告期末持仓。数字全部来自 portfolio_positions 的精确值。
    positions = [p for p in model.portfolio_positions
                 if p["fund_code"] == f["fund_code"]]
    if not positions:
        return ["本基金暂无持仓记录。"]
    as_of = positions[0]["as_of_date"]
    positions.sort(key=lambda p: p["market_value"], reverse=True)
    top = positions[:10]
    lines = [f"截至 {as_of}，本基金投资组合前十大持仓（按公允价值排序）："]
    for i, p in enumerate(top, 1):
        asset = next(a for a in model.assets if a["asset_id"] == p["asset_id"])
        lines.append(f"{i}. {asset['asset_name']}：持仓数量 {p['quantity']:g}，"
                     f"公允价值 {p['market_value']:,.2f} 元（{p['currency']}）。")
        facts.add("投资组合", "position",
                  f"{asset['asset_name']} {p['quantity']:g} {p['market_value']:g}",
                  f"portfolioPositions → {p['asset_id']} qty={p['quantity']} mv={p['market_value']} as_of={as_of}")
    return lines


def _latest_nav(model, fund_code: str, on_or_before: dt.date):
    """≤ on_or_before 的最新单位净值（A 类份额优先）。"""
    candidates = [n for n in model.navs
                  if n["fund_code"] == fund_code
                  and dt.date.fromisoformat(n["valuation_date"]) <= on_or_before]
    if not candidates:
        return None
    candidates.sort(key=lambda n: (n["valuation_date"], n["unit_code"] or ""))
    # 取最新估值日；同一日多份额取 unit_code 最小（A 类）
    latest_date = candidates[-1]["valuation_date"]
    same_day = [n for n in candidates if n["valuation_date"] == latest_date]
    same_day.sort(key=lambda n: n["unit_code"] or "")
    n = same_day[0]
    return (n["valuation_date"], f"{n['unit_nav']:.4f}", f"{n['accumulated_unit_nav']:.4f}")


def quarter_ends(count: int) -> list[tuple[str, dt.date, dt.date, dt.date]]:
    """最近 count 个季度：(period 标识, 起, 止, 披露截止)。以 TODAY 为锚。"""
    out = []
    y, m = TODAY.year, TODAY.month
    # 对齐到已完成的最近季度末
    q = (m - 1) // 3  # 0..3
    for _ in range(count):
        if q == 0:
            y, q = y - 1, 4
        start = dt.date(y, (q - 1) * 3 + 1, 1)
        end = dt.date(y, q * 3 + 1, 1) - dt.timedelta(days=1) if q < 4 else dt.date(y, 12, 31)
        period = f"{y}-Q{q}"
        deadline = end + dt.timedelta(days=15 * 7 // 5)  # 15 个工作日近似
        out.append((period, start, end, deadline))
        q -= 1
    return list(reversed(out))


def build_reports(model, vocab: OntologyVocabulary, quarters: int) -> tuple[Graph, dict]:
    """季报：A-BOX 报告/章节实体 + md 正文 + 事实清单。"""
    g = Graph()
    g.bind("cnfo", CNFO)
    g.bind("cnfo-a", CNFOA)
    chunks: list[dict] = []
    facts_by_doc: dict[str, ReportFacts] = {}

    manager_by_fund = {m["fund_code"]: m["manager_name"] for m in model.managers}
    party_by_id = {p["party_id"]: p for p in model.parties}

    for period, q_start, q_end, _deadline in quarter_ends(quarters):
        quarter_label = f"{period.replace('-', '年').replace('Q', '第')}季度"
        for f in model.funds:
            # 成立晚于季度末的基金不编制当期报告（披露办法第四章）
            if dt.date.fromisoformat(f["inception_date"]) > q_end:
                continue
            code = f["fund_code"]
            doc_id = f"qtr-{period}-{code}"
            report = CNFOA[f"Report{period.replace('-', '')}F{code}"]
            g.add((report, RDF.type, CNFO.FundQuarterlyReport))
            g.add((report, RDFS.label,
                   Literal(f"{_fund_display(f)}{period.replace('-', '年').replace('Q', '第')}季度报告")))
            g.add((report, CNFO.reportForFund, CNFOA[f"F{code}"]))
            g.add((report, CNFO.reportPeriod, Literal(period)))
            g.add((report, CNFO.reportPeriodStart, Literal(q_start.isoformat(), datatype=XSD.date)))
            g.add((report, CNFO.reportPeriodEnd, Literal(q_end.isoformat(), datatype=XSD.date)))
            g.add((report, CNFO.reportType, Literal("quarterly")))

            manager_name = manager_by_fund.get(code, "（未设基金经理）")
            company = party_by_id.get(f["company_id"], {})
            company_name = company.get("name_zh", "（未知管理人）")
            depositary = party_by_id.get(f["depositary_id"], {})
            depositary_name = depositary.get("name_zh", "（未知托管人）")
            style = next((s for s in model.strategies if s["fund_code"] == code), {})
            style_hint = (style.get("investment_focus") or "既定投资策略").replace("（仿真）", "").replace("主要投资于", "").replace("主题相关资产", "主题")

            facts = ReportFacts(doc_id, code)
            sections: list[tuple[str, list[str]]] = [
                ("重要提示", render_section_notice(f, depositary_name)),
                ("基金产品概况", render_section_overview(f, manager_name, company_name, vocab, facts)),
                ("主要财务指标", render_section_financial(model, f, q_end, facts)),
                ("管理人报告", render_section_manager(f, manager_name, quarter_label, style_hint, facts)),
                ("投资组合", render_section_portfolio(model, f, facts)),
            ]
            for order, (title, paras) in enumerate(sections, 1):
                sec_iri = CNFOA[f"Section{period.replace('-', '')}F{code}S{order}"]
                g.add((sec_iri, RDF.type, CNFO.ReportSection))
                g.add((sec_iri, RDFS.label, Literal(f"{_fund_display(f)}·{title}")))
                g.add((sec_iri, CNFO.sectionOf, report))
                g.add((sec_iri, CNFO.sectionTitle, Literal(title)))
                g.add((sec_iri, CNFO.sectionOrder, Literal(order, datatype=XSD.integer)))
                body = "\n".join(paras)
                g.add((sec_iri, CNFO.sectionHasContent, Literal(body)))
                g.add((report, CNFO.hasReportSection, sec_iri))
                chunks.append({
                    "chunk_id": f"{doc_id}#s{order}",
                    "doc_id": doc_id,
                    "fund_code": code,
                    "doc_type": "periodic_report",
                    "period": period,
                    "section": title,
                    "text": body,
                    "locator": {"entity": f"Section{period.replace('-', '')}F{code}S{order}"},
                })
            facts_by_doc[doc_id] = facts
    return g, {"chunks": chunks, "facts": facts_by_doc}


# ---------------------------------------------------------------------------
# 法规条文：从图上仿真约束反向生成
# ---------------------------------------------------------------------------
# 投资比例约束（数值与《公开募集证券投资基金运作管理办法》第三十二条对齐，
# 作为仿真法条正文；引用关系挂回图上的 Fund → governedByRegulation）
ARTICLE_TEMPLATES = [
    {
        "regulation": "JL-002",
        "number": "第三十二条",
        "text": "基金管理人运用基金财产进行证券投资，不得有下列情形："
                "一只基金持有一家公司发行的证券，其市值超过基金资产净值的百分之十；"
                "同一基金管理人管理的全部基金持有一家公司发行的证券，超过该证券的百分之十。"
                "完全按照有关指数的构成比例进行证券投资的基金品种可以不受前述比例限制。",
        "cites_codes": [],
        "kind": "restriction",
    },
    {
        "regulation": "JL-004",
        "number": "第十五条",
        "text": "基金管理人应当在每年结束之日起三个月内编制完成基金年度报告，"
                "在上半年结束之日起两个月内编制完成基金中期报告，"
                "在季度结束之日起十五个工作日内编制完成基金季度报告。"
                "年度报告中的财务会计报告应当经过审计。",
        "cites_codes": [],
        "kind": "disclosure_deadline",
    },
    {
        "regulation": "JL-004",
        "number": "第十七条",
        "text": "基金季度报告应当至少载明以下内容：基金产品概况、主要财务指标、"
                "管理人报告、投资组合报告等信息。报告正文应当在规定报刊和规定网站披露。",
        "cites_codes": [],
        "kind": "disclosure_content",
    },
    {
        "regulation": "JL-005",
        "number": "第八条",
        "text": "基金募集机构应当按照适当性原则，将合适的产品销售给合适的投资者。"
                "基金产品风险等级按风险由低到高至少划分为 R1、R2、R3、R4、R5 五个等级，"
                "与投资者风险承受能力评级 C1 至 C5 相匹配。"
                "投资者风险承受能力评级应当与基金产品风险等级相匹配，"
                "不匹配的不得主动推介。",
        "cites_codes": ["R1", "R2", "R3", "R4", "R5"],
        "kind": "suitability",
    },
    {
        "regulation": "JL-003",
        "number": "第十四条",
        "text": "私募基金管理人应当根据私募基金的投资范围、投资策略、风险收益特征"
                "确定私募基金的风险等级。私募基金应当向合格投资者募集，"
                "单只私募基金的投资者人数累计不得超过法律规定的人数限制。",
        "cites_codes": [],
        "kind": "private_offering",
    },
    {
        "regulation": "JL-001",
        "number": "第五条",
        "text": "从事基金活动，应当遵循自愿、公平、诚实信用原则，不得损害国家利益、"
                "社会公共利益和投资者合法权益。基金管理人、基金托管人和其他基金服务机构"
                "应当恪尽职守，履行诚实信用、谨慎勤勉的义务。",
        "cites_codes": [],
        "kind": "general_principle",
    },
]


def build_articles(vocab: OntologyVocabulary) -> tuple[Graph, list[dict]]:
    """条文实体 + 条文 chunk（articleText 与图一致）。"""
    g = Graph()
    g.bind("cnfo", CNFO)
    g.bind("cnfo-a", CNFOA)
    g.bind("cnfc", CNFC)
    chunks: list[dict] = []
    for art in ARTICLE_TEMPLATES:
        reg_code = art["regulation"]
        # IRI 与主 A-BOX 的 Regulation 实体对齐：Reg{code}（code 含连字符，如 RegJL-001）
        number_local = art["number"].replace("第", "").replace("条", "")
        art_iri = CNFOA[f"Article{reg_code}{number_local}"]
        reg_uri = CNFOA[f"Reg{reg_code}"]
        g.add((art_iri, RDF.type, CNFO.RegulationArticle))
        g.add((art_iri, RDFS.label,
               Literal(f"{reg_code} {art['number']}")))
        g.add((art_iri, CNFO.articleOf, reg_uri))
        g.add((reg_uri, CNFO.hasRegulationArticle, art_iri))
        g.add((art_iri, CNFO.articleNumber, Literal(art["number"])))
        g.add((art_iri, CNFO.articleText, Literal(art["text"])))
        for code in art["cites_codes"]:
            # 代码概念本地名（如 FundRiskLevelR4）直接构造；缺失时跳过不阻断
            local_name = code if code.startswith("FundRiskLevel") else f"FundRiskLevel{code}"
            iri = CNFC[local_name]
            if (iri, None, None) in vocab.graph:
                g.add((art_iri, CNFO.articleCitesCode, iri))
        chunks.append({
            "chunk_id": f"article-{reg_code}-{art['number']}",
            "doc_id": f"regulation-{reg_code}",
            "fund_code": None,
            "doc_type": "regulation_article",
            "period": None,
            "section": art["number"],
            "text": art["text"],
            "locator": {"entity": local(art_iri)},
        })
    return g, chunks


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CNFO 文本资产生成器（季报 + 法规条文）")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT, help="随机种子（须与 gen_sim_abox 一致）")
    ap.add_argument("--funds", type=int, default=40, help="基金数量（默认 40，须与 gen_sim_abox 一致）")
    ap.add_argument("--days", type=int, default=356, help="净值序列交易日数（默认 356）")
    ap.add_argument("--quarters", type=int, default=2, help="生成最近几个季度的季报（默认 2）")
    ap.add_argument("--no-reports", action="store_true", help="不生成季报")
    ap.add_argument("--no-articles", action="store_true", help="不生成法规条文")
    ap.add_argument("--no-md", action="store_true", help="不导出报告 md 正文（只出 TTL + chunks）")
    args = ap.parse_args(argv)

    print(f"[1/4] 加载本体: {TBOX_ENTRY.relative_to(ROOT)}")
    graph = load_ontology_graph(TBOX_ENTRY)
    vocab = OntologyVocabulary(graph)

    print(f"[2/4] 重建仿真数据（seed={args.seed}, funds={args.funds}, days={args.days}）")
    model = generate(vocab, args.funds, args.days, args.seed)

    print(f"[3/4] 生成文本资产")
    out = Graph()
    all_chunks: list[dict] = []
    consistency: dict = {"reports": {}, "articles": []}

    if not args.no_articles:
        art_g, art_chunks = build_articles(vocab)
        out += art_g
        all_chunks.extend(art_chunks)
        consistency["articles"] = [
            {"regulation": c["doc_id"], "number": c["section"],
             "text_in_graph": True}
            for c in art_chunks]
        print(f"      法规条文：{len(art_chunks)} 条")

    if not args.no_reports:
        rep_g, rep_out = build_reports(model, vocab, args.quarters)
        out += rep_g
        all_chunks.extend(rep_out["chunks"])
        for doc_id, facts in rep_out["facts"].items():
            consistency["reports"][doc_id] = facts.facts
        print(f"      季报：{len(rep_out['facts'])} 份，章节 chunk：{len(rep_out['chunks'])} 个")

    REPORTS_TTL.parent.mkdir(parents=True, exist_ok=True)
    out.serialize(destination=str(REPORTS_TTL), format="turtle")
    check = Graph(); check.parse(str(REPORTS_TTL), format="turtle")
    print(f"[4/4] 写出：{REPORTS_TTL.relative_to(ROOT)}（{len(check)} 三元组，回读一致: {len(check) == len(out)}）")

    RAG_DIR.mkdir(parents=True, exist_ok=True)
    with CHUNKS_JSONL.open("w", encoding="utf-8") as fh:
        for c in all_chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    CONSISTENCY_JSON.write_text(
        json.dumps(consistency, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"      chunks: {CHUNKS_JSONL.relative_to(ROOT)}（{len(all_chunks)} 条）")
    print(f"      一致性清单: {CONSISTENCY_JSON.relative_to(ROOT)}")

    if not args.no_md and not args.no_reports:
        md_dir = REPORTS_MD_DIR
        md_dir.mkdir(parents=True, exist_ok=True)
        by_doc: dict[str, dict] = {}
        for c in all_chunks:
            if c["doc_type"] != "periodic_report":
                continue
            by_doc.setdefault(c["doc_id"], {})[c["section"]] = c
        for doc_id, secs in by_doc.items():
            lines = [f"# {doc_id}", ""]
            for title in SECTION_TITLES:
                c = secs.get(title)
                if c:
                    lines += [f"## {title}", "", c["text"], ""]
            (md_dir / f"{doc_id}.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"      报告正文: {md_dir.relative_to(ROOT)}（{len(by_doc)} 份 md）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
