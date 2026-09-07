"""QA 语义查询引擎：Ontology 三阶段生命周期的问数侧实现。

包结构（按三阶段组织）：
- Stage 1 Semantic Modeling：ontology/*.ttl（本包之外）+ tbox/ 组件
- Stage 2 Semantic Enforcement：enforce（数据导入语义控制层）
- Stage 3 Semantic Querying：semantics（本体语义视图）→ intent（语义解析）
  → query_planner（约束感知规划）→ sparql_builder → abox_query
  → evidence/explainer/templates（证据与表达）
- 支撑：graph（分层数据栈 + 定向物化推理）、index/resolver/validator/lexicon
  （词汇四件套）、verify（T-BOX 四状态判链）、context（本体切片）

模块按需惰性导入（PEP 562）：避免 import 包即拉起全部 15+ 模块的启动耦合。
"""
from __future__ import annotations

import importlib

__all__ = [
    "verify", "graph", "semantics", "query_planner", "sparql_builder",
    "abox_query", "evidence", "context", "templates", "engine",
    "index", "resolver", "validator", "lexicon", "intent", "explainer",
    "enforce",
]


def __getattr__(name: str):
    if name in __all__:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
