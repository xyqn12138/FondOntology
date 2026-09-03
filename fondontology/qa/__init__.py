"""QA 语义查询引擎：确定性语义链（M1 起逐阶段实现）。

本包职责划分见 docs（artifacts/cnfo-qa-system-design.md v0.4）：
- verify  —— 四状态语义验证（M1）
- graph   —— TBOX/ABOX/闭包分层装载 + GraphSnapshot（M2）
- query_planner —— Semantic Query IR v1（手写 Intent，M2）
- sparql_builder —— QueryPlan → SPARQL 纯函数（M2）
- abox_query —— 实例查询 + explicit/inferred 证据 + 局部子图（M2）
- evidence/context/templates/engine —— 证据链与确定性端到端（M3）
- index/resolver/validator/lexicon/intent —— 词汇四件套 + NL 意图解构（M4）
"""
from __future__ import annotations

from . import (
    abox_query, context, engine, evidence, explainer, graph, index, intent,
    lexicon, query_planner, resolver, sparql_builder, templates, validator,
    verify,
)

__all__ = [
    "verify", "graph", "query_planner", "sparql_builder", "abox_query",
    "evidence", "context", "templates", "engine",
    "index", "resolver", "validator", "lexicon", "intent", "explainer",
]