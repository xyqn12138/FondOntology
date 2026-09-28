"""Semantic Query IR v1：SemanticParse → QueryPlan（约束感知）。

设计文档 v0.4 §10：Query Plan 是 LLM/SPARQL/后端可替换的架构冻结点（M3 末冻结 schema）。
重构后 planner 不再是 intent 的"直译器"——它消费 OntologyContext 做本体约束校验：
- 关系约束：traversal/relation_path 每一跳校验 domain/range 闭包（拒绝
  "Fund managedBy Fund" 这类语义非法路径）；
- 属性约束：filter/ordering 属性校验 domain 与 target 类相容；
- 聚合：aggregations 字段从冻结空壳变为真实实现（COUNT + HAVING，
  "同时管理多个基金的基金经理"类查询的载体）。
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from rdflib import Graph, Namespace, URIRef

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")

PLAN_VERSION = "1.1"

_AGG_FUNCS = ("count", "sum", "avg", "max", "min")
_CMP_OPS = (">=", "<=", ">", "<", "=")
_DATE_TYPES = {
    "date",
    "dateTime",
}
_NUMERIC_TYPES = {
    "decimal",
    "integer",
    "double",
    "float",
}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T.*)?$")


def resolve_iri(graph: Graph, term: str) -> Optional[URIRef]:
    """local name 或完整 IRI → 图中的 URIRef（存在性校验）。"""
    term = (term or "").strip()
    if not term:
        return None
    if "://" in term:
        uri = URIRef(term)
        return uri if (uri, None, None) in graph or (None, None, uri) in graph else None
    for ns in (str(CNFO), str(CNFOA)):
        uri = URIRef(ns + term)
        if (uri, None, None) in graph or (None, None, uri) in graph:
            return uri
    return None


def _local(uri: str) -> str:
    s = (uri or "").rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def plan_find(*, target: str, tbox: Graph, abox: Optional[Graph] = None,
              source: Optional[str] = None,
              question: Optional[str] = None,           # 原始问句（路径相关性排序用）
              filters: Optional[list[dict]] = None,       # {"property","operator","value"}
              projections: Optional[list[str]] = None,    # 属性 local name / IRI
              exclusions: Optional[list[str]] = None,     # 实体 local name / IRI（ABOX 锚点）
              traversals: Optional[list[dict]] = None,    # {"property","inverse","filter"}
              related_class: Optional[str] = None,        # 聚合/排名涉及的另一类
              relation_path: Optional[list[dict]] = None, # target→related [{"property","inverse"}]
              aggregation: Optional[dict] = None,         # {"func","operator","value"}
              date_ranges: Optional[list[dict]] = None,  # {"property","from","to","on"}
              latest: Optional[dict] = None,             # {"date_property","on"}
              where: Optional[dict] = None,              # P2 AND/OR/NOT/EXISTS
              optional: Optional[list[dict]] = None,     # P2 OPTIONAL paths
              select: Optional[str] = None,               # entities | count
              ordering: Optional[list[dict]] = None,      # {"by": "agg"|属性IRI, "direction"}
              limit: Optional[int] = None, offset: int = 0,
              ctx=None) -> dict:
    """构建 find QueryPlan（约束感知）。返回 plan（errors 非空即 INVALID）。

    source：实体锚点（如投资者）——查询从该实体出发沿 traversals 走到目标类型。
    ctx：OntologyContext（可选）；提供时启用 domain/range 关系约束校验。
    """
    errors: list[str] = []
    warnings: list[str] = []

    target_uri = resolve_iri(tbox, target)
    if target_uri is None:
        errors.append(f"target 无法解析: {target!r}")
    target_uri = target_uri or URIRef(str(CNFO) + target)
    target_local = _local(str(target_uri))

    def resolve_any(term: str) -> Optional[URIRef]:
        uri = resolve_iri(tbox, term)
        if uri is None and abox is not None:
            uri = resolve_iri(abox, term)
        return uri

    plan_source = None
    if source:
        src_uri = resolve_any(source)
        if src_uri is None:
            errors.append(f"source 实体无法解析: {source!r}")
        else:
            plan_source = {"entity": str(src_uri), "origin": source}

    # ---- filters：属性存在性 + domain 约束 ----
    # 过滤默认落在 target 上；带 "on":"related" 的过滤落在 relation_path 终点类上
    # （如"医药基金"的 investmentFocus 属于 FundInvestmentStrategy）
    related_end_local = _local(related_class) if related_class else None
    plan_filters = []
    for f in filters or []:
        prop_uri = resolve_iri(tbox, f.get("property", ""))
        if prop_uri is None:
            errors.append(f"filter 属性无法解析: {f.get('property')!r}")
            continue
        on_related = f.get("on") == "related" and related_end_local
        check_local = related_end_local if on_related else target_local
        if ctx is not None:
            ok, reason = ctx.check_property_domain(_local(str(prop_uri)), check_local)
            if not ok:
                errors.append(f"filter 属性被关系约束拒绝（{reason}）")
                continue
        operator = f.get("operator", "eq")
        if operator not in ("eq", "contains", ">=", "<=", ">", "<"):
            operator = "eq"
        entry = {
            "property": str(prop_uri),
            "operator": operator,
            "value": f.get("value", ""),
            "lexicon_source": f.get("lexicon_source"),
        }
        if on_related:
            entry["on"] = "related"
        plan_filters.append(entry)

    # ---- traversals：逐跳 domain/range 闭包校验 ----
    # 锚点模式（source 存在）的路径起点是 source 实体的类型，而非 target 类：
    # 如"魏辉的基金"= Manager005377(FundManagerPerson) ^hasFundManager→ Fund，
    # 用 target=Fund 校验 ^hasFundManager 会误报（Fund 不在 FundParty 闭包内）。
    hop_start_local = target_local
    if plan_source and abox is not None and ctx is not None:
        from rdflib.namespace import RDF as _RDF
        src_types = [
            _local(str(t)) for t in abox.objects(URIRef(plan_source["entity"]), _RDF.type)
            if str(t).startswith(str(CNFO))
        ]
        src_types = [t for t in src_types if t in ctx.classes]
        if src_types:
            # 取最具体的类型（祖先闭包最大者）
            hop_start_local = max(src_types, key=lambda t: len(ctx.ancestors_of(t)))
    plan_traversals = []
    hop_errors = _validate_hops(ctx, hop_start_local, traversals or []) if ctx else []
    errors.extend(hop_errors)
    if not hop_errors:
        for t in traversals or []:
            prop_uri = resolve_iri(tbox, t.get("property", ""))
            if prop_uri is None:
                errors.append(f"traversal 属性无法解析: {t.get('property')!r}")
                continue
            to_uri = None
            if t.get("to"):
                to_uri = resolve_iri(tbox, t["to"])
                if to_uri is None:
                    errors.append(f"traversal 终点类无法解析: {t.get('to')!r}")
                    continue
            plan_traversals.append({
                "property": str(prop_uri),
                "inverse": bool(t.get("inverse")),
                "filter": t.get("filter"),
                "from": t.get("from"),
                "to": str(to_uri) if to_uri is not None else None,
            })

    # ---- 锚点无路径时的自动发现 ----
    # 意图层锚定了实体但未给 relation_path（LLM 留空/被拒）时，SPARQL 会
    # 丢掉锚点变成 target 全量（"这个基金是哪家公司的"曾因此列出全部公司）。
    # 从锚点类型到 target 发现全部本体合法路径：
    # - 单一候选 → 直接采用；
    # - 多候选（Fund→Party 有托管/管理等多条边）→ 全部候选路径经
    #   execute_find 逐条试到有结果，避免最短路径语义选错（depositary 边
    #   对"哪家公司管理"是错边）。逐条试为确定性顺序（跳数升序），非猜测。
    plan_auto_paths: list[list[dict]] = []
    if plan_source and not plan_traversals and ctx is not None \
            and hop_start_local != target_local and not errors:
        plan_auto_paths = ctx.find_relation_paths(hop_start_local, target_local)
        if plan_auto_paths:
            # 相关性排序必须喂真实问句：喂 IRI 时 score_path 无语义信号，
            # 退化为跳数排序会选中语义错误的边（"哪家公司"曾选中托管边）
            path = ctx.best_path(plan_auto_paths,
                                 question=question or target_local,
                                 from_local=hop_start_local)
            if path:
                for hop in path:
                    plan_traversals.append({
                        "property": str(hop["property"]),
                        "inverse": bool(hop.get("inverse")),
                        "filter": None, "from": None, "to": None,
                    })

    # ---- 聚合：related + relation_path + aggregation ----
    plan_related = None
    plan_rel_path: list[dict] = []
    plan_aggs: list[dict] = []
    if related_class or relation_path or aggregation:
        rel_uri = resolve_iri(tbox, related_class) if related_class else None
        if related_class and rel_uri is None:
            errors.append(f"related_class 无法解析: {related_class!r}")
        raw_path = relation_path or []
        path_ok = True
        for h in raw_path:
            prop_uri = resolve_iri(tbox, h.get("property", ""))
            if prop_uri is None:
                errors.append(f"relation_path 属性无法解析: {h.get('property')!r}")
                path_ok = False
                continue
            plan_rel_path.append({"property": str(prop_uri),
                                  "inverse": bool(h.get("inverse"))})
        if path_ok and ctx is not None:
            errors.extend(_validate_hops(ctx, target_local, raw_path))
        if rel_uri is not None:
            plan_related = {"concept": str(rel_uri),
                            "type_constraints": [{"closure": "rdfs:subClassOf*"}]}
        if aggregation:
            func = str(aggregation.get("func", "count")).lower()
            if func not in _AGG_FUNCS:
                errors.append(f"聚合函数暂未实现: {func}（当前支持 {sorted(_AGG_FUNCS)}）")
            elif not plan_rel_path:
                errors.append("aggregation 缺少 relation_path 支撑")
            else:
                agg_entry: dict = {"func": func, "over": "related"}
                if func != "count":
                    if not related_end_local:
                        errors.append(
                            f"{func.upper()} 聚合必须明确 related_class")
                    measure_term = (aggregation.get("measure_property")
                                    or aggregation.get("property"))
                    measure_uri = resolve_iri(tbox, str(measure_term or ""))
                    if measure_uri is None:
                        errors.append(
                            f"{func.upper()} 聚合缺少可解析的 measure_property")
                    else:
                        measure_local = _local(str(measure_uri))
                        measure_info = ctx.properties.get(measure_local) if ctx else None
                        if measure_info is not None and measure_info.kind != "datatype":
                            errors.append(
                                f"聚合度量属性不是数据属性: {measure_local}")
                        if ctx is not None:
                            ok, reason = ctx.check_property_domain(
                                measure_local, related_end_local or target_local)
                            if not ok:
                                errors.append(
                                    f"聚合度量属性被关系约束拒绝（{reason}）")
                        if measure_info is not None:
                            ranges = set(measure_info.ranges)
                            if ranges and not (ranges & _NUMERIC_TYPES):
                                errors.append(
                                    f"聚合度量属性必须是数值类型: {measure_local}")
                        agg_entry["measure_property"] = str(measure_uri)
                op, val = aggregation.get("operator"), aggregation.get("value")
                if op is not None or val is not None:
                    if op in _CMP_OPS and isinstance(val, (int, float)):
                        agg_entry["having"] = {"operator": op, "value": val}
                    else:
                        errors.append(f"aggregation 阈值非法: operator={op!r} value={val!r}")
                plan_aggs.append(agg_entry)

    plan_exclusions = []
    for e in exclusions or []:
        uri = resolve_any(e)
        if uri is None:
            errors.append(f"exclusion 实体无法解析: {e!r}")
            continue
        plan_exclusions.append(str(uri))

    plan_projections = [str(resolve_iri(tbox, p) or p) for p in (projections or [])]

    # ---- P3 时间范围 / 最新记录 ----
    plan_date_ranges = _normalize_date_ranges(
        date_ranges or [], tbox=tbox, ctx=ctx, target_local=target_local,
        related_local=related_end_local, errors=errors)
    plan_latest = _normalize_latest(
        latest, tbox=tbox, ctx=ctx, target_local=target_local,
        related_local=related_end_local, relation_path=plan_rel_path,
        errors=errors)

    # ---- P2 条件表达式 / OPTIONAL 路径 ----
    plan_where = _normalize_where(
        where, tbox=tbox, ctx=ctx, start_class=target_local,
        errors=errors) if where else None
    plan_optional = _normalize_optional(
        optional or [], tbox=tbox, ctx=ctx, start_class=target_local,
        errors=errors)

    # ---- ordering：by=agg 需聚合支撑；by=属性IRI 需 domain 相容 ----
    plan_ordering: list[dict] = []
    for o in ordering or []:
        by = o.get("by")
        direction = "desc" if o.get("direction") == "desc" else "asc"
        if by == "agg":
            if not plan_aggs:
                errors.append("ordering by=agg 但没有可用聚合")
                continue
            plan_ordering.append({"by": "agg", "direction": direction})
        elif by:
            prop_uri = resolve_iri(tbox, str(by))
            if prop_uri is None:
                errors.append(f"ordering 属性无法解析: {by!r}")
                continue
            if ctx is not None:
                ok, reason = ctx.check_property_domain(_local(str(prop_uri)), target_local)
                if not ok:
                    errors.append(f"ordering 属性被关系约束拒绝（{reason}）")
                    continue
            plan_ordering.append({"by": str(prop_uri), "direction": direction})

    if select not in (None, "entities", "count"):
        warnings.append(f"select 非法值已忽略: {select!r}")
        select = None

    return {
        "plan_version": PLAN_VERSION,
        "kind": "find",
        "select": select or "entities",
        "target": {"concept": str(target_uri), "type_constraints": [{"closure": "rdfs:subClassOf*"}]},
        "source": plan_source,
        "exclusions": plan_exclusions,
        "filters": plan_filters,
        "where": plan_where,
        "optional": plan_optional,
        "traversals": plan_traversals,
        # 锚点自动发现的候选路径（多候选时 execute 侧逐条试到有结果）
        "auto_traversal_candidates": plan_auto_paths,
        # 空结果恢复上下文（execute 侧现场发现候选用）：
        # question 供相关性排序；anchor_hop_start 是锚点实体最具体类型
        "question": question or "",
        "anchor_hop_start": hop_start_local if plan_source else None,
        "related": plan_related,
        "relation_path": plan_rel_path,
        "projections": plan_projections,
        "aggregations": plan_aggs,
        "date_ranges": plan_date_ranges,
        "latest": plan_latest,
        "ordering": plan_ordering,
        "pagination": {"limit": limit, "offset": offset},
        "inference_policy": {"materialize": False, "path_based": True},
        "evidence_policy": {"include_sources": True, "include_query": True},
        "errors": errors,
        "warnings": warnings,
    }


def _validate_hops(ctx, start_class_local: str,
                   hops: list[dict]) -> list[str]:
    """逐跳 domain/range 闭包校验（关系约束）。

    正向跳：当前类必须落在属性 domain 的祖先闭包内，下一类 = range；
    反向跳：当前类必须落在 range 闭包内，下一类 = domain。
    属性无 domain/range 声明时跳过（开放假设）。
    """
    errors: list[str] = []
    current = start_class_local
    for i, h in enumerate(hops, start=1):
        prop_local = _local(str(h.get("property", "")))
        prop = ctx.properties.get(prop_local)
        if prop is None:
            continue  # 存在性由 resolve_iri 报告
        inverse = bool(h.get("inverse"))
        endpoint = prop.ranges if inverse else prop.domains
        nxt_candidates = prop.domains if inverse else prop.ranges
        class_endpoints = [e for e in endpoint if e in ctx.classes]
        if class_endpoints and not (ctx.ancestors_of(current) & set(class_endpoints)):
            errors.append(
                f"关系约束拒绝：第 {i} 跳 {prop_local}"
                f"{'（反向）' if inverse else ''} 的端点类型是 {class_endpoints}，"
                f"但起点 {current} 不在其子类闭包内")
            break
        nxt = next((c for c in nxt_candidates if c in ctx.classes), None)
        if nxt is None:
            break
        current = nxt
    return errors


def _normalize_where(node: dict, *, tbox: Graph, ctx,
                     start_class: str, errors: list[str]) -> Optional[dict]:
    """校验并归一化 P2 条件树；属性和路径统一转为完整 IRI。"""
    if not isinstance(node, dict):
        errors.append("where 必须是对象")
        return None
    op = str(node.get("op") or "").lower()
    if op in ("and", "or"):
        args = node.get("args")
        if not isinstance(args, list) or not args:
            errors.append(f"where {op} 缺少 args")
            return None
        normalized = [
            _normalize_where(arg, tbox=tbox, ctx=ctx,
                             start_class=start_class, errors=errors)
            for arg in args
        ]
        return {"op": op, "args": [arg for arg in normalized if arg is not None]}
    if op == "not":
        args = node.get("args")
        if args is None and "arg" in node:
            args = [node["arg"]]
        if not isinstance(args, list) or len(args) != 1:
            errors.append("where not 必须包含一个 args")
            return None
        child = _normalize_where(args[0], tbox=tbox, ctx=ctx,
                                 start_class=start_class, errors=errors)
        return {"op": "not", "args": [child]} if child else None
    if op == "filter":
        prop_uri = resolve_iri(tbox, str(node.get("property") or ""))
        if prop_uri is None:
            errors.append(f"where filter 属性无法解析: {node.get('property')!r}")
            return None
        operator = node.get("operator", "eq")
        if operator not in ("eq", "contains", "in", ">=", "<=", ">", "<", "!="):
            errors.append(f"where filter 操作符不支持: {operator!r}")
            return None
        if ctx is not None:
            ok, reason = ctx.check_property_domain(
                _local(str(prop_uri)), start_class)
            if not ok:
                errors.append(f"where filter 属性被关系约束拒绝（{reason}）")
                return None
        return {
            "op": "filter",
            "property": str(prop_uri),
            "operator": operator,
            "value": node.get("value", ""),
        }
    if op in ("exists", "not_exists"):
        raw_path = node.get("path") or []
        if not isinstance(raw_path, list) or not raw_path:
            errors.append(f"where {op} 缺少 path")
            return None
        normalized_path: list[dict] = []
        for hop in raw_path:
            prop_uri = resolve_iri(tbox, str(hop.get("property") or ""))
            if prop_uri is None:
                errors.append(
                    f"where {op} 属性无法解析: {hop.get('property')!r}")
                continue
            normalized_path.append({
                "property": str(prop_uri),
                "inverse": bool(hop.get("inverse")),
            })
        if ctx is not None and normalized_path:
            hop_errors = _validate_hops(ctx, start_class, normalized_path)
            errors.extend(f"where {op}：{error}" for error in hop_errors)
        target = node.get("target")
        target_uri = resolve_iri(tbox, str(target)) if target else None
        if target and target_uri is None:
            errors.append(f"where {op} 目标类无法解析: {target!r}")
        return {
            "op": op,
            "path": normalized_path,
            "target": str(target_uri) if target_uri else None,
        }
    errors.append(f"where 操作符不支持: {op!r}")
    return None


def _normalize_optional(items: list[dict], *, tbox: Graph, ctx,
                        start_class: str, errors: list[str]) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        raw_path = item.get("path") or []
        if not isinstance(raw_path, list) or not raw_path:
            errors.append("optional 缺少 path")
            continue
        path: list[dict] = []
        for hop in raw_path:
            prop_uri = resolve_iri(tbox, str(hop.get("property") or ""))
            if prop_uri is None:
                errors.append(
                    f"optional 属性无法解析: {hop.get('property')!r}")
                continue
            path.append({
                "property": str(prop_uri),
                "inverse": bool(hop.get("inverse")),
            })
        if ctx is not None and path:
            errors.extend(f"optional：{error}"
                         for error in _validate_hops(ctx, start_class, path))
        target = item.get("target")
        target_uri = resolve_iri(tbox, str(target)) if target else None
        if target and target_uri is None:
            errors.append(f"optional 目标类无法解析: {target!r}")
        normalized.append({
            "path": path,
            "target": str(target_uri) if target_uri else None,
        })
    return normalized


def _normalize_date_ranges(items: list[dict], *, tbox: Graph, ctx,
                           target_local: str, related_local: Optional[str],
                           errors: list[str]) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            errors.append("date_ranges 项必须是对象")
            continue
        prop_uri = resolve_iri(tbox, str(item.get("property") or ""))
        if prop_uri is None:
            errors.append(f"日期属性无法解析: {item.get('property')!r}")
            continue
        prop_local = _local(str(prop_uri))
        on = "related" if item.get("on") == "related" else "target"
        subject_class = related_local if on == "related" else target_local
        info = ctx.properties.get(prop_local) if ctx else None
        if info is not None:
            if info.kind != "datatype":
                errors.append(f"日期范围属性不是数据属性: {prop_local}")
                continue
            if set(info.ranges) and not (set(info.ranges) & _DATE_TYPES):
                errors.append(f"日期范围属性类型不是 date/dateTime: {prop_local}")
                continue
        if ctx is not None:
            ok, reason = ctx.check_property_domain(prop_local, subject_class)
            if not ok:
                errors.append(f"日期范围属性被关系约束拒绝（{reason}）")
                continue
        start = item.get("from", item.get("start"))
        end = item.get("to", item.get("end"))
        if start is None and end is None:
            errors.append(f"日期范围缺少 from/to: {prop_local}")
            continue
        valid_dates = True
        for label, value in (("from", start), ("to", end)):
            if value is not None and (
                    not isinstance(value, str) or not _ISO_DATE.match(value)):
                errors.append(f"日期范围 {label} 格式非法: {value!r}")
                valid_dates = False
        if not valid_dates:
            continue
        normalized.append({
            "property": str(prop_uri),
            "on": on,
            "from": start,
            "to": end,
        })
    return normalized


def _normalize_latest(latest: Optional[dict], *, tbox: Graph, ctx,
                      target_local: str, related_local: Optional[str],
                      relation_path: list[dict], errors: list[str]) -> Optional[dict]:
    if latest is None:
        return None
    if not isinstance(latest, dict):
        errors.append("latest 必须是对象")
        return None
    if not relation_path:
        errors.append("latest 缺少 relation_path 支撑")
        return None
    on = "related" if latest.get("on", "related") == "related" else "target"
    if on != "related":
        errors.append("latest 当前仅支持 relation_path 终点（on=related）")
        return None
    subject_class = related_local if on == "related" else target_local
    term = latest.get("date_property") or latest.get("property")
    prop_uri = resolve_iri(tbox, str(term or ""))
    if prop_uri is None:
        errors.append(f"latest 日期属性无法解析: {term!r}")
        return None
    prop_local = _local(str(prop_uri))
    info = ctx.properties.get(prop_local) if ctx else None
    if info is not None:
        if info.kind != "datatype":
            errors.append(f"latest 日期属性不是数据属性: {prop_local}")
            return None
        if set(info.ranges) and not (set(info.ranges) & _DATE_TYPES):
            errors.append(f"latest 日期属性类型不是 date/dateTime: {prop_local}")
            return None
    if ctx is not None:
        ok, reason = ctx.check_property_domain(prop_local, subject_class)
        if not ok:
            errors.append(f"latest 日期属性被关系约束拒绝（{reason}）")
            return None
    return {"date_property": str(prop_uri), "on": on}


def validate_plan(plan: dict) -> list[str]:
    """计划合法性（计划级 INVALID 对应）：target/filter/traversal 白名单已解析。"""
    return list(plan.get("errors") or [])


def write_plan_schema(path: Path) -> None:
    """写出 QueryPlan v1.1 字段骨架（P3 时间/度量算子）。"""
    schema = {
        "plan_version": PLAN_VERSION,
        "fields": [
            "target", "source", "exclusions", "type_constraints", "filters",
            "traversals", "related", "relation_path", "projections",
            "aggregations", "date_ranges", "latest", "where", "optional",
            "ordering", "pagination",
            "inference_policy", "evidence_policy",
        ],
        "kind": ["find", "verify", "aggregate", "compare"],
        "note": "M3 末冻结；除 errors 外的字段不可再增删大改",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(schema, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
