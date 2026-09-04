"""QA 数据分层装载：TBOX / TBOX_INFERRED / ABOX（/ ABOX_INFERRED 延后）与快照。

设计文档 v0.4 §3：不再 TBOX ∪ ABOX 一锅烩。
- TBOX          = load_ontology_graph(domain 入口)（显式 schema）
- TBOX_INFERRED = owlrl(TBOX)（schema 闭包，惰性）
- ABOX          = parse(sim-abox.ttl)（显式事实）
- ABOX_INFERRED = owlrl(ABOX ∪ TBOX_INFERRED) —— M2 不物化（find 用显式图 +
  TBOX 子类路径即可；显式/隐式证据通过“声明类型 + 子类链”计算，无需闭包）。
  设计允许“查询计划要求的最小推理”，物化在 M3 证据链阶段按需启用（require_abox_inferred()）。

三元组来源标记由各层方法与证据模块显式区分（declared vs inference）。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

from fondontology.ontology_loader import load_ontology_graph
from fondontology.tbox.inference import compute_closure

CNFO = Namespace("https://ontology.example.cn/cnfo/ontology/")
CNFC = Namespace("https://ontology.example.cn/cnfo/code/")
CNFOA = Namespace("https://ontology.example.cn/cnfo/abox/")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local(uri: URIRef) -> str:
    s = str(uri).rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


@dataclass(frozen=True)
class GraphSnapshot:
    ontology_iri: str
    ontology_version: str
    ontology_hash: str
    abox_file: str
    abox_hash: str
    reasoner_profile: str
    built_at: str


@dataclass
class DataStack:
    """分层数据栈；查询图 = TBOX(显式) + ABOX(显式)（含绑定前缀）。"""
    tbox: Graph
    abox: Graph
    snapshot: GraphSnapshot
    _tbox_inferred: Optional[Graph] = field(default=None, repr=False)
    _abox_inferred: Optional[Graph] = field(default=None, repr=False)
    _combined: Optional[Graph] = field(default=None, repr=False)
    _inference_registry: Optional[dict] = field(default=None, repr=False)
    _inf_counts: Optional[dict] = field(default=None, repr=False)

    # ---- 惰性闭包 ----
    @property
    def tbox_inferred(self) -> Graph:
        if self._tbox_inferred is None:
            self._tbox_inferred = compute_closure(self.tbox)
        return self._tbox_inferred

    def require_abox_inferred(self) -> Graph:
        """ABOX 定向推理物化（打开推理层）：只传播本体的 propertyChainAxiom 与
        逆关系（playsFundRole→rolePlayedBy），并登记每条产物的规则与前提三元组
        （inference_registry），供证据链"由什么推出"归因。

        相比全量 OWL-RL 闭包：无需 O(n³) 传播、产物逐条可解释、查询图增量小。
        每类规则：
        - property_chain:<p1>∘<p2>  → (s, head, o)，前提 (s,p1,x),(x,p2,o)
        - inverse:<p>               → (o, q, s)，前提 (s, p, o)
        """
        if self._abox_inferred is None:
            from rdflib.namespace import OWL
            from ..tbox.inference import property_chain_axioms

            g = Graph()
            g += self.tbox
            g += self.abox
            registry: dict[tuple, dict] = {}
            explicit = set(g)

            # 1) 逆关系传播先行：playsFundRole → rolePlayedBy（经理人进入角色承担者，
            #    供 property chain 物化的前提使用）
            for s, p, o in list(g):
                if not (isinstance(s, URIRef) and isinstance(o, URIRef)):
                    continue
                if p == CNFO.playsFundRole:
                    fact = (o, CNFO.rolePlayedBy, s)
                    if fact not in explicit:
                        g.add(fact)
                        registry[fact] = {"rule": "inverse:playsFundRole",
                                          "premises": [(s, p, o)]}
            # 2) property chain 物化（链长 2 直连；在含逆关系产物的图上扫描）
            for head, parts in property_chain_axioms(self.tbox):
                if len(parts) != 2:
                    continue
                p1, p2 = parts
                for s in g.subjects(p1, None):
                    if not isinstance(s, URIRef):
                        continue
                    for x in g.objects(s, p1):
                        if not isinstance(x, URIRef):
                            continue
                        for o in g.objects(x, p2):
                            if not isinstance(o, URIRef):
                                continue
                            fact = (s, head, o)
                            if fact in explicit:
                                continue
                            g.add(fact)
                            registry[fact] = {
                                "rule": f"property_chain:{_local(p1)}∘{_local(p2)}",
                                "premises": [(s, p1, x), (x, p2, o)],
                            }
            self._abox_inferred = g
            self._inference_registry = registry
            self._inf_counts = {
                rule.split(":")[0] if ":" in rule else rule: 0
                for rule in {v["rule"] for v in registry.values()}
            }
            from collections import Counter
            self._inf_counts = Counter(v["rule"] for v in registry.values())
        return self._abox_inferred

    @property
    def inference_registry(self) -> dict:
        """推理产物 → {rule, premises} 登记（require_abox_inferred 之后可用）。"""
        if self._abox_inferred is None:
            self.require_abox_inferred()
        return self._inference_registry

    @property
    def inference_counts(self):
        if self._abox_inferred is None:
            self.require_abox_inferred()
        return self._inf_counts

    # ---- 查询图 ----
    def query_graph(self, with_abox_inferred: bool = False) -> Graph:
        if with_abox_inferred:
            g = Graph()
            g.bind("cnfo", CNFO)
            g.bind("cnfc", CNFC)
            g.bind("cnfo-a", CNFOA)
            g += self.tbox
            g += self.abox
            g += self.require_abox_inferred()
            return g
        if self._combined is None:
            g = Graph()
            g.bind("cnfo", CNFO)
            g.bind("cnfc", CNFC)
            g.bind("cnfo-a", CNFOA)
            g += self.tbox
            g += self.abox
            self._combined = g
        return self._combined

    # ---- ABOX 显式类型 ----
    def declared_types(self, entity: URIRef) -> set[URIRef]:
        return {o for o in self.abox.objects(entity, RDF.type) if isinstance(o, URIRef)}

    def __len__(self) -> int:
        return len(self.tbox) + len(self.abox)


def build_stack(tbox_source: Path, abox_ttl: Optional[Path] = None,
                reasoner_profile: str = "OWL-RL") -> DataStack:
    tbox_source = Path(tbox_source).expanduser().resolve()
    if not tbox_source.is_file():
        raise FileNotFoundError(f"T-BOX 源不存在: {tbox_source}")
    tbox = load_ontology_graph(tbox_source)
    abox = Graph()
    abox_file = "（无 A-BOX）"
    abox_hash = ""
    if abox_ttl is not None:
        abox_ttl = Path(abox_ttl).expanduser().resolve()
        if not abox_ttl.is_file():
            raise FileNotFoundError(f"A-BOX 不存在: {abox_ttl}")
        abox.parse(str(abox_ttl), format="turtle")
        abox_file = str(abox_ttl)
        abox_hash = file_sha256(abox_ttl)

    version = "unknown"
    for o in tbox.objects(CNFO.CNFODomain, OWL.versionInfo):
        version = str(o)
        break
    snapshot = GraphSnapshot(
        ontology_iri=str(CNFO.CNFODomain),
        ontology_version=version,
        ontology_hash=file_sha256(tbox_source),
        abox_file=abox_file,
        abox_hash=abox_hash,
        reasoner_profile=reasoner_profile,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    return DataStack(tbox=tbox, abox=abox, snapshot=snapshot)