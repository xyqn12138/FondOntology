"""Lexicon Resolver：自然语言归一化（确定性规则，不交给 LLM 推断）。

链：exact alias → 规则模式 →（Phase 2）BM25 → embedding → candidate → whitelist。
本文档规则命中后仍须经计划白名单（属性存在性）才会进入 QueryPlan。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .index import CNFC

_RISK_ORDER = ["FundRiskLevelR1", "FundRiskLevelR2", "FundRiskLevelR3",
               "FundRiskLevelR4", "FundRiskLevelR5"]


@dataclass(frozen=True)
class LexiconSpec:
    property_iri: str          # 归一化目标属性（合法 CNFO 属性 IRI 或 local name）
    operator: str              # eq | in | max_ordering 预留
    value: object              # IRI 串 / 字面量 / IRI 列表
    lexicon_source: str        # 命中的自然语言片段（溯源）


_RISK_PROP = "https://ontology.example.cn/cnfo/ontology/hasFundRiskLevel"
_JURIS_PROP = "https://ontology.example.cn/cnfo/ontology/jurisdictionCode"


def apply(text: str) -> list[LexiconSpec]:
    """对问题文本应用确定性归一化规则。"""
    specs: list[LexiconSpec] = []
    m = re.search(r"R([1-5])(以上|及以上|及以下|以下)?", text)
    if m:
        level = int(m.group(1))
        mode = m.group(2) or ""
        if mode in ("以上", "及以上"):
            codes = [CNFC + _RISK_ORDER[i] for i in range(level - 1, len(_RISK_ORDER))]
            specs.append(LexiconSpec(_RISK_PROP, "in", codes, m.group(0)))
        elif mode in ("以下", "及以下"):
            codes = [CNFC + _RISK_ORDER[i] for i in range(0, level)]
            specs.append(LexiconSpec(_RISK_PROP, "in", codes, m.group(0)))
        else:
            specs.append(LexiconSpec(_RISK_PROP, "eq", CNFC + f"FundRiskLevelR{level}", m.group(0)))
    if "国内" in text:
        specs.append(LexiconSpec(_JURIS_PROP, "eq", "CN", "国内"))
    return specs


def resolve(property_iri: str, tbox_graph) -> Optional[str]:
    """归一化结果过白名单：属性必须存在于本体，否则丢弃（返回 None）。"""
    if property_iri in set(tbox_graph.subjects(None, None)) or \
            any(str(s) == property_iri for s in tbox_graph.subjects(None, None)):
        return property_iri
    return None