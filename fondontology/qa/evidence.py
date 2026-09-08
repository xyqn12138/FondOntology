"""Evidence Builder：证据 + Claim-Evidence Map + provenance chain + 引用校验。

设计文档 v0.4 §7（v3 合同）：
- Evidence ID 由后端生成（LLM 不能自造）；kind ∈ declared|inference|query|definition
- 推理证据带 `rule` / `premises`（由什么推出）/ `derived`（推出什么），证据成图：
  Claim → Evidence → Derived Evidence → Premises → Ontology Rule
- Claim 定义：可被事实验证的陈述（非表达性语言成分）；type ∈
  fact|count|comparison|classification|inference|definition
- citation validation：引用集合必须 ⊆ evidence 集合，否则拒绝。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from .abox_query import FindResult, local_subgraph
from .graph import DataStack

_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def _local(uri: str) -> str:
    s = uri.rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _anchor_layers(graph: Graph, src: URIRef, hops: list[dict],
                   cap: int = 500, tbox: Optional[Graph] = None) -> list[set]:
    """锚点遍历的逐跳到达层：layers[0]={src}，layers[i]=第 i 跳到达的实体集。

    hop 带 "to"（终点类 IRI）时按类型闭包过滤（与 SPARQL 的跳终点约束一致）。
    """
    to_closures: dict[int, set] = {}
    if tbox is not None:
        from rdflib.namespace import RDFS as _RDFS
        for i, h in enumerate(hops):
            if not h.get("to"):
                continue
            to_uri = URIRef(h["to"])
            closure = {to_uri}
            frontier = [to_uri]
            while frontier:
                cur = frontier.pop()
                for s in tbox.subjects(_RDFS.subClassOf, cur):
                    if isinstance(s, URIRef) and s not in closure:
                        closure.add(s)
                        frontier.append(s)
            to_closures[i] = closure
    layers: list[set] = [{src}]
    for i, h in enumerate(hops):
        prop = URIRef(h["property"])
        nxt: set = set()
        for x in layers[-1]:
            if h.get("inverse"):
                nxt |= {s for s in graph.subjects(prop, x) if isinstance(s, URIRef)}
            else:
                nxt |= {o for o in graph.objects(x, prop) if isinstance(o, URIRef)}
            if len(nxt) >= cap:
                break
        if i in to_closures:
            closure = to_closures[i]
            nxt = {n for n in nxt
                   if any((n, RDF.type, t) in graph for t in closure)}
        layers.append(set(list(nxt)[:cap]))
    return layers


def _witness_path(graph: Graph, layers: list[set], hops: list[dict],
                  entity: URIRef) -> list[tuple]:
    """从结果实体沿各跳层回走一条到 source 的见证路径（事实列表，src→entity 序）。"""
    facts: list[tuple] = []
    cur = entity
    for i in range(len(hops) - 1, -1, -1):
        prop = URIRef(hops[i]["property"])
        inverse = bool(hops[i].get("inverse"))
        found = None
        for x in layers[i]:
            candidate = (cur, prop, x) if inverse else (x, prop, cur)
            if candidate in graph:
                found = candidate
                break
        if found is None:
            return []
        facts.append(found)
        cur = found[2] if inverse else found[0]
    facts.reverse()
    return facts


def zh_label(graph: Graph, uri: URIRef, default: str = "") -> str:
    for pred in (SKOS.prefLabel, RDFS.label):
        for o in graph.objects(uri, pred):
            if getattr(o, "language", None) == "zh":
                return str(o)
    for o in graph.objects(uri, RDFS.label):
        return str(o)
    return default or _local(str(uri))


class EvidenceBuilder:
    """为一次 find/verify 回答构建证据链与 Claim 映射。"""

    def __init__(self, stack: DataStack):
        self.stack = stack
        self._seq = 0

    def _disp(self, value) -> str:
        """实体/类引用的用户可读名：IRI → T-BOX 中文 label，其余原样。"""
        s = str(value or "")
        if s.startswith("http"):
            return zh_label(self.stack.tbox, URIRef(s), _local(s))
        return s

    def _next(self) -> str:
        self._seq += 1
        return f"E{self._seq}"

    def build_for_find(self, plan: dict, result: FindResult, *,
                       max_subgraph_entities: int = 8,
                       max_query_rows: int = 20) -> dict:
        report: dict = {
            "meta": {
                "ontology": {"iri": self.stack.snapshot.ontology_iri,
                             "version": self.stack.snapshot.ontology_version,
                             "hash": self.stack.snapshot.ontology_hash},
                "abox": {"file": self.stack.snapshot.abox_file,
                         "hash": self.stack.snapshot.abox_hash},
                "reasoning": {"profile": self.stack.snapshot.reasoner_profile,
                              "inference_enabled": False,
                              "query_graph": "TBOX + ABOX（显式；类型证据用声明+子类链）"},
            },
            "plan": plan,
            "evidence": [],
            "claims": [],
            "subgraph": {},
            "unresolved": list(result.errors),
        }
        if result.errors:
            return report

        target = plan.get("target", {}).get("concept", "")
        graph = self.stack.query_graph()
        # 面向用户的 claim 文本一律用中文 label（如「基金经理」），
        # 不得出现本体内部名/IRI（如 FundManagerPerson）
        target_label = (zh_label(graph, URIRef(target), _local(target))
                        if target else target)

        # ---- 查询证据 ----
        aggs = plan.get("aggregations") or []
        query_eid = self._next()
        query_ev = {
            "id": query_eid, "kind": "query",
            "source": [plan.get("kind", "find"), str(target)],
            "sparql": result.sparql,
            "row_count": result.count,
            "rows": result.entities[:max_query_rows],
            "premises": [], "derived": [],
        }
        if result.measures:
            query_ev["measures"] = {e: result.measures[e]
                                    for e in result.entities[:max_query_rows]
                                    if e in result.measures}
        report["evidence"].append(query_ev)

        # ---- 实体证据（declared / inference + provenance chain）----
        entity_evidence: dict[str, list[str]] = {}
        entity_labels: dict[str, str] = {}
        focus = result.entities[:max_subgraph_entities]
        for entity in focus:
            uri = URIRef(entity)
            entity_labels[entity] = zh_label(graph, uri, _local(entity))
            tev = result.evidence.get(entity, {})
            ids: list[str] = []
            if tev.get("kind") == "declared":
                eid = self._next()
                report["evidence"].append({
                    "id": eid, "kind": "declared",
                    "source": [entity, _RDF_TYPE, tev.get("via", "")],
                    "premises": [], "derived": [],
                })
                ids.append(eid)
            elif tev.get("kind") == "inference":
                declared_eid = self._next()
                report["evidence"].append({
                    "id": declared_eid, "kind": "declared",
                    "source": [entity, _RDF_TYPE, tev.get("via", "")],
                    "premises": [], "derived": [],
                })
                inf_eid = self._next()
                report["evidence"].append({
                    "id": inf_eid, "kind": "inference",
                    "rule": "rdfs:subClassOf",
                    "source": tev.get("chain", []),      # [{"s","p","o"}, ...]
                    "premises": [declared_eid],
                    "derived": [],
                })
                # 证据图：声明类型证据 → 子类链证据 推导出“属于 target”
                report["evidence"][-1]["derived"].append(inf_eid)
                ids.extend([declared_eid, inf_eid])
            elif tev.get("kind") == "unknown_route":
                eid = self._next()
                report["evidence"].append({
                    "id": eid, "kind": "query",
                    "source": [entity], "premises": [], "derived": [],
                    "note": "类型归属路径未闭合",
                })
                ids.append(eid)
            entity_evidence[entity] = ids

        # ---- 推理层归因（锚点链：逐跳见证路径上的物化边登记规则与前提）----
        # 如 hasFundManager 由 propertyChain 物化；多跳链（基金→经理→其他基金）
        # 沿见证路径逐跳归因，显式边也给 declared 证据，保证链上每跳可溯源。
        infer_evidence: dict[str, list[str]] = {}
        witness_facts: dict[str, list[tuple]] = {}
        pivot_claims: list[dict] = []
        src_entity = (plan.get("source") or {}).get("entity")
        hops = [h for h in (plan.get("traversals") or []) if h.get("property")]
        if src_entity and hops:
            inf_graph = self.stack.require_abox_inferred()
            registry = self.stack.inference_registry
            layers = _anchor_layers(inf_graph, URIRef(src_entity), hops,
                                    tbox=self.stack.tbox)
            fact_eids: dict[tuple, list[str]] = {}

            def emit_fact(fact: tuple) -> list[str]:
                """物化边 → inference 证据（含前提）；显式边 → declared 证据。按 fact 去重。"""
                if fact in fact_eids:
                    return fact_eids[fact]
                eids: list[str] = []
                reg = registry.get(fact)
                if reg is not None:
                    premise_eids = []
                    for pr in reg["premises"]:
                        e_prem = self._next()
                        report["evidence"].append({
                            "id": e_prem, "kind": "declared",
                            "source": [str(pr[0]), str(pr[1]), str(pr[2])],
                            "premises": [], "derived": [],
                        })
                        premise_eids.append(e_prem)
                    e_inf = self._next()
                    report["evidence"].append({
                        "id": e_inf, "kind": "inference",
                        "rule": reg["rule"],
                        "source": [str(fact[0]), str(fact[1]), str(fact[2])],
                        "premises": premise_eids,
                        "derived": [],
                    })
                    eids = premise_eids + [e_inf]
                else:
                    e_dec = self._next()
                    report["evidence"].append({
                        "id": e_dec, "kind": "declared",
                        "source": [str(fact[0]), str(fact[1]), str(fact[2])],
                        "premises": [], "derived": [],
                    })
                    eids = [e_dec]
                fact_eids[fact] = eids
                return eids

            for entity in focus:
                witness = _witness_path(inf_graph, layers, hops, URIRef(entity))
                eids: list[str] = []
                for fact in witness:
                    eids.extend(emit_fact(fact))
                if eids:
                    infer_evidence[entity] = eids
                    witness_facts[entity] = witness

            # 多跳锚点链的 pivot（第一跳到达的实体，如"基金的基金经理"）：
            # 结果实体是链终点，pivot 不在结果集中——必须显式给 claim，
            # 否则表达层拿不到"基金经理是谁"这一半问题的答案
            if len(hops) >= 2 and len(layers) > 1 and layers[1]:
                hop1 = hops[0]
                prop_label = zh_label(self.stack.tbox, URIRef(hop1["property"]),
                                      _local(hop1["property"]))
                src_label = zh_label(graph, URIRef(src_entity), _local(src_entity))
                for pivot in sorted(layers[1], key=str)[:3]:
                    pivot_label = zh_label(graph, pivot, _local(str(pivot)))
                    if not hop1.get("inverse"):
                        fact = (URIRef(src_entity), URIRef(hop1["property"]), pivot)
                        text = f"「{src_label}」{prop_label}「{pivot_label}」"
                    else:
                        fact = (pivot, URIRef(hop1["property"]), URIRef(src_entity))
                        text = f"「{pivot_label}」{prop_label}「{src_label}」"
                    pivot_claims.append({"type": "fact", "claim": text,
                                         "evidence": emit_fact(fact)})

        # ---- Claim 映射 ----
        # 聚合语义描述（"关联「基金」数量 >= 2"），让 count claim 携带约束而非裸计数
        agg_desc = ""
        aggs = plan.get("aggregations") or []
        if aggs:
            related_uri = (plan.get("related") or {}).get("concept", "")
            related_label = (zh_label(graph, URIRef(related_uri), _local(related_uri))
                             if related_uri else "")
            having = aggs[0].get("having")
            if having:
                agg_desc = (f"（关联「{related_label}」数量 "
                            f"{having['operator']} {having['value']}）")
            else:
                agg_desc = f"（按关联「{related_label}」数量聚合）"
        claims: list[dict] = []
        claims.append({
            "claim_id": "C1", "type": "count",
            "claim": f"共找到 {result.count} 个「{target_label}」{agg_desc}",
            "evidence": [query_eid],
        })
        if result.measures:
            listed = [f"{entity_labels[e]}（{result.measures[e]:g}）"
                      for e in focus if e in result.measures]
        else:
            listed = [entity_labels[e] for e in focus]
        claims.append({
            "claim_id": "C2", "type": "fact",
            "claim": "结果实体：" + "、".join(listed[:10]) + ("…" if result.count > len(listed) else ""),
            "evidence": [query_eid],
        })
        seq = 3
        for pc in pivot_claims:
            claims.append({"claim_id": f"C{seq}", **pc})
            seq += 1
        for i, entity in enumerate(focus[:3]):
            witness = witness_facts.get(entity)
            if witness:
                # 锚点查询：结果实体与锚点链末端的关系（末跳事实）即答案语义——
                # 「结果基金」具有基金管理人「陶凯」，而非"属于 Fund"式同义反复
                s, p, o = witness[-1]
                s_label = zh_label(graph, s, _local(str(s)))
                o_label = zh_label(graph, o, _local(str(o)))
                p_label = zh_label(self.stack.tbox, p, _local(str(p)))
                claims.append({
                    "claim_id": f"C{seq}", "type": "fact",
                    "claim": f"「{s_label}」{p_label}「{o_label}」",
                    "evidence": infer_evidence.get(entity, [query_eid]),
                })
            else:
                claims.append({
                    "claim_id": f"C{seq}", "type": "classification",
                    "claim": f"「{entity_labels[entity]}」属于「{target_label}」",
                    "evidence": entity_evidence.get(entity, [query_eid]),
                })
            seq += 1
        report["claims"] = claims

        # ---- 局部子图（带上限，防撑爆上下文）----
        sub = local_subgraph(graph, [URIRef(e) for e in focus], hop=1)
        report["subgraph"] = sub
        report["_inner"] = {"entity_labels": entity_labels}
        return report

    def build_for_verify(self, operation: str, result) -> dict:
        """verify 回答的证据合同（链条证据 + 单 Claim；UNKNOWN 也带开放世界查询证据）。"""
        chain = result.chain or []
        evidence = []
        for i, edge in enumerate(chain):
            evidence.append({
                "id": f"E{i + 1}", "kind": "declared",
                "source": [edge.get("s"), edge.get("p", ""), edge.get("o")],
                "premises": [],
                "derived": [f"E{i + 2}"] if i + 1 < len(chain) else [],
            })
        claims = []
        if result.answer in ("ENTAILED", "CONTRADICTED", "UNKNOWN"):
            if evidence:
                pass  # 判链证据即足够
            else:
                # 开放世界查询证据：ASK 未发现可证明路径（result=false），
                # 保证 UNKNOWN 也有据可查，而不是"无证据的断言"
                evidence.append({
                    "id": "E1", "kind": "query",
                    "sparql": _open_world_ask(self.stack.tbox, result),
                    "result": "false",
                    "note": f"开放世界：未在 T-BOX 中发现 {result.relation} 可证明路径/声明",
                    "premises": [], "derived": [],
                })
            claims.append({
                "claim_id": "C1", "type": "classification",
                "claim": f"「{self._disp(result.subject)}」"
                         f"{_relation_zh(result.relation)}"
                         f"「{self._disp(result.object)}」：{result.answer}",
                "evidence": [e["id"] for e in evidence],
            })
        report = {
            "meta": {
                "ontology": {"iri": self.stack.snapshot.ontology_iri,
                             "version": self.stack.snapshot.ontology_version,
                             "hash": self.stack.snapshot.ontology_hash},
                "reasoning": {"profile": self.stack.snapshot.reasoner_profile,
                              "inference_enabled": False,
                              "query_graph": "TBOX（verify 不访问 A-BOX）"},
            },
            "operation": operation,
            "verify": {"answer": result.answer, "basis": result.basis,
                       "note": result.note, "reason": result.reason},
            "evidence": evidence,
            "claims": claims,
            "unresolved": [result.reason] if result.reason else [],
        }
        return report


def _relation_zh(relation: str) -> str:
    return {
        "subClassOf": "是…的子类",
        "equivalentClass": "与…等价",
        "disjointWith": "与…互斥",
        "subPropertyOf": "是…的子属性",
        "domainOf": "是…的 domain",
        "rangeOf": "是…的 range",
    }.get(relation, relation)


def _open_world_ask(graph: Graph, result) -> str:
    """生成 UNKNOWN 判定的 ASK 查询字符串（resolve 原始输入 → IRI）。"""
    from .verify import resolve
    sub, _ = resolve(graph, result.subject)
    obj, _ = resolve(graph, result.object)
    if sub is None or obj is None:
        return f"ASK {{ }}  -- 不可解析: {result.subject!r} / {result.object!r}"
    s, o = sub.n3(), obj.n3()
    return {
        "subClassOf": f"ASK {{ {s} rdfs:subClassOf+ {o} }}",
        "subPropertyOf": f"ASK {{ {s} rdfs:subPropertyOf+ {o} }}",
        "equivalentClass": f"ASK {{ {{ {s} owl:equivalentClass {o} }} UNION {{ {o} owl:equivalentClass {s} }} }}",
        "disjointWith": f"ASK {{ {s} owl:disjointWith {o} }}",
        "domainOf": f"ASK {{ {s} rdfs:domain {o} }}",
        "rangeOf": f"ASK {{ {s} rdfs:range {o} }}",
    }.get(result.relation, f"ASK {{ }}  -- 未知关系 {result.relation}")


# ---------------------------------------------------------------------------
# 合同校验（M3 硬闸门）
# ---------------------------------------------------------------------------
def evidence_ids(report: dict) -> set[str]:
    return {e["id"] for e in report.get("evidence", [])}


def claims(report: dict) -> list[dict]:
    return list(report.get("claims", []))


def validate_citations(report: dict, cited: Optional[Iterable[str]] = None) -> list[str]:
    """校验引用：返回未在证据集合中的 id 列表（空 = 通过）。"""
    known = evidence_ids(report)
    used = set(cited or [])
    for c in claims(report):
        used.update(c.get("evidence", []))
    return sorted(u for u in used if u not in known)


def evidence_completeness(report: dict) -> tuple[bool, list[str]]:
    """每条 claim 都有非空证据且 evidence id 全部存在。返回 (ok, 问题列表)。"""
    known = evidence_ids(report)
    problems: list[str] = []
    for c in claims(report):
        cid = c.get("claim_id")
        ev = c.get("evidence") or []
        if not ev:
            problems.append(f"{cid}: 缺证据")
        else:
            for eid in ev:
                if eid not in known:
                    problems.append(f"{cid}: 引用未知证据 {eid}")
    return (not problems), problems