"""Ontology Index：词汇/实体只读索引（设计文档 v0.4 §1 —— Index 只建索引，不回答）。

索引内容：CNFO 类/对象属性/数据属性、CNFC 代码概念、ABOX 实体（个体），
各带 IRI / label / prefLabel / altLabel / 代码 / 命名空间 / 类型。
检索由 resolver 承担；判定由 validator 承担；本模块无任何语义逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .graph import DataStack

CNFO = "https://ontology.example.cn/cnfo/ontology/"
CNFC = "https://ontology.example.cn/cnfo/code/"
CNFOA = "https://ontology.example.cn/cnfo/abox/"

_ENTITY_CODE_PROPS = (CNFO + "fundCode", CNFO + "fundUnitCode", CNFO + "accountNumber")
_NORMALIZE_SUFFIXES = ("证券投资基金", "交易型开放式指数证券投资基金",
                       "证券投资基金（QDII）", "基金中基金（FOF）", "货币市场基金")


@dataclass(frozen=True)
class Candidate:
    iri: str
    kind: str                  # class | property | code | entity
    label: str
    match_type: str            # iri | local_name | label | pref_label | alt_label | code | contains | normalized
    score: float
    extra: dict = field(default_factory=dict)   # 如 {"collision": bool, "scheme": str, "code": str}


def _local(uri: str) -> str:
    s = uri.rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _zh(graph: Graph, uri, pred) -> str:
    for o in graph.objects(uri, pred):
        if getattr(o, "language", None) == "zh":
            return str(o)
    return ""


class OntologyIndex:
    def __init__(self, stack: DataStack):
        self.stack = stack
        g = stack.query_graph()
        self._g = g

        # ---- 概念（TBOX 词汇）----
        self.classes: dict[str, str] = {}          # iri -> label（zh 优先）
        self.object_properties: dict[str, str] = {}
        self.datatype_properties: dict[str, str] = {}
        self.codes: dict[str, dict] = {}           # iri -> {label, scheme}
        for s in g.subjects(RDF.type, None):
            if not isinstance(s, URIRef):
                continue
            label = _zh(g, s, SKOS.prefLabel) or _zh(g, s, RDFS.label) or _local(str(s))
            if str(s).startswith(CNFO):
                types = set(g.objects(s, RDF.type))
                if OWL.Class in types:
                    self.classes[str(s)] = label
                elif OWL.ObjectProperty in types:
                    self.object_properties[str(s)] = label
                elif OWL.DatatypeProperty in types:
                    self.datatype_properties[str(s)] = label
            elif str(s).startswith(CNFC):
                scheme = ""
                for sc in g.objects(s, SKOS.inScheme):
                    scheme = _local(str(sc))
                    break
                self.codes[str(s)] = {"label": label, "scheme": scheme}

        # 概念别名/标签索引（label/prefLabel/altLabel 精确）
        self._concept_labels: dict[str, list[str]] = {}
        for iri in list(self.classes) + list(self.object_properties) + list(self.datatype_properties):
            u = URIRef(iri)
            for pred in (SKOS.prefLabel, SKOS.altLabel, RDFS.label):
                for o in g.objects(u, pred):
                    if isinstance(o, Literal):
                        self._concept_labels.setdefault(str(o), []).append(iri)

        # ---- 实体（ABOX 个体）----
        self.entities: dict[str, dict] = {}        # iri -> {label, codes[], types[]}
        self._entity_codes: dict[str, list[str]] = {}
        abox = stack.abox
        for s in abox.subjects(RDF.type, None):
            if not isinstance(s, URIRef) or not str(s).startswith(CNFOA):
                continue
            label = _zh(abox, s, RDFS.label) or _local(str(s))
            codes: list[str] = []
            for p in _ENTITY_CODE_PROPS:
                for o in abox.objects(s, URIRef(p)):
                    if isinstance(o, Literal):
                        codes.append(str(o))
            types = sorted({str(t) for t in abox.objects(s, RDF.type) if isinstance(t, URIRef)})
            self.entities[str(s)] = {"label": label, "codes": codes, "types": types}
            for c in codes:
                self._entity_codes.setdefault(c, []).append(str(s))

        # 实体名称归一化索引（受控后缀剥离；家族名不合并，碰撞即记录）
        self._entity_norm: dict[str, list[str]] = {}
        for iri, meta in self.entities.items():
            norm = _normalize_name(meta["label"])
            self._entity_norm.setdefault(norm, []).append(iri)

    # ---- 白名单集合（validator 用）----
    @property
    def class_iris(self) -> frozenset[str]:
        return frozenset(self.classes)

    @property
    def property_iris(self) -> frozenset[str]:
        return frozenset(self.object_properties) | frozenset(self.datatype_properties)

    @property
    def code_iris(self) -> frozenset[str]:
        return frozenset(self.codes)

    @property
    def entity_iris(self) -> frozenset[str]:
        return frozenset(self.entities)

    def graph(self) -> Graph:
        return self._g


def _normalize_name(label: str) -> str:
    """受控名称归一化：只做后缀剥离与空白压缩，不做截断/合并。"""
    s = label.strip()
    changed = True
    while changed:
        changed = False
        for suffix in _NORMALIZE_SUFFIXES:
            if s.endswith(suffix):
                s = s[: -len(suffix)].strip()
                changed = True
    return " ".join(s.split())