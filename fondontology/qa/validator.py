"""Whitelist Validator：candidate → valid/invalid（只判定，不解释语义）。

设计文档 v0.4 §1：Validator 的规则是“候选必须来自 Index 且类型匹配预期槽位”。
白名单集合 = index.class_iris / property_iris / code_iris / entity_iris。
"""
from __future__ import annotations

from .index import Candidate, OntologyIndex

_SLOT_KINDS = {
    "concept": ("class", "property"),
    "class": ("class",),
    "property": ("property",),
    "code": ("code",),
    "entity": ("entity",),
}


class WhitelistValidator:
    def __init__(self, index: OntologyIndex):
        self.index = index
        self.whitelist: dict[str, frozenset[str]] = {
            "class": index.class_iris,
            "property": index.property_iris,
            "code": index.code_iris,
            "entity": index.entity_iris,
        }

    def validate(self, candidate: Candidate, slot: str = "concept") -> tuple[bool, str]:
        """判定候选是否合法。返回 (ok, reason)。"""
        allowed = _SLOT_KINDS.get(slot)
        if allowed is None:
            return False, f"未知槽位 {slot!r}"
        if candidate.kind not in allowed:
            return False, f"候选类型 {candidate.kind} 不匹配槽位 {slot}"
        whitelist = self.whitelist.get(candidate.kind, frozenset())
        if candidate.iri not in whitelist:
            return False, f"{candidate.iri} 不在 {candidate.kind} 白名单中"
        return True, "ok"

    def validate_iris(self, iri: str, slot: str = "concept") -> tuple[bool, str]:
        allowed = _SLOT_KINDS.get(slot, ())
        for kind in allowed:
            if iri in self.whitelist.get(kind, frozenset()):
                return True, "ok"
        return False, f"{iri} 不在槽位 {slot} 白名单中"