"""Vocabulary Resolver：string → candidates（确定性检索，不判断对错）。

设计文档 v0.4 §1：Resolver 只做检索；判定（合法/非法）归 Validator，
语义解释归 Compiler。命中顺序：IRI → local name → label/pref/alt 精确 →
代码 → 子串（中文按最长命中加分）→ 受控归一化（实体，碰撞标记）。
"""
from __future__ import annotations

from .index import Candidate, OntologyIndex, _local, _normalize_name

# 子串命中的基础分与按命中长度占比的加成；精确类命中为 1.0
_CONTAINS_BASE = 0.5
_CONTAINS_BONUS_COEF = 0.3
_VIABLE_THRESHOLD = 0.6


class VocabularyResolver:
    def __init__(self, index: OntologyIndex):
        self.index = index

    def search(self, text: str, limit: int = 12) -> list[Candidate]:
        """全类型检索（概念+代码+实体），按 score 降序。"""
        text = (text or "").strip()
        if not text:
            return []
        found: list[Candidate] = []
        found.extend(self.resolve_concept(text, limit=limit))
        found.extend(self.resolve_code(text, limit=limit))
        found.extend(self.resolve_entity(text, limit=limit))
        found.sort(key=lambda c: c.score, reverse=True)
        return found[:limit]

    def resolve_concept(self, text: str, limit: int = 12) -> list[Candidate]:
        """类/属性候选（本体词汇）。"""
        idx = self.index
        out: list[Candidate] = []
        if "://" in text:
            c = idx.classes.get(text) or idx.object_properties.get(text) or idx.datatype_properties.get(text)
            if c is not None:
                kind = ("class" if text in idx.class_iris else "property")
                out.append(Candidate(text, kind, c, "iri", 1.0))
                return out
        # local name（CNFO 类/属性）
        for u in idx.class_iris:
            if _local(u) == text:
                out.append(Candidate(u, "class", idx.classes[u], "local_name", 0.95))
                break
        else:
            for u in idx.property_iris:
                if _local(u) == text:
                    out.append(Candidate(u, "property", idx.object_properties.get(u)
                                         or idx.datatype_properties.get(u) or _local(u),
                                         "local_name", 0.95))
                    break
        # 标签精确
        for hit, iri_list in idx._concept_labels.items():
            if hit != text:
                continue
            for iri in iri_list:
                kind = "class" if iri in idx.class_iris else "property"
                label = idx.classes.get(iri) or idx.object_properties.get(iri) \
                    or idx.datatype_properties.get(iri) or hit
                if any(c.iri == iri for c in out):
                    continue
                out.append(Candidate(iri, kind, label, "label", 1.0))
        # 中文子串（按命中长度占比加成，避免“基金”吞掉“基金中基金”）
        if not out:
            for label, iri_list in idx._concept_labels.items():
                if label in text and isinstance(label, str) and label:
                    bonus = _CONTAINS_BONUS_COEF * len(label) / max(len(text), 1)
                    score = _CONTAINS_BASE + bonus
                    for iri in iri_list:
                        kind = "class" if iri in idx.class_iris else "property"
                        lbl = idx.classes.get(iri) or idx.object_properties.get(iri) \
                            or idx.datatype_properties.get(iri) or label
                        if any(c.iri == iri for c in out):
                            continue
                        out.append(Candidate(iri, kind, lbl, "contains", round(score, 4)))
        out.sort(key=lambda c: c.score, reverse=True)
        return out[:limit]

    def resolve_code(self, text: str, limit: int = 6) -> list[Candidate]:
        """CNFC 代码值候选（label 精确/子串）。"""
        out: list[Candidate] = []
        for iri, meta in self.index.codes.items():
            label = meta["label"]
            if label == text:
                out.append(Candidate(iri, "code", label, "label", 1.0, {"scheme": meta["scheme"]}))
            elif label in text and label:
                bonus = _CONTAINS_BONUS_COEF * len(label) / max(len(text), 1)
                out.append(Candidate(iri, "code", label, "contains", round(_CONTAINS_BASE + bonus, 4),
                                     {"scheme": meta["scheme"]}))
        out.sort(key=lambda c: c.score, reverse=True)
        return out[:limit]

    def resolve_entity(self, text: str, limit: int = 8) -> list[Candidate]:
        """ABOX 实体候选：代码精确 → 标签精确 → 受控归一化（碰撞标记）。"""
        out: list[Candidate] = []
        for code, iri_list in self.index._entity_codes.items():
            if code == text:
                for iri in iri_list:
                    out.append(Candidate(iri, "entity", self.index.entities[iri]["label"],
                                         "code", 1.0, {"code": code}))
        if not out:
            for iri, meta in self.index.entities.items():
                if meta["label"] == text:
                    out.append(Candidate(iri, "entity", meta["label"], "label", 0.95))
        if not out:
            norm = _normalize_name(text)
            if norm:
                hits = self.index._entity_norm.get(norm, [])
                for iri in hits:
                    collision = len(hits) > 1
                    out.append(Candidate(iri, "entity", self.index.entities[iri]["label"],
                                         "normalized", 0.6, {"collision": collision}))
        out.sort(key=lambda c: c.score, reverse=True)
        return out[:limit]

    def viable(self, candidates: list[Candidate]) -> list[Candidate]:
        """≥ 阈值的候选（供 resolution 使用；confidence 仅展示，不参与判定）。"""
        return [c for c in candidates if c.score >= _VIABLE_THRESHOLD]