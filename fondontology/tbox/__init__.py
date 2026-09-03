"""CNFO T-BOX 语义组件：taxonomy（分类学）/ constraints（schema 约束）/ inference（推理闭包）。

分工（冻结于设计文档 v0.4 §2）：
- taxonomy   —— subClassOf/subPropertyOf 闭包与判链（不推理、不做 schema 语义）
- constraints—— domain/range/disjoint/restriction 查询（只查声明）
- inference  —— OWL-RL 闭包（"能推出什么"），产物 = closure − explicit
"""
from __future__ import annotations

from . import constraints, inference, taxonomy

__all__ = ["taxonomy", "constraints", "inference"]