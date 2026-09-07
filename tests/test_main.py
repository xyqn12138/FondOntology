"""调试观察脚本：打印每一次 LLM 调用的输入/输出（各取前几行）。

直接运行：.venv\\Scripts\\python.exe tests\\test_main.py
原理：包装 qa.intent._stream_chat_content（intent 与 explainer 共用的唯一
LLM 传输入口），不改库代码；HEAD_LINES 控制每侧打印行数。
"""
from fondontology.qa.graph import build_stack
from fondontology.qa.engine import answer_question
from fondontology.qa import intent as intent_mod

HEAD_LINES = 10  # 输入/输出各打印的行数

_orig_chat = intent_mod._stream_chat_content
_call_no = {"n": 0}


def _spy_chat(prompt, temperature=0, max_attempts=2):
    _call_no["n"] += 1
    n = _call_no["n"]
    print(f"\n{'=' * 20} LLM 调用 #{n} · 输入（前 {HEAD_LINES} 行）{'=' * 20}")
    print("\n".join(prompt.splitlines()[:HEAD_LINES]))
    out = _orig_chat(prompt, temperature=temperature, max_attempts=max_attempts)
    print(f"{'=' * 20} LLM 调用 #{n} · 输出（前 {HEAD_LINES} 行）{'=' * 20}")
    print("\n".join((out or "<None：调用失败/超时>").splitlines()[:HEAD_LINES]))
    return out


intent_mod._stream_chat_content = _spy_chat

stack = build_stack("ontology/modules/cnfo-domain.ttl", "artifacts/cnfo/abox/cnfo-sim-abox.ttl")
ans = answer_question("有哪些FOF基金？", stack)
print("\n" + "=" * 60)
print(ans.text)                 # 答案（带 [E#]）
# print(ans.explanation)          # {'gate', 'used_llm', 'ucr', 'claims_used'}
# print(ans.report)               # 证据合同（meta/evidence/claims/subgraph）
