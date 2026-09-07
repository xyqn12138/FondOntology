"""Semantic Enforcement：数据导入时的本体语义控制层（三阶段生命周期之二）。

用户问数哲学（本项目语义控制层）：
  数据导入阶段 Ontology 不是"让 LLM 推理"，而是 Graph 的语义控制层 / Schema 层。
  Raw Data → Entity Resolution → Ontology Mapping → Validation → (静态) Reasoning
  → Semantic Graph。

一条松散记录（dict/JSON）被约束成合法语义三元组：
- 类型约束：人名→FundManagerPerson、公司名→FundManagementCompany、基金→Fund
  及其类型子类（"混合型"→HybridFund，经本体词表而非自由文本）
- 关系约束：只允许本体声明的 domain/range（如 hasFundManager 仅允许
  Fund→FundParty；端点类型非法直接拒绝，不允许 Fund managedBy Fund）
- 属性约束：字段名必须映射到 CNFO/CNFC 合法属性/代码值，未知字段报错
- 继承闭环：新实例断言类型子类并补全祖先链（HybridFund→Fund→FundBusinessObject）
- 推理衔接：产出图可并入数据栈，交给既有推理层与问数链路继续使用
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from .graph import DataStack
from .index import OntologyIndex

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFC = Namespace("https://ontology.example.cn/cnfo/code/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")

# 原始基金类型文本 → CNFO 类型类（类型约束词表）
_TYPE_LEXICON = {
    "股票型": "EquityFund", "混合型": "HybridFund", "债券型": "BondFund",
    "货币市场": "MoneyMarketFund", "货币市场型": "MoneyMarketFund",
    "指数型": "EquityFund", "ETF": "ExchangeTradedFund", "FOF": "FundOfFunds",
    "QDII": "QDIIFund", "私募股权": "PrivateEquityFund", "私募证券": "PrivateSecuritiesInvestmentFund",
}
# 原始字段 → (CNFO 属性, 代码词表)
_CODE_FIELDS = {
    "operation_mode": ("hasFundOperationMode", {
        "开放式": "FundOperationModeOpenEnded", "封闭式": "FundOperationModeClosedEnded"}),
    "organization_form": ("hasFundOrganizationForm", {
        "契约型": "FundOrganizationFormContractual", "公司型": "FundOrganizationFormCorporate",
        "合伙型": "FundOrganizationFormPartnership"}),
    "risk_level": ("hasFundRiskLevel", {
        "R1": "FundRiskLevelR1", "R2": "FundRiskLevelR2", "R3": "FundRiskLevelR3",
        "R4": "FundRiskLevelR4", "R5": "FundRiskLevelR5"}),
}
# 原始字段名 → CNFO 数据属性（属性约束词表）
_DATATYPE_MAP = {
    "fund_code": "fundCode", "fund_name": "fundName", "fund_short_name": "fundShortName",
    "inception_date": "inceptionDate", "base_currency": "baseCurrency",
}
_AUM_UNIT = 1e8  # "32.5亿" → 32.5 * 1e8


def _local(uri) -> str:
    s = str(uri).rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


@dataclass
class EnforcementResult:
    graph: Graph = field(default_factory=Graph)
    resolved: dict = field(default_factory=dict)
    new_entities: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    validations: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class SemanticEnforcer:
    """一条原始记录 → 本体约束的语义三元组。"""

    def __init__(self, stack: DataStack):
        self.stack = stack
        self.index = OntologyIndex(stack)
        self._tbox = stack.tbox
        self._abox = stack.abox
        self._seq = 1000

    # ---------------------------------------------------------------- 实体
    def _allocate(self) -> URIRef:
        self._seq += 1
        return URIRef(str(CNFOA) + f"E{self._seq}")

    def _fund_by_code(self, code: str) -> Optional[URIRef]:
        for iri in self.index._entity_codes.get(code, []):
            return URIRef(iri)
        return None

    def _fund_by_name(self, name: str) -> Optional[URIRef]:
        """按基金名称查既有 Fund 实体（唯一性约束用；fundName / rdfs:label 双通道）。

        与 _fund_by_code 的语义分工：fundCode 是合并键（同代码 → 同一基金，
        走更新）；fundName 是全库唯一约束（同名称不同代码 → 冗余数据，拒绝）。
        """
        for s in self._abox.subjects(CNFO.fundName, Literal(name)):
            return s
        for s in self._abox.subjects(RDFS.label, Literal(name, lang="zh")):
            if (s, RDF.type, CNFO.Fund) in self._abox:
                return s
        return None

    def _find_by_label(self, label: str) -> Optional[URIRef]:
        for iri, meta in self.index.entities.items():
            if meta.get("label") == label:
                return URIRef(iri)
        return None

    def _subclass_closure(self, cls: URIRef) -> set[URIRef]:
        return {c for c in self._tbox.transitive_subjects(RDFS.subClassOf, cls)} | {cls}

    def _instance_of_any(self, graph: Graph, entity: URIRef, classes: set[URIRef]) -> bool:
        """实体是否属于 classes 闭包：合并本次结果图断言与既有 A-BOX 断言。"""
        types = set(graph.objects(entity, RDF.type)) | set(self._abox.objects(entity, RDF.type))
        for t in types:
            if isinstance(t, URIRef) and self._subclass_closure(t) & classes:
                return True
        return False

    def _existing_types_ok(self, entity: URIRef, classes: set[URIRef]) -> bool:
        """仅按既有断言校验（新实体视为待建、允许）；已有类型必须落入合法闭包。"""
        existing = {t for t in self._abox.objects(entity, RDF.type) if isinstance(t, URIRef)}
        if not existing:
            return True
        return any(self._subclass_closure(t) & classes for t in existing)

    # ---------------------------------------------------------------- 入口
    def enforce(self, record: dict) -> EnforcementResult:
        r = EnforcementResult()
        g = r.graph

        # ---- ① 实体解析 ----
        code = str(record.get("fund_code") or "").strip()
        type_text = str(record.get("fund_type") or "").strip()
        company_name = str(record.get("management_company") or "").strip()
        person_name = str(record.get("person") or "").strip()
        if not code or not type_text:
            r.errors.append("必填字段缺失（fund_code / fund_type）")

        fund = self._fund_by_code(code)
        is_new_fund = fund is None
        if fund is None:
            fund = self._allocate()
            r.new_entities[fund] = "Fund"
            r.validations.append(f"新建基金实体 {_local(fund)}（fund_code={code}）")
        company = self._find_by_label(company_name) if company_name else None
        if company is None and company_name:
            company = self._allocate()
        person = self._find_by_label(person_name) if person_name else None
        if person is None and person_name:
            person = self._allocate()

        r.resolved = {"fund": str(fund), "fund_code": code,
                      "management_company": str(company) if company else None,
                      "person": str(person) if person else None}

        # ---- ①b 唯一性约束：新基金名称不得与库内既有 Fund 重复 ----
        # （同 fundCode 走实体合并属正常更新；同名称不同代码 = 冗余录入，拒绝。
        #  批内重复同样被拦截：import_records 逐条合并，后一条能查到前一条。）
        fund_name = str(record.get("fund_name") or "").strip()
        if is_new_fund and fund_name:
            clash = self._fund_by_name(fund_name)
            if clash is not None:
                r.errors.append(
                    f"唯一性约束违反：基金名称 {fund_name!r} 已被 {_local(clash)} 使用"
                    "（fundCode 是合并键、fundName 全库唯一；"
                    "若实为同一只基金，请使用其既有 fund_code 导入）")

        # ---- ② 类型约束（本体词表映射） ----
        type_cls = _TYPE_LEXICON.get(type_text)
        if type_cls is None:
            r.errors.append(f"fund_type 不在本体类型词表：{type_text!r}（可选：{sorted(_TYPE_LEXICON)}）")
            type_cls = "Fund"
        cls_iri = CNFO[type_cls]
        if (cls_iri, RDF.type, None) not in self._tbox:
            r.errors.append(f"类型类不存在于本体：{type_cls}")
        # 继承闭环：子类→祖先链到 Fund（静态推理样例）
        if is_new_fund:
            g.add((fund, RDF.type, CNFO.Fund))
        g.add((fund, RDF.type, cls_iri))
        chain = [cls_iri]
        cur = cls_iri
        while True:
            parent = next((o for o in self._tbox.objects(cur, RDFS.subClassOf)
                           if isinstance(o, URIRef) and str(o).startswith(str(CNFO))), None)
            if parent is None or parent in chain:
                break
            chain.append(parent)
            cur = parent
        if is_new_fund:
            for anc in chain[1:]:
                g.add((fund, RDF.type, anc))  # 显式继承：HybridFund→Fund→FundBusinessObject
        elif not self._instance_of_any(g, fund, {cls_iri}):
            g.add((fund, RDF.type, cls_iri))
        if record.get("fund_name"):
            g.add((fund, RDFS.label, Literal(str(record["fund_name"]), lang="zh")))

        # ---- ③ 属性约束（字段必须命中本体词表；aum 映射到净值记录） ----
        for field, value in record.items():
            if field in ("fund_type", "management_company", "person"):
                continue
            if field == "aum":
                try:
                    aum = Decimal(str(value).replace("亿", "")) * Decimal(_AUM_UNIT)
                except Exception:
                    r.errors.append(f"aum 无法解析：{value!r}")
                    continue
                nav = self._allocate()
                g.add((nav, RDF.type, CNFO.NetAssetValueRecord))
                g.add((nav, CNFO.recordForFund, fund))
                g.add((nav, CNFO.valuationDate,
                       Literal(date.today().isoformat(), datatype=XSD.date)))
                lex = str(round(aum)) if aum == aum.to_integral_value() else format(aum, "f")
                g.add((nav, CNFO.fundNetAssetValue, Literal(lex, datatype=XSD.decimal)))
                g.add((fund, CNFO.hasNetAssetValueRecord, nav))
                r.validations.append(f"aum={value} → NetAssetValueRecord（{lex}）")
                continue
            if field in _DATATYPE_MAP:
                g.add((fund, CNFO[_DATATYPE_MAP[field]], Literal(str(value))))
                continue
            if field in _CODE_FIELDS:
                prop_name, vocab = _CODE_FIELDS[field]
                code_val = vocab.get(str(value).strip())
                if code_val is None:
                    r.errors.append(f"{field} 值不在代码词表：{value!r}")
                    continue
                g.add((fund, CNFO[prop_name], CNFC[code_val]))
                continue
            if field == "fund_code" or field == "fund_name" and _DATATYPE_MAP.get(field):
                pass  # 已在上方处理
            else:
                r.errors.append(f"未知字段 {field!r}：本体属性/代码词表中不存在")

        # ---- ④ 关系约束（domain/range 校验；关系走属性链，由推理层物化
        #       hasFundManager，而非导入时直接写出） ----
        role = None
        if company is not None:
            # 既有实体必须已落在合法 range 闭包（不允许 Fund managedBy Fund）；
            # 新建实体视为"待建设"，由本层断言正确类型
            if not self._existing_types_ok(company, self._subclass_closure(CNFO.FundParty)):
                r.errors.append("关系被拒：hasFundManagerRole∘rolePlayedBy 的终点范围是 "
                                f"FundParty，但 {_local(company)} 的类型不在其子类闭包内")
                company = None
            else:
                g.add((company, RDF.type, CNFO.FundParty))
                g.add((company, RDF.type, CNFO.FundManagementCompany))
                g.add((company, RDFS.label, Literal(company_name, lang="zh")))
        if person is not None:
            g.add((person, RDF.type, CNFO.FundParty))
            g.add((person, RDF.type, CNFO.FundManagerPerson))
            if person_name:
                g.add((person, RDFS.label, Literal(person_name, lang="zh")))
        if company is not None or person is not None:
            role = self._allocate()
            g.add((role, RDF.type, CNFO.FundManagerRole))
            g.add((role, CNFO.roleInFund, fund))
            g.add((fund, CNFO.hasFundManagerRole, role))
            if company is not None:
                g.add((role, CNFO.rolePlayedBy, company))
                r.validations.append(f"关系：{_local(fund)} hasFundManagerRole "
                                     f"{_local(role)} rolePlayedBy {_local(company)}")
            if person is not None:
                g.add((person, CNFO.playsFundRole, role))
                r.validations.append(f"关系：{_local(person)} playsFundRole {_local(role)}"
                                     "（逆关系+属性链 → 推理物化 hasFundManager）")

        return r

    def merge_into_stack(self, r: EnforcementResult) -> None:
        """把约束产物并入数据栈（失效推理/查询/索引缓存，供问数链路即用）。"""
        if not r.ok:
            raise ValueError(f"约束未通过，拒绝并入：{r.errors}")
        for triple in r.graph:
            self._abox.add(triple)
        self.stack._abox_inferred = None
        self.stack._combined = None
        self.stack._inference_registry = None
        # 索引缓存失效（弱引用键：栈对象仍在，需显式清出）
        from . import engine as _engine
        _engine._INDEX_CACHE.pop(self.stack, None)
        # 同步本层实体索引：批量导入时后续记录能解析到本次新建实体（同基金/同公司）
        idx = self.index
        for s in set(r.graph.subjects(RDF.type, None)):
            if not isinstance(s, URIRef) or not str(s).startswith(str(CNFOA)):
                continue
            key = str(s)
            if key not in idx.entities:
                label = ""
                for o in r.graph.objects(s, RDFS.label):
                    label = str(o)
                    break
                codes = [str(o) for p in (CNFO.fundCode, CNFO.fundUnitCode,
                                          CNFO.accountNumber)
                         for o in r.graph.objects(s, p)]
                types = sorted({str(t) for t in r.graph.objects(s, RDF.type)
                                if isinstance(t, URIRef)})
                idx.entities[key] = {"label": label or _local(key),
                                     "codes": codes, "types": types}
                for c in codes:
                    idx._entity_codes.setdefault(c, []).append(key)


def import_records(records: list[dict], stack: DataStack, *,
                   strict: bool = False) -> dict:
    """批量数据导入生产路径：Raw Records → Semantic Enforcement → Semantic Graph。

    三阶段生命周期之"Semantic Enforcement"的正式入口：
    每条原始记录（dict/JSON 行）经类型约束 → 关系约束 → 属性约束 → 继承闭环
    约束为合法语义三元组后并入数据栈；推理缓存失效后，问数链路即刻可答
    （hasFundManager 等由定向物化推理补全）。

    strict=False（默认）：失败记录跳过并记入 failed，成功记录照常导入；
    strict=True：任一记录失败则整体拒绝（原子导入，已并入的不会回滚——
    调用方应在导入前自行快照）。

    返回 {"imported": int, "failed": [{"index","record","errors"}],
          "validations": [...]}。
    """
    enforcer = SemanticEnforcer(stack)
    imported = 0
    failed: list[dict] = []
    validations: list[str] = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            failed.append({"index": i, "record": record,
                           "errors": ["记录不是 dict/JSON 对象"]})
            if strict:
                break
            continue
        r = enforcer.enforce(record)
        if not r.ok:
            failed.append({"index": i, "record": record, "errors": list(r.errors)})
            if strict:
                break
            continue
        enforcer.merge_into_stack(r)
        imported += 1
        validations.extend(r.validations)
    return {"imported": imported, "failed": failed, "validations": validations}