"""SPARQL Builder：QueryPlan → SPARQL（纯函数，LLM 永不生成 SPARQL）。

设计文档 v0.4 §10：每个算子（type closure / filter / traversal / projection /
aggregation / ordering / pagination）独立可单测。输出用完整 IRI（尖括号形式），
不依赖前缀绑定。

聚合算子（aggregations + relation_path + related）：
  "同时管理多个基金的基金经理" →
  SELECT ?entity (COUNT(DISTINCT ?a1) AS ?agg) WHERE {
    ?entity rdf:type/rdfs:subClassOf* <FundManagerPerson> .
    ?entity ^<hasFundManager> ?a1 .
    ?a1 rdf:type/rdfs:subClassOf* <Fund> .
  } GROUP BY ?entity HAVING (COUNT(DISTINCT ?a1) >= 2) ORDER BY DESC(?agg)
"""
from __future__ import annotations

_RDF_TYPE = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
_RDFS_SUBCLASS = "<http://www.w3.org/2000/01/rdf-schema#subClassOf>"
_RDFS_LABEL = "<http://www.w3.org/2000/01/rdf-schema#label>"

_AGG_VAR = "?agg"


def _iri(uri: str) -> str:
    return f"<{uri}>"


def _like_iri(value: str) -> bool:
    return "://" in value


def _type_pattern(var: str, class_iri: str) -> str:
    return f"  {var} {_RDF_TYPE}/{_RDFS_SUBCLASS}* {_iri(class_iri)} ."


def build_select(plan: dict) -> str:
    """find 计划 → SELECT。聚合计划走 GROUP BY/HAVING 形态。"""
    if plan.get("aggregations"):
        return _build_aggregate(plan)
    return _build_plain(plan)


def _build_plain(plan: dict) -> str:
    """普通 find：SELECT DISTINCT <结果变量> WHERE { … }。"""
    src = (plan.get("source") or {}).get("entity")
    hops = plan.get("traversals") or []
    result_var = f"?h{len(hops)}" if (src and hops) else "?entity"

    lines = [f"SELECT DISTINCT {result_var} WHERE {{"]

    target = plan.get("target", {}).get("concept")
    # 模式顺序即 rdflib 求值顺序（无代价重排）：锚点模式下固定 IRI 出发的
    # 跳链选择性极高，必须先放——若类型闭包 pattern 在先，rdflib 会先枚举
    # 全图 (entity, type) 再做闭包（28 万三元组下约 16s）；跳链在先则类型
    # 校验只落在链终点候选上（亚秒级）。非锚点模式保持类型 pattern 在先。
    type_first = not (src and hops)
    if target and type_first:
        # rdf:type/rdfs:subClassOf* —— 类型闭包（M2 用显式图即可，无需物化闭包）
        lines.append(_type_pattern(result_var, target))

    # traversals：逐跳链；锚点模式根为固定 IRI，普通模式根为结果变量
    prev = f"<{src}>" if src else result_var
    for i, trav in enumerate(hops, start=1):
        var = f"?h{i}"
        prop = _iri(trav['property'])
        if trav.get("inverse"):
            lines.append(f"  {prev} ^{prop} {var} .")
        else:
            lines.append(f"  {prev} {prop} {var} .")
        prev = var
        if trav.get("to"):
            # 跳终点类约束（如复合锚点链把 pivot 收窄到 FundManagerPerson，
            # 避免 hasFundManager 的 FundParty range 混入管理公司）
            lines.append(_type_pattern(var, trav["to"]))
        flt = trav.get("filter")
        if flt and flt.get("kind") == "label" and flt.get("value"):
            # 标签带语言标记（@zh），需 STR() 比较
            lbl = f"?lbl{i}"
            lines.append(f"  {var} {_RDFS_LABEL} {lbl} .")
            lines.append(f"  FILTER(STR({lbl}) = {flt['value']!r})")
        elif flt and flt.get("kind") == "iri" and flt.get("value"):
            lines.append(f"  {var} {_iri(flt['value'])} .")

    if target and not type_first:
        lines.append(_type_pattern(result_var, target))

    lines.extend(_filter_lines(plan, result_var))

    # related + relation_path（无聚合时）：target 与 related 的关联存在性约束，
    # "on":"related" 的过滤落在路径终点（如医药主题过滤落在 FundInvestmentStrategy）
    rel_path = plan.get("relation_path") or []
    related_var = None
    if rel_path:
        prev = result_var
        for i, hop in enumerate(rel_path, start=1):
            var = f"?a{i}"
            prop = _iri(hop["property"])
            if hop.get("inverse"):
                lines.append(f"  {prev} ^{prop} {var} .")
            else:
                lines.append(f"  {prev} {prop} {var} .")
            prev = var
        related_var = prev
        related = (plan.get("related") or {}).get("concept")
        if related:
            lines.append(_type_pattern(related_var, related))
        lines.extend(_filter_lines(plan, related_var, only_related=True))

    # projections（可选绑定；SELECT 仍以结果变量为主键）
    for i, prop in enumerate(plan.get("projections") or []):
        lines.append(f"  OPTIONAL {{ {result_var} {_iri(prop)} ?p{i} }}")

    # exclusions：实体显式排除（"其他/除外/不包括"）
    for exc in plan.get("exclusions") or []:
        lines.append(f"  FILTER({result_var} != {_iri(exc)})")

    lines.append("}")

    # ordering：by=属性IRI 需其在 projections 中（绑定 ?p{i}）；默认结果变量稳定排序
    order_by = []
    for o in plan.get("ordering") or []:
        by = o.get("by")
        pidx = None
        for i, p in enumerate(plan.get("projections") or []):
            if p == by:
                pidx = i
                break
        if pidx is not None:
            order_by.append(f"?p{pidx}" + (" DESC" if o.get("direction") == "desc" else ""))
    if not order_by:
        order_by.append(result_var)
    lines.append("ORDER BY " + " ".join(order_by))

    pag = plan.get("pagination") or {}
    if pag.get("limit"):
        lines.append(f"LIMIT {int(pag['limit'])}")
    if pag.get("offset"):
        lines.append(f"OFFSET {int(pag['offset'])}")

    return "\n".join(lines)


def _build_aggregate(plan: dict) -> str:
    """聚合 find：target 按 relation_path 分组计数，HAVING 阈值 + 排序。

    SELECT ?entity (COUNT(DISTINCT ?aN) AS ?agg) … GROUP BY ?entity HAVING …
    聚合变量 = relation_path 终点（related 类实例）；COUNT(DISTINCT) 去重。
    """
    agg = (plan.get("aggregations") or [{}])[0]
    func = agg.get("func", "count").upper()
    path = plan.get("relation_path") or []
    n = len(path)
    agg_target_var = f"?a{n}" if n else "?entity"

    lines = [f"SELECT ?entity ({func}(DISTINCT {agg_target_var}) AS {_AGG_VAR}) WHERE {{"]

    target = plan.get("target", {}).get("concept")
    if target:
        lines.append(_type_pattern("?entity", target))

    # relation_path：target → related（inverse 跳用 ^ 属性）
    prev = "?entity"
    for i, hop in enumerate(path, start=1):
        var = f"?a{i}"
        prop = _iri(hop["property"])
        if hop.get("inverse"):
            lines.append(f"  {prev} ^{prop} {var} .")
        else:
            lines.append(f"  {prev} {prop} {var} .")
        prev = var

    # related 类约束（如聚合计数对象必须是 Fund 而非其它 FundParty 关联物）
    related = (plan.get("related") or {}).get("concept")
    if related and n:
        lines.append(_type_pattern(agg_target_var, related))

    lines.extend(_filter_lines(plan, "?entity"))

    for exc in plan.get("exclusions") or []:
        lines.append(f"  FILTER(?entity != {_iri(exc)})")

    lines.append("}")
    lines.append("GROUP BY ?entity")

    having = agg.get("having")
    if having:
        lines.append(
            f"HAVING ({func}(DISTINCT {agg_target_var}) {having['operator']} {having['value']})")

    order_by = []
    for o in plan.get("ordering") or []:
        if o.get("by") == "agg":
            order_by.append(f"DESC({_AGG_VAR})" if o.get("direction") == "desc"
                            else f"ASC({_AGG_VAR})")
    if not order_by:
        order_by.append("?entity")
    lines.append("ORDER BY " + " ".join(order_by))

    pag = plan.get("pagination") or {}
    if pag.get("limit"):
        lines.append(f"LIMIT {int(pag['limit'])}")
    if pag.get("offset"):
        lines.append(f"OFFSET {int(pag['offset'])}")

    return "\n".join(lines)


def _filter_lines(plan: dict, result_var: str,
                  only_related: bool = False) -> list[str]:
    """filters：对象属性值给 IRI 则做三元组模式，否则做字面量 FILTER；in 支持列表。

    only_related=True 时只渲染 "on":"related" 的过滤（绑定到关系路径终点变量），
    其余过滤由主变量调用点渲染；contains 算子 → FILTER(CONTAINS(STR(?v), …))。
    """
    lines: list[str] = []
    for i, f in enumerate(plan.get("filters") or []):
        is_related = f.get("on") == "related"
        if only_related != is_related:
            continue
        prop, value = f["property"], f.get("value", "")
        if isinstance(value, list):
            var = f"?v{i}r" if is_related else f"?v{i}"
            lines.append(f"  {result_var} {_iri(prop)} {var} .")
            rendered = [(_iri(v) if _like_iri(v) else repr(v)) for v in value]
            lines.append(f"  FILTER({var} IN ({', '.join(rendered)}))")
            continue
        if _like_iri(value):
            lines.append(f"  {result_var} {_iri(prop)} {_iri(value)} .")
            continue
        var = f"?v{i}r" if is_related else f"?v{i}"
        lines.append(f"  {result_var} {_iri(prop)} {var} .")
        op = f.get("operator", "eq")
        if op == "contains":
            lines.append(f"  FILTER(CONTAINS(STR({var}), {value!r}))")
        elif op == "eq":
            lines.append(f"  FILTER({var} = {value!r})")
        else:
            lines.append(f"  FILTER({var} {op} {value!r})")
    return lines
