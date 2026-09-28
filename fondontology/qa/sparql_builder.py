"""SPARQL Builder：QueryPlan -> GraphQueryIR -> SPARQL。

LLM 永不生成 SPARQL。算子定义见 docs/sparql-operator-development.md。
当前覆盖类型扫描、关系连接、过滤、OPTIONAL、条件树、时间范围、
最新记录子查询、COUNT 及数值聚合、排序和分页。
"""
from __future__ import annotations

from .query_ir import (
    Aggregate,
    BooleanExpr,
    ExistsExpr,
    FilterExpr,
    GraphQueryIR,
    OptionalPattern,
    OrderExpr,
    PathJoin,
    RawPattern,
    Subquery,
    TypeScan,
    iri,
    literal,
    render_condition,
    render_filter,
    render_pattern,
)

_RDFS_LABEL = iri("http://www.w3.org/2000/01/rdf-schema#label")
_AGG_VAR = "?agg"


def _like_iri(value: str) -> bool:
    return "://" in value


def build_select(plan: dict) -> str:
    """把 find QueryPlan 编译为 SELECT SPARQL。"""
    return render_ir(build_ir(plan))


def build_ir(plan: dict) -> GraphQueryIR:
    """QueryPlan -> GraphQueryIR。"""
    if plan.get("aggregations"):
        return _build_aggregate_ir(plan)
    return _build_plain_ir(plan)


def _build_plain_ir(plan: dict) -> GraphQueryIR:
    src = (plan.get("source") or {}).get("entity")
    hops = plan.get("traversals") or []
    result_var = f"?h{len(hops)}" if (src and hops) else "?entity"
    ir = GraphQueryIR(
        mode="count" if plan.get("select") == "count" else "entities",
        select_vars=[result_var],
        distinct=True,
    )

    target = plan.get("target", {}).get("concept")
    # 锚点路径先走固定 IRI，再在终点做类型闭包，避免先扫描整张图。
    type_first = not (src and hops)
    if target and type_first:
        ir.patterns.append(TypeScan(result_var, target))

    prev = f"<{src}>" if src else result_var
    for i, trav in enumerate(hops, start=1):
        var = f"?h{i}"
        ir.patterns.append(PathJoin(
            prev, trav["property"], var, inverse=bool(trav.get("inverse"))))
        prev = var
        if trav.get("to"):
            ir.patterns.append(TypeScan(var, trav["to"]))
        flt = trav.get("filter")
        if flt and flt.get("kind") == "label" and flt.get("value"):
            lbl = f"?lbl{i}"
            ir.patterns.append(RawPattern(f"{var} {_RDFS_LABEL} {lbl} ."))
            ir.filters.append(FilterExpr(
                f"STR({lbl}) = {literal(flt['value'])}"))
        elif flt and flt.get("kind") == "iri" and flt.get("value"):
            ir.filters.append(FilterExpr(f"{var} = {iri(flt['value'])}"))

    if target and not type_first:
        ir.patterns.append(TypeScan(result_var, target))

    _add_filter_ir(ir, plan, result_var)
    _add_condition_ir(ir, plan.get("where"), result_var)
    _add_optional_ir(ir, plan.get("optional") or [], result_var)

    # related + relation_path：关联终点的类型和过滤单独绑定。
    rel_path = plan.get("relation_path") or []
    if rel_path:
        prev = result_var
        for i, hop in enumerate(rel_path, start=1):
            var = f"?a{i}"
            ir.patterns.append(PathJoin(
                prev, hop["property"], var, inverse=bool(hop.get("inverse"))))
            prev = var
        related = (plan.get("related") or {}).get("concept")
        if related:
            ir.patterns.append(TypeScan(prev, related))
        _add_filter_ir(ir, plan, prev, only_related=True)
        _add_date_range_ir(ir, plan, result_var, prev)
        _add_latest_ir(ir, plan, result_var, rel_path, prev)
    else:
        _add_date_range_ir(ir, plan, result_var, result_var)

    # 显式 projection 使用 OPTIONAL，避免缺失属性把实体过滤掉。
    projection_map: dict[str, int] = {}
    for i, prop in enumerate(plan.get("projections") or []):
        projection_map[prop] = i
        ir.optional.append(OptionalPattern((
            RawPattern(f"{result_var} {iri(prop)} ?p{i} ."),)))

    for exc in plan.get("exclusions") or []:
        ir.filters.append(FilterExpr(f"{result_var} != {iri(exc)}"))

    # 排序属性自动绑定，调用方不必同时声明 projections。
    for order in plan.get("ordering") or []:
        by = order.get("by")
        if not by or by == "agg":
            continue
        if by not in projection_map:
            index = len(projection_map)
            projection_map[by] = index
            ir.optional.append(OptionalPattern((
                RawPattern(f"{result_var} {iri(by)} ?p{index} ."),)))
        ir.order_by.append(OrderExpr(
            f"?p{projection_map[by]}",
            "desc" if order.get("direction") == "desc" else "asc"))
    if not ir.order_by:
        ir.order_by.append(OrderExpr(result_var, "asc"))

    pagination = plan.get("pagination") or {}
    ir.limit = int(pagination["limit"]) if pagination.get("limit") else None
    ir.offset = int(pagination.get("offset") or 0)
    return ir


def _build_aggregate_ir(plan: dict) -> GraphQueryIR:
    """聚合 find：target 按 relation_path 分组并生成度量。"""
    agg = (plan.get("aggregations") or [{}])[0]
    func = str(agg.get("func", "count")).upper()
    path = plan.get("relation_path") or []
    agg_target_var = f"?a{len(path)}" if path else "?entity"
    ir = GraphQueryIR(
        mode="aggregate",
        select_vars=["?entity"],
        distinct=False,
    )
    measure_property = agg.get("measure_property")
    measure_var = "?measure"
    if func == "COUNT":
        aggregate_expression = agg_target_var
        distinct = True
    else:
        aggregate_expression = measure_var
        distinct = bool(agg.get("distinct", False))
    ir.aggregates.append(Aggregate(
        func=func, expression=aggregate_expression, alias=_AGG_VAR,
        distinct=distinct))

    target = plan.get("target", {}).get("concept")
    if target:
        ir.patterns.append(TypeScan("?entity", target))

    prev = "?entity"
    for i, hop in enumerate(path, start=1):
        var = f"?a{i}"
        ir.patterns.append(PathJoin(
            prev, hop["property"], var, inverse=bool(hop.get("inverse"))))
        prev = var

    related = (plan.get("related") or {}).get("concept")
    if related and path:
        ir.patterns.append(TypeScan(agg_target_var, related))
    if measure_property and func != "COUNT":
        ir.patterns.append(RawPattern(
            f"{agg_target_var} {iri(measure_property)} {measure_var} ."))

    _add_filter_ir(ir, plan, "?entity")
    if path:
        _add_date_range_ir(ir, plan, "?entity", agg_target_var)
        _add_latest_ir(ir, plan, "?entity", path, agg_target_var)
    else:
        _add_date_range_ir(ir, plan, "?entity", "?entity")
    for exc in plan.get("exclusions") or []:
        ir.filters.append(FilterExpr(f"?entity != {iri(exc)}"))

    ir.group_by.append("?entity")
    having = agg.get("having")
    if having:
        having_expression = (
            f"{func}(DISTINCT {agg_target_var})"
            if func == "COUNT" else f"{func}({measure_var})"
        )
        ir.having.append(FilterExpr(
            f"{having_expression} {having['operator']} "
            f"{literal(having['value'])}"))

    for order in plan.get("ordering") or []:
        if order.get("by") == "agg":
            ir.order_by.append(OrderExpr(
                _AGG_VAR,
                "desc" if order.get("direction") == "desc" else "asc"))
    if not ir.order_by:
        ir.order_by.append(OrderExpr("?entity", "asc"))

    pagination = plan.get("pagination") or {}
    ir.limit = int(pagination["limit"]) if pagination.get("limit") else None
    ir.offset = int(pagination.get("offset") or 0)
    return ir


def _add_filter_ir(ir: GraphQueryIR, plan: dict, result_var: str,
                   only_related: bool = False) -> None:
    """把 plan filters 降为 ValuePattern + FilterExpr。"""
    for i, item in enumerate(plan.get("filters") or []):
        is_related = item.get("on") == "related"
        if only_related != is_related:
            continue
        prop = item["property"]
        value = item.get("value", "")
        suffix = "r" if is_related else ""
        value_var = f"?v{i}{suffix}"

        if isinstance(value, list):
            ir.patterns.append(RawPattern(
                f"{result_var} {iri(prop)} {value_var} ."))
            rendered = [iri(v) if _like_iri(v) else literal(v) for v in value]
            ir.filters.append(FilterExpr(
                f"{value_var} IN ({', '.join(rendered)})"))
            continue
        if _like_iri(value):
            ir.patterns.append(RawPattern(
                f"{result_var} {iri(prop)} {iri(value)} ."))
            continue

        ir.patterns.append(RawPattern(
            f"{result_var} {iri(prop)} {value_var} ."))
        operator = item.get("operator", "eq")
        if operator == "contains":
            ir.filters.append(FilterExpr(
                f"CONTAINS(STR({value_var}), {literal(value)})"))
        elif operator == "eq":
            ir.filters.append(FilterExpr(
                f"{value_var} = {literal(value)}"))
        else:
            ir.filters.append(FilterExpr(
                f"{value_var} {operator} {literal(value)}"))


_XSD_DATE = "http://www.w3.org/2001/XMLSchema#date"
_XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"


def _date_literal(value: object) -> str:
    text = str(value)
    datatype = _XSD_DATETIME if "T" in text else _XSD_DATE
    return literal(text, datatype=datatype)


def _add_date_range_ir(ir: GraphQueryIR, plan: dict, target_var: str,
                       related_var: str) -> None:
    """把 P3 日期范围编译为 typed-literal 比较。"""
    for i, item in enumerate(plan.get("date_ranges") or []):
        subject = related_var if item.get("on") == "related" else target_var
        value_var = f"?date{i}{'r' if item.get('on') == 'related' else ''}"
        ir.patterns.append(RawPattern(
            f"{subject} {iri(item['property'])} {value_var} ."))
        clauses = []
        if item.get("from") is not None:
            clauses.append(f"{value_var} >= {_date_literal(item['from'])}")
        if item.get("to") is not None:
            clauses.append(f"{value_var} <= {_date_literal(item['to'])}")
        if clauses:
            ir.filters.append(FilterExpr(" && ".join(clauses)))


def _latest_subquery(result_var: str, path: list[dict],
                     date_property: str, date_ranges: list[dict]) -> Subquery:
    patterns: list[object] = []
    prev = result_var
    for i, hop in enumerate(path, start=1):
        var = f"?latestR{i}"
        patterns.append(PathJoin(
            prev, hop["property"], var, inverse=bool(hop.get("inverse"))))
        prev = var
    patterns.append(RawPattern(
        f"{prev} {iri(date_property)} ?latestDateValue ."))
    for i, item in enumerate(date_ranges):
        if item.get("on") != "related":
            continue
        range_var = "?latestDateValue" if item["property"] == date_property \
            else f"?latestRange{i}"
        patterns.append(RawPattern(
            f"{prev} {iri(item['property'])} {range_var} ."))
        clauses = []
        if item.get("from") is not None:
            clauses.append(f"{range_var} >= {_date_literal(item['from'])}")
        if item.get("to") is not None:
            clauses.append(f"{range_var} <= {_date_literal(item['to'])}")
        if clauses:
            patterns.append(FilterExpr(" && ".join(clauses)))
    return Subquery(
        select_vars=(result_var,),
        aggregate_func="MAX",
        aggregate_expression="?latestDateValue",
        aggregate_alias="?latestDate",
        patterns=tuple(patterns),
        group_by=(result_var,),
    )


def _add_latest_ir(ir: GraphQueryIR, plan: dict, result_var: str,
                   path: list[dict], related_var: str) -> None:
    latest = plan.get("latest")
    if not latest or latest.get("on") != "related":
        return
    ir.patterns.append(_latest_subquery(
        result_var, path, latest["date_property"],
        plan.get("date_ranges") or []))
    ir.patterns.append(RawPattern(
        f"{related_var} {iri(latest['date_property'])} ?latestDate ."))


def _add_condition_ir(ir: GraphQueryIR, condition: object,
                      result_var: str) -> None:
    """把 P2 where 表达式编译成 EXISTS/NOT EXISTS 组合表达式。

    每个属性条件都放进 EXISTS 子模式，保证 OR 不会被多个外部三元组
    模式错误地编译成 AND。
    """
    if not condition:
        return
    ir.conditions.append(_compile_condition(condition, result_var))


def _compile_condition(node: object, result_var: str,
                       seq: list[int] | None = None) -> object:
    if seq is None:
        seq = [0]
    if not isinstance(node, dict):
        raise ValueError("where 条件必须是对象")
    op = str(node.get("op") or "").lower()

    if op in ("and", "or"):
        args = tuple(_compile_condition(arg, result_var, seq)
                     for arg in node.get("args") or [])
        if not args:
            raise ValueError(f"{op} 条件不能为空")
        return BooleanExpr(op, args)
    if op == "not":
        args = node.get("args")
        if args is None:
            args = [node.get("arg")]
        if len(args) != 1:
            raise ValueError("not 条件必须只有一个参数")
        return BooleanExpr("not", (
            _compile_condition(args[0], result_var, seq),))
    if op in ("exists", "not_exists"):
        patterns = _compile_exists_path(
            node.get("path") or [], result_var,
            target=node.get("target"), seq=seq)
        return ExistsExpr(tuple(patterns), negated=op == "not_exists")
    if op == "filter":
        prop = node.get("property")
        if not prop:
            raise ValueError("filter 条件缺少 property")
        value = node.get("value", "")
        var = f"?c{seq[0]}"
        seq[0] += 1
        pattern = RawPattern(f"{result_var} {iri(prop)} {var} .")
        if isinstance(value, list):
            rendered = [iri(v) if _like_iri(v) else literal(v) for v in value]
            expr = FilterExpr(f"{var} IN ({', '.join(rendered)})")
        elif _like_iri(value):
            pattern = RawPattern(f"{result_var} {iri(prop)} {iri(value)} .")
            expr = FilterExpr("true")
        else:
            operator = node.get("operator", "eq")
            if operator == "contains":
                text = f"CONTAINS(STR({var}), {literal(value)})"
            elif operator == "eq":
                text = f"{var} = {literal(value)}"
            else:
                text = f"{var} {operator} {literal(value)}"
            expr = FilterExpr(text)
        return ExistsExpr((pattern, expr), negated=False)
    raise ValueError(f"不支持的 where 操作符: {op}")


def _compile_exists_path(path: list[dict], start_var: str,
                         target: str | None,
                         seq: list[int]) -> list[object]:
    if not path:
        raise ValueError("exists 条件缺少 path")
    patterns: list[object] = []
    prev = start_var
    for hop in path:
        prop = hop.get("property")
        if not prop:
            raise ValueError("exists path 缺少 property")
        var = f"?e{seq[0]}"
        seq[0] += 1
        patterns.append(PathJoin(
            prev, prop, var, inverse=bool(hop.get("inverse"))))
        prev = var
    if target:
        patterns.append(TypeScan(prev, target))
    return patterns


def _add_optional_ir(ir: GraphQueryIR, optional: list[dict],
                     result_var: str) -> None:
    """把 P2 optional path 编译成 OPTIONAL 图模式。"""
    for item in optional:
        path = item.get("path") or []
        if not path:
            continue
        patterns = _compile_exists_path(path, result_var, item.get("target"),
                                        [len(ir.optional)])
        ir.optional.append(OptionalPattern(tuple(patterns)))


def render_ir(ir: GraphQueryIR) -> str:
    """统一渲染 GraphQueryIR。"""
    if ir.mode == "count":
        count_var = ir.select_vars[0] if ir.select_vars else "?entity"
        select = f"(COUNT(DISTINCT {count_var}) AS ?count)"
    elif ir.mode == "aggregate":
        expressions = [
            f"{a.func}(DISTINCT {a.expression}) AS {a.alias}"
            if a.distinct else f"{a.func}({a.expression}) AS {a.alias}"
            for a in ir.aggregates
        ]
        select = " ".join([
            *ir.select_vars,
            *(f"({expression})" for expression in expressions),
        ])
    else:
        select = " ".join(ir.select_vars)
        if ir.distinct:
            select = f"DISTINCT {select}"

    lines = [f"SELECT {select} WHERE {{"]
    for pattern in ir.patterns:
        lines.extend(render_pattern(pattern))
    for optional in ir.optional:
        lines.append("  OPTIONAL {")
        for pattern in optional.patterns:
            lines.extend(render_pattern(pattern))
        lines.append("  }")
    for expression in ir.filters:
        lines.append(render_filter(expression))
    for condition in ir.conditions:
        lines.extend(render_condition(condition))
    lines.append("}")

    if ir.group_by:
        lines.append("GROUP BY " + " ".join(ir.group_by))
    if ir.having:
        lines.append("HAVING " + " ".join(
            f"({expression.text})" for expression in ir.having))
    if ir.order_by:
        order = []
        for item in ir.order_by:
            order.append(
                f"DESC({item.expression})"
                if item.direction == "desc" else item.expression)
        lines.append("ORDER BY " + " ".join(order))
    if ir.limit is not None:
        lines.append(f"LIMIT {ir.limit}")
    if ir.offset:
        lines.append(f"OFFSET {ir.offset}")
    return "\n".join(lines)
