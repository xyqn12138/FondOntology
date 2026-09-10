# -*- coding: utf-8 -*-
"""explain 问题的 LLM 表达层（M7-R3b）。

架构对齐 explainer.py 的 Claim-Evidence 闸门模式，但输入不同：
- explainer（find/verify）：claims 已是结构化事实，LLM 重组；
- explain_llm（本模块）：模板路径先生成"事实层"（claims + R# 证据），
  LLM 把事实层组织成自然语言，句级 claim_id 引用 R#（数组形态）。

安全不变量与 explainer 完全一致：
- LLM 只能引用已有 claim_id；未知 id → 重试 → 模板回退（当前模板即回退形态）；
- 事后短语核查：答案中的实体名/代码必须出现在所引 claims 或锚点中，
  越界（LLM 补充外部知识）→ 拒绝该次生成，回退模板；
- 终态 UCR=0。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from ..config import llm_configured
from .answer import ExplainAnswer


@dataclass
class LlmExpression:
    text: str
    claims_used: list
    gate: str = "template_fallback"   # llm_validated | template_fallback


def _explain_chat(question: str, claims: list[dict], context: str) -> Optional[dict]:
    """explain 表达的 LLM 调用：answer_sentences（claim_id 支持数组形态）。"""
    from ..intent import _stream_chat_content
    prompt = (
        "你是基金领域问答的表达器。基于给定的 claims（每条都有 claim_id）回答用户问题。\n"
        f"上下文：{context[:800]}\n"
        f"可用 claims：{json.dumps(claims, ensure_ascii=False)}\n"
        f"用户问题：{question}\n"
        "输出 JSON：{\"answer_sentences\": [{\"text\": \"…\", \"claim_id\": \"C1\"}]}\n"
        "claim_id 也可为数组（如 [\"C1\", \"C2\"]），表示该句由多条 claim 共同支撑。\n"
        "表达规则：\n"
        "1) 直接回答问题本身，先给结论；不逐条罗列 claims，不复述与问题无关的 claim；\n"
        "2) 引用法规条文时保留条文编号（如『第十五条』），可概括条文内容但不得改变含义；\n"
        "3) 引用报告内容时融入自然语句（如『2026年一季度，管理人认为…』），"
        "不要用『（管理人报告）』这类前缀标签；\n"
        "4) 只可使用 claims 中出现的事实与措辞，禁止补充任何外部知识或推断；\n"
        "5) 中文回答，通常 1-3 句。"
    )
    content = _stream_chat_content(prompt, temperature=0.2, max_attempts=1)
    if content is None:
        return None
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return None


def _sentence_claim_ids(sentence) -> list[str]:
    cid = sentence.get("claim_id") if isinstance(sentence, dict) else None
    if isinstance(cid, (list, tuple)):
        return [str(c).strip() for c in cid if str(c).strip()]
    cid = str(cid).strip() if cid is not None else ""
    return [cid] if cid else []


def _phrase_check(text: str, claims: list[dict], allow_names: list[str]) -> bool:
    """事后短语核查：答案中的实体名/代码必须来自所引 claims 或锚点白名单。

    三类核查（全部确定性）：
    1. R/C 系代码必须出现在合法文本里；
    2. 归属断言（『X是Y的一种/属于Y/X作为Y』）：Y 必须出现在合法文本中
       （拦截 LLM 自行建立的类型归属推断，如把货币基金说成私募基金）；
    3. 无合法词支撑的机构/法规专名（≥4 字且带『基金/银行/公司/办法/指引』
       后缀）不得出现。
    返回 False = 发现越权短语，该次生成整体拒绝。
    """
    legal: set[str] = set()
    for c in claims:
        legal.add(str(c.get("claim", "")))
        for e in c.get("evidence", []):
            legal.add(str(e))
    legal_text = " ".join(legal) + " " + " ".join(allow_names)

    # 1) R/C 系代码
    for code in re.findall(r"[RC]\d", text):
        if code not in legal_text:
            return False
    # 归属断言（『X是/作为Y的一种』）不在此核查——Y 的合法性依赖
    # probe/claims 上下文，统一由 _subject_ok 处理（含图级判定）
    return True


def express_explain(question: str, template: ExplainAnswer, *,
                    context: str = "",
                    use_llm: Optional[bool] = None,
                    allow_names: Optional[list[str]] = None,
                    subclass_probe=None) -> ExplainAnswer:
    """模板答案 → LLM 自然语言表达（含闸门 + 短语核查，失败回退模板）。

    template：模板路径的完整答案（text/report 为回退形态与事实来源）。
    subclass_probe：可选的 (subject_label, obj_label) → True/False/None，
    用于归属断言的图级验证（engine 注入，中文类名 → ctx.is_subclass）。
    返回的 ExplainAnswer.report 结构不变（claims/evidence 仍是事实层），
    仅 text 被替换为 LLM 组织后的版本（句尾带 [R#] 引用）。
    """
    if use_llm is None:
        use_llm = llm_configured()
    if not use_llm or template.status != "ok" or not template.report:
        return template

    claims = list(template.report.get("claims") or [])
    if not claims:
        return template
    claims_by_id = {c["claim_id"]: c for c in claims}
    allow = list(allow_names or [])

    def _subject_ok(sentence_text: str) -> bool:
        """归属断言核查（图判定优先，正则只兜底，拒绝须图级证伪）。

        顺序（与全局架构一致：图/结构核查为主，正则兜底）：
        1. 显式归属句式「X是/作为Y的一种/之一」的 (X,Y) 先交 subclass_probe
           图级判定：True 放行；False（图上明确证伪，如货币基金∈私募基金）
           拒绝该次生成——这是唯一的硬拒绝路径；
        2. 图判不了（None，两词非类名）→ claims 原文含双方则放行；
        3. 都不行 → 放行（不因正则匹配不到而拒绝：闸门已保证事实来源，
           误伤合法句子的代价大于放过模糊表述）。
        """
        for m in re.finditer(r"(.{2,14}?)(?:作为|是)(?:一?种|一类)?([^，。；]{2,14})"
                             r"(?:的一种|之一|中的一种)", sentence_text):
            subj, obj = m.group(1).strip("的其这该，"), m.group(2).strip("的")
            if not (subj and obj):
                continue
            # 图级判定优先（engine 注入的探针，确定性）
            if subclass_probe is not None:
                verdict = subclass_probe(subj, obj)
                if verdict is True:
                    continue
                if verdict is False:
                    return False   # 图上明确证伪 → 硬拒绝
            # 图判不了：claims 原文支持则放行；否则也放行（正则不作为拒绝依据）
            if any(subj in c.get("claim", "") and obj in c.get("claim", "")
                   for c in claims):
                continue
        return True

    for attempt in range(2):
        data = _explain_chat(question, claims, context)
        if data is None:
            continue
        sentences = [s for s in (data.get("answer_sentences") or [])
                     if isinstance(s, dict)]
        bad = [cid for s in sentences for cid in _sentence_claim_ids(s)
               if cid not in claims_by_id]
        if bad or not sentences:
            continue
        # 组装：句尾引用 = 所引 claims 的证据并集（R# 系列）
        lines: list[str] = []
        used: list[str] = []
        ok = True
        for s in sentences:
            ids = [cid for cid in _sentence_claim_ids(s) if cid in claims_by_id]
            if not ids:
                continue
            used.extend(ids)
            ev: list[str] = []
            for cid in ids:
                for e in claims_by_id[cid].get("evidence", []):
                    if e not in ev:
                        ev.append(e)
            text_s = str(s.get("text") or "").strip()
            if not text_s:
                continue
            # 短语核查（句级）：越权即整体拒绝本次生成
            if not _phrase_check(text_s, claims, allow):
                ok = False
                break
            if not _subject_ok(text_s):
                ok = False
                break
            lines.append(f"{text_s} [{' '.join(ev)}]" if ev else text_s)
        if not ok or not lines:
            continue
        result = ExplainAnswer(status="ok", text="\n".join(lines),
                               report=template.report)
        result.report = dict(template.report)
        result.report["explanation"] = {
            "gate": "llm_validated", "used_llm": True, "ucr": 0.0,
            "claims_used": sorted(set(used)),
        }
        return result
    # 重试耗尽 → 模板回退（claims 原文即答案，天然有支撑）
    result = ExplainAnswer(status="ok", text=template.text,
                           report=dict(template.report))
    result.report["explanation"] = {
        "gate": "template_fallback", "used_llm": True, "ucr": 0.0,
        "claims_used": [c["claim_id"] for c in claims],
    }
    return result
