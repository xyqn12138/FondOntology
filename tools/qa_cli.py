# -*- coding: utf-8 -*-
"""CNFO 基金智能问数 — 命令行入口（单问 / 交互式 REPL）。

用法：
    .venv\\Scripts\\python.exe tools\\qa_cli.py "有哪些交易型开放式指数基金"
    .venv\\Scripts\\python.exe tools\\qa_cli.py --repl
    .venv\\Scripts\\python.exe tools\\qa_cli.py --detail "R4以上的基金有哪些"

选项：--source（T-BOX 入口，默认 ontology/modules/cnfo-domain.ttl）
      --abox（A-BOX TTL，默认 artifacts/cnfo/abox/cnfo-sim-abox.ttl）
      --no-llm（强制模板表达）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.qa.engine import answer_question
from fondontology.qa.graph import build_stack

ROOT = Path(__file__).resolve().parents[1]


def run(stack, question: str, *, detail: bool, use_llm: bool | None) -> int:
    ans = answer_question(question, stack, use_llm=use_llm)
    print(ans.text)
    if detail:
        print()
        print("── 溯源 ──")
        print(f"状态: {ans.status}（意图 {ans.intent_status or '-'} / 判定 {ans.verdict or '-'}）")
        if ans.explanation:
            e = ans.explanation
            print(f"表达: gate={e['gate']} used_llm={e['used_llm']} UCR={e['ucr']} "
                  f"claims={e['claims_used']}")
        if ans.report:
            print(f"证据: {len(ans.report.get('evidence', []))} 条 / "
                  f"claims: {len(ans.report.get('claims', []))} 条")
            for c in ans.report.get("claims", []):
                print(f"  {c['claim_id']}[{c['type']}] {c['claim']} → {c['evidence']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CNFO 智能问数 CLI")
    ap.add_argument("question", nargs="?", default=None, help="单次提问；省略则进入 REPL")
    ap.add_argument("--repl", action="store_true", help="交互式问答循环")
    ap.add_argument("--detail", action="store_true", help="输出证据/claims 溯源")
    ap.add_argument("--source", type=Path, default=ROOT / "ontology" / "modules" / "cnfo-domain.ttl")
    ap.add_argument("--abox", type=Path, default=ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl")
    ap.add_argument("--no-llm", action="store_true", help="强制确定性模板表达")
    args = ap.parse_args(argv)

    print(f"加载本体数据栈（{args.source.name} + {args.abox.name}）…")
    stack = build_stack(args.source, args.abox)
    use_llm = False if args.no_llm else None

    question = (args.question or "").strip()
    if question:
        return run(stack, question, detail=args.detail, use_llm=use_llm)
    if args.repl or args.question is None and not args.repl:
        print("交互式问数（输入问题回车；输入 exit/quit 退出）")
        while True:
            try:
                q = input("问数> ").strip()
            except EOFError:
                break
            if not q:
                continue
            if q.lower() in ("exit", "quit"):
                break
            run(stack, q, detail=args.detail, use_llm=use_llm)
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())