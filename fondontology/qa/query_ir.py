"""GraphQueryIR：QueryPlan 与 SPARQL 文本之间的稳定中间层。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def iri(value: str) -> str:
    """把已通过 planner 校验的 IRI 渲染为 SPARQL IRI。"""
    return f"<{value}>"


def variable(name: str) -> str:
    return name if name.startswith("?") else f"?{name}"


def literal(value: object, datatype: str | None = None) -> str:
    """安全渲染常用 RDF 字面量。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    escaped = (text.replace("\\", "\\\\")
                    .replace("'", "\\'")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r"))
    if datatype:
        return f'"{escaped.replace(chr(34), chr(92) + chr(34))}"^^<{datatype}>'
    return f"'{escaped}'"


@dataclass(frozen=True)
class TypeScan:
    var: str
    class_iri: str


@dataclass(frozen=True)
class PathJoin:
    subject: str
    property_iri: str
    object: str
    inverse: bool = False


@dataclass(frozen=True)
class RawPattern:
    text: str


@dataclass(frozen=True)
class FilterExpr:
    text: str


@dataclass(frozen=True)
class BooleanExpr:
    op: str
    args: tuple[object, ...]


@dataclass(frozen=True)
class ExistsExpr:
    patterns: tuple[object, ...]
    negated: bool = False


@dataclass(frozen=True)
class OptionalPattern:
    patterns: tuple[object, ...]


@dataclass(frozen=True)
class Subquery:
    """嵌入 WHERE 的分组子查询，例如每个实体的 MAX(date)。"""

    select_vars: tuple[str, ...]
    aggregate_func: str
    aggregate_expression: str
    aggregate_alias: str
    patterns: tuple[object, ...]
    group_by: tuple[str, ...]


@dataclass(frozen=True)
class Aggregate:
    func: str
    expression: str
    alias: str
    distinct: bool = True


@dataclass(frozen=True)
class OrderExpr:
    expression: str
    direction: str = "asc"


@dataclass
class GraphQueryIR:
    mode: str = "entities"  # entities | count | aggregate
    select_vars: list[str] = field(default_factory=list)
    patterns: list[object] = field(default_factory=list)
    filters: list[FilterExpr] = field(default_factory=list)
    conditions: list[object] = field(default_factory=list)
    optional: list[OptionalPattern] = field(default_factory=list)
    aggregates: list[Aggregate] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    having: list[FilterExpr] = field(default_factory=list)
    order_by: list[OrderExpr] = field(default_factory=list)
    limit: Optional[int] = None
    offset: int = 0
    distinct: bool = True


def render_pattern(pattern: object) -> list[str]:
    if isinstance(pattern, TypeScan):
        return [
            f"  {variable(pattern.var)} "
            f"<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>/"
            f"<http://www.w3.org/2000/01/rdf-schema#subClassOf>* "
            f"{iri(pattern.class_iri)} ."
        ]
    if isinstance(pattern, PathJoin):
        pred = f"^{iri(pattern.property_iri)}" if pattern.inverse \
            else iri(pattern.property_iri)
        return [f"  {pattern.subject} {pred} {pattern.object} ."]
    if isinstance(pattern, RawPattern):
        return [f"  {pattern.text}"]
    if isinstance(pattern, FilterExpr):
        return [f"  FILTER({pattern.text})"]
    if isinstance(pattern, Subquery):
        select = " ".join(pattern.select_vars)
        select += (
            f" ({pattern.aggregate_func}({pattern.aggregate_expression}) "
            f"AS {pattern.aggregate_alias})"
        )
        lines = ["  {", f"    SELECT {select}", "    WHERE {"]
        for nested in pattern.patterns:
            lines.extend("  " + line for line in render_pattern(nested))
        lines.append("    }")
        if pattern.group_by:
            lines.append("    GROUP BY " + " ".join(pattern.group_by))
        lines.append("  }")
        return lines
    raise TypeError(f"不支持的 GraphQueryIR pattern: {type(pattern).__name__}")


def render_filter(expr: FilterExpr) -> str:
    return f"  FILTER({expr.text})"


def render_expression(expr: object) -> str:
    """把 P2 条件表达式渲染为 FILTER 内表达式。"""
    if isinstance(expr, FilterExpr):
        return expr.text
    if isinstance(expr, ExistsExpr):
        inner = " ".join(
            line.strip() for pattern in expr.patterns
            for line in render_pattern(pattern))
        keyword = "NOT EXISTS" if expr.negated else "EXISTS"
        return f"{keyword} {{ {inner} }}"
    if isinstance(expr, BooleanExpr):
        if expr.op == "not":
            if len(expr.args) != 1:
                raise ValueError("NOT 表达式必须只有一个参数")
            return f"!({render_expression(expr.args[0])})"
        if expr.op not in ("and", "or"):
            raise ValueError(f"不支持的布尔操作符: {expr.op}")
        joiner = " && " if expr.op == "and" else " || "
        return "(" + joiner.join(render_expression(arg)
                                 for arg in expr.args) + ")"
    raise TypeError(f"不支持的 GraphQueryIR expression: {type(expr).__name__}")


def render_condition(condition: object) -> list[str]:
    """渲染顶层条件；存在性表达式使用 FILTER(EXISTS {...})。"""
    if isinstance(condition, ExistsExpr):
        keyword = "NOT EXISTS" if condition.negated else "EXISTS"
        lines = [f"  FILTER({keyword} {{"]
        for pattern in condition.patterns:
            lines.extend(render_pattern(pattern))
        lines.append("  })")
        return lines
    return [f"  FILTER({render_expression(condition)})"]
