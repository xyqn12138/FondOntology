"""问题驱动的本体局部上下文检索。

第一版只使用确定性词法匹配和 OntologyContext 的关系图：
- 从问题中召回类、对象属性、数据属性和实体类型；
- 为召回概念补齐必要的父类、domain/range 和关系路径；
- 只渲染当前问题相关的本体子图，并设置字符预算。

完整 T-BOX 仍由 planner 使用，本模块只控制送入 LLM 的上下文大小。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .index import OntologyIndex
from .resolver import VocabularyResolver, _TYPE_SYNONYMS
from .semantics import OntologyContext


_GENERIC_LABELS = frozenset({"基金", "对象", "记录", "数据", "信息"})
_TYPE_HINTS = (
    ("基金经理", "FundManagerPerson"),
    ("基金管理人", "FundManagerPerson"),
    ("经理", "FundManagerPerson"),
    ("基金", "Fund"),
)
_PROPERTY_HINTS = (
    (("管理", "经理"), "hasFundManager"),
    (("托管", "托管人"), "hasFundDepositary"),
    (("策略", "主题", "行业", "投资方向", "投资重点", "医药", "消费", "科技"),
     "investmentFocus"),
    (("风险", "R1", "R2", "R3", "R4", "R5"), "hasFundRiskLevel"),
)


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


def estimate_token_count(text: str) -> tuple[int, str]:
    """估算上下文 token 数；有 tiktoken 时使用 cl100k_base 精确计算。"""
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

    def __init__(self, index: OntologyIndex, *, max_chars: int = 10000):
        self.index = index
        self.ctx = OntologyContext.from_stack(index.stack)
        self.resolver = VocabularyResolver(index)
        self.max_chars = max_chars

    def retrieve(self, question: str,
                 context: Optional[dict] = None) -> SchemaContext:
        text = self._question_with_context(question, context)
        class_seeds: dict[str, float] = {}
        property_seeds: dict[str, float] = {}
        conditions: list[str] = []

        # 现有 resolver 负责精确标签、别名、同义词和实体候选。
        for candidate in self.resolver.search(text, limit=24):
            local = candidate.iri.rsplit("/", 1)[-1]
            if candidate.kind == "class" and local in self.ctx.classes:
                class_seeds[local] = max(class_seeds.get(local, 0.0),
                                         candidate.score)
            elif candidate.kind == "property" and local in self.ctx.properties:
                property_seeds[local] = max(property_seeds.get(local, 0.0),
                                            candidate.score)
            elif candidate.kind == "entity":
                for type_iri in self.index.entities.get(candidate.iri, {}).get("types", []):
                    type_local = type_iri.rsplit("/", 1)[-1]
                    if type_local in self.ctx.classes:
                        class_seeds[type_local] = max(
                            class_seeds.get(type_local, 0.0), candidate.score + 0.2)

        # resolver.search 以完整问题做匹配时可能错过问题中的短属性词，
        # 因此补一次逐概念词法扫描。低信息量的“基金”等词不单独触发扩展。
        self._scan_concepts(text, class_seeds, property_seeds)
        self._apply_hints(text, class_seeds, property_seeds)

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
        class_list = sorted(selected_classes,
                            key=lambda c: (-class_seeds.get(c, 0.0), c))
        seed_class_list = sorted(class_seeds,
                                 key=lambda c: (-class_seeds.get(c, 0.0), c))

        def add_paths(source: str, target: str,
                      preferred_property: Optional[str] = None,
                      exact_endpoint: bool = False) -> None:
            if source == target:
                return
            found = self.ctx.find_relation_paths(source, target,
                                                 max_hops=3, limit=24)
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
            for path in found[:4]:
                if not path:
                    continue
                paths.append(path)
                selected_properties.update(h["property_local"] for h in path)
                selected_classes.update(
                    h["via"] for h in path if h["via"] in self.ctx.classes)

        # 数据属性的 domain 是过滤真正落点；先补“目标类 -> domain”的路径。
        for prop_local in property_seeds:
            prop = self.ctx.properties.get(prop_local)
            if prop is None or prop.kind != "datatype":
                continue
            for domain in prop.domains:
                if domain not in self.ctx.classes:
                    continue
                for source in seed_class_list:
                    add_paths(source, domain, exact_endpoint=True)

        # 对象属性直接表达问题中的关系，优先保留它的 domain -> range 路径；
        # 对子类目标（如 EquityFund）再补一条从具体目标类出发的路径。
        for prop_local in property_seeds:
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

        # 没有直接命中关系词时，保留少量类间候选路径作为语义补充。
        if not property_seeds:
            for source in class_list:
                for target in class_list:
                    add_paths(source, target)

        # 路径的 domain/range 是约束信息，补入关系两端；避免只给一条裸属性。
        for prop_local in list(selected_properties):
            prop = self.ctx.properties.get(prop_local)
            if prop is None:
                continue
            selected_classes.update(d for d in prop.domains if d in self.ctx.classes)
            selected_classes.update(r for r in prop.ranges if r in self.ctx.classes)

        # 去重关系路径，保留短路径和较相关路径。
        paths = self._dedupe_paths(paths)
        rendered = self._render(
            question=question,
            classes=selected_classes,
            class_scores=class_seeds,
            properties=selected_properties,
            property_scores=property_seeds,
            paths=paths,
            conditions=conditions,
        )
        token_count, tokenizer = estimate_token_count(rendered)

        return SchemaContext(
            classes=sorted(selected_classes),
            properties=sorted(selected_properties),
            paths=paths,
            conditions=conditions,
            render_text=rendered,
            char_count=len(rendered),
            token_count=token_count,
            tokenizer=tokenizer,
            candidate_count=len(class_seeds) + len(property_seeds),
        )

    def _question_with_context(self, question: str,
                               context: Optional[dict]) -> str:
        if not context:
            return question or ""
        parts = [question or "", context.get("last_question") or "",
                 (context.get("last_answer") or "")[:300]]
        return "\n".join(p for p in parts if p)

    def _scan_concepts(self, text: str, class_seeds: dict[str, float],
                       property_seeds: dict[str, float]) -> None:
        for local, info in self.ctx.classes.items():
            terms = {local, info.label}
            for term in terms:
                if len(term) >= 3 and term not in _GENERIC_LABELS and term in text:
                    class_seeds[local] = max(class_seeds.get(local, 0.0), 0.82)
        for local, info in self.ctx.properties.items():
            terms = {local, info.label}
            for term in terms:
                if len(term) >= 3 and term not in _GENERIC_LABELS and term in text:
                    property_seeds[local] = max(property_seeds.get(local, 0.0), 0.80)

        # 复用已有受控类型同义词，不在这里维护第二套基金类型表。
        for phrase, local in _TYPE_SYNONYMS.items():
            if phrase in text and local in self.ctx.classes:
                class_seeds[local] = max(class_seeds.get(local, 0.0), 0.95)

    def _apply_hints(self, text: str, class_seeds: dict[str, float],
                     property_seeds: dict[str, float]) -> None:
        for phrase, local in _TYPE_HINTS:
            if phrase in text and local in self.ctx.classes:
                class_seeds[local] = max(class_seeds.get(local, 0.0), 0.72)
        for phrases, local in _PROPERTY_HINTS:
            if any(p in text for p in phrases) and local in self.ctx.properties:
                property_seeds[local] = max(property_seeds.get(local, 0.0), 0.72)

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
    def _dedupe_paths(paths: list[list[dict]]) -> list[list[dict]]:
        unique: dict[tuple, list[dict]] = {}
        for path in paths:
            key = tuple((h["property_local"], bool(h.get("inverse")),
                         h.get("via")) for h in path)
            unique[key] = path
        return sorted(unique.values(),
                      key=lambda p: (len(p),
                                     [h["property_local"] for h in p]))[:12]

    def _render(self, *, question: str, classes: set[str],
                class_scores: dict[str, float], properties: set[str],
                property_scores: dict[str, float],
                paths: list[list[dict]], conditions: list[str]) -> str:
        lines = [
            "【问题相关本体上下文】（仅为当前问题裁剪；local 名必须严格按此表使用）",
            f"问题：{question}",
            "",
            "【候选类】",
        ]
        for local in sorted(classes,
                            key=lambda c: (-class_scores.get(c, 0.0), c)):
            info = self.ctx.classes.get(local)
            if info is None:
                continue
            parent = "、".join(info.parents) if info.parents else "无"
            lines.append(f"{local}({info.label})；父类：{parent}")

        lines.extend(["", "【对象属性】"])
        for local in sorted(properties):
            prop = self.ctx.properties.get(local)
            if prop is None or prop.kind != "object":
                continue
            domains = "、".join(prop.domains) or "未声明"
            ranges = "、".join(prop.ranges) or "未声明"
            lines.append(f"{local}({prop.label})：{domains} -> {ranges}")

        lines.extend(["", "【数据属性】"])
        for local in sorted(properties):
            prop = self.ctx.properties.get(local)
            if prop is None or prop.kind != "datatype":
                continue
            domains = "、".join(prop.domains) or "未声明"
            ranges = "、".join(prop.ranges) or "未声明"
            lines.append(f"{local}({prop.label})：{domains} -> {ranges}")

        if paths:
            lines.extend(["", "【可用关系路径】"])
            for path in paths:
                hops = []
                for hop in path:
                    direction = "^" if hop.get("inverse") else ""
                    hops.append(f"{direction}{hop['property_local']} -> {hop['via']}")
                lines.append("；".join(hops))

        if conditions:
            lines.extend(["", "【问题中需要保留的条件词】", "、".join(conditions)])

        # 第一版采用字符预算，约 4 字符≈1 token；不截断单条关系/属性行。
        if len("\n".join(lines)) <= self.max_chars:
            return "\n".join(lines)
        mandatory = lines[:4]
        tail = lines[4:]
        kept: list[str] = []
        size = len("\n".join(mandatory))
        for line in tail:
            extra = len(line) + 1
            if size + extra > self.max_chars:
                continue
            kept.append(line)
            size += extra
        return "\n".join(mandatory + kept)
