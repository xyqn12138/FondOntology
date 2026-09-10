"""ABOX 实例查询与局部子图（M2）。

- execute_find：QueryPlan + DataStack → FindResult（含 explicit/inferred 类型证据、
  执行的 SPARQL 与行数——证据链由 M3 formalize，此处先产出原始证据对象）。
- local_subgraph：焦点实体 hop 邻域子图（nodes/edges），供后续 LLM 上下文（M3）与
  页面渲染使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from .graph import DataStack
from .query_planner import validate_plan
from .sparql_builder import build_select


@dataclass
class FindResult:
    plan: dict
    sparql: str
    count: int
    entities: list[str] = field(default_factory=list)
    measures: dict = field(default_factory=dict)  # 聚合值：entity IRI -> float（COUNT 等）
    evidence: dict = field(default_factory=dict)   # entity IRI -> {"kind","via","chain"}
    errors: list[str] = field(default_factory=list)


def _local_name(uri: str) -> str:
    s = uri.rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def execute_find(stack: DataStack, plan: dict,
                 with_abox_inferred: bool = True) -> FindResult:
    """实例检索；默认在推理层启用的查询图上执行（定向物化：property chain +
    逆关系传播，产物可经 stack.inference_registry 归因）。

    聚合计划（plan["aggregations"] 非空）时结果行为 (entity, agg_value)，
    agg_value 进入 measures（如"在管基金数"），并供证据链按实体引用。
    """
    errors = validate_plan(plan)
    if errors:
        return FindResult(plan, "", 0, errors=errors)

    graph = stack.query_graph(with_abox_inferred=with_abox_inferred)
    sparql = build_select(plan)
    rows = list(graph.query(sparql))

    # 锚点空结果恢复：查询空结果且存在锚点时，穷尽锚点类型→target 的
    # 全部合法替代路径逐条试到有结果（查询层不变量：锚定查询不因单边
    # 选错而宣告空）。候选来源两路：
    # ① plan 预生成（planner 安全网，LLM 未填路径时）；
    # ② 现场发现（LLM 填了语义错误的边——"哪家公司"曾选中托管边返回 0，
    #    预生成条件 not plan_traversals 不满足导致无候选可试）。
    if not rows and not plan.get("aggregations") and plan.get("source"):
        candidates = list(plan.get("auto_traversal_candidates") or [])
        anchor_start = plan.get("anchor_hop_start")
        target_concept = (plan.get("target") or {}).get("concept")
        if anchor_start and target_concept and not candidates:
            try:
                from .semantics import OntologyContext
                from .graph import DataStack
                if isinstance(stack, DataStack):
                    ctx = OntologyContext.from_stack(stack)
                    from rdflib.namespace import RDF as _RDF
                    from rdflib import URIRef as _URIRef
                    CNFO_NS = "https://ontology.example.cn/cnfo/ontology/"
                    types = [_local_name(str(t)) for t in
                             stack.abox.objects(_URIRef(plan["source"]["entity"]), _RDF.type)
                             if str(t).startswith(CNFO_NS)]
                    types = [t for t in types if t in ctx.classes]
                    if types:
                        start = max(types, key=lambda t: len(ctx.ancestors_of(t)))
                        candidates = ctx.find_relation_paths(start, _local_name(target_concept))
            except Exception:
                candidates = []
        tried = {tuple((t.get("property"), t.get("inverse")) for t in plan.get("traversals") or [])}
        for path in candidates:
            cand_traversals = [{
                "property": str(hop["property"]),
                "inverse": bool(hop.get("inverse")),
                "filter": None, "from": None, "to": None,
            } for hop in path]
            key = tuple((t["property"], t["inverse"]) for t in cand_traversals)
            if not cand_traversals or key in tried:
                continue
            tried.add(key)
            cand_plan = dict(plan)
            cand_plan["traversals"] = cand_traversals
            cand_sparql = build_select(cand_plan)
            cand_rows = list(graph.query(cand_sparql))
            if cand_rows:
                rows = cand_rows
                # 采用的候选路径回写 plan（证据链 SPARQL 与实际执行一致）
                plan["traversals"] = cand_traversals
                sparql = cand_sparql
                break

    is_agg = bool(plan.get("aggregations"))
    measures: dict[str, float] = {}
    if is_agg:
        for row in rows:
            entity = str(row[0])
            try:
                measures[entity] = float(row[1])
            except (TypeError, ValueError, IndexError):
                measures[entity] = 0.0
        # 排序与 SPARQL ORDER BY 保持一致：有 agg 排序时按值降/升，否则按 IRI
        order_desc = any(o.get("by") == "agg" and o.get("direction") == "desc"
                         for o in plan.get("ordering") or [])
        order_asc = any(o.get("by") == "agg" and o.get("direction") != "desc"
                        for o in plan.get("ordering") or [])
        if order_desc:
            entities = sorted(measures, key=lambda e: (-measures[e], e))
        elif order_asc:
            entities = sorted(measures, key=lambda e: (measures[e], e))
        else:
            entities = sorted(measures)
    else:
        entities = sorted({str(row[0]) for row in rows})

    target = plan.get("target", {}).get("concept", "")
    result = FindResult(plan=plan, sparql=sparql, count=len(entities),
                        entities=entities, measures=measures)
    for entity in entities:
        result.evidence[entity] = type_evidence(stack, URIRef(entity), URIRef(target))
    return result


def type_evidence(stack: DataStack, entity: URIRef, target: URIRef) -> dict:
    """实体属于 target 的显式/隐式证据。

    - declared：ABOX 中直接声明 rdf:type == target（或声明类型即 target 本身）
    - inference：经 TBOX 子类链到达（声明类型 X，X rdfs:subClassOf+ target）
    - chain：给出第一条可达链（边列表），供 M3 证据 ID 化
    """
    declared = stack.declared_types(entity)
    if target in declared:
        return {"kind": "declared", "via": str(target), "chain": []}
    for cls in sorted(declared, key=str):
        path = _chain_to(stack.tbox, cls, target)
        if path is not None:
            return {"kind": "inference", "via": str(cls),
                    "chain": [{"s": str(a), "p": str(b), "o": str(c)} for a, b, c in path]}
    return {"kind": "unknown_route", "via": "", "chain": []}


def _chain_to(graph: Graph, start: URIRef, end: URIRef) -> Optional[list]:
    """BFS 求 start → end 的 rdfs:subClassOf 链；不存在返回 None。"""
    if start == end:
        return []
    prev: dict[URIRef, tuple[URIRef, URIRef]] = {}
    seen = {start}
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for nxt in graph.objects(cur, RDFS.subClassOf):
            if not isinstance(nxt, URIRef) or nxt in seen:
                continue
            prev[nxt] = (cur, RDFS.subClassOf)
            if nxt == end:
                chain = []
                node = end
                while node in prev:
                    parent, pred = prev[node]
                    chain.append((parent, pred, node))
                    node = parent
                chain.reverse()
                return chain
            seen.add(nxt)
            queue.append(nxt)
    return None


def local_subgraph(graph: Graph, focus: list[URIRef], hop: int = 1,
                   include_literals: bool = True) -> dict:
    """焦点实体 hop 邻域的 nodes/edges（RDF 视图，供局部上下文/渲染）。

    与 Explorer 图 JSON 不同：此处保留完整 IRI 与 rdf:type 语义。
    nodes: {iri, label, types[]}；edges: {s,p,o}（URI-URI）；literal 边并入
    nodes[].properties（含中文 label 优先）。
    """
    focus_set = set(focus)
    boundary = set(focus_set)
    for _ in range(hop):
        boundary |= {
            o for s in boundary for o in graph.objects(URIRef(s) if isinstance(s, str) else s, None)
            if isinstance(o, URIRef)
        }
        # 入边（保证 hop=1 语义完整）
        for node in list(boundary):
            n = URIRef(node) if isinstance(node, str) else node
            boundary |= {s for s in graph.subjects(None, n) if isinstance(s, URIRef)}

    nodes: dict[str, dict] = {}
    for uri in sorted(str(u) for u in boundary):
        u = URIRef(uri)
        types = sorted({str(t) for t in graph.objects(u, RDF.type)})
        label = ""
        for o in graph.objects(u, RDFS.label):
            if getattr(o, "language", None) == "zh":
                label = str(o)
                break
        else:
            for o in graph.objects(u, RDFS.label):
                label = str(o)
                break
        node = {"iri": uri, "label": label or _local_name(uri), "types": types,
                "properties": {}}
        if include_literals and uri in {str(f) for f in focus_set}:
            for p, o in graph.predicate_objects(u):
                if isinstance(o, Literal):
                    node["properties"][_local_name(str(p))] = str(o)
        nodes[uri] = node

    edges = []
    for s in boundary:
        su = URIRef(s) if isinstance(s, str) else s
        for p, o in graph.predicate_objects(su):
            if p == RDF.type or not isinstance(o, URIRef):
                continue
            if str(o) in nodes:
                edges.append({"s": str(su), "p": str(p), "o": str(o)})
    return {"nodes": nodes, "edges": edges}