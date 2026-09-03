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

        # ---- 查询证据 ----
        query_eid = self._next()
        report["evidence"].append({
            "id": query_eid, "kind": "query",
            "source": [plan.get("kind", "find"), str(target)],
            "sparql": result.sparql,
            "row_count": result.count,
            "rows": result.entities[:max_query_rows],
            "premises": [], "derived": [],
        })

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

        # ---- Claim 映射 ----
        claims: list[dict] = []
        claims.append({
            "claim_id": "C1", "type": "count",
            "claim": f"共找到 {result.count} 个「{_local(target)}」",
            "evidence": [query_eid],
        })
        listed = [entity_labels[e] for e in focus]
        claims.append({
            "claim_id": "C2", "type": "fact",
            "claim": "结果实体：" + "、".join(listed[:10]) + ("…" if result.count > len(listed) else ""),
            "evidence": [query_eid],
        })
        for i, entity in enumerate(focus[:3]):
            claims.append({
                "claim_id": f"C{3 + i}", "type": "classification",
                "claim": f"实体「{entity_labels[entity]}」属于 {_local(target)}",
                "evidence": entity_evidence.get(entity, [query_eid]),
            })
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
                "claim": f"「{result.subject}」{_relation_zh(result.relation)}「{result.object}」：{result.answer}",
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