# -*- coding: utf-8 -*-
"""CNFO V0.5.2：restriction 稳定性分类 + 属性关系契约表生成。

输出：
- artifacts/v05_restriction_classification.md  49 条 OWL restriction 三类分类
- artifacts/v05_property_contract.md           101 对象属性 + 42 数据属性契约表
"""
from __future__ import annotations

import re
from pathlib import Path

import rdflib
from rdflib import Namespace, term
from rdflib.namespace import OWL, RDF, RDFS, SKOS

ROOT_DIR = Path(__file__).resolve().parents[1]
NS = Namespace("https://ontology.example.cn/cnfo/ontology/")
OUT = ROOT_DIR / "artifacts"


def local(uri) -> str:
    s = str(uri)
    return s.replace(str(NS), "") if s.startswith(str(NS)) else s.rsplit("/", 1)[-1]


def main() -> None:
    g = rdflib.Graph()
    g.parse(ROOT_DIR / "ontology" / "modules" / "cnfo-domain.ttl", format="turtle")
    g.parse(ROOT_DIR / "ontology" / "cnfo-fund.ttl", format="turtle")
    g.parse(ROOT_DIR / "ontology" / "modules" / "cnfo-fund-codes.ttl", format="turtle")
    g.parse(ROOT_DIR / "ontology" / "modules" / "cnfo-module-vocabulary.ttl", format="turtle")

    # ============ 1. restriction 分类 ============
    # 手动分类：稳定本体语义 / 条件性业务语义 / 数据质量校验
    QUALITY_KEYS = {
        ("FundRoleAssignment", "effectiveFrom"), ("FundRoleAssignment", "effectiveTo"),
        ("FundStatusRecord", "effectiveFrom"), ("FundStatusRecord", "effectiveTo"),
        ("FundPosition", "positionQuantity"), ("PortfolioPosition", "positionAsOfDate"),
        ("NetAssetValueRecord", "valuationDate"), ("NetAssetValueRecord", "valuationCurrency"),
        ("FundUnit", "unitCurrency"),
    }
    CONDITIONAL_KEYS = {
        ("FundPortfolioInvestmentPolicy", "stipulatesBenchmark"),
        ("FundInvestmentObjective", "hasIntendedRiskLevel"),
        ("Fund", "hasFundStatusRecord"),
    }

    rows = []
    for r in g.subjects(RDF.type, OWL.Restriction):
        prop = g.value(r, OWL.onProperty)
        owner = g.value(subject=None, predicate=RDFS.subClassOf, object=r)
        pname = local(prop) if prop else "?"
        oname = local(owner) if owner else "?"
        quant = None
        for pred, lab in (
            (OWL.someValuesFrom, "some"), (OWL.allValuesFrom, "only"),
            (OWL.hasValue, "value"), (OWL.qualifiedCardinality, "q1"),
            (OWL.minQualifiedCardinality, "q-min"), (OWL.maxQualifiedCardinality, "q-max"),
            (OWL.cardinality, "exactly1"), (OWL.minCardinality, "min"),
            (OWL.maxCardinality, "max"),
        ):
            v = g.value(r, pred)
            if v is not None:
                on_class = g.value(r, OWL.onClass)
                filler = local(v) if isinstance(v, term.URIRef) else str(v)
                quant = f"{lab} {filler}" + (f"[onClass {local(on_class)}]" if on_class else "")
                break
        key = (oname, pname)
        if key in CONDITIONAL_KEYS:
            cat, note = "条件性业务语义", "仅适用于特定监管类型或业务场景，不宜作为所有基金的通用约束。"
        elif key in QUALITY_KEYS:
            cat, note = "数据质量校验", "必填/单值基数，属数据完整性要求，落地为 SHACL minCount/maxCount。"
        else:
            cat, note = "稳定本体语义", "结构性定义语义，保留在 OWL T-BOX。"
        rows.append((oname, pname, quant, cat, note))

    lines = ["# CNFO V0.5 OWL Restriction 稳定性分类（49 条）", ""]
    lines.append("| 所属类 | 属性 | 约束 | 分类 | 说明 |")
    lines.append("|---|---|---|---|---|")
    order = {"稳定本体语义": 0, "条件性业务语义": 1, "数据质量校验": 2}
    for oname, pname, quant, cat, note in sorted(rows, key=lambda x: (order[x[3]], x[0], x[1])):
        lines.append(f"| {oname} | {pname} | {quant} | {cat} | {note} |")
    lines.append("")
    from collections import Counter

    cnt = Counter(r_[3] for r_ in rows)
    lines.append(f"**统计**：稳定本体语义 {cnt['稳定本体语义']} 条；条件性业务语义 {cnt['条件性业务语义']} 条；"
                 f"数据质量校验 {cnt['数据质量校验']} 条。")
    (OUT / "v05_restriction_classification.md").write_text("\n".join(lines), encoding="utf-8")

    # ============ 2. 属性契约表 ============
    # SHACL 形状中出现的路径（从 shapes 解析）
    shapes_graph = rdflib.Graph()
    shapes_graph.parse(ROOT_DIR / "ontology" / "shacl" / "cnfo-fund-shapes.ttl", format="turtle")
    sh_path = rdflib.URIRef("http://www.w3.org/ns/shacl#path")
    shacl_props = set()
    for p in shapes_graph.objects(None, sh_path):
        if isinstance(p, term.URIRef) and str(p).startswith(str(NS)):
            shacl_props.add(local(p))

    prop_rows = []
    for rdf_type, kind in ((OWL.ObjectProperty, "对象属性"), (OWL.DatatypeProperty, "数据属性")):
        for p in g.subjects(RDF.type, rdf_type):
            if not str(p).startswith(str(NS)):
                continue
            name = local(p)
            label = next((str(o) for o in g.objects(p, RDFS.label) if getattr(o, "language", None) == "zh"), "")
            definition = next((str(o) for o in g.objects(p, SKOS.definition) if getattr(o, "language", None) == "zh"), "")
            domains = [local(o) for o in g.objects(p, RDFS.domain)]
            ranges = [local(o) for o in g.objects(p, RDFS.range)]
            sub_of = [local(o) for o in g.objects(p, RDFS.subPropertyOf) if str(o).startswith(str(NS))]
            inv_of = [local(o) for o in g.objects(p, OWL.inverseOf) if str(o).startswith(str(NS))]
            std_name = next((str(o) for o in g.objects(p, rdflib.Namespace("https://ontology.example.cn/cnfo/module/").standardName)), "")
            std_ref = next((str(o) for o in g.objects(p, rdflib.Namespace("https://ontology.example.cn/cnfo/module/").standardRef)), "")
            # 使用的 restriction
            uses = []
            for r in g.subjects(OWL.onProperty, p):
                owner = g.value(subject=None, predicate=RDFS.subClassOf, object=r)
                if owner:
                    uses.append(local(owner))
            use_txt = "；".join(sorted(set(uses))) if uses else "—"
            shacl_txt = "是" if name in shacl_props else "—"
            std_name_txt = std_name or "—"
            std_ref_txt = std_ref or "—"
            prop_rows.append((kind, name, label, definition, "、".join(domains) or "—",
                              "、".join(ranges) or "—", "、".join(sub_of) or "—",
                              "、".join(inv_of) or "—", "—（未声明）", std_name_txt, std_ref_txt,
                              use_txt, shacl_txt))

    object_count = sum(
        1 for resource in g.subjects(RDF.type, OWL.ObjectProperty)
        if str(resource).startswith(str(NS))
    )
    data_count = sum(
        1 for resource in g.subjects(RDF.type, OWL.DatatypeProperty)
        if str(resource).startswith(str(NS))
    )
    lines2 = [
        f"# CNFO V0.5.2 属性关系契约表（{len(prop_rows)} 项：{object_count} 对象属性 + {data_count} 数据属性）",
        "",
    ]
    lines2.append("| 类型 | 属性名称 | 中文标签 | 中文定义 | domain | range | 父属性 | 逆属性 | 属性特征 | 标准英文名 | 标准出处 | 用于 restriction | SHACL 覆盖 |")
    lines2.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in prop_rows:
        cells = "|".join(c.replace("|", "｜") for c in row)
        lines2.append(f"|{cells}|")
    (OUT / "v05_property_contract.md").write_text("\n".join(lines2), encoding="utf-8")

    print(f"restrictions classified: {len(rows)} -> stable {cnt['稳定本体语义']}, "
          f"conditional {cnt['条件性业务语义']}, quality {cnt['数据质量校验']}")
    print(f"property contract rows: {len(prop_rows)}; SHACL-covered props: {len(shacl_props)}")


if __name__ == "__main__":
    main()
