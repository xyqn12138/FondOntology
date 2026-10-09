"""最小示例：展示问题驱动的本体上下文压缩结果。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever, estimate_token_count
from fondontology.qa.semantics import OntologyContext


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
DEFAULT_ABOX = ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
DEFAULT_QUESTION = "医药基金有哪些？"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="展示问题驱动的本体上下文压缩结果")
    parser.add_argument("--question", default=DEFAULT_QUESTION,
                        help="待分析的问题")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="T-BOX 入口文件")
    parser.add_argument("--abox", type=Path, default=DEFAULT_ABOX,
                        help="A-BOX 文件")
    parser.add_argument("--max-chars", type=int, default=10000,
                        help="压缩上下文最大字符数")
    args = parser.parse_args()

    stack = build_stack(args.source, args.abox)
    index = OntologyIndex(stack)
    ontology_context = OntologyContext.from_stack(stack)
    full_text = ontology_context.render_for_llm()
    retriever = SchemaRetriever(index, max_chars=args.max_chars)
    compact = retriever.retrieve(args.question)
    full_tokens, full_tokenizer = estimate_token_count(full_text)

    print(f"问题：{args.question}")
    print()
    print("【压缩统计】")
    print(f"完整上下文：{len(full_text)} 字符，约 {full_tokens} token"
          f"（{full_tokenizer}）")
    print(f"压缩上下文：{compact.char_count} 字符，约 {compact.token_count} token"
          f"（{compact.tokenizer}）")
    if full_text:
        print(f"字符缩减：{1 - compact.char_count / len(full_text):.1%}")
    if full_tokens:
        print(f"token 缩减：{1 - compact.token_count / full_tokens:.1%}")
    print(f"保留类：{', '.join(compact.classes) or '无'}")
    print(f"保留属性：{', '.join(compact.properties) or '无'}")
    print(f"保留路径：{len(compact.paths)} 条")
    print()
    print("【送入 LLM 的压缩上下文】")
    print(compact.render_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
