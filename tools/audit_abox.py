# -*- coding: utf-8 -*-
"""ABOX 数据一致性审计（仿真数据完整性门槛）。

检查项：
1. 基金管理链闭合：每只基金 hasFundManagerRole → roleInFund → rolePlayedBy ≥1
   （"基金必有人管理"，与 SHACL FundShape.hasFundManagerRole minCount=1 呼应）
2. 基金经理绑定：绑定（playsFundRole）与"在职未分派"（无边，合法孤立）分布
3. 孤儿实体：type/label 之外无任何业务出入边的 CNFOA 实体
   ——预期仅剩"无在管基金经理"这类有意保留的合法实体
4. 登记机构等主体营业性抽查（可选输出）

用法：
    .venv\\Scripts\\python.exe tools\\audit_abox.py [--ttl artifacts/cnfo/abox/cnfo-sim-abox.ttl]
退出码：0 = 通过；1 = 存在非预期问题。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")
CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")

ALLOWED_ORPHAN_TYPES = {"FundManagerPerson"}  # “在职未分派”经理：合法孤立


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CNFO A-BOX 一致性审计")
    ap.add_argument("--ttl", type=Path,
                    default=Path("artifacts/cnfo/abox/cnfo-sim-abox.ttl"))
    args = ap.parse_args(argv)

    g = Graph()
    g.parse(str(args.ttl), format="turtle")
    outd, ind = Counter(), Counter()
    for s, p, o in g:
        if p == RDF.type or p == RDFS.label:
            continue
        if isinstance(s, URIRef):
            outd[s] += 1
        if isinstance(o, URIRef):
            ind[o] += 1

    problems: list[str] = []

    # 1) 基金管理链闭合
    funds = list(g.subjects(RDF.type, CNFO.Fund))
    bad_fund = 0
    for f in funds:
        roles = list(g.objects(f, CNFO.hasFundManagerRole))
        if len(roles) != 1 or roles[0] is None:
            bad_fund += 1
            continue
        r = roles[0]
        if (r, CNFO.roleInFund, f) not in g or not list(g.objects(r, CNFO.rolePlayedBy)):
            bad_fund += 1
    print(f"[1] 基金管理链闭合：{len(funds) - bad_fund}/{len(funds)}"
          + ("" if bad_fund == 0 else f"  ← 问题 {bad_fund}"))
    if bad_fund:
        problems.append(f"{bad_fund} 只基金管理链不闭合")

    # 2) 基金经理绑定分布
    persons = list(g.subjects(RDF.type, CNFO.FundManagerPerson))
    bound = sum(1 for p in persons if list(g.objects(p, CNFO.playsFundRole)))
    print(f"[2] 基金经理：{len(persons)} 位（绑定 {bound}，无在管 {len(persons) - bound}）")

    # 3) 孤儿实体
    orphans: list[tuple[str, str]] = []
    for s in g.subjects(RDF.type, None):
        if not isinstance(s, URIRef) or not str(s).startswith(str(CNFOA)):
            continue
        if outd[s] == 0 and ind[s] == 0:
            label = next((str(x) for x in g.objects(s, RDFS.label)), str(s).split("/")[-1])
            types = [str(t).split("/")[-1] for t in g.objects(s, RDF.type)
                     if str(t).startswith(str(CNFO))]
            orphans.append((label, types[0] if types else "?"))
    unexpected = [(lb, ty) for lb, ty in orphans if ty not in ALLOWED_ORPHAN_TYPES]
    print(f"[3] 孤儿实体：{len(orphans)} 个（有意保留：{sorted(ALLOWED_ORPHAN_TYPES)}）")
    for label, ty in orphans:
        print(f"      {label!r} [{ty}]")
    if unexpected:
        problems.append(f"非预期孤儿实体 {unexpected}")

    # 4) 登记机构营业性（有角色承担入边）
    registrars = [
        p for p in g.subjects(RDF.type, CNFO.FundParty)
        if any(k in str(o) for o in g.objects(p, RDFS.label) for k in ("华登", "中证"))
    ]
    for p in registrars:
        name = next(str(o) for o in g.objects(p, RDFS.label))
        print(f"[4] 登记机构 {name}：被承担角色数（入边）={ind[p]}"
              + ("" if ind[p] > 0 else "  ← 无业务"))

    if problems:
        print("\n审计未通过：")
        for p in problems:
            print("  -", p)
        return 1
    print("\n审计通过：全部一致（基金必有人管理；孤立实体均为合法保留）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())