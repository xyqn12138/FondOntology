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


def run(stack, question: str, *, detail: bool, use_llm: bool | None, rag_store=None) -> int:
    ans = answer_question(question, stack, use_llm=use_llm, rag_store=rag_store)
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
            corpus = (ans.report.get("meta") or {}).get("corpus")
            if corpus:
                print(f"来源: corpus snapshot={corpus.get('snapshot_id')} "
                      f"as_of={corpus.get('as_of')} kind={corpus.get('kind')}")
                if corpus.get("include_undated_research"):
                    print("日期范围含未知发布日期的研究资料，不证明历史可用性或现行法律效力。")
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
    ap.add_argument("--corpus-db", type=Path, default=None)
    ap.add_argument("--corpus-snapshot", default=None)
    ap.add_argument("--as-of", default=None,
                    help="Corpus issue/effective date cutoff (YYYY-MM-DD), not latest-version selection")
    ap.add_argument("--allow-nontrusted", "--allow-nontrusted-corpus",
                    dest="allow_nontrusted_corpus", action="store_true")
    ap.add_argument("--include-undated-research", action="store_true",
                    help="Include unknown issue dates in research snapshots only; not legal validity")
    args = ap.parse_args(argv)
    corpus_options = (args.corpus_db, args.corpus_snapshot, args.as_of)
    if any(corpus_options) and not all(corpus_options):
        ap.error("--corpus-db, --corpus-snapshot and --as-of must be supplied together")
    if args.allow_nontrusted_corpus and not all(corpus_options):
        ap.error("--allow-nontrusted-corpus requires corpus options")
    if args.include_undated_research and not (all(corpus_options) and args.allow_nontrusted_corpus):
        ap.error("--include-undated-research requires corpus options and --allow-nontrusted")
    rag_store = None
    if all(corpus_options):
        from fondontology.corpus import CorpusError
        from fondontology.qa.rag.store import load_corpus_store
        try:
            rag_store = load_corpus_store(
                args.corpus_db, args.corpus_snapshot, as_of=args.as_of,
                allow_nontrusted=args.allow_nontrusted_corpus,
                include_undated_research=args.include_undated_research)
        except CorpusError as error:
            print(f"Corpus unavailable: {error}")
            return 1
        print(f"Corpus snapshot={args.corpus_snapshot} kind={rag_store.corpus_metadata['kind']} "
              f"as_of={args.as_of} retrieval=bm25-only")
        if args.include_undated_research:
            print("包含未知发布日期的研究资料；不证明历史可用性或现行法律效力。")

    print(f"加载本体数据栈（{args.source.name} + {args.abox.name}）…")
    stack = build_stack(args.source, args.abox)
    use_llm = False if args.no_llm else None

    question = (args.question or "").strip()
    if question:
        return run(stack, question, detail=args.detail, use_llm=use_llm, rag_store=rag_store)
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
            run(stack, q, detail=args.detail, use_llm=use_llm, rag_store=rag_store)
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
