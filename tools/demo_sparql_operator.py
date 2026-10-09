"""最小示例：展示日期范围 + AVG 聚合 SPARQL 算子。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.qa.abox_query import execute_find
from fondontology.qa.graph import build_stack
from fondontology.qa.query_planner import plan_find
from fondontology.qa.semantics import OntologyContext
from fondontology.qa.sparql_builder import build_select


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
DEFAULT_ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="展示日期范围 + AVG 聚合 SPARQL 算子")
    parser.add_argument("--from-date", default="2025-04-01",
                        help="估值日期起点，格式 YYYY-MM-DD")
    parser.add_argument("--to-date", default="2025-04-30",
                        help="估值日期终点，格式 YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=5,
                        help="最多展示多少条结果")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="T-BOX 入口文件")
    parser.add_argument("--abox", type=Path, default=DEFAULT_ABOX,
                        help="A-BOX 文件")
    parser.add_argument("--show-sparql", action="store_true",
                        help="输出完整 SPARQL")
    args = parser.parse_args()

    stack = build_stack(args.source, args.abox)
    plan = plan_find(
        target="Fund",
        tbox=stack.tbox,
        abox=stack.abox,
        related_class="NetAssetValueRecord",
        relation_path=[{"property": "hasNetAssetValueRecord"}],
        date_ranges=[{
            "property": "valuationDate",
            "on": "related",
            "from": args.from_date,
            "to": args.to_date,
        }],
        aggregation={
            "func": "avg",
            "measure_property": "fundUnitNetAssetValue",
        },
        ctx=OntologyContext.from_stack(stack),
    )

    if plan["errors"]:
        print("QueryPlan 无效：")
        for error in plan["errors"]:
            print(f" - {error}")
        return 1

    sparql = build_select(plan)
    result = execute_find(stack, plan, with_abox_inferred=False)
    if result.errors:
        print("查询执行失败：")
        for error in result.errors:
            print(f" - {error}")
        return 1

    print("问题：查询指定日期范围内每只基金的平均份额净值")
    print(f"日期范围：{args.from_date} 至 {args.to_date}")
    print("算子：PathJoin + DateRange + AVG + GROUP BY")
    print(f"命中基金数：{result.count}")
    print()
    print("【前几条结果】")
    for fund, value in list(result.measures.items())[:max(args.limit, 0)]:
        print(f"{fund}: {value}")

    if args.show_sparql:
        print()
        print("【生成的 SPARQL】")
        print(sparql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
