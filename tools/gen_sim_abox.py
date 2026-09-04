# -*- coding: utf-8 -*-
"""CNFO 仿真 A-BOX 生成器：根据当前最新版本体生成一批仿真业务数据。

数据来源（运行时加载，跟随本体最新版本）：
- 本体入口: ontology/modules/cnfo-domain.ttl（经 load_ontology_graph 递归加载
  cnfo-fund.ttl / cnfo-fund-codes.ttl / cnfo-module-vocabulary.ttl）
- 标准代码概念: 直接从本体图中提取 cnfc: 下的 SKOS 受控代码表
- 生命周期状态类: 由 cnfo:FundLifecycleStatus 的子类推导

产出：
- SQLite 数据库 artifacts/cnfo/abox/cnfo-sim.sqlite（主交付物，规范化镜像
  本体中的核心业务类与关系）
- Turtle A-BOX artifacts/cnfo/abox/cnfo-sim-abox.ttl（默认导出；标准 A-BOX
  实例图，含 owl:Ontology 数据集头与 owl:imports，不含任何 T-BOX 声明）
- Semantica Explorer 图 artifacts/cnfo/abox/cnfo-sim-explorer.json（默认导出；
  nodes/edges 格式与 cnfo-fund-tbox-explorer.json 一致，可直接
  GraphSession.from_file 加载，或 POST /api/import 导入；不含 owl:Ontology 数据集头，
  避免被 Ontology Hub 推断为“本体”条目）
- T-BOX + A-BOX 会话图 artifacts/cnfo/abox/cnfo-sim-session.json（默认导出；合并
  cnfo-fund-tbox-explorer.json 与 A-BOX 图，补上真正的 T-BOX 本体节点与
  scheme_uri 标注，Ontology 面板会显示设计的 T-BOX 及其类/属性计数）
- 内置 SHACL 校验：用 ontology/shacl/cnfo-fund-shapes.ttl 对生成的 A-BOX
  做数据质量校验，打印 conforms 结论与违规统计

全部人名、机构名、基金名、资产名为仿真虚构，与任何真实机构无关。

用法：
    .venv\\Scripts\\python.exe tools\\gen_sim_abox.py [--funds 40] [--days 356]
        [--seed 20260826] [--no-export-ttl] [--no-validate]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rdflib
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

from fondontology.ontology_loader import load_ontology_graph

ROOT = Path(__file__).resolve().parents[1]
TBOX_ENTRY = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
SHAPES = ROOT / "ontology" / "shacl" / "cnfo-fund-shapes.ttl"
ABOX_DIR = ROOT / "artifacts" / "cnfo" / "abox"
DB_PATH = ABOX_DIR / "cnfo-sim.sqlite"
TTL_PATH = ABOX_DIR / "cnfo-sim-abox.ttl"
EXPLORER_JSON_PATH = ABOX_DIR / "cnfo-sim-explorer.json"

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFC = Namespace("https://ontology.example.cn/cnfo/code/")
CNFOM = Namespace("https://ontology.example.cn/cnfo/module/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")

TODAY = dt.date(2026, 8, 26)
SEED_DEFAULT = 20260826


# ---------------------------------------------------------------------------
# 名称素材池（全部为仿真虚构）
# ---------------------------------------------------------------------------
COMPANY_NAMES = [
    ("华曦基金管理有限公司", "华曦基金"),
    ("磐石基金管理有限公司", "磐石基金"),
    ("云帆基金管理股份有限公司", "云帆基金"),
    ("恒信基金管理有限公司", "恒信基金"),
]
BANK_NAMES = [
    ("蓝海银行股份有限公司", "蓝海银行"),
    ("曦岳银行股份有限公司", "曦岳银行"),
    ("岷江银行股份有限公司", "岷江银行"),
    ("澜舟银行股份有限公司", "澜舟银行"),
]
AGENT_NAMES = [
    ("信达财富基金销售有限公司", "信达财富"),
    ("汇泓基金销售股份有限公司", "汇泓销售"),
    ("安澜财富基金销售有限公司", "安澜财富"),
]
REGISTRAR_NAMES = [
    ("中证登记结算有限责任公司（示例）", "示例登记结算"),
    ("华登基金登记服务有限公司", "华登登记"),
]
SUPERVISOR_NAMES = [
    ("中国基金业监督管理委员会（仿真）", "仿真监管局"),
]
SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
GIVEN_M = ["伟", "强", "磊", "军", "洋", "勇", "杰", "涛", "明", "超", "刚", "平", "辉", "鹏", "宇", "浩", "凯", "磊"]
GIVEN_F = ["芳", "娜", "敏", "静", "丽", "娟", "艳", "燕", "玲", "蕾", "颖", "霞", "雪", "梅", "秀英", "晓红"]
FUND_STYLES = [
    ("稳健成长", "稳健", "hybrid"),
    ("价值精选", "价值", "equity"),
    ("科技创新", "科技", "equity"),
    ("医疗健康", "医疗", "hybrid"),
    ("消费升级", "消费", "equity"),
    ("新能源", "新能源", "equity"),
    ("高端制造", "制造", "equity"),
    ("红利低波", "红利", "bond"),
    ("纯债", "纯债", "bond"),
    ("短债", "短债", "bond"),
    ("货币", "货币", "money"),
    ("沪深300", "沪深300", "index"),
    ("中证500", "中证500", "index"),
    ("创业板指", "创业", "index"),
    ("标普500", "标普500", "qdii"),
    ("香港恒生", "恒生", "qdii"),
    ("优选FOF", "FOF", "fof"),
    ("养老目标", "养老", "fof"),
]
ASSET_TYPE_MAP = {
    "equity": ("股票投资资产", "equity"),
    "hybrid": ("股票投资资产", "equity"),
    "bond": ("债券投资资产", "debt"),
    "money": ("货币市场工具", "mm"),
    "index": ("股票投资资产", "equity"),
    "qdii": ("股票投资资产", "equity"),
    "fof": ("基金投资资产", "fund"),
    "private-equity": ("股权投资资产", "equity"),
    "private-sec": ("股票投资资产", "equity"),
}
EQUITY_ASSETS = [
    "清泉信息科技股份有限公司", "南山新能源股份有限公司", "北辰半导体股份有限公司",
    "澜山生物医药股份有限公司", "云图人工智能股份有限公司", "星澜智能制造股份有限公司",
    "旭日光伏科技股份有限公司", "青禾消费电子股份有限公司", "东辰航天科技股份有限公司",
    "琼华新材料股份有限公司", "瀚海物流股份有限公司", "白鹭航运股份有限公司",
    "川岳食品股份有限公司", "听澜文化传媒股份有限公司", "若水医疗器械股份有限公司",
    "栖霞软件股份有限公司", "苍梧生态农业股份有限公司", "昭明乳业股份有限公司",
]
BOND_ASSETS = [
    "示例国债2026", "示例政策性金融债2026", "示例城投债2026",
    "示例公司债AAA", "示例中票AA+", "示例短融AA", "示例可转债",
]
MM_ASSETS = [
    "示例央行票据", "示例同业存单", "示例银行间回购", "示例国债逆回购",
]
CASH_ASSETS = ["示例银行存款活期", "示例银行协议存款"]
INDEX_ASSETS = ["示例沪深300指数期货"]


def local(uri: URIRef) -> str:
    s = str(uri)
    for ns in (str(CNFO), str(CNFC)):
        if s.startswith(ns):
            return s[len(ns):]
    return s.rsplit("/", 1)[-1]


def zh_label(graph: Graph, uri: URIRef, default: str = "") -> str:
    for pred in (SKOS.prefLabel, RDFS.label):
        for o in graph.objects(uri, pred):
            if getattr(o, "language", None) == "zh":
                return str(o)
    return default or local(uri)


def dec_lit(x) -> Literal:
    """生成词法形式干净的 xsd:decimal 字面量（浮点值先经 Decimal 规整）。"""
    if x is None:
        return Literal("0", datatype=XSD.decimal)
    return Literal(format(Decimal(str(x)), "f"), datatype=XSD.decimal)


# ---------------------------------------------------------------------------
# 本体词汇提取（“基于当前最新版本体”的核心）
# ---------------------------------------------------------------------------
class OntologyVocabulary:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.ontology_version = self._version()
        # cnfc 标准代码概念：code -> (scheme, label)
        self.code_concepts: dict[str, tuple[str, str]] = {}
        self.code_schemes: dict[str, str] = {}
        for code in graph.subjects(SKOS.inScheme, None):
            if not str(code).startswith(str(CNFC)):
                continue
            for scheme in graph.objects(code, SKOS.inScheme):
                scheme_local = local(scheme)
                break
            else:
                scheme_local = "General"
            self.code_concepts[str(code)[len(str(CNFC)):]] = (
                scheme_local,
                zh_label(graph, code, str(code)[len(str(CNFC)):]),
            )
            self.code_schemes.setdefault(scheme_local, str(scheme))
        # 生命周期状态类（FundLifecycleStatus 的子类）
        self.lifecycle_statuses: dict[str, str] = {}
        for cls in graph.transitive_subjects(RDFS.subClassOf, CNFO.FundLifecycleStatus):
            if cls == CNFO.FundLifecycleStatus or not isinstance(cls, URIRef):
                continue
            if (cls, RDF.type, OWL.Class) not in graph:
                continue
            self.lifecycle_statuses[local(cls)] = zh_label(graph, cls, local(cls))

    def _version(self) -> str:
        for o in self.graph.objects(CNFO.CNFODomain, OWL.versionInfo):
            return str(o)
        return "unknown"

    def code_iri(self, scheme: str, code: str) -> URIRef:
        for s, o in self.graph.subject_objects(SKOS.prefLabel):
            pass
        for s in self.graph.subjects(SKOS.inScheme, URIRef(self.code_schemes.get(scheme, ""))):
            if str(s).startswith(str(CNFC)) and str(s)[len(str(CNFC)):] == code:
                return s
        raise KeyError(f"code not found: {scheme}/{code}")

    def all_code_iris(self) -> list[URIRef]:
        return [URIRef(str(CNFC) + c) for c in self.code_concepts]


# ---------------------------------------------------------------------------
# 仿真数据模型
# ---------------------------------------------------------------------------
class SimModel:
    """在内存中组装仿真数据，同时供给 SQLite 写入与 RDF 构建。"""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.parties: list[dict] = []
        self.regulations: list[dict] = []
        self.supervisors: list[dict] = []
        self.indices: list[dict] = []
        self.funds: list[dict] = []
        self.products: list[dict] = []
        self.managers: list[dict] = []
        self.units: list[dict] = []
        self.subscription_terms: list[dict] = []
        self.redemption_terms: list[dict] = []
        self.roles: list[dict] = []
        self.assignments: list[dict] = []
        self.status_records: list[dict] = []
        self.strategies: list[dict] = []
        self.objectives: list[dict] = []
        self.assets: list[dict] = []
        self.portfolio_positions: list[dict] = []
        self.fees: list[dict] = []
        self.performances: list[dict] = []
        self.benchmarks: list[dict] = []
        self.fund_regulations: list[dict] = []
        self.investors: list[dict] = []
        self.accounts: list[dict] = []
        self.positions: list[dict] = []
        self.navs: list[dict] = []
        # 无在管基金的经理自然人（合法存在：在职未分派，仅 type+label，无 playsFundRole 边）
        self.unassigned_managers: list[str] = []


def trading_days(end: dt.date, count: int) -> list[dt.date]:
    days: list[dt.date] = []
    d = end
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d)
        d -= dt.timedelta(days=1)
    return list(reversed(days))


def pick(rng: random.Random, seq: list[str]) -> str:
    return seq[rng.randrange(len(seq))]


def gen_code(rng: random.Random, tables: dict[str, set[str]], block: int, size: int) -> str:
    for _ in range(200):
        code = f"{block:03d}{rng.randrange(10 ** size):0{size}d}"
        if code not in tables.setdefault("fund", set()):
            tables["fund"].add(code)
            return code
    raise RuntimeError("too many collisions")


def generate(vocab: OntologyVocabulary, funds_count: int, days_count: int, seed: int) -> SimModel:
    rng = random.Random(seed)
    m = SimModel(rng)

    # ---- 参与主体 ----
    for i, (name, short) in enumerate(COMPANY_NAMES):
        m.parties.append({"party_id": i + 1, "party_kind": "fund_management_company",
                          "name_zh": name, "short_name": short})
    next_party_id = len(COMPANY_NAMES) + 1
    for i, (name, short) in enumerate(BANK_NAMES):
        m.parties.append({"party_id": next_party_id + i, "party_kind": "depositary_bank",
                          "name_zh": name, "short_name": short})
    next_party_id += len(BANK_NAMES)
    for i, (name, short) in enumerate(AGENT_NAMES):
        m.parties.append({"party_id": next_party_id + i, "party_kind": "fund_sales_agent",
                          "name_zh": name, "short_name": short})
    next_party_id += len(AGENT_NAMES)
    for i, (name, short) in enumerate(REGISTRAR_NAMES):
        m.parties.append({"party_id": next_party_id + i, "party_kind": "fund_registrar",
                          "name_zh": name, "short_name": short})
    next_party_id += len(REGISTRAR_NAMES)
    for i, (name, short) in enumerate(SUPERVISOR_NAMES):
        m.parties.append({"party_id": next_party_id + i, "party_kind": "fund_supervisor",
                          "name_zh": name, "short_name": short})

    # ---- 法规与监管机构 ----
    regulations = [
        ("JL-001", "证券投资基金监督管理条例（仿真）", "第一章 总则"),
        ("JL-002", "公开募集证券投资基金运作管理办法（仿真）", "第二章 基金运作"),
        ("JL-003", "私募投资基金监督管理暂行办法（仿真）", "第三章 私募基金募集"),
        ("JL-004", "基金信息披露管理办法（仿真）", "第四章 信息披露"),
        ("JL-005", "基金募集机构投资者适当性管理指引（仿真）", "第五章 适当性管理"),
    ]
    for i, (code, title, article) in enumerate(regulations):
        m.regulations.append({"regulation_code": code, "regulation_title": title,
                              "article_reference": article})
    supervisor_ids = [p["party_id"] for p in m.parties if p["party_kind"] == "fund_supervisor"]
    m.supervisors.append({"supervisor_id": supervisor_ids[0], "name_zh": SUPERVISOR_NAMES[0][0]})

    # ---- 市场指数 ----
    index_defs = [
        ("SX.900001", "仿真沪深300指数", "CNY"),
        ("SX.900002", "仿真中证500指数", "CNY"),
        ("SX.900003", "仿真创业板指数", "CNY"),
        ("SX.900004", "仿真标普500指数", "USD"),
        ("SX.900005", "仿真恒生指数", "HKD"),
    ]
    compiler_id = m.parties[0]["party_id"]
    for i, (code, name, cur) in enumerate(index_defs):
        m.indices.append({"index_code": code, "index_name": name, "index_currency": cur,
                          "compiler_party_id": compiler_id})

    # ---- 基金集合 ----
    type_blocks = {
        "equity": (1, 3), "hybrid": (2, 3), "bond": (4, 3), "money": (5, 2),
        "index": (6, 3), "etf": (51, 2), "fof": (7, 2), "qdii": (8, 2),
        "private-equity": (9, 2), "private-sec": (10, 2),
    }
    used_codes: set[str] = set()

    def new_code(block: int) -> str:
        for _ in range(500):
            code = f"{block:03d}{rng.randrange(1000):03d}"
            if code not in used_codes:
                used_codes.add(code)
                return code
        raise RuntimeError("code block exhausted")

    total_target = funds_count
    order = list(type_blocks)
    # 先按类型轮询分配，保证类型分布均衡
    plan: list[str] = []
    while len(plan) < total_target:
        for t in order:
            if len(plan) < total_target:
                plan.append(t)
    # 固定每个类型至少 1 只
    for t in ("private-equity", "private-sec", "money", "etf", "qdii", "fof"):
        if t not in plan[:total_target]:
            plan.insert(0, t)

    fund_idx = 0
    for fi, ftype in enumerate(plan[:total_target]):
        if ftype in ("etf",):
            ftype_eff = "index"
        else:
            ftype_eff = ftype
        company = COMPANY_NAMES[fi % len(COMPANY_NAMES)]
        bank = BANK_NAMES[fi % len(BANK_NAMES)]
        agent = AGENT_NAMES[fi % len(AGENT_NAMES)]
        block = type_blocks[ftype][0]
        code = new_code(block)
        style_tag = {
            "equity": "equity", "hybrid": "hybrid", "bond": "bond", "money": "money",
            "index": "index", "etf": "index", "qdii": "qdii", "fof": "fof",
            "private-equity": "equity", "private-sec": "hybrid",
        }[ftype]
        style_pool = [s for s in FUND_STYLES if s[2] == style_tag]
        style, style_short, _ = style_pool[(fi * 3 + fund_idx) % len(style_pool)]
        suffix_map = {
            "equity": "股票型证券投资基金", "hybrid": "混合型证券投资基金",
            "bond": "债券型证券投资基金", "money": "货币市场基金",
            "index": "指数型证券投资基金", "etf": "交易型开放式指数证券投资基金",
            "fof": "基金中基金（FOF）", "qdii": "合格境内机构投资者（QDII）证券投资基金",
            "private-equity": "私募股权投资基金", "private-sec": "私募证券投资基金",
        }
        fund_name = f"{company[1].replace('基金', '')}{style}{suffix_map[ftype]}"
        short_name = f"{company[1].replace('基金', '')}{style_short}"
        inception = dt.date(2012, 1, 1) + dt.timedelta(days=rng.randrange(0, 14 * 365))
        if inception > TODAY:
            inception = TODAY - dt.timedelta(days=rng.randrange(100, 400))
        is_private = ftype.startswith("private")
        is_open = ftype not in ("private-equity",) and rng.random() > 0.06
        is_etf = ftype == "etf"
        is_mm = ftype == "money"
        risk_map = {"equity": "R4", "hybrid": "R3", "bond": "R2", "money": "R1",
                    "index": "R4", "etf": "R4", "fof": "R3", "qdii": "R5",
                    "private-equity": "R5", "private-sec": "R4"}
        op_mode = "FundOperationModeOpenEnded" if is_open else "FundOperationModeClosedEnded"
        org_form = "FundOrganizationFormContractual"
        status = "OperatingStatus"
        terminated = False
        if (not is_private) and rng.random() < 0.06 and len(m.funds) >= 3:
            terminated = True
            status = "TerminatedStatus"
            termination = TODAY - dt.timedelta(days=rng.randrange(60, 500))
            if termination < inception:
                termination = inception + dt.timedelta(days=400)
        fund = {
            "fund_code": code,
            "fund_name": fund_name,
            "fund_short_name": short_name,
            "company_id": company[0] and next(p["party_id"] for p in m.parties
                                              if p["name_zh"] == company[0]),
            "depositary_id": next(p["party_id"] for p in m.parties if p["name_zh"] == bank[0]),
            "fund_type": ftype,
            "public_private": "private" if is_private else "public",
            "operation_mode": op_mode,
            "organization_form": org_form,
            "risk_level": f"FundRiskLevel{risk_map[ftype]}",
            "status_code": status,
            "is_open_ended": int(is_open),
            "is_exchange_traded": int(is_etf),
            "is_private": int(is_private),
            "inception_date": inception.isoformat(),
            "termination_date": termination.isoformat() if terminated else None,
            "base_currency": "CNY",
            "filing_number": f"PF{code}" if is_private else (None if rng.random() < 0.5 else f"RC{code}"),
            "registration_number": f"REG{code}" if not is_private else None,
            "fund_type_code": ftype.upper(),
            "source_identifier": f"SIM-{code}",
        }
        m.funds.append(fund)
        product = {"fund_code": code, "product_name": f"{fund_name}（产品）"}
        m.products.append(product)
        m.managers.append({"fund_code": code,
                           "manager_name": pick(rng, SURNAMES) + pick(rng, GIVEN_M),
                           "manager_title": "基金经理"})
        m.strategies.append({
            "fund_code": code,
            "strategy_type": "IndexTrackingStrategy" if ftype in ("index", "etf") else "ActiveInvestmentStrategy",
            "investment_focus": f"主要投资于{style}主题相关资产（仿真）",
        })
        m.objectives.append({
            "fund_code": code,
            "objective_text": f"在严格控制风险的前提下，追求{style}主题资产的长期稳健回报（仿真）",
            "intended_risk_level": f"FundRiskLevel{risk_map[ftype]}",
        })
        # 份额类别
        unit_classes = ["A"]
        if (not is_private) and ftype not in ("money", "etf") and rng.random() < 0.8:
            unit_classes.append("C")
        if is_private:
            unit_classes = ["A"]
        total_outstanding = 10 ** rng.uniform(7.0, 9.5) if not is_private else 10 ** rng.uniform(6.0, 8.0)
        for ui, ucls in enumerate(unit_classes):
            if ucls == "A":
                unit_code = code
            else:
                unit_code = (code + "3")[:10]
            if ucls == "A":
                dist_mode = "FundDistributionModeCashDividend"
                fee_mode = "FundFeeModeFrontEnd"
                reinvest = bool(rng.random() < 0.3)
            else:
                dist_mode = "FundDistributionModeReinvestment"
                fee_mode = "FundFeeModeSalesService"
                reinvest = True
            if is_mm:
                dist_mode = "FundDistributionModeCashDividend"
                fee_mode = "FundFeeModeNone"
            if is_etf:
                dist_mode = "FundDistributionModeReinvestment"
                fee_mode = "FundFeeModeNone"
            outstanding = total_outstanding / len(unit_classes)
            m.units.append({
                "unit_code": unit_code,
                "fund_code": code,
                "unit_class": ucls,
                "currency": "CNY",
                "outstanding_units": round(outstanding, 2),
                "distribution_mode": dist_mode,
                "fee_mode": fee_mode,
                "distribution_with_reinvestment": int(reinvest),
                "subscription_min_amount": 10.0 if not is_private else 1_000_000.0,
                "subscription_min_units": 10.0 if not is_private else 100.0,
            })
            m.subscription_terms.append({
                "unit_code": unit_code,
                "min_amount": 10.0 if not is_private else 1_000_000.0,
                "min_units": 10.0 if not is_private else 100.0,
            })
        # 赎回条款
        m.redemption_terms.append({
            "fund_code": code,
            "redemption_min_units": 1.0 if not is_private else 1000.0,
            "allow_amount": 0 if is_private else 1,
        })
        # 角色与任职
        m.roles.append({"fund_code": code, "role_type": "FundManagerRole",
                        "party_id": fund["company_id"]})
        if not is_private:
            m.roles.append({"fund_code": code, "role_type": "FundDepositaryRole",
                            "party_id": fund["depositary_id"]})
        m.roles.append({"fund_code": code, "role_type": "FundAgentRole",
                        "party_id": next(p["party_id"] for p in m.parties if p["name_zh"] == agent[0])})
        if not is_private:
            registrars = [p["party_id"] for p in m.parties if p["party_kind"] == "fund_registrar"]
            m.roles.append({"fund_code": code, "role_type": "FundRegistrarRole",
                            "party_id": registrars[len(m.funds) % len(registrars)]})
        m.assignments.append({"fund_code": code, "role_type": "FundManagerRole",
                              "party_id": fund["company_id"], "effective_from": inception.isoformat(),
                              "effective_to": None})
        if not is_private:
            m.assignments.append({"fund_code": code, "role_type": "FundDepositaryRole",
                                  "party_id": fund["depositary_id"],
                                  "effective_from": inception.isoformat(), "effective_to": None})
        # 状态记录
        m.status_records.append({"fund_code": code, "status_code": status,
                                 "effective_from": inception.isoformat(),
                                 "effective_to": termination.isoformat() if terminated else None})
        # 业绩基准与指数
        idx = rng.choice(m.indices)
        bench_name = f"{idx['index_name']}×100%"
        m.benchmarks.append({"fund_code": code, "benchmark_name": bench_name,
                             "index_code": idx["index_code"]})
        # 法规关联
        for reg in rng.sample(m.regulations, k=min(3, len(m.regulations))):
            m.fund_regulations.append({"fund_code": code,
                                       "regulation_code": reg["regulation_code"]})
        # 费率
        fees_base = [
            ("基金管理费率", 0.015, "基金资产净值"),
            ("基金托管费率", 0.0025, "基金资产净值"),
        ]
        if not is_private:
            fees_base.append(("基金申购费率（前端）", round(rng.uniform(0.008, 0.015), 4), "申购金额"))
            fees_base.append(("基金赎回费率", round(rng.uniform(0.003, 0.015), 4), "赎回份额"))
        if any(u["fee_mode"] == "FundFeeModeSalesService" for u in m.units if u["fund_code"] == code):
            fees_base.append(("基金销售服务费率", 0.004, "基金资产净值"))
        for fname, frate, fbasis in fees_base:
            m.fees.append({"fund_code": code, "unit_code": None, "fee_name": fname,
                           "fee_rate": frate, "fee_amount": None, "fee_basis": fbasis})
        # 业绩
        period_start = TODAY - dt.timedelta(days=365)
        perf = {
            "fund_code": code, "period_start": period_start.isoformat(), "period_end": TODAY.isoformat(),
            "cumulative_return": round(rng.uniform(-0.15, 0.35), 6),
            "annualized_return": round(rng.uniform(-0.12, 0.3), 6),
            "maximum_drawdown": round(rng.uniform(0.02, 0.45), 6),
            "excess_return": round(rng.uniform(-0.08, 0.2), 6),
        }
        if ftype in ("index", "etf") or ftype == "qdii":
            perf["tracking_error"] = round(rng.uniform(0.002, 0.02), 6)
        else:
            perf["tracking_error"] = None
        m.performances.append(perf)
        fund_idx += 1

    # ---- 无在管基金的经理自然人（合法存在：在职未分派；仅出现在 RDF，不产生
    # playsFundRole 边，体现"经理可无基金"；"基金必有人管理"由角色链+SHACL 保证）。
    # 注意：使用独立派生随机源，不消费主 rng（保持数据集可复现、基准锚点稳定）。----
    aux_rng = random.Random(seed + 0x5EED)
    used_manager_names = {x["manager_name"] for x in m.managers}
    while len(m.unassigned_managers) < 4:
        name = pick(aux_rng, SURNAMES) + pick(aux_rng, GIVEN_M)
        if name not in used_manager_names and name not in m.unassigned_managers:
            m.unassigned_managers.append(name)

    # ---- 投资资产目录 ----
    asset_id = 0

    def add_asset(kind: str, code: str, name: str) -> int:
        nonlocal asset_id
        asset_id += 1
        m.assets.append({"asset_id": asset_id, "asset_code": code, "asset_name": name,
                         "asset_type": kind, "currency": "CNY"})
        return asset_id

    for i, name in enumerate(EQUITY_ASSETS):
        add_asset("equity", f"EQ{i:04d}", name)
    for i, name in enumerate(BOND_ASSETS):
        add_asset("debt", f"BD{i:04d}", name)
    for i, name in enumerate(MM_ASSETS):
        add_asset("mm", f"MM{i:04d}", name)
    for i, name in enumerate(CASH_ASSETS):
        add_asset("cash", f"CS{i:04d}", name)
    for i, name in enumerate(INDEX_ASSETS):
        add_asset("derivative", f"DR{i:04d}", name)

    # ---- 净值序列（随机游走 + 漂移，服从类型风险特征）----
    days = trading_days(TODAY, days_count)
    daily = {
        "equity": (0.0005, 0.012), "hybrid": (0.0004, 0.008), "bond": (0.0002, 0.0012),
        "money": (0.00008, 0.0001), "index": (0.0004, 0.011), "etf": (0.0004, 0.011),
        "fof": (0.0003, 0.006), "qdii": (0.0004, 0.014),
        "private-equity": (0.0008, 0.004), "private-sec": (0.0003, 0.009),
    }
    for fund in m.funds:
        ftype = fund["fund_type"]
        drift, vol = daily[ftype]
        units_this = [u for u in m.units if u["fund_code"] == fund["fund_code"]]
        series: dict[str, dict[str, float]] = {}
        for u in units_this:
            nav = 1.0
            acc = 1.0
            val: dict[str, float] = {}
            for di, d in enumerate(days):
                if d < dt.date.fromisoformat(fund["inception_date"]):
                    continue
                ret = rng.gauss(drift, vol)
                nav = max(0.001, nav * (1 + ret))
                acc = max(acc, nav)
                if di > 0 and di % 60 == 0 and ftype != "money":
                    acc += round(rng.uniform(0.005, 0.02), 4)
                val[d.isoformat()] = (nav, acc)
                m.navs.append({
                    "fund_code": fund["fund_code"], "unit_code": u["unit_code"],
                    "valuation_date": d.isoformat(), "unit_nav": round(nav, 4),
                    "accumulated_unit_nav": round(acc, 4), "fund_nav": None,
                    "valuation_currency": "CNY",
                })
            series[u["unit_code"]] = val
        # 基金级净值记录（记录 A 类份额净值 + 基金资产净值）
        total_outstanding = sum(u["outstanding_units"] for u in units_this)
        a_unit = next(u for u in units_this if u["unit_class"] == "A")
        a_series = series[a_unit["unit_code"]]
        for d_iso, (nav, acc) in a_series.items():
            m.navs.append({
                "fund_code": fund["fund_code"], "unit_code": None,
                "valuation_date": d_iso, "unit_nav": nav,
                "accumulated_unit_nav": acc,
                "fund_nav": round(nav * total_outstanding, 2),
                "valuation_currency": "CNY",
            })

    # ---- 投资组合与持仓 ----
    latest = TODAY.isoformat()
    for fund in m.funds:
        ftype = fund["fund_type"]
        kind = ASSET_TYPE_MAP.get(ftype, ("股票投资资产", "equity"))[1]
        # 持仓资产挑选
        candidates = [a for a in m.assets if a["asset_type"] == kind]
        if kind == "equity":
            picks = rng.sample(candidates, k=min(6, len(candidates)))
        elif kind == "fund":
            picks = rng.sample([a for a in m.assets if a["asset_type"] == "equity"], k=3)
            picks += rng.sample([a for a in m.assets if a["asset_type"] == "debt"], k=2)
        else:
            picks = candidates[: min(4, len(candidates))]
        if not picks:
            picks = [candidates[0]]
        # 各类资产权重
        if kind == "equity":
            weights = [0.5, 0.25, 0.12, 0.07, 0.04, 0.02][: len(picks)]
        elif kind == "debt":
            weights = [0.4, 0.25, 0.15, 0.1, 0.07, 0.03][: len(picks)]
        elif kind == "mm":
            weights = [0.5, 0.3, 0.2][: len(picks)]
        elif kind == "fund":
            w = [0.3, 0.2, 0.15, 0.1, 0.08]  # 2*equity + debt mix + cash tail below
            weights = (w[:2] + [0.05] + w[2:4])[: len(picks)]
        else:
            weights = [1.0 / len(picks)] * len(picks)
        wsum = sum(weights)
        latest_fund_nav_row = None
        for nv in reversed(m.navs):
            if nv["fund_code"] == fund["fund_code"] and nv["unit_code"] is None:
                latest_fund_nav_row = nv
                break
        aum = (latest_fund_nav_row["fund_nav"] if latest_fund_nav_row else 10 ** 8)
        for p_, w in zip(picks, weights):
            mv = aum * w / wsum
            price = rng.uniform(2, 120) if kind in ("equity", "fund") else rng.uniform(50, 105)
            qty = mv / price
            m.portfolio_positions.append({
                "fund_code": fund["fund_code"], "asset_id": p_["asset_id"],
                "quantity": round(qty, 2), "market_value": round(mv, 2),
                "as_of_date": latest, "currency": "CNY",
            })
        # 现金尾巴（保证权重不被截断）
        if kind in ("equity", "debt", "fund") and rng.random() < 0.6:
            cash_asset = next(a for a in m.assets if a["asset_type"] == "cash")
            mv = aum * rng.uniform(0.01, 0.05)
            m.portfolio_positions.append({
                "fund_code": fund["fund_code"], "asset_id": cash_asset["asset_id"],
                "quantity": round(mv, 2), "market_value": round(mv, 2),
                "as_of_date": latest, "currency": "CNY",
            })

    # ---- 投资者、账户、持仓 ----
    investor_count = 260
    surnames = list(SURNAMES)
    for i in range(1, investor_count + 1):
        surname = surnames[i % len(surnames)]
        given = GIVEN_M[i % len(GIVEN_M)] if i % 2 else GIVEN_F[i % len(GIVEN_F)]
        is_qualified = rng.random() < 0.25 or i % 7 == 0
        m.investors.append({
            "investor_id": i,
            "investor_name": surname + given,
            "risk_rating_code": f"R{rng.randint(1, 5)}",
            "risk_rating_date": (TODAY - dt.timedelta(days=rng.randrange(30, 700))).isoformat(),
            "is_qualified": int(is_qualified),
        })
    public_funds = [f for f in m.funds if not f["is_private"]]
    private_funds = [f for f in m.funds if f["is_private"]]
    acct_seq = 0
    for inv in m.investors:
        pool = public_funds if not inv["is_qualified"] else public_funds[:30] + private_funds
        if not inv["is_qualified"]:
            k = rng.randint(1, 4)
            chosen = rng.sample(pool, k=min(k, len(pool)))
        else:
            k = rng.randint(1, 5)
            chosen = rng.sample(pool, k=min(k, len(pool)))
            # 合格投资者至少持有一只私募
            if private_funds and rng.random() < 0.8:
                chosen = chosen[: max(len(chosen) - 1, 1)] + [rng.choice(private_funds)]
        for f in chosen:
            acct_seq += 1
            account_number = f"{inv['investor_id']:06d}{acct_seq:08d}{rng.randrange(1000):03d}"[:20]
            m.accounts.append({
                "account_number": account_number,
                "investor_id": inv["investor_id"],
                "fund_code": f["fund_code"],
                "opening_date": (dt.date.fromisoformat(f["inception_date"])
                                 + dt.timedelta(days=rng.randrange(30, 500))).isoformat(),
            })
    for acc in m.accounts:
        unit = rng.choice([u for u in m.units if u["fund_code"] == acc["fund_code"]])
        qty = round(rng.uniform(1000, 2_000_000), 2)
        m.positions.append({
            "account_number": acc["account_number"], "unit_code": unit["unit_code"],
            "quantity": qty, "currency": "CNY", "as_of_date": latest,
        })

    # 私募基金的投资者只能是合格投资者（SHACL 约束）
    for f in private_funds:
        qualified_ids = {a["investor_id"] for a in m.accounts
                         if a["fund_code"] == f["fund_code"]
                         and next(i2["is_qualified"] for i2 in m.investors if i2["investor_id"] == a["investor_id"])}
        if not qualified_ids:
            for inv in rng.sample([i2 for i2 in m.investors if i2["is_qualified"]], k=10):
                acct_seq += 1
                account_number = f"{inv['investor_id']:06d}{acct_seq:08d}{rng.randrange(1000):03d}"[:20]
                m.accounts.append({
                    "account_number": account_number, "investor_id": inv["investor_id"],
                    "fund_code": f["fund_code"],
                    "opening_date": (dt.date.fromisoformat(f["inception_date"])
                                     + dt.timedelta(days=rng.randrange(30, 500))).isoformat(),
                })
                unit = rng.choice([u for u in m.units if u["fund_code"] == f["fund_code"]])
                m.positions.append({
                    "account_number": account_number, "unit_code": unit["unit_code"],
                    "quantity": round(rng.uniform(1_000_000, 50_000_000), 2),
                    "currency": "CNY", "as_of_date": latest,
                })
    return m


# ---------------------------------------------------------------------------
# SQLite 写出
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS cnfc_code (
    scheme TEXT NOT NULL, code TEXT NOT NULL, label_zh TEXT NOT NULL, iri TEXT NOT NULL,
    PRIMARY KEY (scheme, code)
);
CREATE TABLE IF NOT EXISTS lifecycle_status (
    status_code TEXT PRIMARY KEY, label_zh TEXT NOT NULL, iri TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_party (
    party_id INTEGER PRIMARY KEY, party_kind TEXT NOT NULL, name_zh TEXT NOT NULL, short_name TEXT
);
CREATE TABLE IF NOT EXISTS fund (
    fund_code TEXT PRIMARY KEY, fund_name TEXT NOT NULL, fund_short_name TEXT,
    company_id INTEGER REFERENCES fund_party(party_id),
    depositary_id INTEGER REFERENCES fund_party(party_id),
    fund_type TEXT NOT NULL, public_private TEXT NOT NULL,
    operation_mode_code TEXT NOT NULL, organization_form_code TEXT NOT NULL,
    risk_level_code TEXT NOT NULL, status_code TEXT NOT NULL,
    is_open_ended INTEGER NOT NULL, is_exchange_traded INTEGER NOT NULL, is_private INTEGER NOT NULL,
    inception_date TEXT NOT NULL, termination_date TEXT,
    base_currency TEXT NOT NULL, filing_number TEXT, registration_number TEXT,
    fund_type_code TEXT, source_identifier TEXT
);
CREATE TABLE IF NOT EXISTS fund_product (
    fund_code TEXT PRIMARY KEY REFERENCES fund(fund_code), product_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_manager (
    fund_code TEXT PRIMARY KEY REFERENCES fund(fund_code),
    manager_name TEXT NOT NULL, manager_title TEXT
);
CREATE TABLE IF NOT EXISTS fund_unit (
    unit_code TEXT PRIMARY KEY, fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    unit_class TEXT NOT NULL, currency TEXT NOT NULL, outstanding_units REAL,
    distribution_mode_code TEXT NOT NULL, fee_mode_code TEXT NOT NULL,
    distribution_with_reinvestment INTEGER NOT NULL,
    subscription_min_amount REAL, subscription_min_units REAL
);
CREATE TABLE IF NOT EXISTS fund_subscription_terms (
    unit_code TEXT PRIMARY KEY REFERENCES fund_unit(unit_code),
    min_amount REAL NOT NULL, min_units REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_redemption_terms (
    fund_code TEXT PRIMARY KEY REFERENCES fund(fund_code),
    redemption_min_units REAL NOT NULL, allow_amount INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_role (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    role_type TEXT NOT NULL, party_id INTEGER NOT NULL REFERENCES fund_party(party_id)
);
CREATE TABLE IF NOT EXISTS fund_role_assignment (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    role_type TEXT NOT NULL, party_id INTEGER NOT NULL REFERENCES fund_party(party_id),
    effective_from TEXT NOT NULL, effective_to TEXT
);
CREATE TABLE IF NOT EXISTS fund_status_record (
    status_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    status_code TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT
);
CREATE TABLE IF NOT EXISTS fund_strategy (
    fund_code TEXT PRIMARY KEY REFERENCES fund(fund_code),
    strategy_type TEXT NOT NULL, investment_focus TEXT
);
CREATE TABLE IF NOT EXISTS fund_objective (
    fund_code TEXT PRIMARY KEY REFERENCES fund(fund_code),
    objective_text TEXT NOT NULL, intended_risk_level TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investment_asset (
    asset_id INTEGER PRIMARY KEY, asset_code TEXT NOT NULL, asset_name TEXT NOT NULL,
    asset_type TEXT NOT NULL, currency TEXT NOT NULL DEFAULT 'CNY'
);
CREATE TABLE IF NOT EXISTS portfolio_position (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    asset_id INTEGER NOT NULL REFERENCES investment_asset(asset_id),
    quantity REAL NOT NULL, market_value REAL NOT NULL,
    as_of_date TEXT NOT NULL, currency TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nav_record (
    nav_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    unit_code TEXT REFERENCES fund_unit(unit_code),
    valuation_date TEXT NOT NULL,
    unit_nav REAL, accumulated_unit_nav REAL, fund_nav REAL,
    valuation_currency TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_performance (
    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    period_start TEXT NOT NULL, period_end TEXT NOT NULL,
    cumulative_return REAL, annualized_return REAL, maximum_drawdown REAL,
    excess_return REAL, tracking_error REAL
);
CREATE TABLE IF NOT EXISTS fund_fee (
    fee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    unit_code TEXT REFERENCES fund_unit(unit_code),
    fee_name TEXT NOT NULL, fee_rate REAL, fee_amount REAL, fee_basis TEXT
);
CREATE TABLE IF NOT EXISTS market_index (
    index_code TEXT PRIMARY KEY, index_name TEXT NOT NULL,
    index_currency TEXT NOT NULL, compiler_party_id INTEGER REFERENCES fund_party(party_id)
);
CREATE TABLE IF NOT EXISTS fund_benchmark (
    fund_code TEXT PRIMARY KEY REFERENCES fund(fund_code),
    benchmark_name TEXT NOT NULL, index_code TEXT NOT NULL REFERENCES market_index(index_code)
);
CREATE TABLE IF NOT EXISTS regulation (
    regulation_code TEXT PRIMARY KEY, regulation_title TEXT NOT NULL, article_reference TEXT
);
CREATE TABLE IF NOT EXISTS fund_regulation (
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    regulation_code TEXT NOT NULL REFERENCES regulation(regulation_code),
    PRIMARY KEY (fund_code, regulation_code)
);
CREATE TABLE IF NOT EXISTS fund_supervisor (
    supervisor_id INTEGER PRIMARY KEY REFERENCES fund_party(party_id), name_zh TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investor (
    investor_id INTEGER PRIMARY KEY, investor_name TEXT NOT NULL,
    risk_rating_code TEXT NOT NULL, risk_rating_date TEXT NOT NULL, is_qualified INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_account (
    account_number TEXT PRIMARY KEY,
    investor_id INTEGER NOT NULL REFERENCES investor(investor_id),
    fund_code TEXT NOT NULL REFERENCES fund(fund_code),
    opening_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fund_position (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL REFERENCES fund_account(account_number),
    unit_code TEXT NOT NULL REFERENCES fund_unit(unit_code),
    quantity REAL NOT NULL, currency TEXT NOT NULL, as_of_date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nav_fund_date ON nav_record(fund_code, valuation_date);
CREATE INDEX IF NOT EXISTS idx_nav_unit_date ON nav_record(unit_code, valuation_date);
CREATE INDEX IF NOT EXISTS idx_pos_fund ON portfolio_position(fund_code);
CREATE INDEX IF NOT EXISTS idx_account_investor ON fund_account(investor_id);
"""


def write_sqlite(model: SimModel, db_path: Path, vocab: OntologyVocabulary, seed: int) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(str(db_path))
    try:
        con.executescript(SCHEMA_SQL)
        cur = con.cursor()
        counts: dict[str, int] = {}
        cur.executemany("INSERT INTO cnfc_code(scheme, code, label_zh, iri) VALUES (?,?,?,?)",
                        [(scheme, code, label, str(CNFC) + code)
                         for code, (scheme, label) in sorted(vocab.code_concepts.items())])
        counts["cnfc_code"] = len(vocab.code_concepts)
        cur.executemany("INSERT INTO lifecycle_status(status_code, label_zh, iri) VALUES (?,?,?)",
                        [(code, label, str(CNFO) + code)
                         for code, label in sorted(vocab.lifecycle_statuses.items())])
        counts["lifecycle_status"] = len(vocab.lifecycle_statuses)
        cur.executemany("INSERT INTO fund_party(party_id, party_kind, name_zh, short_name) VALUES (?,?,?,?)",
                        [(p["party_id"], p["party_kind"], p["name_zh"], p["short_name"]) for p in model.parties])
        cur.executemany("INSERT INTO fund VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (f["fund_code"], f["fund_name"], f["fund_short_name"], f["company_id"],
             f["depositary_id"], f["fund_type"], f["public_private"], f["operation_mode"],
             f["organization_form"], f["risk_level"], f["status_code"], f["is_open_ended"],
             f["is_exchange_traded"], f["is_private"], f["inception_date"], f["termination_date"],
             f["base_currency"], f["filing_number"], f["registration_number"],
             f["fund_type_code"], f["source_identifier"])
            for f in model.funds])
        cur.executemany("INSERT INTO fund_product(fund_code, product_name) VALUES (?,?)",
                        [(p["fund_code"], p["product_name"]) for p in model.products])
        cur.executemany("INSERT INTO fund_manager(fund_code, manager_name, manager_title) VALUES (?,?,?)",
                        [(x["fund_code"], x["manager_name"], x["manager_title"]) for x in model.managers])
        cur.executemany("INSERT INTO fund_unit VALUES (?,?,?,?,?,?,?,?,?,?)", [
            (u["unit_code"], u["fund_code"], u["unit_class"], u["currency"], u["outstanding_units"],
             u["distribution_mode"], u["fee_mode"], u["distribution_with_reinvestment"],
             u["subscription_min_amount"], u["subscription_min_units"])
            for u in model.units])
        cur.executemany("INSERT INTO fund_subscription_terms(unit_code, min_amount, min_units) VALUES (?,?,?)",
                        [(t["unit_code"], t["min_amount"], t["min_units"]) for t in model.subscription_terms])
        cur.executemany("INSERT INTO fund_redemption_terms VALUES (?,?,?)",
                        [(t["fund_code"], t["redemption_min_units"], t["allow_amount"])
                         for t in model.redemption_terms])
        cur.executemany("INSERT INTO fund_role(fund_code, role_type, party_id) VALUES (?,?,?)",
                        [(r["fund_code"], r["role_type"], r["party_id"]) for r in model.roles])
        cur.executemany("INSERT INTO fund_role_assignment(fund_code, role_type, party_id, effective_from, effective_to) VALUES (?,?,?,?,?)",
                        [(a["fund_code"], a["role_type"], a["party_id"], a["effective_from"], a["effective_to"])
                         for a in model.assignments])
        cur.executemany("INSERT INTO fund_status_record(fund_code, status_code, effective_from, effective_to) VALUES (?,?,?,?)",
                        [(r["fund_code"], r["status_code"], r["effective_from"], r["effective_to"])
                         for r in model.status_records])
        cur.executemany("INSERT INTO fund_strategy(fund_code, strategy_type, investment_focus) VALUES (?,?,?)",
                        [(s["fund_code"], s["strategy_type"], s["investment_focus"]) for s in model.strategies])
        cur.executemany("INSERT INTO fund_objective(fund_code, objective_text, intended_risk_level) VALUES (?,?,?)",
                        [(o["fund_code"], o["objective_text"], o["intended_risk_level"]) for o in model.objectives])
        cur.executemany("INSERT INTO investment_asset VALUES (?,?,?,?,?)",
                        [(a["asset_id"], a["asset_code"], a["asset_name"], a["asset_type"], a["currency"])
                         for a in model.assets])
        cur.executemany("INSERT INTO portfolio_position(fund_code, asset_id, quantity, market_value, as_of_date, currency) VALUES (?,?,?,?,?,?)",
                        [(p["fund_code"], p["asset_id"], p["quantity"], p["market_value"],
                          p["as_of_date"], p["currency"]) for p in model.portfolio_positions])
        cur.executemany("INSERT INTO nav_record(fund_code, unit_code, valuation_date, unit_nav, accumulated_unit_nav, fund_nav, valuation_currency) VALUES (?,?,?,?,?,?,?)",
                        [(n["fund_code"], n["unit_code"], n["valuation_date"], n["unit_nav"],
                          n["accumulated_unit_nav"], n["fund_nav"], n["valuation_currency"])
                         for n in model.navs])
        cur.executemany("INSERT INTO fund_performance(fund_code, period_start, period_end, cumulative_return, annualized_return, maximum_drawdown, excess_return, tracking_error) VALUES (?,?,?,?,?,?,?,?)",
                        [(p["fund_code"], p["period_start"], p["period_end"], p["cumulative_return"],
                          p["annualized_return"], p["maximum_drawdown"], p["excess_return"],
                          p["tracking_error"]) for p in model.performances])
        cur.executemany("INSERT INTO fund_fee(fund_code, unit_code, fee_name, fee_rate, fee_amount, fee_basis) VALUES (?,?,?,?,?,?)",
                        [(f["fund_code"], f["unit_code"], f["fee_name"], f["fee_rate"],
                          f["fee_amount"], f["fee_basis"]) for f in model.fees])
        cur.executemany("INSERT INTO market_index VALUES (?,?,?,?)",
                        [(i["index_code"], i["index_name"], i["index_currency"], i["compiler_party_id"])
                         for i in model.indices])
        cur.executemany("INSERT INTO fund_benchmark(fund_code, benchmark_name, index_code) VALUES (?,?,?)",
                        [(b["fund_code"], b["benchmark_name"], b["index_code"]) for b in model.benchmarks])
        cur.executemany("INSERT INTO regulation VALUES (?,?,?)",
                        [(r["regulation_code"], r["regulation_title"], r["article_reference"])
                         for r in model.regulations])
        cur.executemany("INSERT INTO fund_regulation(fund_code, regulation_code) VALUES (?,?)",
                        [(r["fund_code"], r["regulation_code"]) for r in model.fund_regulations])
        for s in model.supervisors:
            cur.execute("INSERT INTO fund_supervisor(supervisor_id, name_zh) VALUES (?,?)",
                        (s["supervisor_id"], s["name_zh"]))
        cur.executemany("INSERT INTO investor VALUES (?,?,?,?,?)",
                        [(i["investor_id"], i["investor_name"], i["risk_rating_code"],
                          i["risk_rating_date"], i["is_qualified"]) for i in model.investors])
        cur.executemany("INSERT INTO fund_account VALUES (?,?,?,?)",
                        [(a["account_number"], a["investor_id"], a["fund_code"], a["opening_date"])
                         for a in model.accounts])
        cur.executemany("INSERT INTO fund_position(account_number, unit_code, quantity, currency, as_of_date) VALUES (?,?,?,?,?)",
                        [(p["account_number"], p["unit_code"], p["quantity"], p["currency"], p["as_of_date"])
                         for p in model.positions])
        cur.executemany("INSERT INTO meta(key, value) VALUES (?,?)", [
            ("schema_version", "1.0"),
            ("simulated", "true"),
            ("simulation_note", "全部数据为仿真生成，与真实机构/个人无关"),
            ("ontology_version", vocab.ontology_version),
            ("seed", str(seed)),
            ("generated_at", dt.datetime.now().isoformat(timespec="seconds")),
            ("fund_count", str(len(model.funds))),
            ("unit_count", str(len(model.units))),
            ("nav_count", str(len(model.navs))),
            ("investor_count", str(len(model.investors))),
            ("account_count", str(len(model.accounts))),
            ("position_count", str(len(model.positions))),
        ])
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------------------
# RDF A-BOX 构建（用本体属性名，供 SHACL 校验）
# ---------------------------------------------------------------------------
def build_rdf(model: SimModel, nav_window_days: int | None = None,
              ontology_version: str = "unknown") -> Graph:
    g = Graph()
    g.bind("cnfo", CNFO)
    g.bind("cnfc", CNFC)
    g.bind("cnfom", CNFOM)
    g.bind("cnfo-a", CNFOA)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("dcterms", DCTERMS)
    g.bind("xsd", XSD)

    # ---- A-BOX 数据集头：声明自身为 owl:Ontology 实例数据集，通过 owl:imports
    # 关联本体的领域入口 / 基金本体 / 模块词汇；不含任何 T-BOX 词汇声明。----
    abox_onto = CNFOA.CNFOSimulatedAbox
    g.add((abox_onto, RDF.type, OWL.Ontology))
    g.add((abox_onto, OWL.imports, CNFO.CNFODomain))
    g.add((abox_onto, OWL.imports, CNFO.CNFOFundOntology))
    g.add((abox_onto, OWL.imports, CNFOM.CNFOModuleVocabulary))
    g.add((abox_onto, RDFS.label, Literal("CNFO 仿真 A-BOX（模拟基金业务数据）", lang="zh")))
    g.add((abox_onto, DCTERMS.description, Literal(
        "基于 CNFO 本体的仿真实例数据：基金、份额类别、净值记录、投资组合与持仓、"
        "参与主体与角色任职、投资者/账户/持仓、业绩、费率、基准与法规关联。"
        "全部数据为仿真虚构，与真实机构/个人无关。", lang="zh")))
    g.add((abox_onto, OWL.versionInfo, Literal(f"{ontology_version}-sim")))

    if nav_window_days is None:
        navs = model.navs
    else:
        # 仅保留最近 N 个估值日的净值记录（校验阶段控制 SPARQL 成本）
        nav_dates = sorted({n["valuation_date"] for n in model.navs},
                           reverse=True)[: nav_window_days]
        keep = set(nav_dates)
        navs = [n for n in model.navs if n["valuation_date"] in keep]

    def cnfoa(name: str) -> URIRef:
        return CNFOA[name]

    # 参与主体 / 监管机构
    party_uri: dict[int, URIRef] = {}
    for p in model.parties:
        u = cnfoa(f"Party{p['party_id']}")
        party_uri[p["party_id"]] = u
        kind_class = {
            "fund_management_company": CNFO.FundManagementCompany,
            "depositary_bank": CNFO.FundParty,
            "fund_sales_agent": CNFO.FundAgent,
            "fund_registrar": CNFO.FundParty,
            "fund_supervisor": CNFO.FundSupervisor,
        }[p["party_kind"]]
        g.add((u, RDF.type, CNFO.FundParty))
        if kind_class != CNFO.FundParty:
            g.add((u, RDF.type, kind_class))
        g.add((u, RDFS.label, Literal(p["name_zh"], lang="zh")))

    # 法规与监管
    reg_uri: dict[str, URIRef] = {}
    for r in model.regulations:
        u = cnfoa(f"Reg{r['regulation_code'].replace('.', '')}")
        reg_uri[r["regulation_code"]] = u
        g.add((u, RDF.type, CNFO.Regulation))
        g.add((u, CNFO.regulationCode, Literal(r["regulation_code"])))
        g.add((u, CNFO.regulationTitle, Literal(r["regulation_title"])))
        g.add((u, CNFO.articleReference, Literal(r["article_reference"])))
    for s in model.supervisors:
        sup = party_uri[s["supervisor_id"]]
        for r in model.regulations:
            g.add((sup, CNFO.authorityForRegulation, reg_uri[r["regulation_code"]]))

    # 市场指数
    index_uri: dict[str, URIRef] = {}
    for i in model.indices:
        u = cnfoa(f"Index{i['index_code'].replace('.', '')}")
        index_uri[i["index_code"]] = u
        g.add((u, RDF.type, CNFO.MarketIndex))
        g.add((u, CNFO.indexCode, Literal(i["index_code"])))
        g.add((u, CNFO.indexName, Literal(i["index_name"])))
        g.add((u, CNFO.indexCurrency, Literal(i["index_currency"])))
        if i["compiler_party_id"] in party_uri:
            g.add((u, CNFO.compiledBy, party_uri[i["compiler_party_id"]]))

    def add_date(node, pred, iso: str) -> None:
        g.add((node, pred, Literal(iso, datatype=XSD.date)))

    # 基金
    unit_uri: dict[str, URIRef] = {}
    investor_uri: dict[int, URIRef] = {}
    for f in model.funds:
        fund = cnfoa(f"F{f['fund_code']}")
        types = [CNFO.Fund]
        if f["is_private"]:
            types.append(CNFO.PrivateFund)
            types.append(CNFO.PrivateSecuritiesInvestmentFund
                         if f["fund_type"] == "private-sec" else CNFO.PrivateEquityFund)
        else:
            types.append(CNFO.PublicFund)
            mode_class = {
                "equity": CNFO.EquityFund, "hybrid": CNFO.HybridFund, "bond": CNFO.BondFund,
                "money": CNFO.MoneyMarketFund, "index": CNFO.EquityFund,
                "etf": CNFO.ExchangeTradedFund, "fof": CNFO.FundOfFunds, "qdii": CNFO.QDIIFund,
            }.get(f["fund_type"])
            if mode_class:
                types.append(mode_class)
            types.append(CNFO.OpenEndedFund if f["is_open_ended"] else CNFO.ClosedEndedFund)
        for t in types:
            g.add((fund, RDF.type, t))
        g.add((fund, RDFS.label, Literal(f["fund_name"], lang="zh")))
        g.add((fund, CNFO.fundCode, Literal(f["fund_code"])))
        g.add((fund, CNFO.fundName, Literal(f["fund_name"])))
        g.add((fund, CNFO.fundShortName, Literal(f["fund_short_name"])))
        add_date(fund, CNFO.inceptionDate, f["inception_date"])
        if f["termination_date"]:
            add_date(fund, CNFO.terminationDate, f["termination_date"])
        g.add((fund, CNFO.baseCurrency, Literal(f["base_currency"])))
        g.add((fund, CNFO.isOpenEnded, Literal(bool(f["is_open_ended"]))))
        g.add((fund, CNFO.isPrivate, Literal(bool(f["is_private"]))))
        g.add((fund, CNFO.isExchangeTraded, Literal(bool(f["is_exchange_traded"]))))
        if f["filing_number"]:
            g.add((fund, CNFO.filingNumber, Literal(f["filing_number"])))
        if f["registration_number"]:
            g.add((fund, CNFO.registrationNumber, Literal(f["registration_number"])))
        if f["fund_type_code"]:
            g.add((fund, CNFO.fundTypeCode, Literal(f["fund_type_code"])))
        if f["source_identifier"]:
            g.add((fund, CNFO.sourceIdentifier, Literal(f["source_identifier"])))
        g.add((fund, CNFO.hasFundOperationMode, CNFC[f["operation_mode"]]))
        g.add((fund, CNFO.hasFundOrganizationForm, CNFC[f["organization_form"]]))
        g.add((fund, CNFO.hasFundRiskLevel, CNFC[f["risk_level"]]))
        g.add((fund, CNFO.hasFundStatus, CNFO[f["status_code"]]))
        status_rec = cnfoa(f"StatusRec{f['fund_code']}")
        g.add((status_rec, RDF.type, CNFO.FundStatusRecord))
        g.add((status_rec, CNFO.statusRecordForFund, fund))
        g.add((status_rec, CNFO.hasStatusValue, CNFO[f["status_code"]]))
        add_date(status_rec, CNFO.effectiveFrom, f["inception_date"])
        g.add((fund, CNFO.hasFundStatusRecord, status_rec))
        if f["is_private"]:
            g.add((fund, CNFO.hasPrivateFundType,
                   CNFC.PrivateFundTypeSecurities
                   if f["fund_type"] == "private-sec" else CNFC.PrivateFundTypeEquityVenture))
        # 产品
        prod = cnfoa(f"Prod{f['fund_code']}")
        g.add((prod, RDF.type, CNFO.FundProduct))
        g.add((prod, RDFS.label, Literal(f["fund_name"] + "产品", lang="zh")))
        g.add((fund, CNFO.hasFundProduct, prod))
        g.add((fund, CNFO.realizesFundProduct, prod))
        # 合同/法律结构
        contract = cnfoa(f"Contract{f['fund_code']}")
        g.add((contract, RDF.type, CNFO.FundContract))
        g.add((fund, CNFO.governedBy, contract))
        g.add((contract, CNFO.contractParty, party_uri[f["company_id"]]))
        if f["depositary_id"] in party_uri and not f["is_private"]:
            g.add((contract, CNFO.contractParty, party_uri[f["depositary_id"]]))
        structure = cnfoa(f"Structure{f['fund_code']}")
        g.add((structure, RDF.type, CNFO.FundLegalStructure))
        g.add((structure, RDF.type, CNFO.ContractualFundStructure))
        juris = cnfoa(f"Juris{f['fund_code']}")
        g.add((juris, RDF.type, CNFO.FundJurisdiction))
        g.add((juris, CNFO.jurisdictionCode, Literal("CN")))
        g.add((structure, CNFO.hasApplicableJurisdiction, juris))
        g.add((fund, CNFO.hasLegalStructure, structure))
        # 法规
        for fr in [x for x in model.fund_regulations if x["fund_code"] == f["fund_code"]]:
            g.add((fund, CNFO.governedByRegulation, reg_uri[fr["regulation_code"]]))
        sup = party_uri[model.supervisors[0]["supervisor_id"]]
        g.add((fund, CNFO.hasFundSupervisor, sup))
        g.add((sup, CNFO.supervisesFund, fund))
        # 策略与目标
        strat = cnfoa(f"Strategy{f['fund_code']}")
        strat_type = (CNFO.IndexTrackingStrategy if f["fund_type"] in ("index", "etf")
                      else CNFO.ActiveInvestmentStrategy)
        g.add((strat, RDF.type, CNFO.FundInvestmentStrategy))
        g.add((strat, RDF.type, strat_type))
        g.add((strat, CNFO.strategyOfFund, fund))
        g.add((fund, CNFO.usesInvestmentStrategy, strat))
        focus = next((s["investment_focus"] for s in model.strategies if s["fund_code"] == f["fund_code"]), "")
        g.add((strat, CNFO.investmentFocus, Literal(focus)))
        if f["fund_type"] in ("index", "etf"):
            bench = next((b for b in model.benchmarks if b["fund_code"] == f["fund_code"]), None)
            if bench and bench["index_code"] in index_uri:
                g.add((strat, CNFO.trackingTargetIndex, index_uri[bench["index_code"]]))
        obj = cnfoa(f"Objective{f['fund_code']}")
        g.add((obj, RDF.type, CNFO.FundInvestmentObjective))
        g.add((obj, CNFO.objectiveOfFund, fund))
        g.add((fund, CNFO.hasInvestmentObjective, obj))
        obj_text = next((o["objective_text"] for o in model.objectives if o["fund_code"] == f["fund_code"]), "")
        if obj_text:
            g.add((obj, RDFS.label, Literal(obj_text, lang="zh")))
        riskt = cnfoa(f"RiskT{f['fund_code']}")
        g.add((riskt, RDF.type, CNFO.FundRiskLevel))
        g.add((riskt, CNFO.riskLevelCode, Literal(CNFC[f["risk_level"]][len(str(CNFC)):])))
        g.add((obj, CNFO.hasIntendedRiskLevel, riskt))
        # 基金经理人（自然人）
        mgr = next((x for x in model.managers if x["fund_code"] == f["fund_code"]), None)
        if mgr:
            mperson = cnfoa(f"Manager{f['fund_code']}")
            g.add((mperson, RDF.type, CNFO.FundManagerPerson))
            g.add((mperson, RDFS.label, Literal(mgr["manager_name"], lang="zh")))
        # 份额
        units = [u for u in model.units if u["fund_code"] == f["fund_code"]]
        for u in units:
            unit = cnfoa(f"U{u['unit_code']}")
            unit_uri[u["unit_code"]] = unit
            g.add((unit, RDF.type, CNFO.FundUnit))
            g.add((unit, RDF.type, CNFO.FundUnitClass))
            g.add((unit, CNFO.fundUnitCode, Literal(u["unit_code"])))
            g.add((unit, CNFO.unitCurrency, Literal(u["currency"])))
            g.add((unit, CNFO.unitQuantity, dec_lit(u["outstanding_units"])))
            g.add((unit, CNFO.issuedByFund, fund))
            g.add((fund, CNFO.issuesFundUnit, unit))
            g.add((fund, CNFO.hasFundUnit, unit))
            g.add((fund, CNFO.hasFundUnitClass, unit))
            g.add((unit, CNFO.hasFundDistributionMode, CNFC[u["distribution_mode"]]))
            g.add((unit, CNFO.hasFundFeeMode, CNFC[u["fee_mode"]]))
            policy = cnfoa(f"Policy{u['unit_code']}")
            if u["distribution_with_reinvestment"]:
                g.add((policy, RDF.type, CNFO.FundReinvestmentPolicy))
                g.add((policy, RDF.type, CNFO.FundUnitDistributionPolicy))
                g.add((policy, CNFO.distributionWithReinvestment, Literal(True)))
            else:
                g.add((policy, RDF.type, CNFO.FundCashDistributionPolicy))
                g.add((policy, RDF.type, CNFO.FundUnitDistributionPolicy))
                g.add((policy, CNFO.distributionWithReinvestment, Literal(False)))
            method = cnfoa(f"Method{u['unit_code']}")
            g.add((method, RDF.type, CNFO.FundDistributionMethod))
            g.add((method, RDFS.label,
                   Literal("红利转投方式" if u["distribution_with_reinvestment"] else "现金分红方式", lang="zh")))
            g.add((policy, CNFO.hasDistributionMethod, method))
            g.add((unit, CNFO.hasDistributionPolicy, policy))
            terms = cnfoa(f"SubTerms{u['unit_code']}")
            g.add((terms, RDF.type, CNFO.FundSubscriptionTerms))
            g.add((terms, CNFO.appliesToFundUnit, unit))
            g.add((terms, CNFO.subscriptionMinimumAmount, dec_lit(u["subscription_min_amount"])))
            g.add((terms, CNFO.subscriptionMinimumUnits, dec_lit(u["subscription_min_units"])))
            g.add((fund, CNFO.hasFundSubscriptionTerms, terms))
        # 赎回条款
        rt = next((x for x in model.redemption_terms if x["fund_code"] == f["fund_code"]), None)
        if rt:
            rterms = cnfoa(f"RedemTerms{f['fund_code']}")
            g.add((rterms, RDF.type, CNFO.FundRedemptionTerms))
            g.add((rterms, CNFO.redemptionMinimumUnits, dec_lit(rt["redemption_min_units"])))
            g.add((rterms, CNFO.redemptionInAmountAllowed, Literal(bool(rt["allow_amount"]))))
            g.add((fund, CNFO.hasFundRedemptionTerms, rterms))
        # 角色与任职
        role_uri: dict[tuple[str, int], URIRef] = {}
        for r in [x for x in model.roles if x["fund_code"] == f["fund_code"]]:
            role = cnfoa(f"Role{f['fund_code']}{r['role_type']}")
            role_uri[(r["role_type"], r["party_id"])] = role
            g.add((role, RDF.type, CNFO[r["role_type"]]))
            g.add((role, CNFO.roleInFund, fund))
            g.add((role, CNFO.rolePlayedBy, party_uri[r["party_id"]]))
            g.add((fund, CNFO.hasFundRole, role))
            link_pred = {
                "FundManagerRole": CNFO.hasFundManagerRole,
                "FundDepositaryRole": CNFO.hasFundDepositaryRole,
                "FundAgentRole": CNFO.hasFundAgentRole,
                "FundRegistrarRole": CNFO.hasFundRegistrarRole,
            }
            if r["role_type"] in link_pred:
                g.add((fund, link_pred[r["role_type"]], role))
        for a in [x for x in model.assignments if x["fund_code"] == f["fund_code"]]:
            role = role_uri.get((a["role_type"], a["party_id"]))
            if role is None:
                continue
            assign = cnfoa(f"Assign{f['fund_code']}{a['role_type']}")
            g.add((assign, RDF.type, CNFO.FundRoleAssignment))
            g.add((assign, CNFO.assignmentForFund, fund))
            g.add((assign, CNFO.assignsFundRole, role))
            g.add((assign, CNFO.assignmentPlayedBy, party_uri[a["party_id"]]))
            add_date(assign, CNFO.effectiveFrom, a["effective_from"])
            if a["effective_to"]:
                add_date(assign, CNFO.effectiveTo, a["effective_to"])
            g.add((fund, CNFO.hasFundRoleAssignment, assign))
        # 基金经理自然人承担该基金管理人角色（playsFundRole 与 rolePlayedBy 互逆；
        # 打开"某某管理的基金"查询路径，不影响 hasFundManagerRole maxCount=1 的 SHACL 约束）
        if mgr:
            mgr_role = role_uri.get(("FundManagerRole", f["company_id"]))
            if mgr_role is not None:
                g.add((mperson, CNFO.playsFundRole, mgr_role))
        # 投资组合与持仓
        portfolio = cnfoa(f"Portfolio{f['fund_code']}")
        g.add((portfolio, RDF.type, CNFO.FundPortfolio))
        g.add((portfolio, CNFO.portfolioOfFund, fund))
        g.add((fund, CNFO.hasFundPortfolio, portfolio))
        for pos in [x for x in model.portfolio_positions if x["fund_code"] == f["fund_code"]]:
            posnode = cnfoa(f"PPos{f['fund_code']}{pos['asset_id']}")
            asset = cnfoa(f"Asset{pos['asset_id']}")
            g.add((posnode, RDF.type, CNFO.PortfolioPosition))
            g.add((posnode, CNFO.positionOfPortfolio, portfolio))
            g.add((posnode, CNFO.positionInAsset, asset))
            g.add((posnode, CNFO.positionQuantity, dec_lit(pos["quantity"])))
            add_date(posnode, CNFO.positionAsOfDate, pos["as_of_date"])
            g.add((posnode, CNFO.positionCurrency, Literal(pos["currency"])))
            g.add((portfolio, CNFO.hasFundPortfolioPosition, posnode))
    # 投资资产
    # 无在管基金的经理自然人（合法孤立：仅 type+label；不产生 playsFundRole 边）
    for i, mgr_name in enumerate(model.unassigned_managers, start=1):
        mperson = cnfoa(f"ManagerUnassigned{i}")
        g.add((mperson, RDF.type, CNFO.FundManagerPerson))
        g.add((mperson, RDFS.label, Literal(mgr_name, lang="zh")))
    for a in model.assets:
        asset = cnfoa(f"Asset{a['asset_id']}")
        g.add((asset, RDF.type, CNFO.FundInvestmentAsset))
        subtype = {
            "equity": CNFO.EquityInvestmentAsset, "debt": CNFO.DebtInvestmentAsset,
            "mm": CNFO.MoneyMarketInstrument, "cash": CNFO.CashAndDepositAsset,
            "derivative": CNFO.DerivativeInvestmentAsset, "fund": CNFO.FundUnitInvestmentAsset,
        }[a["asset_type"]]
        g.add((asset, RDF.type, subtype))
        g.add((asset, RDFS.label, Literal(a["asset_name"], lang="zh")))
        if a["asset_code"]:
            g.add((asset, CNFO.sourceIdentifier, Literal(a["asset_code"])))
    # 净值记录
    funded = {f["fund_code"] for f in model.funds}
    for n in navs:
        if n["fund_code"] not in funded:
            continue
        if n["unit_code"]:
            nav = cnfoa(f"NAVU{n['fund_code']}{n['unit_code']}{n['valuation_date'].replace('-', '')}")
            g.add((nav, RDF.type, CNFO.NetAssetValueRecord))
            g.add((nav, CNFO.recordForFundUnit, unit_uri[n["unit_code"]]))
            g.add((nav, CNFO.valuationDate, Literal(n["valuation_date"], datatype=XSD.date)))
            g.add((nav, CNFO.valuationCurrency, Literal(n["valuation_currency"])))
            g.add((nav, CNFO.fundUnitNetAssetValue, dec_lit(n["unit_nav"])))
            g.add((nav, CNFO.accumulatedUnitNetAssetValue, dec_lit(n["accumulated_unit_nav"])))
            g.add((unit_uri[n["unit_code"]], CNFO.hasNetAssetValueRecordForFundUnit, nav))
        else:
            nav = cnfoa(f"NAVF{n['fund_code']}{n['valuation_date'].replace('-', '')}")
            g.add((nav, RDF.type, CNFO.NetAssetValueRecord))
            g.add((nav, CNFO.recordForFund, CNFOA[f"F{n['fund_code']}"]))
            g.add((nav, CNFO.valuationDate, Literal(n["valuation_date"], datatype=XSD.date)))
            g.add((nav, CNFO.valuationCurrency, Literal(n["valuation_currency"])))
            g.add((nav, CNFO.fundUnitNetAssetValue, dec_lit(n["unit_nav"])))
            g.add((nav, CNFO.fundNetAssetValue, dec_lit(n["fund_nav"])))
            if n["accumulated_unit_nav"] is not None:
                g.add((nav, CNFO.accumulatedUnitNetAssetValue, dec_lit(n["accumulated_unit_nav"])))
            g.add((CNFOA[f"F{n['fund_code']}"], CNFO.hasNetAssetValueRecord, nav))
    # 业绩
    for p in model.performances:
        node = cnfoa(f"Perf{p['fund_code']}")
        g.add((node, RDF.type, CNFO.FundPerformanceRecord))
        g.add((node, CNFO.performanceForFund, CNFOA[f"F{p['fund_code']}"]))
        add_date(node, CNFO.performancePeriodStart, p["period_start"])
        add_date(node, CNFO.performancePeriodEnd, p["period_end"])
        g.add((node, CNFO.cumulativeReturn, dec_lit(p["cumulative_return"])))
        g.add((node, CNFO.annualizedReturn, dec_lit(p["annualized_return"])))
        g.add((node, CNFO.maximumDrawdown, dec_lit(p["maximum_drawdown"])))
        g.add((node, CNFO.excessReturn, dec_lit(p["excess_return"])))
        if p["tracking_error"] is not None:
            g.add((node, CNFO.trackingError, dec_lit(p["tracking_error"])))
        g.add((CNFOA[f"F{p['fund_code']}"], CNFO.hasFundPerformanceRecord, node))
        bench = next((b for b in model.benchmarks if b["fund_code"] == p["fund_code"]), None)
        if bench:
            bench_node = cnfoa(f"Bench{p['fund_code']}")
            g.add((bench_node, RDF.type, CNFO.FundBenchmark))
            g.add((bench_node, CNFO.benchmarkName, Literal(bench["benchmark_name"])))
            if bench["index_code"] in index_uri:
                g.add((bench_node, CNFO.benchmarkIndex, index_uri[bench["index_code"]]))
            g.add((bench_node, CNFO.benchmarkUsedForPerformance, node))
            g.add((CNFOA[f"F{p['fund_code']}"], CNFO.fundBenchmark, bench_node))
    # 费率（IRI 使用全数据内的稳定序号，保证可复现）
    for fee_idx, fe in enumerate(model.fees):
        node = cnfoa(f"Fee{fe['fund_code']}{fee_idx}")
        g.add((node, RDF.type, CNFO.FundFee))
        g.add((node, CNFO.feeForFund, CNFOA[f"F{fe['fund_code']}"]))
        g.add((node, CNFO.feeName, Literal(fe["fee_name"])))
        if fe["fee_rate"] is not None:
            g.add((node, CNFO.feeRate, dec_lit(fe["fee_rate"])))
        if fe["fee_amount"] is not None:
            g.add((node, CNFO.feeAmount, dec_lit(fe["fee_amount"])))
        if fe["fee_basis"]:
            g.add((node, CNFO.feeBasis, Literal(fe["fee_basis"])))
        g.add((CNFOA[f"F{fe['fund_code']}"], CNFO.hasFundFee, node))
    # 投资者、账户、持仓
    for inv in model.investors:
        u = cnfoa(f"Inv{inv['investor_id']}")
        investor_uri[inv["investor_id"]] = u
        g.add((u, RDF.type, CNFO.Investor))
        if inv["is_qualified"]:
            g.add((u, RDF.type, CNFO.QualifiedInvestor))
        g.add((u, RDFS.label, Literal(inv["investor_name"], lang="zh")))
        rating = cnfoa(f"InvRating{inv['investor_id']}")
        g.add((rating, RDF.type, CNFO.InvestorRiskRating))
        code_local = f"R{inv['risk_rating_code'][-1]}"
        g.add((rating, CNFO.investorRiskRatingCode, Literal(code_local)))
        g.add((rating, CNFO.ratingForInvestor, u))
        g.add((u, CNFO.hasInvestorRiskRating, rating))
    for acc in model.accounts:
        acct = cnfoa(f"Acct{acc['account_number']}")
        fund = CNFOA[f"F{acc['fund_code']}"]
        g.add((acct, RDF.type, CNFO.FundAccount))
        g.add((acct, CNFO.accountNumber, Literal(acc["account_number"])))
        add_date(acct, CNFO.accountOpeningDate, acc["opening_date"])
        g.add((acct, CNFO.accountForFund, fund))
        g.add((acct, CNFO.accountHeldBy, investor_uri[acc["investor_id"]]))
        g.add((investor_uri[acc["investor_id"]], CNFO.hasFundAccount, acct))
        g.add((fund, CNFO.hasInvestor, investor_uri[acc["investor_id"]]))
        g.add((fund, CNFO.hasFundAccountFor, acct))
    for pos in model.positions:
        node = cnfoa(f"FPos{pos['account_number']}{pos['unit_code']}")
        g.add((node, RDF.type, CNFO.FundPosition))
        g.add((node, CNFO.positionQuantity, dec_lit(pos["quantity"])))
        g.add((node, CNFO.positionCurrency, Literal(pos["currency"])))
        g.add((node, CNFO.positionInFundUnit, unit_uri[pos["unit_code"]]))
        acct = CNFOA[f"Acct{pos['account_number']}"]
        g.add((node, CNFO.positionRecordedInAccount, acct))
        g.add((acct, CNFO.accountRecordsPosition, node))
        inv_id = next(a["investor_id"] for a in model.accounts
                      if a["account_number"] == pos["account_number"])
        g.add((node, CNFO.heldByInvestor, investor_uri[inv_id]))
        g.add((investor_uri[inv_id], CNFO.holdsFundPosition, node))
        g.add((unit_uri[pos["unit_code"]], CNFO.hasFundPosition, node))
    return g


def _first_zh_label(graph: Graph, uri) -> str:
    for pred in (SKOS.prefLabel, RDFS.label):
        for o in graph.objects(uri, pred):
            if getattr(o, "language", None) == "zh":
                return str(o)
    return ""


def _compact_predicate(pred) -> str:
    s = str(pred)
    for ns, pfx in ((str(CNFO), "cnfo"), (str(CNFC), "cnfc"), (str(CNFOM), "cnfom"),
                    (str(RDF), "rdf"), (str(RDFS), "rdfs"), (str(OWL), "owl")):
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    return s


def _pick_node_type(types: list[str]) -> str:
    """Explorer 每个节点只有一个 type（SPARQL 投影为 rdf:type 断言）。

    词法排序会有 Bug 式取舍（如 BondFund/EquityFund/ExchangeTradedFund 排在
    Fund 前面，导致 a ent:cnfo:Fund 查不全）。这里优先使用“种类”类，让
    a ent:cnfo:Fund / a ent:cnfo:FundParty / a ent:cnfo:FundUnit 等常用查询
    全部命中；具体子类型仍保留在 properties.rdf:type 中，并可用
    prop:cnfo:fundTypeCode 等数据属性过滤。
    """
    _priorities = (
        (str(CNFO.Fund), "cnfo:Fund"),
        (str(CNFO.FundParty), "cnfo:FundParty"),
        (str(CNFO.FundUnit), "cnfo:FundUnit"),
        (str(CNFO.FundAccount), "cnfo:FundAccount"),
    )
    for iri, compact in _priorities:
        if iri in types:
            return compact
    return _compact_predicate(URIRef(sorted(types)[0]))


def export_explorer_json(model: SimModel, rdf: Graph, out_path: Path,
                         vocab: OntologyVocabulary) -> dict[str, int]:
    """导出 Semantica Explorer 图（graph_id/nodes/edges，与 cnfo-fund-tbox-explorer.json
    同构）。为了可浏览性排除 3 万余条净值记录节点；代码概念与状态值以轻量节点补全，
    保证关系边两端都存在节点。

    注意：不导出 A-BOX 数据集头节点（cnfo-a:CNFOSimulatedAbox）。Semantica 的
    /api/ontology/registry 会把图中每个 owl:Ontology 节点推断为一个”本体“条目，
    若保留该节点，Ontology 面板就会显示”CNFO 仿真 A-BOX…0 Classes/0 Concepts/0 Props“，
    掩盖了真正的 T-BOX。A-BOX 数据集头只保留在 cnfo-sim-abox.ttl 中。
    """
    ppos_lookup = {(p["fund_code"], p["asset_id"]): p for p in model.portfolio_positions}

    def extra_props(s, props: dict[str, str]) -> None:
        # 组合持仓市值只存在于关系模型，补进节点属性
        if str(s).startswith(str(CNFOA) + "PPos"):
            for (fc, aid), pw in ppos_lookup.items():
                if s == CNFOA[f"PPos{fc}{aid}"]:
                    props["cnfo:positionMarketValue"] = str(pw["market_value"])
                    break

    nodes, _ = _explorer_parts(rdf, skip_prefixes=("NAV",), extra_props=extra_props)
    node_ids = {str(n["id"]) for n in nodes}
    for code_local, (scheme, label) in sorted(vocab.code_concepts.items()):
        uri = str(CNFC) + code_local
        if uri in node_ids:
            continue
        node_ids.add(uri)
        nodes.append({"id": uri, "type": "cnfc:code", "content": label,
                      "properties": {"iri": uri, "label": label, "scheme": scheme, "source": "CNFO"}})
    for status_local, label in sorted(vocab.lifecycle_statuses.items()):
        uri = str(CNFO) + status_local
        if uri in node_ids:
            continue
        node_ids.add(uri)
        nodes.append({"id": uri, "type": "cnfo:lifecycle", "content": label,
                      "properties": {"iri": uri, "label": label, "source": "CNFO"}})
    # 边必须在补全代码/状态节点后构建，否则指向这些词汇节点的关系会丢失
    edges: list[dict[str, object]] = []
    for s, p, o in rdf:
        if p == RDF.type or p == OWL.imports:
            continue
        if not isinstance(s, URIRef) or not isinstance(o, URIRef):
            continue
        if str(s) not in node_ids or str(o) not in node_ids:
            continue
        edges.append({
            "source": str(s), "target": str(o),
            "type": _compact_predicate(p), "weight": 1.0,
            "properties": {"predicate": str(p), "source": "CNFO-SIM"},
        })

    payload = {"graph_id": "cnfo-sim-abox", "nodes": nodes, "edges": edges}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"node_count": len(nodes), "edge_count": len(edges)}


def _explorer_parts(rdf: Graph, skip_prefixes: tuple[str, ...] = (),
                    extra_props=None) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """通用转换：把任意 RDF 图转成 Explorer 图的 nodes/edges 两部分。

    - 每个带 rdf:type 的 URIRef 主体成为一个节点；owl:Ontology（本体/数据集头）
      与 BNode 不作为实体节点。
    - 节点 type 优先按“种类类”（cnfo:Fund / cnfo:FundParty / ...），否则取词法
      第一类型；子类型保留在 properties.rdf:type 中。
    - 数据属性（字面量）以 "cnfo:xxx" 形式进节点 properties（网页端 SPARQL 投影
      后为 prop:cnfo:xxx）。
    - 边：URI-URI 关系；rdf:type 与 owl:imports 不作为边。
    - skip_prefixes：按节点局部名前缀排除（如 "NAV"）。
    """
    node_ids: set[str] = set()
    nodes: list[dict[str, object]] = []
    for s in sorted({s for s in rdf.subjects(RDF.type, None) if isinstance(s, URIRef)}, key=str):
        types = sorted({str(o) for o in rdf.objects(s, RDF.type)})
        if str(OWL.Ontology) in types or str(SKOS.ConceptScheme) in types:
            continue  # 本体/数据集头/SKOS 代码表方案不作为实体节点（避免 Registry 噪音）
        local_name = str(s).rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        if any(local_name.startswith(p) for p in skip_prefixes):
            continue
        label = _first_zh_label(rdf, s) or local_name
        node_ids.add(str(s))
        props: dict[str, str] = {"iri": str(s), "label": label,
                                 "rdf:type": ";".join(types), "source": "CNFO-SIM"}
        for p, o in rdf.predicate_objects(s):
            if p == RDF.type or p == RDFS.label or not isinstance(o, Literal):
                continue
            key = _compact_predicate(p)
            if key == "cnfo:sourceIdentifier":
                continue  # 冗余噪音
            props[key] = str(o)
        if extra_props is not None:
            extra_props(s, props)
        nodes.append({"id": str(s), "type": _pick_node_type(types),
                      "content": label, "properties": props})
    edges: list[dict[str, object]] = []
    for s, p, o in rdf:
        if p == RDF.type or p == OWL.imports:
            continue
        if not isinstance(s, URIRef) or not isinstance(o, URIRef):
            continue
        if str(s) not in node_ids or str(o) not in node_ids:
            continue
        edges.append({
            "source": str(s), "target": str(o),
            "type": _compact_predicate(p), "weight": 1.0,
            "properties": {"predicate": str(p), "source": "CNFO-SIM"},
        })
    return nodes, edges


def ttl_to_explorer_json(ttl_path: Path, out_path: Path,
                         skip_prefixes: tuple[str, ...] = (),
                         tbox_path: Path | None = None) -> dict[str, int]:
    """把任意 Turtle A-BOX 文件转换为 Explorer 图 JSON（--graph 仅支持 JSON）。

    - 可选 --tbox：合并 T-BOX Turtle，使 cnfc 代码概念/状态类有类型与中文标签，
      指向它们的边不会被丢弃。
    - 注意：约 3.5 万条净值记录会让 JSON 过大且超出 SPARQL 的 50k 边上限；
      转换 cnfo-sim-abox.ttl 时请加 --ttl-skip NAV。
    """
    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    if tbox_path is not None:
        g.parse(str(tbox_path), format="turtle")
    nodes, edges = _explorer_parts(g, skip_prefixes=tuple(skip_prefixes))
    payload = {"graph_id": out_path.stem, "nodes": nodes, "edges": edges}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"node_count": len(nodes), "edge_count": len(edges)}


_VOCAB_NODE_TYPES = frozenset({
    "owl:Class", "rdfs:Class", "owl:ObjectProperty", "owl:DatatypeProperty",
    "owl:AnnotationProperty", "rdf:Property", "rdfs:Datatype",
})
TBOX_EXPLORER_JSON = ROOT / "artifacts" / "cnfo" / "cnfo-fund-tbox-explorer.json"
SESSION_JSON_PATH = ABOX_DIR / "cnfo-sim-session.json"


def build_session_json(tbox_explorer: Path, abox_explorer: Path, out_path: Path,
                       ontology_version: str) -> dict[str, int] | None:
    """合并 T-BOX Explorer 图与 A-BOX Explorer 图为一个会话图。

    Semantica 的 Ontology Hub 会从图中 owl:Ontology 节点推断本体条目；T-BOX
    Explorer JSON（cnfo_tbox.export_explorer）本身不含 owl:Ontology 节点，因此这里
    补上真正的 T-BOX 本体节点（cnfo:CNFODomain，标签/版本取自 T-BOX），并给 T-BOX
    的类/属性/概念节点标注 scheme_uri，使 Registry 的 Class/Property 计数归到该
    本体条目。A-BOX 数据集头节点不出现在会话图中。
    """
    if not tbox_explorer.is_file():
        return None
    with tbox_explorer.open(encoding="utf-8") as f:
        tbox_data = json.load(f)
    with abox_explorer.open(encoding="utf-8") as f:
        abox_data = json.load(f)

    onto_uri = str(CNFO.CNFODomain)
    onto_label = "CNFO 基金领域入口"
    version = ontology_version
    # 尽量从 T-BOX 文件中取真实标签/版本
    try:
        ttl_path = ABOX_DIR.parent / "cnfo-fund-tbox.ttl"
        if ttl_path.is_file():
            tg = Graph()
            tg.parse(str(ttl_path), format="turtle")
            lbl = _first_zh_label(tg, CNFO.CNFODomain)
            if lbl:
                onto_label = lbl
            v = tg.value(CNFO.CNFODomain, OWL.versionInfo)
            if v is not None:
                version = str(v)
    except Exception:
        pass

    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str], dict] = {}
    for node in tbox_data.get("nodes", []):
        n2 = json.loads(json.dumps(node))
        props = n2.setdefault("properties", {})
        if n2.get("type") in _VOCAB_NODE_TYPES:
            props["scheme_uri"] = onto_uri
        nodes[n2["id"]] = n2
    for node in abox_data.get("nodes", []):
        nodes.setdefault(node["id"], node)
    for edge in tbox_data.get("edges", []) + abox_data.get("edges", []):
        key = (edge["source"], edge["target"], edge["type"])
        edges[key] = edge

    if onto_uri not in nodes:
        nodes[onto_uri] = {
            "id": onto_uri, "type": "owl:Ontology", "content": onto_label,
            "properties": {"iri": onto_uri, "label": onto_label, "rdf:type": "owl:Ontology",
                           "owl:versionInfo": version, "format": "turtle", "source": "CNFO"},
        }

    payload = {"graph_id": "cnfo-sim-session", "nodes": list(nodes.values()),
               "edges": list(edges.values())}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"node_count": len(payload["nodes"]), "edge_count": len(payload["edges"])}


def validate_rdf(graph: Graph) -> tuple[bool, str]:
    from pyshacl import validate
    conforms, results_graph, text = validate(
        graph,
        shacl_graph=str(SHAPES),
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
    )
    return bool(conforms), text


def validation_graph(abox: Graph) -> Graph:
    """与 tests 中 load_sample_data() 一致：T-BOX（含 cnfc 代码概念类型声明）
    + 生成的 A-BOX 合并为校验数据图。合并图需重新绑定前缀，否则形状内的
    SPARQL（cnfo:/cnfc:）无法解析。"""
    data = load_ontology_graph(TBOX_ENTRY)
    data.bind("cnfo", CNFO)
    data.bind("cnfc", CNFC)
    data.bind("cnfo-a", CNFOA)
    for triple in abox:
        data.add(triple)
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CNFO 仿真 A-BOX 生成器")
    ap.add_argument("--funds", type=int, default=40, help="基金数量（默认 40）")
    ap.add_argument("--days", type=int, default=356, help="净值序列交易日数（默认 356）")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT, help="随机种子")
    ap.add_argument("--db", type=Path, default=DB_PATH, help="SQLite 输出路径")
    ap.add_argument("--no-export-ttl", action="store_true",
                    help="不导出 Turtle A-BOX（默认导出 cnfo-sim-abox.ttl）")
    ap.add_argument("--no-explorer-json", action="store_true",
                    help="不导出 Semantica Explorer 图（默认导出 cnfo-sim-explorer.json）")
    ap.add_argument("--explorer-json-out", type=Path, default=EXPLORER_JSON_PATH,
                    help="Semantica Explorer 图输出路径")
    ap.add_argument("--no-session-json", action="store_true",
                    help="不导出 T-BOX+A-BOX 合并会话图（默认导出 cnfo-sim-session.json）")
    ap.add_argument("--session-json-out", type=Path, default=SESSION_JSON_PATH,
                    help="T-BOX+A-BOX 会话图输出路径")
    ap.add_argument("--ttl-to-json", type=Path, default=None,
                    help="仅把指定 Turtle A-BOX 转换为 Explorer 图 JSON，然后退出")
    ap.add_argument("--ttl-skip", action="append", default=[],
                    help="--ttl-to-json 时按局部名前缀排除节点（可重复，如 NAV）")
    ap.add_argument("--tbox", type=Path, default=None,
                    help="--ttl-to-json 时合并的 T-BOX Turtle（提供代码概念类型与中文标签）")
    ap.add_argument("--ttl-json-out", type=Path, default=None,
                    help="--ttl-to-json 的输出路径（默认 <ttl 同名>.explorer.json）")
    ap.add_argument("--validate-days", type=int, default=15,
                    help="SHACL 校验时每个基金的净值记录保留最近 N 个估值日（默认 15，"
                         "控制 SPARQL 校验成本；SQLite 中仍写入全量序列）")
    ap.add_argument("--no-validate", action="store_true", help="跳过 SHACL 校验")
    args = ap.parse_args(argv)

    if args.ttl_to_json is not None:
        ttl_in = Path(args.ttl_to_json).expanduser().resolve()
        if not ttl_in.is_file():
            print(f"TTL 文件不存在: {ttl_in}")
            return 1
        ttl_out = Path(args.ttl_json_out).expanduser().resolve() if args.ttl_json_out \
            else ttl_in.with_name(ttl_in.stem + ".explorer.json")
        tbox_in = Path(args.tbox).expanduser().resolve() if args.tbox else None
        print(f"[ttl-to-json] 转换: {ttl_in}")
        if tbox_in:
            print(f"  合并 T-BOX: {tbox_in}")
        counts = ttl_to_explorer_json(ttl_in, ttl_out,
                                      tuple(args.ttl_skip or ()), tbox_in)
        print(f"  输出: {ttl_out}（节点 {counts['node_count']} / 边 {counts['edge_count']}）")
        print("  可用 fondontology\\explorer.py --mode graph --graph <输出路径> 加载浏览")
        return 0

    print(f"[1/4] 加载本体: {TBOX_ENTRY.relative_to(ROOT)}")
    graph = load_ontology_graph(TBOX_ENTRY)
    vocab = OntologyVocabulary(graph)
    print(f"      本体版本 {vocab.ontology_version}，代码概念 {len(vocab.code_concepts)}，"
          f"生命周期状态 {len(vocab.lifecycle_statuses)}")

    print(f"[2/4] 生成仿真数据（seed={args.seed}, funds={args.funds}, days={args.days}）")
    model = generate(vocab, args.funds, args.days, args.seed)

    print(f"[3/4] 写入 SQLite: {args.db}")
    write_sqlite(model, args.db, vocab, args.seed)
    n_funds = len(model.funds)
    n_units = len(model.units)
    n_navs = len(model.navs)
    n_inv = len(model.investors)
    n_acct = len(model.accounts)
    n_pos = len(model.positions)
    n_ppos = len(model.portfolio_positions)
    print(f"      基金 {n_funds} / 份额 {n_units} / 净值记录 {n_navs} / 投资者 {n_inv} / "
          f"账户 {n_acct} / 投资者持仓 {n_pos} / 组合持仓 {n_ppos}")

    rdf = build_rdf(model, ontology_version=vocab.ontology_version)
    print(f"      A-BOX 图规模: {len(rdf)} 三元组")

    if not args.no_export_ttl:
        out_ttl = args.db.with_name("cnfo-sim-abox.ttl")
        print(f"      导出 Turtle A-BOX: {out_ttl}")
        rdf.serialize(destination=str(out_ttl), format="turtle")
        # 回读校验导出文件本身可被解析
        check = Graph()
        check.parse(str(out_ttl), format="turtle")
        print(f"      回读校验: {len(check)} 三元组（与内存一致: {len(check) == len(rdf)}）")

    if not args.no_explorer_json:
        print(f"      导出 Semantica Explorer 图: {args.explorer_json_out}")
        counts = export_explorer_json(model, rdf, args.explorer_json_out, vocab)
        print(f"      节点 {counts['node_count']} / 边 {counts['edge_count']}")

    if not args.no_session_json:
        print(f"      导出 T-BOX+A-BOX 会话图: {args.session_json_out}")
        ses = build_session_json(TBOX_EXPLORER_JSON, args.explorer_json_out,
                                 args.session_json_out, vocab.ontology_version)
        if ses is None:
            print("      跳过：未找到 T-BOX Explorer 图，请先运行 "
                  "`.venv\\Scripts\\python.exe main.py export-explorer`")
        else:
            print(f"      节点 {ses['node_count']} / 边 {ses['edge_count']}")

    if args.no_validate:
        print("[4/4] 已跳过 SHACL 校验")
    else:
        print(f"[4/4] SHACL 数据质量校验（A-BOX + T-BOX，净值取最近 {args.validate_days} 个估值日）…")
        rdf_v = build_rdf(model, nav_window_days=args.validate_days,
                          ontology_version=vocab.ontology_version)
        data = validation_graph(rdf_v)
        print(f"      校验图规模: {len(data)} 三元组")
        conforms, text = validate_rdf(data)
        print(f"      conforms = {conforms}")
        if not conforms:
            print("------ 违规报告（前 80 行）------")
            for line in text.splitlines()[:80]:
                print(line)
            print("----------------------------------")
            return 2
        print("      OK：全部通过 SHACL 数据质量校验")
    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())