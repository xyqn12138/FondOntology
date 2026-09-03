"""QA 语义验证层：verify 四状态（设计文档 v0.4 §5）。

ENTAILED / CONTRADICTED / UNKNOWN / INVALID_REQUEST
- ENTAILED      —— T-BOX 可证明（正链/声明）
- CONTRADICTED  —— 与 T-BOX 声明冲突（如子类断言却存在互斥声明）
- UNKNOWN       —— 本体不能证明为真（开放世界：不等于证明为假）
- INVALID_REQUEST —— 输入语义错误（不可解析/歧义/关系不在白名单），非逻辑结果

relation 白名单：subClassOf / equivalentClass / disjointWith / subPropertyOf / domainOf / rangeOf
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS, SKOS

from ..tbox import constraints, taxonomy

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")

RELATIONS = frozenset({
    "subClassOf", "equivalentClass", "disjointWith",
    "subPropertyOf", "domainOf", "rangeOf",
})

ENTAILED = "ENTAILED"
CONTRADICTED = "CONTRADICTED"
UNKNOWN = "UNKNOWN"
INVALID_REQUEST = "INVALID_REQUEST"


@dataclass
class VerifyResult:
    answer: str
    subject: str
    relation: str
    object: str
    basis: str = ""                  # taxonomy | constraints
    chain: list[dict] = field(default_factory=list)   # [{s,p,o}] 判链证据
    evidence_ids: list[str] = field(default_factory=list)
    note: Optional[str] = None
    reason: Optional[str] = None     # INVALID_REQUEST 原因


def _node_present(graph: Graph, uri: URIRef) -> bool:
    return (uri, None, None) in graph or (None, None, uri) in graph


def resolve(graph: Graph, text: str) -> tuple[Optional[URIRef], Optional[str]]:
    """把输入解析为本体中的 URIRef。返回 (uri, None) 或 (None, reason)。"""
    text = (text or "").strip()
    if not text:
        return None, "参数为空"
    if "://" in text:
        uri = URIRef(text)
        return (uri, None) if _node_present(graph, uri) else (None, "IRI 不在本体中")
    # 本地名直接解析（CNFO 命名空间）
    uri = URIRef(str(CNFO) + text)
    if _node_present(graph, uri):
        return uri, None
    # label / prefLabel 回退（严格文本匹配）
    matches: set[URIRef] = set()
    for pred in (RDFS.label, SKOS.prefLabel):
        for obj in list(graph.objects(None, pred)):
            if str(obj) != text:
                continue
            for s in graph.subjects(pred, obj):
                if isinstance(s, URIRef):
                    matches.add(s)
    if len(matches) == 1:
        return matches.pop(), None
    if len(matches) > 1:
        return None, "名称存在多个候选，需消歧"
    return None, "无法解析为 CNFO 词汇"


def verify(graph: Graph, subject: str, relation: str, object: str) -> VerifyResult:
    """四状态 verify（M1 冻结契约）。"""
    if not relation or relation not in RELATIONS:
        return VerifyResult(INVALID_REQUEST, subject, relation, object,
                            reason=f"关系不在白名单: {relation!r}")

    sub, sub_reason = resolve(graph, subject)
    if sub is None:
        return VerifyResult(INVALID_REQUEST, subject, relation, object,
                            reason=f"subject {subject!r}: {sub_reason}")
    obj, obj_reason = resolve(graph, object)
    if obj is None:
        return VerifyResult(INVALID_REQUEST, subject, relation, object,
                            reason=f"object {object!r}: {obj_reason}")

    base = VerifyResult("", subject, relation, object)

    # 自反：RDFS 语义下 subClassOf/subPropertyOf/equivalentClass 对自身平凡成立
    if sub == obj and relation in ("subClassOf", "subPropertyOf", "equivalentClass"):
        return _result(base, ENTAILED, "taxonomy", note="自反（同一实体，平凡成立）")

    if relation == "subClassOf":
        path = taxonomy.find_subclass_path(graph, sub, obj)
        if path:
            return _entailed(base, "taxonomy", path)
        if constraints.declared_disjoint(graph, sub, obj):
            return _result(base, CONTRADICTED, "taxonomy",
                           note="目标被声明为互斥，子类断言与之冲突")
        return _result(base, UNKNOWN, "taxonomy")

    if relation == "subPropertyOf":
        path = taxonomy.find_subproperty_path(graph, sub, obj)
        if path:
            return _entailed(base, "taxonomy", path)
        return _result(base, UNKNOWN, "taxonomy")

    if relation == "equivalentClass":
        declared = sub in taxonomy.equivalents(graph, obj) or bool(
            taxonomy.equivalents(graph, sub) & {obj})
        mutual = (taxonomy.find_subclass_path(graph, sub, obj) is not None
                  and taxonomy.find_subclass_path(graph, obj, sub) is not None)
        if declared or mutual:
            return _result(base, ENTAILED, "taxonomy",
                           chain=_chain_of(graph, sub, obj))
        if constraints.declared_disjoint(graph, sub, obj):
            return _result(base, CONTRADICTED, "taxonomy",
                           note="目标被声明为互斥，等价断言与之冲突")
        return _result(base, UNKNOWN, "taxonomy")

    if relation == "disjointWith":
        if constraints.declared_disjoint(graph, sub, obj):
            return _result(base, ENTAILED, "constraints",
                           note="仅证声明存在；若实例出现共指需一致性校验（SHACL）")
        if (taxonomy.find_subclass_path(graph, sub, obj) is not None
                or taxonomy.find_subclass_path(graph, obj, sub) is not None):
            return _result(base, CONTRADICTED, "constraints",
                           note="存在子类链，互斥声明与之冲突")
        return _result(base, UNKNOWN, "constraints")

    if relation == "domainOf":
        if (sub, RDFS.domain, obj) in graph:
            return _result(base, ENTAILED, "constraints")
        return _result(base, UNKNOWN, "constraints")

    if relation == "rangeOf":
        if (sub, RDFS.range, obj) in graph:
            return _result(base, ENTAILED, "constraints")
        return _result(base, UNKNOWN, "constraints")

    return VerifyResult(INVALID_REQUEST, subject, relation, object,
                        reason="未实现的关系分支")  # 防御性


def _entailed(base: VerifyResult, basis: str, path: list) -> VerifyResult:
    return _result(base, ENTAILED, basis, chain=[
        {"s": str(p[0]), "p": str(p[1]), "o": str(p[2])} for p in path
    ])


def _chain_of(graph: Graph, sub: URIRef, obj: URIRef) -> list[dict]:
    """equivalentClass 判链：两条子类链的方向证据（尽量给出）。"""
    a = taxonomy.find_subclass_path(graph, sub, obj)
    b = taxonomy.find_subclass_path(graph, obj, sub)
    chain: list[dict] = []
    for path in (a, b):
        if path:
            chain.append({
                "direction": "forward" if path == a else "reverse",
                "edges": [{"s": str(x[0]), "p": str(x[1]), "o": str(x[2])} for x in path],
            })
    return chain


def _result(base: VerifyResult, answer: str, basis: str, *,
            chain: Optional[list] = None, note: Optional[str] = None,
            evidence_ids: Optional[list[str]] = None) -> VerifyResult:
    base.answer = answer
    base.basis = basis
    if chain:
        base.chain = chain
    base.note = note
    if evidence_ids:
        base.evidence_ids = evidence_ids
    if answer == ENTAILED:
        base.evidence_ids = [f"V{i + 1}" for i in range(max(len(base.chain), 1))]
    return base