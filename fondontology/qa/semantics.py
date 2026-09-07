"""Ontology Context：本体语义视图（Query-time world model）。

三阶段生命周期之"Semantic Querying"的基础设施：
- 从 T-BOX 提取类层级（含中文标签/定义）、属性 domain/range、类间关系图；
- render_for_llm() 把语义视图渲染成 LLM 可读的紧凑文本，注入意图解析 prompt——
  LLM 由此"看到"基金经理与基金之间的管理边，而不是只看到一张类名表；
- find_relation_path() 在关系图上做闭包感知的 BFS，为 planner 提供
  "target 类 → related 类"的合法属性路径（含反向边与推理物化快捷边）；
- check_property_domain() 供 planner 做关系/属性的 domain-range 约束校验。

本模块只读 T-BOX，不做实例查询；构建结果按 DataStack 弱引用缓存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from weakref import WeakKeyDictionary

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from ..tbox.taxonomy import ancestors, descendants
from .graph import DataStack

CNFO_NS = "https://ontology.example.cn/cnfo/ontology/"

_CONTEXT_CACHE: "WeakKeyDictionary[DataStack, OntologyContext]" = WeakKeyDictionary()


def _local(uri) -> str:
    s = str(uri).rstrip("/#")
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _zh(graph: Graph, uri: URIRef, pred) -> str:
    for o in graph.objects(uri, pred):
        if getattr(o, "language", None) == "zh":
            return str(o)
    return ""


def _label(graph: Graph, uri: URIRef) -> str:
    return (_zh(graph, uri, SKOS.prefLabel) or _zh(graph, uri, RDFS.label)
            or _local(str(uri)))


@dataclass
class ClassInfo:
    iri: str
    local: str
    label: str
    definition: str = ""
    parents: list[str] = field(default_factory=list)   # 直接父类 local
    children: list[str] = field(default_factory=list)  # 直接子类 local


@dataclass
class PropertyInfo:
    iri: str
    local: str
    label: str
    kind: str                              # object | datatype
    domains: list[str] = field(default_factory=list)  # 类 local（仅 CNFO 类）
    ranges: list[str] = field(default_factory=list)   # 类 local / xsd 类型


@dataclass(frozen=True)
class RelationEdge:
    """类间关系边：domain --property--> range（inverse=True 表示反向使用）。"""
    property_iri: str
    property_local: str
    property_label: str
    domain_local: str
    range_local: str


class OntologyContext:
    """T-BOX 语义视图：类层级 + 属性约束 + 类间关系图。"""

    def __init__(self, stack: DataStack):
        self.stack = stack
        g = stack.tbox
        self._g = g

        # ---- 类 ----
        self.classes: dict[str, ClassInfo] = {}
        for s in g.subjects(RDF.type, OWL.Class):
            if not isinstance(s, URIRef) or not str(s).startswith(CNFO_NS):
                continue
            local = _local(str(s))
            parents = sorted(
                _local(str(o)) for o in g.objects(s, RDFS.subClassOf)
                if isinstance(o, URIRef) and str(o).startswith(CNFO_NS)
                and (o, RDF.type, OWL.Class) in g
            )
            self.classes[local] = ClassInfo(
                iri=str(s), local=local, label=_label(g, s),
                definition=_zh(g, s, SKOS.definition), parents=parents,
            )
        for info in self.classes.values():
            for p in info.parents:
                if p in self.classes:
                    self.classes[p].children.append(info.local)

        # ---- 属性 ----
        self.properties: dict[str, PropertyInfo] = {}
        for owl_type, kind in ((OWL.ObjectProperty, "object"),
                               (OWL.DatatypeProperty, "datatype")):
            for s in g.subjects(RDF.type, owl_type):
                if not isinstance(s, URIRef) or not str(s).startswith(CNFO_NS):
                    continue
                local = _local(str(s))
                domains = sorted(
                    _local(str(d)) for d in g.objects(s, RDFS.domain)
                    if isinstance(d, URIRef) and str(d).startswith(CNFO_NS)
                    and _local(str(d)) in self.classes
                )
                ranges = sorted(
                    _local(str(r)) for r in g.objects(s, RDFS.range)
                    if isinstance(r, URIRef)
                )
                self.properties[local] = PropertyInfo(
                    iri=str(s), local=local, label=_label(g, s), kind=kind,
                    domains=domains, ranges=ranges,
                )

        # ---- 类间关系边（对象属性且 domain/range 均为 CNFO 类）----
        self.relations: list[RelationEdge] = []
        for prop in self.properties.values():
            if prop.kind != "object":
                continue
            for d in prop.domains:
                for r in prop.ranges:
                    if r in self.classes:
                        self.relations.append(RelationEdge(
                            property_iri=prop.iri, property_local=prop.local,
                            property_label=prop.label, domain_local=d, range_local=r,
                        ))

        # 类 local -> 祖先 local 闭包（含自身），供闭包感知匹配
        self._ancestor_cache: dict[str, set[str]] = {}

    # ---------------------------------------------------------------- 构造
    @classmethod
    def from_stack(cls, stack: DataStack) -> "OntologyContext":
        ctx = _CONTEXT_CACHE.get(stack)
        if ctx is None:
            ctx = cls(stack)
            _CONTEXT_CACHE[stack] = ctx
        return ctx

    # ---------------------------------------------------------------- 查询
    def ancestors_of(self, class_local: str) -> set[str]:
        """类的祖先 local 闭包（含自身）；未知类返回 {自身}。"""
        cached = self._ancestor_cache.get(class_local)
        if cached is not None:
            return cached
        info = self.classes.get(class_local)
        if info is None:
            return {class_local}
        iri = URIRef(info.iri)
        result = {class_local} | {
            _local(str(a)) for a in ancestors(self._g, iri)
            if _local(str(a)) in self.classes
        }
        self._ancestor_cache[class_local] = result
        return result

    def descendants_of(self, class_local: str) -> set[str]:
        info = self.classes.get(class_local)
        if info is None:
            return {class_local}
        iri = URIRef(info.iri)
        return {class_local} | {
            _local(str(d)) for d in descendants(self._g, iri)
            if _local(str(d)) in self.classes
        }

    def is_subclass(self, sub_local: str, sup_local: str) -> bool:
        return sup_local in self.ancestors_of(sub_local)

    def edges_from(self, class_local: str) -> list[tuple[RelationEdge, bool, str]]:
        """从类出发可用的关系边（闭包感知）。

        返回 (edge, inverse, 到达类 local)：
        - 正向：class_local ⊂ edge.domain → 沿属性到 range（及其子类）；
        - 反向：class_local ⊂ edge.range  → 沿 ^属性到 domain（及其子类）。
        """
        closure = self.ancestors_of(class_local)
        out: list[tuple[RelationEdge, bool, str]] = []
        for e in self.relations:
            if e.domain_local in closure:
                out.append((e, False, e.range_local))
            if e.range_local in closure:
                out.append((e, True, e.domain_local))
        return out

    def find_relation_paths(self, from_local: str, to_local: str,
                            max_hops: int = 3, limit: int = 12) -> list[list[dict]]:
        """BFS 求 from 类 → to 类的关系路径（闭包感知，含反向边）。

        返回 ≤ max_hops 的全部路径（去重，按跳数升序），每条路径为
        [{"property": iri, "inverse": bool, "via": to_class_local,
          "property_local": str, "property_label": str}, ...]；不存在返回 []。
        终点类只需是 to_local 的祖先（含自身）。
        同一对端点常有多条边（如 Fund→FundParty 有 hasFundManager /
        hasFundDepositary），选路须结合问题文本用 score_path / best_path。
        """
        if self.is_subclass(from_local, to_local) or self.is_subclass(to_local, from_local):
            return [[]]  # 同类/继承关系：无需遍历（调用方应直接用类型约束）
        found: list[list[dict]] = []
        seen_paths: set[tuple] = set()
        frontier: list[tuple[str, list[dict]]] = [(from_local, [])]
        visited_depth: dict[str, int] = {from_local: 0}
        pops = 0
        while frontier and len(found) < limit and pops < 2000:
            cur, path = frontier.pop(0)
            pops += 1
            if len(path) >= max_hops:
                continue
            for edge, inverse, nxt in self.edges_from(cur):
                hop = {"property": edge.property_iri, "inverse": inverse,
                       "via": nxt, "property_local": edge.property_local,
                       "property_label": edge.property_label}
                new_path = path + [hop]
                if self.is_subclass(to_local, nxt) or nxt == to_local:
                    key = tuple((h["property"], h["inverse"]) for h in new_path)
                    if key not in seen_paths:
                        seen_paths.add(key)
                        found.append(new_path)
                    continue
                # 同点以更短/同长路径到达过才继续扩展（防环防爆）
                if visited_depth.get(nxt, max_hops + 1) < len(new_path):
                    continue
                visited_depth[nxt] = len(new_path)
                frontier.append((nxt, new_path))
        found.sort(key=lambda p: (len(p), [h["property_local"] for h in p]))
        return found[:limit]

    def find_relation_path(self, from_local: str, to_local: str,
                           max_hops: int = 3,
                           question: str = "") -> Optional[list[dict]]:
        """求 from → to 的最佳关系路径：问题相关性优先，跳数少次之。"""
        return self.best_path(
            self.find_relation_paths(from_local, to_local, max_hops=max_hops),
            question=question, from_local=from_local)

    def best_path(self, paths: list[list[dict]], question: str = "",
                  from_local: str = "") -> Optional[list[dict]]:
        """在候选路径中选最佳：相关性 × 2 − 跳数 降序。"""
        if not paths:
            return None
        if len(paths) == 1:
            return paths[0]
        scored = [(self.score_path(p, question, from_local) * 2 - len(p), i, p)
                  for i, p in enumerate(paths)]
        scored.sort(key=lambda t: (-t[0], t[1]))
        return scored[0][2]

    # 问题-属性匹配时无区分度的通用片段（几乎每条基金属性都含"基金"）
    _GENERIC_GRAMS = frozenset({"基金", "拥有", "具有", "关联", "相关", "记录"})

    @classmethod
    def score_path(cls, path: list[dict], question: str, from_local: str = "") -> float:
        """路径与问题的词汇相关性。

        - 属性 local/label 与问题文本的最长公共片段（2-4 字），越长权重越高；
          通用片段（"基金"等）不计分，避免全平；
        - from 类的英文特征词（FundManagerPerson → Manager）命中属性 local
          时加权（区分 hasFundManager / hasFundDepositary）。
        """
        if not path:
            return 0.0
        score = 0.0
        # from 类特征词：camelCase 拆分，去掉通用词
        generic_tokens = {"Fund", "Person", "Role", "Party", "Record", "Value"}
        from_tokens = set()
        if from_local:
            token, buf = [], ""
            for ch in from_local:
                if ch.isupper() and buf:
                    from_tokens.add(buf)
                    buf = ch
                else:
                    buf += ch
            if buf:
                from_tokens.add(buf)
            from_tokens -= generic_tokens
        for hop in path:
            best_n = 0
            for token in (hop.get("property_local", ""), hop.get("property_label", "")):
                if not token:
                    continue
                for n in (4, 3, 2):
                    if n <= best_n:
                        continue
                    for i in range(len(token) - n + 1):
                        gram = token[i:i + n]
                        if gram and gram not in cls._GENERIC_GRAMS and gram in question:
                            best_n = n
                            break
            score += best_n * best_n
            for ft in from_tokens:
                if ft and ft.lower() in hop.get("property_local", "").lower():
                    score += 8.0
        return score

    def check_property_domain(self, property_local: str, subject_class_local: str) -> tuple[bool, str]:
        """domain 约束校验：subject 类是否落在属性 domain 闭包内。

        无 domain 声明的属性视为可用（开放假设）；有声明则要求
        subject 的祖先闭包与 domain 集合有交集。
        """
        prop = self.properties.get(property_local)
        if prop is None:
            return False, f"属性不存在于本体：{property_local}"
        if not prop.domains:
            return True, "ok（无 domain 声明）"
        overlap = self.ancestors_of(subject_class_local) & set(prop.domains)
        if overlap:
            return True, f"ok（domain {sorted(overlap)} 命中）"
        return False, (f"domain 冲突：{property_local} 的 domain 是 "
                       f"{prop.domains}，{subject_class_local} 不在其子类闭包内")

    # ---------------------------------------------------------------- 渲染
    def render_for_llm(self, *, max_class_depth: int = 6,
                       include_definitions: bool = False) -> str:
        """渲染紧凑语义视图文本，注入意图解析 prompt。

        三段：类层级（缩进树）/ 类间关系（domain--属性-->range）/ 数据属性（按类分组）。
        """
        lines: list[str] = []

        # 1) 类层级树
        lines.append("【类层级】（local名(中文)，缩进=继承）")
        roots = sorted([c for c in self.classes.values() if not c.parents],
                       key=lambda c: c.local)
        visited: set[str] = set()

        def render_tree(info: ClassInfo, depth: int) -> None:
            if info.local in visited or depth > max_class_depth:
                return
            visited.add(info.local)
            suffix = f" — {info.definition}" if include_definitions and info.definition else ""
            lines.append(f"{'  ' * depth}{info.local}({info.label}){suffix}")
            for child_local in sorted(info.children):
                render_tree(self.classes[child_local], depth + 1)

        for root in roots:
            render_tree(root, 0)
        # 兜底：因环/孤立未访问到的类平铺列出
        for local in sorted(set(self.classes) - visited):
            info = self.classes[local]
            lines.append(f"{info.local}({info.label})")

        # 2) 类间关系
        lines.append("")
        lines.append("【类间关系】（domain --属性local(中文)--> range；查询可正向或反向(^)使用）")
        seen_edge: set[tuple] = set()
        for e in sorted(self.relations,
                        key=lambda e: (e.domain_local, e.property_local, e.range_local)):
            key = (e.domain_local, e.property_local, e.range_local)
            if key in seen_edge:
                continue
            seen_edge.add(key)
            d, r = self.classes.get(e.domain_local), self.classes.get(e.range_local)
            d_label = d.label if d else e.domain_local
            r_label = r.label if r else e.range_local
            lines.append(f"{e.domain_local}({d_label}) --{e.property_local}"
                         f"({e.property_label})--> {e.range_local}({r_label})")

        # 3) 数据属性（按 domain 类分组）
        lines.append("")
        lines.append("【数据属性】（类 → 属性local(中文)，可用于过滤/排序）")
        by_class: dict[str, list[PropertyInfo]] = {}
        for prop in self.properties.values():
            if prop.kind != "datatype":
                continue
            for d in prop.domains:
                by_class.setdefault(d, []).append(prop)
        for d in sorted(by_class):
            cls = self.classes.get(d)
            head = f"{d}({cls.label})" if cls else d
            props = "、".join(f"{p.local}({p.label})" for p in
                             sorted(by_class[d], key=lambda p: p.local))
            lines.append(f"{head}: {props}")

        return "\n".join(lines)
