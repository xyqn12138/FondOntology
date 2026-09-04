"""Semantic Query IR v1（草案）：Intent + Semantic Specification → QueryPlan。

设计文档 v0.4 §10：Query Plan 是 LLM/SPARQL/后端可替换的架构冻结点（M3 末冻结 schema）。
M2 只实现 find 子集，但字段结构按 v1.0 全字段预留：
target/source/exclusions/type_constraints/filters/traversals/projections/aggregations/
ordering/pagination/inference_policy/evidence_policy。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rdflib import Graph, Namespace, URIRef

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")

PLAN_VERSION = "1.0"


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


def plan_find(*, target: str, tbox: Graph, abox: Optional[Graph] = None,
              source: Optional[str] = None,
              filters: Optional[list[dict]] = None,       # {"property","operator","value"}
              projections: Optional[list[str]] = None,    # 属性 local name / IRI
              exclusions: Optional[list[str]] = None,     # 实体 local name / IRI（ABOX 锚点）
              traversals: Optional[list[dict]] = None,    # {"property","filter"({kind,value}|None)}
              ordering: Optional[list[dict]] = None,
              limit: Optional[int] = None, offset: int = 0) -> dict:
    """构建 find QueryPlan（hand-written intent，M2 无 LLM）。返回 (plan, errors)。

    source：实体锚点（如投资者）——查询从该实体出发沿 traversals 走到目标类型。
    """
    errors: list[str] = []

    target_uri = resolve_iri(tbox, target)
    if target_uri is None:
        errors.append(f"target 无法解析: {target!r}")
    target_uri = target_uri or URIRef(str(CNFO) + target)

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

    plan_filters = []
    for f in filters or []:
        prop_uri = resolve_iri(tbox, f.get("property", ""))
        if prop_uri is None:
            errors.append(f"filter 属性无法解析: {f.get('property')!r}")
            continue
        value = f.get("value", "")
        plan_filters.append({
            "property": str(prop_uri),
            "operator": f.get("operator", "eq"),
            "value": value,
            "lexicon_source": f.get("lexicon_source"),
        })

    plan_traversals = []
    for t in traversals or []:
        prop_uri = resolve_iri(tbox, t.get("property", ""))
        if prop_uri is None:
            errors.append(f"traversal 属性无法解析: {t.get('property')!r}")
            continue
        plan_traversals.append({
            "property": str(prop_uri),
            "inverse": bool(t.get("inverse")),
            "filter": t.get("filter"),
            "from": t.get("from"),
            "to": t.get("to"),
        })

    plan_exclusions = []
    for e in exclusions or []:
        uri = resolve_any(e)
        if uri is None:
            errors.append(f"exclusion 实体无法解析: {e!r}")
            continue
        plan_exclusions.append(str(uri))

    plan_projections = [str(resolve_iri(tbox, p) or p) for p in (projections or [])]

    return {
        "plan_version": PLAN_VERSION,
        "kind": "find",
        "target": {"concept": str(target_uri), "type_constraints": [{"closure": "rdfs:subClassOf*"}]},
        "source": plan_source,
        "exclusions": plan_exclusions,
        "filters": plan_filters,
        "traversals": plan_traversals,
        "projections": plan_projections,
        "aggregations": [],
        "ordering": ordering or [],
        "pagination": {"limit": limit, "offset": offset},
        "inference_policy": {"materialize": False, "path_based": True},
        "evidence_policy": {"include_sources": True, "include_query": True},
        "errors": errors,
    }


def validate_plan(plan: dict) -> list[str]:
    """计划合法性（计划级 INVALID 对应）：target/filter/traversal 白名单已解析。"""
    return list(plan.get("errors") or [])


def write_plan_schema(path: Path) -> None:
    """写出 QueryPlan v1.0 字段骨架（M3 冻结的初稿，供人工评审）。"""
    schema = {
        "plan_version": "1.0",
        "fields": [
            "target", "source", "exclusions", "type_constraints", "filters",
            "traversals", "projections", "aggregations", "ordering",
            "pagination", "inference_policy", "evidence_policy",
        ],
        "kind": ["find", "verify", "aggregate", "compare"],
        "note": "M3 末冻结；除 errors 外的字段不可再增删大改",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(schema, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")