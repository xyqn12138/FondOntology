"""问题驱动的本体局部上下文检索。

第一版只使用确定性词法匹配和 OntologyContext 的关系图：
- 从问题中召回类、对象属性、数据属性和实体类型；
- 为召回概念补齐必要的父类、domain/range 和关系路径；
- 只渲染当前问题相关的本体子图，并设置字符预算。

完整 T-BOX 仍由 planner 使用，本模块只控制送入 LLM 的上下文大小。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Optional

from rdflib import URIRef
from rdflib.namespace import RDFS, SKOS

from .index import OntologyIndex
from .resolver import VocabularyResolver, _TYPE_SYNONYMS
from .semantics import OntologyContext
from .owl_expression import canonical_graph, graph_hash


_GENERIC_LABELS = frozenset({"基金", "对象", "记录", "数据", "信息"})
_TYPE_HINTS = (
    ("基金经理", "FundManagerPerson"),
    ("经理", "FundManagerPerson"),
)
_PROPERTY_HINTS = (
    (("管理", "经理"), "hasFundManager"),
    (("托管", "托管人"), "hasFundDepositary"),
    (("策略", "主题", "行业", "投资方向", "投资重点", "医药", "消费", "科技"),
     "investmentFocus"),
    (("风险", "R1", "R2", "R3", "R4", "R5"), "hasFundRiskLevel"),
)


@dataclass
class SchemaCandidate:
    name: str
    kind: str
    score: float
    evidence_source: str
    matched_span: str = ""
    anchor_classes: list[str] = field(default_factory=list)
    role: str = "support"
    required_by: list[str] = field(default_factory=list)
    alternative_group: Optional[str] = None
    uncertain: bool = False


@dataclass
class SchemaContext:
    """送入语义解析 prompt 的局部本体上下文。"""

    classes: list[str] = field(default_factory=list)
    properties: list[str] = field(default_factory=list)
    paths: list[list[dict]] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    render_text: str = ""
    char_count: int = 0
    token_count: int = 0
    tokenizer: str = "char_heuristic"
    candidate_count: int = 0
    truncated: bool = False
    critical_missing: bool = False
    dropped_items: dict = field(default_factory=dict)
    budget_used: dict = field(default_factory=dict)
    degradation: str = "none"
    retrieval_rejected: list[dict] = field(default_factory=list)
    path_search_capped: bool = False
    path_candidates_before_limit: int = 0
    path_candidates_retained: int = 0
    path_trace: list[dict] = field(default_factory=list)
    schema_version: str = "schema-context-v3"
    ontology_version: str = ""
    missing_reason: str = "none"
    budget_dropped: dict = field(default_factory=dict)
    candidates: list[dict] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    required_missing: list[dict] = field(default_factory=list)
    support_dropped: list[str] = field(default_factory=list)
    optional_dropped: list[str] = field(default_factory=list)
    candidate_budget_dropped: list[str] = field(default_factory=list)
    selection_rejected: list[dict] = field(default_factory=list)
    path_selection_capped: bool = False


def estimate_token_count(text: str) -> tuple[int, str]:
    """估算上下文 token 数；有 tiktoken 时使用 cl100k_base 精确计算。"""
    if not text:
        return 0, "char_heuristic"
    try:
        import tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text)), "cl100k_base"
    except Exception:
        # 运行环境不一定安装 tokenizer。中文字符按单元估算，ASCII 连续词
        # 作为一个单元，结果只用于预算观测，不冒充具体模型的精确 token 数。
        units = 0
        ascii_run = False
        for char in text:
            is_ascii_word = char.isascii() and (char.isalnum() or char in "_-")
            if is_ascii_word:
                if not ascii_run:
                    units += 1
                ascii_run = True
            else:
                units += 1
                ascii_run = False
        return max(1, units), "char_heuristic"


class SchemaRetriever:
    """从完整本体中检索当前问题所需的局部语义子图。"""

    def __init__(self, index: OntologyIndex, *, max_chars: int = 10000,
                 max_tokens: Optional[int] = None):
        self.index = index
        self.ctx = OntologyContext.from_stack(index.stack)
        self.resolver = VocabularyResolver(index)
        self.max_chars = max(0, max_chars)
        self.max_tokens = None if max_tokens is None else max(0, max_tokens)
        self._lexical_documents = self._build_lexical_documents()
        self.ontology_version = graph_hash(canonical_graph(index.stack.tbox))

    def retrieve(self, question: str,
                 context: Optional[dict] = None) -> SchemaContext:
        text = self._question_with_context(question, context)
        # Domain phrase normalization, not question-to-IRI mappings.
        text = self._normalize_terms(text)
        class_seeds: dict[str, float] = {}
        property_seeds: dict[str, float] = {}
        conditions: list[str] = []
        retrieval_rejected = []
        path_trace = []
        evidence = {}

        # 现有 resolver 负责精确标签、别名、同义词和实体候选。
        for candidate in sorted(self.resolver.search(text, limit=24),
                                key=lambda c: (-c.score, c.iri)):
            local = candidate.iri.rsplit("/", 1)[-1]
            if candidate.kind == "class" and local in self.ctx.classes:
                class_seeds[local] = max(class_seeds.get(local, 0.0),
                                         candidate.score)
                evidence[("class", local)] = ("resolver:" + candidate.match_type,
                                               candidate.label if candidate.label in text else "")
            elif candidate.kind == "property" and local in self.ctx.properties:
                property_seeds[local] = max(property_seeds.get(local, 0.0),
                                            candidate.score)
                evidence[("property", local)] = ("resolver:" + candidate.match_type,
                                                  candidate.label if candidate.label in text else "")
            elif candidate.kind == "entity":
                for type_iri in self.index.entities.get(candidate.iri, {}).get("types", []):
                    type_local = type_iri.rsplit("/", 1)[-1]
                    if type_local in self.ctx.classes:
                        class_seeds[type_local] = max(
                            class_seeds.get(type_local, 0.0), candidate.score + 0.2)
                        evidence[("class", type_local)] = ("entity_type", candidate.label)

        # resolver.search 以完整问题做匹配时可能错过问题中的短属性词，
        # 因此补一次逐概念词法扫描。低信息量的“基金”等词不单独触发扩展。
        self._scan_concepts(text, class_seeds, property_seeds, retrieval_rejected, evidence)
        self._apply_hints(text, class_seeds, property_seeds)
        before_scope = (dict(class_seeds), dict(property_seeds))
        self._refine_seeds(text, class_seeds, property_seeds)
        for kind, before, after in (("class", before_scope[0], class_seeds),
                                    ("property", before_scope[1], property_seeds)):
            retrieval_rejected.extend(
                {"name": name, "kind": kind, "score": score, "source": "scope",
                 "selection_reason": "scope_rejected"}
                for name, score in sorted(before.items()) if name not in after)
        candidates = self._candidate_contract(text, class_seeds, property_seeds, evidence)
        required_classes = {c.name for c in candidates if c.kind == "class"
                            and c.role == "required"}
        required_properties = {c.name for c in candidates if c.kind == "property"
                               and c.role == "required"}

        # 问题中出现的数值、时间、否定、排序等条件不一定对应本体节点，
        # 先显式保留给 LLM，后续由 SemanticParse 处理。
        conditions.extend(self._extract_conditions(question))

        selected_classes = set(class_seeds)
        selected_properties = set(property_seeds)

        # 属性命中时补 domain/range 类；类命中时补直接父类。
        for prop_local in list(selected_properties):
            prop = self.ctx.properties[prop_local]
            selected_classes.update(d for d in prop.domains if d in self.ctx.classes)
            selected_classes.update(r for r in prop.ranges if r in self.ctx.classes)
        for local in list(selected_classes):
            selected_classes.update(self.ctx.classes[local].parents)

        # 对问题命中的属性优先补路径。不能只取 BFS 返回的前两条：
        # 同一对类可能存在多条合法关系，最短路径不一定是问题语义所指的属性。
        paths: list[list[dict]] = []
        seed_class_list = sorted(class_seeds,
                                 key=lambda c: (-class_seeds.get(c, 0.0), c))

        def add_paths(source: str, target: str,
                      preferred_property: Optional[str] = None,
                      exact_endpoint: bool = False,
                      required_by: Optional[str] = None) -> None:
            if source == target:
                return
            diagnostic = {}
            found = self.ctx.find_relation_paths(source, target,
                                                 max_hops=3, limit=24,
                                                 diagnostics=diagnostic)
            trace = {"source": source, "target": target,
                     "purpose": "property_dependency" if preferred_property else "class_bridge",
                     "preferred_property": preferred_property,
                     "required_by": required_by,
                     "search": diagnostic, "candidates_before_selection": len(found),
                     "selection_reason": "preferred_then_shortest_then_relevance"}
            path_trace.append(trace)
            if exact_endpoint:
                found = [path for path in found
                         if path and path[-1].get("via") == target]
            if preferred_property:
                preferred = [
                    path for path in found
                    if any(h["property_local"] == preferred_property
                           for h in path)
                ]
                found = preferred or found
            else:
                # 数据属性没有可用于路径匹配的对象属性名。此时优先保留
                # 最短直接边，避免无关的兄弟路径挤掉 domain 连接。
                shortest = min((len(path) for path in found), default=0)
                direct = [path for path in found if len(path) == shortest]
                found = direct + [path for path in found if path not in direct]
            found.sort(key=lambda p: (len(p), sum(bool(h.get("inverse")) for h in p),
                                      -self.ctx.score_path(p, text, source),
                                      [h["property_local"] for h in p]))
            trace["selected"] = [{"path": path, "score": self.ctx.score_path(path, text, source)}
                                 for path in found[:1]]
            trace["rejected"] = found[1:]
            for path in found[:1]:
                if not path:
                    continue
                paths.append(path)
                selected_properties.update(h["property_local"] for h in path)
                selected_classes.update(
                    h["via"] for h in path if h["via"] in self.ctx.classes)

        # 数据属性的 domain 是过滤真正落点；先补“目标类 -> domain”的路径。
        for prop_local in sorted(property_seeds):
            prop = self.ctx.properties.get(prop_local)
            if prop is None or prop.kind != "datatype":
                continue
            for domain in prop.domains:
                if domain not in self.ctx.classes:
                    continue
                for source in seed_class_list:
                    add_paths(source, domain, exact_endpoint=True, required_by=prop_local)

        # 对象属性直接表达问题中的关系，优先保留它的 domain -> range 路径；
        # 对子类目标（如 EquityFund）再补一条从具体目标类出发的路径。
        for prop_local in sorted(property_seeds):
            prop = self.ctx.properties.get(prop_local)
            if prop is None or prop.kind != "object":
                continue
            for domain in prop.domains:
                for target in prop.ranges:
                    if domain in self.ctx.classes and target in self.ctx.classes:
                        add_paths(domain, target, prop_local,
                                  exact_endpoint=True)
                for source in seed_class_list:
                    add_paths(source, domain, prop_local,
                              exact_endpoint=True)

        # A mentioned container and its child need their own bridge, even when
        # unrelated scalar attributes have already been recalled.
        for source in seed_class_list:
            for target in seed_class_list:
                if source < target:
                    direct = self.ctx.find_relation_paths(source, target, max_hops=1)
                    if direct and direct[0]:
                        add_paths(source, target)

        # 没有直接命中关系词时，保留少量类间候选路径作为语义补充。
        if not property_seeds and len(seed_class_list) > 1:
            for source in seed_class_list:
                for target in seed_class_list:
                    add_paths(source, target)

        # 路径的 domain/range 是约束信息，补入关系两端；避免只给一条裸属性。
        for prop_local in list(selected_properties):
            prop = self.ctx.properties.get(prop_local)
            if prop is None:
                continue
            selected_classes.update(d for d in prop.domains if d in self.ctx.classes)
            selected_classes.update(r for r in prop.ranges if r in self.ctx.classes)

        # 去重关系路径，保留短路径和较相关路径。
        all_paths = self._dedupe_paths(paths, text, limit=None)
        paths = all_paths[:12]
        requirements = self._requirements(
            candidates, required_classes, required_properties, path_trace)
        rendered, retained_classes, retained_properties, retained_paths, dropped = self._render(
            question=question,
            classes=selected_classes,
            class_scores=class_seeds,
            properties=selected_properties,
            property_scores=property_seeds,
            paths=paths,
            conditions=conditions,
            requirements=requirements,
        )
        required_missing = self._missing_requirements(
            requirements, retained_classes, retained_properties, retained_paths)
        candidate_budget_dropped = sorted(set(dropped["critical"]))
        roles = {c.name: c.role for c in candidates}
        dropped_names = set(dropped["classes"]) | set(dropped["properties"])
        token_count, tokenizer = estimate_token_count(rendered)

        return SchemaContext(
            classes=sorted(retained_classes),
            properties=sorted(retained_properties),
            paths=retained_paths,
            conditions=conditions,
            render_text=rendered,
            char_count=len(rendered),
            token_count=token_count,
            tokenizer=tokenizer,
            candidate_count=len(class_seeds) + len(property_seeds),
            truncated=any(dropped.values()),
            critical_missing=bool(required_missing),
            dropped_items=dropped,
            budget_used={"chars": len(rendered), "tokens": token_count,
                         "max_chars": self.max_chars, "max_tokens": self.max_tokens,
                         "tokenizer": tokenizer},
            degradation="budget_insufficient" if required_missing else (
                "optional_context_dropped" if any(dropped.values()) else "none"),
            retrieval_rejected=[row for row in retrieval_rejected
                                if row["name"] not in class_seeds
                                and row["name"] not in property_seeds],
            path_search_capped=any(t["search"].get("capped") for t in path_trace),
            path_selection_capped=len(all_paths) > 12,
            selection_rejected=[{"source": t["source"], "target": t["target"],
                                 "purpose": t["purpose"], "paths": t.get("rejected", [])}
                                for t in path_trace if t.get("rejected")],
            path_candidates_before_limit=sum(t["candidates_before_selection"]
                                             for t in path_trace),
            path_candidates_retained=len(paths),
            path_trace=path_trace,
            ontology_version=self.ontology_version,
            missing_reason=("ontology_unavailable" if not self.ctx.classes else
                            "budget_dropped" if required_missing else
                            "not_found" if not class_seeds and not property_seeds else "none"),
            budget_dropped=dropped,
            candidates=[asdict(candidate) for candidate in candidates],
            requirements=requirements,
            required_missing=required_missing,
            candidate_budget_dropped=candidate_budget_dropped,
            support_dropped=sorted(n for n in dropped_names if roles.get(n) == "support"),
            optional_dropped=sorted(n for n in dropped_names if roles.get(n, "optional") == "optional"),
        )

    def _question_with_context(self, question: str,
                               context: Optional[dict]) -> str:
        if not context:
            return question or ""
        parts = [question or "", context.get("last_question") or "",
                 (context.get("last_answer") or "")[:300]]
        return "\n".join(p for p in parts if p)

    def _scan_concepts(self, text: str, class_seeds: dict[str, float],
                       property_seeds: dict[str, float], rejected=None, evidence=None) -> None:
        for local, info in self.ctx.classes.items():
            terms = {local, info.label}
            for term in terms:
                if len(term) >= 3 and term not in _GENERIC_LABELS and term in text:
                    class_seeds[local] = max(class_seeds.get(local, 0.0), 0.82)
                    if evidence is not None:
                        evidence[("class", local)] = ("explicit_label", term)
        for local, info in self.ctx.properties.items():
            terms = {local, info.label}
            for term in terms:
                if len(term) >= 3 and term not in _GENERIC_LABELS and term in text:
                    property_seeds[local] = max(property_seeds.get(local, 0.0), 0.80)
                    if evidence is not None:
                        evidence[("property", local)] = ("explicit_label", term)

        # 复用已有受控类型同义词，不在这里维护第二套基金类型表。
        for phrase, local in _TYPE_SYNONYMS.items():
            if phrase in text and local in self.ctx.classes:
                class_seeds[local] = max(class_seeds.get(local, 0.0), 0.95)
                if evidence is not None:
                    evidence[("class", local)] = ("type_synonym", phrase)
        self._match_lexical_documents(text, class_seeds, property_seeds, rejected, evidence)

    @staticmethod
    def _normalize_terms(value: str) -> str:
        for phrase, normalized in (("债基", "债券基金"), ("规模", "资产净值"),
                                   ("单位净值", "份额净值"), ("收费", "费用")):
            value = value.replace(phrase, normalized)
        return value

    @staticmethod
    def _content_label(value: str) -> str:
        for word in ("具有", "拥有", "对应", "基金", "标准", "取值"):
            value = value.replace(word, "")
        return value

    def _build_lexical_documents(self):
        documents = []
        for kind, items in (("class", self.ctx.classes), ("property", self.ctx.properties)):
            for local, info in sorted(items.items()):
                uri = URIRef(info.iri)
                labels = {local, info.label}
                for pred in (RDFS.label, SKOS.prefLabel, SKOS.altLabel):
                    labels.update(str(o) for o in self.index.stack.tbox.objects(uri, pred))
                definitions = [str(o) for pred in (SKOS.definition, RDFS.comment)
                               for o in self.index.stack.tbox.objects(uri, pred)]
                documents.append((kind, local, labels, definitions))
        return documents

    def _match_lexical_documents(self, text, class_seeds, property_seeds, rejected=None,
                                 evidence=None):
        candidates = {"class": [], "property": []}
        generic = {"日期", "名称", "代码", "基金", "投资", "份额", "记录",
                   "期间", "主体", "方式", "金额", "数量", "报告", "管理",
                   "是否", "用于", "表示", "对应", "相关", "具有"}
        # Remove entity/category mentions when scoring field descriptions.
        # Otherwise every field whose definition repeats "investor" is recalled
        # by an unsupported question about an investor.
        property_text = text
        for name in sorted(class_seeds, key=lambda c: -len(self.ctx.classes[c].label)):
            if name != "Fund":
                property_text = property_text.replace(self.ctx.classes[name].label, "")
        for kind, local, labels, definitions in self._lexical_documents:
            best, source, span = 0.0, "", ""
            query = property_text if kind == "property" else text
            for label in labels:
                value = self._normalize_terms(self._content_label(label))
                if value and len(value) >= 2 and value not in generic and value in query:
                    score = 0.94 + min(len(value), 10) * 0.002
                    if score > best:
                        best, source, span = score, "label", value
                if not re.search(r"[\u4e00-\u9fff]", value):
                    continue
                # Long partial label matches handle qualified labels such as
                # "report period identifier" without per-property aliases.
                for n in range(min(6, len(value)), 3 if kind == "class" else 1, -1):
                    if n / max(1, len(value)) < 0.5:
                        continue
                    matches = [value[i:i + n] for i in range(len(value) - n + 1)
                               if value[i:i + n] in query and value[i:i + n] not in generic]
                    if matches:
                        score = 0.76 + n * 0.015
                        if score > best:
                            best, source, span = score, "label_fragment", matches[0]
                        break
            for definition in definitions if kind == "property" else []:
                value = self._content_label(definition)
                for n in range(min(8, len(value)), 3, -1):
                    matches = [value[i:i + n] for i in range(len(value) - n + 1)
                               if value[i:i + n] in query
                               and re.fullmatch(r"[\u4e00-\u9fff]+", value[i:i + n])]
                    if matches:
                        score = 0.58 + n * 0.018
                        if score > best:
                            best, source, span = score, "definition", matches[0]
                        break
            if best:
                candidates[kind].append((best, local, source, span))
        for kind, seeds in (("class", class_seeds), ("property", property_seeds)):
            ranked = sorted(candidates[kind], key=lambda r: (-r[0], r[1]))
            limit = 6 if kind == "class" else 12
            if rejected is not None:
                rejected.extend({"name": local, "kind": kind, "score": score,
                                 "source": source, "selection_reason": "lexical_top_k"}
                                for score, local, source, span in ranked[limit:])
            for score, local, source, span in ranked[:limit]:
                if evidence is not None and (kind, local) not in evidence:
                    evidence[(kind, local)] = (source, span)
                seeds[local] = max(seeds.get(local, 0.0), score)

    def _apply_hints(self, text: str, class_seeds: dict[str, float],
                     property_seeds: dict[str, float]) -> None:
        for phrase, local in _TYPE_HINTS:
            if phrase in text and local in self.ctx.classes:
                class_seeds[local] = max(class_seeds.get(local, 0.0), 0.72)
        for phrases, local in _PROPERTY_HINTS:
            if any(p in text for p in phrases) and local in self.ctx.properties:
                property_seeds[local] = max(property_seeds.get(local, 0.0), 0.72)
        # Compound names (accounts, reports, investors) do not themselves mean
        # the question requests the Fund class.
        remaining = text
        for name in sorted(class_seeds, key=lambda n: -len(self.ctx.classes[n].label)):
            if name != "Fund":
                remaining = remaining.replace(self.ctx.classes[name].label, "")
        if "基金" in remaining and "Fund" in self.ctx.classes:
            class_seeds["Fund"] = max(class_seeds.get("Fund", 0), 0.72)
        elif "Fund" in class_seeds and any(
                self.ctx.classes[c].label in text for c in class_seeds if c != "Fund"):
            class_seeds.pop("Fund", None)

    def _refine_seeds(self, text, class_seeds, property_seeds):
        """Scope weak field fragments to mentioned classes and inferred domains."""
        explicit = set()
        for name, info in self.ctx.classes.items():
            label = self._normalize_terms(info.label)
            if name == "Fund" or not label or label not in text:
                continue
            # Do not expand "portfolio" into every class whose longer label
            # begins with that word, or treat "units" inside "unit class" twice.
            if any(label != self._normalize_terms(other.label)
                   and label in self._normalize_terms(other.label)
                   and self._normalize_terms(other.label) in text
                   for other in self.ctx.classes.values()):
                continue
            explicit.add(name)
        explicit.update(name for phrase, name in _TYPE_SYNONYMS.items()
                        if phrase in text and name in self.ctx.classes)
        explicit.update(name for phrase, name in _TYPE_HINTS
                        if phrase in text and name in self.ctx.classes)
        if explicit:
            for name in list(class_seeds):
                label = self._normalize_terms(self.ctx.classes[name].label)
                if name not in explicit and name != "Fund" and class_seeds[name] < 0.90 \
                        and any(self._normalize_terms(self.ctx.classes[c].label) in label
                                for c in explicit if c != "Fund"):
                    class_seeds.pop(name)
            # A generic parent mention ("投资资产", "基金记录") should not
            # force all of its sibling subclasses into the required packet.
            # Keep a subclass only when it was an exact/high-confidence hit.
            for name in list(class_seeds):
                if class_seeds[name] >= 0.90:
                    continue
                if any(name != parent and self.ctx.is_subclass(name, parent)
                       and parent in class_seeds for parent in class_seeds):
                    class_seeds.pop(name)
        strong_domains = set(explicit)
        for name, score in property_seeds.items():
            if score >= 0.90 or self.ctx.properties[name].kind == "datatype":
                strong_domains.update(self.ctx.properties[name].domains)
        scope = set().union(*(self.ctx.ancestors_of(c) for c in strong_domains)) if strong_domains else set()
        if scope:
            for name in list(property_seeds):
                prop = self.ctx.properties[name]
                label = self._normalize_terms(self._content_label(prop.label))
                hinted = any(local == name and any(p in text for p in phrases)
                             for phrases, local in _PROPERTY_HINTS)
                if property_seeds[name] < 0.90 and not scope.intersection(prop.domains) \
                        and not hinted and not (len(label) >= 3 and label in text):
                    property_seeds.pop(name)
            # Generic field words ("name", "amount", "date") are useful only
            # after the domain is known. Never match them globally.
            for name, prop in self.ctx.properties.items():
                if prop.kind != "datatype" or not scope.intersection(prop.domains):
                    continue
                label = self._normalize_terms(self._content_label(prop.label))
                if any(word in text and word in label
                       for word in ("名称", "金额", "代码", "市值", "数量")):
                    property_seeds[name] = max(property_seeds.get(name, 0), 0.86)
            time_requested = any(word in text for word in
                                 ("最近", "最新", "去年", "今年", "起止", "哪段日期", "覆盖"))
            if time_requested:
                for name, prop in self.ctx.properties.items():
                    if prop.kind == "datatype" and scope.intersection(prop.domains) \
                            and any(r in ("date", "dateTime") for r in prop.ranges):
                        property_seeds[name] = max(property_seeds.get(name, 0), 0.88)
        # A scalar attribute can express the business object without its class
        # label appearing verbatim ("fund fee rate"). Preserve an explicit Fund
        # prefix, but not the Fund inside an unrelated compound class label.
        if "Fund" in self.ctx.classes and text.startswith("基金") and not any(
                self._normalize_terms(self.ctx.classes[c].label) in text
                and self._normalize_terms(self.ctx.classes[c].label).startswith("基金")
                for c in explicit if c != "Fund"):
            class_seeds["Fund"] = max(class_seeds.get("Fund", 0), 0.82)
        # Questions phrased as "基金的 X" still need the business-object
        # connection when X itself is the selected target class.
        if "Fund" in self.ctx.classes and text.startswith("基金") and "Fund" not in class_seeds:
            if any(self.ctx.is_subclass(name, "Fund") for name in class_seeds):
                class_seeds["Fund"] = max(class_seeds.get("Fund", 0), 0.82)
            else:
                for name in class_seeds:
                    if any("Fund" in (p.domains + p.ranges)
                           for p in self.ctx.properties.values()
                           if name in p.domains or name in p.ranges):
                        class_seeds["Fund"] = max(class_seeds.get("Fund", 0), 0.82)
                        break
        # Exact descriptive property labels may be outside the lexical top-k.
        for name, prop in self.ctx.properties.items():
            label = self._normalize_terms(self._content_label(prop.label))
            if prop.kind == "object" and len(label) >= 3 and label in text:
                property_seeds[name] = max(property_seeds.get(name, 0), 0.84)
            if prop.kind == "object" and any(
                    class_seeds.get(c, 0) >= 0.90 for c in prop.domains) and any(
                    class_seeds.get(c, 0) >= 0.90 for c in prop.ranges):
                property_seeds[name] = max(property_seeds.get(name, 0), 0.92)

    @staticmethod
    def _extract_conditions(question: str) -> list[str]:
        found: list[str] = []
        patterns = (
            "同时管理", "多个", "至少", "超过", "最多", "最少", "排名",
            "最高", "最低", "以上", "以下", "不包括", "除了", "去年",
            "今年", "最近", "是否", "是不是", "互斥", "等价",
        )
        for marker in patterns:
            if marker in question and marker not in found:
                found.append(marker)
        return found

    @staticmethod
    def _dedupe_paths(paths: list[list[dict]], question: str = "",
                      limit: Optional[int] = 12) -> list[list[dict]]:
        unique: dict[tuple, list[dict]] = {}
        for path in paths:
            key = tuple((h["property_local"], bool(h.get("inverse")),
                         h.get("via")) for h in path)
            unique[key] = path
        return sorted(unique.values(),
                      key=lambda p: (-OntologyContext.score_path(p, question), len(p),
                                     [h["property_local"] for h in p]))[:limit]

    def _candidate_contract(self, text, classes, properties, evidence):
        anchors = {name for name in classes if evidence.get(("class", name), ("", ""))[0]
                   in ("explicit_label", "type_synonym", "entity_type")}
        anchors.update(name for name in classes if self.ctx.classes[name].label in text)
        anchors = {name for name in anchors if not any(
            self.ctx.classes[name].label != self.ctx.classes[other].label
            and self.ctx.classes[name].label in self.ctx.classes[other].label
            and self.ctx.classes[other].label in text for other in anchors)}
        scope = set().union(*(self.ctx.ancestors_of(c) for c in anchors)) if anchors else set()
        out = []
        for kind, values in (("class", classes), ("property", properties)):
            for name, score in sorted(values.items()):
                source, span = evidence.get((kind, name), ("inferred", ""))
                explicit = source in ("explicit_label", "type_synonym", "entity_type", "label")
                if kind == "class" and name in anchors:
                    explicit = True
                    source, span = "explicit_class", self.ctx.classes[name].label
                elif kind == "class":
                    explicit = False
                if kind == "property" and source.startswith("resolver:") and span:
                    label = self._normalize_terms(self._content_label(
                        self.ctx.properties[name].label))
                    if label in text:
                        explicit = True
                required_by = ["query:" + span] if explicit else []
                if kind == "property" and not explicit:
                    prop = self.ctx.properties[name]
                    label = self._normalize_terms(self._content_label(prop.label))
                    field_words = [word for word in ("名称", "金额", "代码", "市值", "数量")
                                   if word in text and word in label]
                    temporal = (any(word in text for word in
                                    ("最近", "最新", "去年", "今年", "起止", "哪段日期", "覆盖"))
                                and any(r in ("date", "dateTime") for r in prop.ranges))
                    if scope.intersection(prop.domains) and (field_words or temporal):
                        required_by = ["field:" + word for word in field_words]
                        if temporal:
                            required_by.append("temporal_slot")
                        source = "anchored_field_role"
                        explicit = True
                    elif any(local == name and any(p in text for p in phrases)
                             for phrases, local in _PROPERTY_HINTS):
                        # Domain hints stay visible as uncertain support, not
                        # necessary solely because they have a ranking score.
                        source = "domain_hint"
                out.append(SchemaCandidate(
                    name=name, kind=kind, score=score, evidence_source=source,
                    matched_span=span, anchor_classes=sorted(anchors),
                    role="required" if explicit else "optional" if source == "label_fragment"
                    else "support", required_by=required_by,
                    uncertain=not explicit))
        return out

    def _requirements(self, candidates, required_classes, required_properties, path_trace):
        requirements = [
            {"kind": c.kind, "name": c.name, "role": c.role,
             "required_by": c.required_by, "alternative_group": c.alternative_group}
            for c in candidates if c.role == "required"
        ]
        for name in sorted(required_properties):
            prop = self.ctx.properties[name]
            anchors = {a for c in candidates for a in c.anchor_classes}
            sources = sorted(c for c in required_classes & anchors if not any(
                self.ctx.is_subclass(c, domain) for domain in prop.domains))
            # If an explicit object already owns the field, no cross-object
            # access requirement is justified by other recalled class labels.
            if any(any(self.ctx.is_subclass(c, domain) for domain in prop.domains)
                   for c in required_classes & anchors):
                sources = []
            for source in sources:
                traces = [t for t in path_trace if t["source"] == source and (
                    t.get("required_by") == name or t.get("preferred_property") == name)]
                routes = [row["path"] for t in traces for row in t.get("selected", [])]
                if routes:
                    requirements.append({
                        "kind": "path", "name": name, "role": "required",
                        "required_by": ["field:" + name], "source": source,
                        "target": sorted(prop.domains), "purpose": "field_access",
                        "alternatives": routes, "alternative_group": f"{source}:{name}",
                    })
        return requirements

    @staticmethod
    def _missing_requirements(requirements, classes, properties, paths):
        missing = []
        for item in requirements:
            if item["kind"] == "class" and item["name"] not in classes:
                missing.append(item)
            elif item["kind"] == "property" and item["name"] not in properties:
                missing.append(item)
            elif item["kind"] == "path":
                if not any(item["source"] in classes and all(
                               h["property_local"] in properties and h["via"] in classes
                               for h in route) and route in paths
                           for route in item["alternatives"]):
                    missing.append(item)
        return missing

    def _render(self, *, question: str, classes: set[str],
                class_scores: dict[str, float], properties: set[str],
                property_scores: dict[str, float],
                paths: list[list[dict]], conditions: list[str],
                requirements: Optional[list[dict]] = None) -> tuple:
        kept_classes, kept_properties, kept_paths = set(), set(), []
        dropped = {"classes": [], "properties": [], "paths": [], "critical": []}

        def class_closure(names):
            out = set()
            for name in names:
                if name in self.ctx.classes:
                    out.update(self.ctx.ancestors_of(name))
            return out

        def text_for(cs, ps, route_list):
            lines = ["【问题相关本体上下文】", "【候选类】"]
            for name in sorted(cs, key=lambda c: (-class_scores.get(c, 0), c)):
                info = self.ctx.classes[name]
                parents = "、".join(p for p in info.parents if p in cs) or "无"
                lines.append(f"{name}({info.label})；父类：{parents}")
            for kind, title in (("object", "对象属性"), ("datatype", "数据属性")):
                matching = [p for p in sorted(ps) if self.ctx.properties[p].kind == kind]
                if matching:
                    lines.append(f"【{title}】")
                for name in matching:
                    info = self.ctx.properties[name]
                    lines.append(f"{name}({info.label})："
                                 f"{'、'.join(info.domains) or '未声明'} -> "
                                 f"{'、'.join(info.ranges) or '未声明'}")
            if route_list:
                lines.append("【可用关系路径】")
                for path in route_list:
                    lines.append("；".join(
                        f"{'^' if h.get('inverse') else ''}{h['property_local']} -> {h['via']}"
                        for h in path))
            if conditions:
                lines.extend(["【条件词】", "、".join(conditions)])
            return "\n".join(lines)

        def fits(text):
            return len(text) <= self.max_chars and (
                self.max_tokens is None or estimate_token_count(text)[0] <= self.max_tokens)

        # The question is already a separate prompt field; do not duplicate a
        # potentially unbounded input inside the schema allocation.
        if not fits(text_for(set(), set(), [])):
            dropped["critical"].append("schema_header")
            dropped["classes"] = sorted(classes)
            dropped["properties"] = sorted(properties)
            dropped["paths"] = paths
            return "", kept_classes, kept_properties, kept_paths, dropped

        def accept(cs, ps, path=None):
            cs = class_closure(cs)
            for prop in ps:
                info = self.ctx.properties[prop]
                cs.update(class_closure(info.domains + info.ranges))
            candidate_paths = kept_paths + ([path] if path is not None else [])
            if not fits(text_for(kept_classes | cs, kept_properties | ps, candidate_paths)):
                return False
            kept_classes.update(cs)
            kept_properties.update(ps)
            if path is not None:
                kept_paths.append(path)
            return True

        # Join a hit attribute to its domain before spending budget on optional
        # paths. Prefer direct connections when relevance is tied.
        required_names = {r["name"] for r in requirements or []}
        for name in sorted(class_scores, key=lambda c: (-class_scores[c], c)):
            if name in required_names and name not in kept_classes:
                if not accept({name}, set()):
                    dropped["critical"].append(name)
        for name in sorted(property_scores, key=lambda p: (
                p not in required_names, -property_scores[p], p)):
            if name not in properties:
                continue
            info = self.ctx.properties[name]
            related = [p for p in paths if any(h["property_local"] == name for h in p)
                       or (p and p[-1]["via"] in info.domains)]
            necessary_routes = [route for requirement in requirements or []
                                if requirement["kind"] == "path" and requirement["name"] == name
                                for route in requirement["alternatives"]]
            if necessary_routes:
                related = necessary_routes
            related.sort(key=lambda p: (len(p), sum(bool(h.get("inverse")) for h in p),
                                       -self.ctx.score_path(p, question),
                                       [h["property_local"] for h in p]))
            route = related[0] if related else None
            ps = {name} | ({h["property_local"] for h in route} if route else set())
            cs = {h["via"] for h in route} if route else set()
            # Paths carry destinations but not their source. Include the
            # declared source endpoint without pulling in all candidate classes.
            if route:
                first = self.ctx.properties[route[0]["property_local"]]
                cs.update(first.ranges if route[0].get("inverse") else first.domains)
            if route in kept_paths:
                route = None
            if not accept(cs, ps, route):
                dropped["critical"].append(name)
        for name in sorted(class_scores, key=lambda c: (
                c not in required_names, -class_scores[c], c)):
            if name not in kept_classes and not accept({name}, set()):
                dropped["critical"].append(name)
        for path in paths:
            if path in kept_paths:
                continue
            ps = {h["property_local"] for h in path}
            cs = {h["via"] for h in path}
            if not accept(cs, ps, path):
                dropped["paths"].append(path)
        for name in sorted(properties - kept_properties - set(dropped["critical"]),
                           key=lambda p: (-property_scores.get(p, 0), p)):
            accept(set(), {name})
        for name in sorted(classes - kept_classes):
            accept({name}, set())
        dropped["classes"] = sorted(classes - kept_classes)
        dropped["properties"] = sorted(properties - kept_properties)
        return text_for(kept_classes, kept_properties, kept_paths), kept_classes, kept_properties, kept_paths, dropped
