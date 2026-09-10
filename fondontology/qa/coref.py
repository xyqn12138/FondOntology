# -*- coding: utf-8 -*-
"""指代消解（M7-R4.5b，v2：LLM 改写器，无规则词典）。

v1 曾用代词词典+类型路由做规则替换，实测暴露两个问题：
① 代词形态与实体类型的匹配表是又一层"写死"，复杂指代（这家公司/
   那只/他们管的产品）覆盖不住；② 上文多实体时规则路由易错。
架构原则回归：语义理解交给 LLM，确定性代码只做护栏。

职责单一化为"自包含改写"：
- 输入：上文最近一轮（问题+答案+话题实体）+ 当前问句；
- LLM 判断问句是否自包含；不是则改写为自包含问句（代词/省略/任意
  指代形态均由 LLM 理解，无词典）；
- 唯一护栏：保真检查（原问实词 2-gram 60% 须保留），防 LLM 改写
  偷换语义；越界弃用原句走正常链路。

无上文 → 直通（零成本）。无 key → 直通（不消解，交 LLM 意图主判
自行理解——主判模型看着同一个上文也能兜住，双保险）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CorefResult:
    question: str            # 改写后的问题（不改写时 == 原文）
    resolved: bool
    method: str = ""         # llm | ""
    entity: str = ""         # LLM 标注的指代对象（展示用）


def resolve_coreference(question: str, index, context: Optional[dict],
                        *, use_llm: Optional[bool] = None) -> CorefResult:
    """有上文的问题 → LLM 改写为自包含问句。

    context: {"last_question","last_answer","last_entities"}。
    无上文 / 未配置 LLM / 改写失败或越界 → 原样返回（resolved=False）。
    """
    if not context or not (context.get("last_question") or context.get("last_answer")):
        return CorefResult(question=question, resolved=False)
    from .config import llm_configured
    if use_llm is False or not llm_configured():
        return CorefResult(question=question, resolved=False)

    rewritten, entity = _llm_rewrite(question, context)
    if not rewritten or rewritten == question:
        return CorefResult(question=question, resolved=False)
    if not _faithful(question, rewritten):
        # 改写偷换了问题主干（如 持仓→业绩）→ 弃用，原句交主判链路
        return CorefResult(question=question, resolved=False)
    return CorefResult(question=rewritten, resolved=True,
                       method="llm", entity=entity)


def _llm_rewrite(question: str, context: dict) -> tuple[Optional[str], str]:
    """LLM 自包含改写。返回 (改写问句, 指代对象标注)；失败 (None, "")。

    失败原因透传 intent._LAST_LLM_ERROR（UI 出错时可定位到 coref 层，
    与意图层的失败记录同机制）。
    """
    import fondontology.qa.intent as _im
    from .intent import _stream_chat_content
    last_q = context.get("last_question") or ""
    last_a = (context.get("last_answer") or "")[:600]
    ents = "、".join(e for e in (context.get("last_entities") or []) if e)
    prompt = (
        "你是多轮对话的问题改写器。判断当前问题是否自包含（不看上文也能理解）；"
        "若包含代词（它/他/这家公司/那只…）、省略主语或其他指代，"
        "改写为自包含的完整问题。\n"
        f"上文问题：{last_q}\n"
        f"上文回答（节选）：{last_a}\n"
        + (f"上文涉及对象：{ents}\n" if ents else "")
        + f"当前问题：{question}\n"
        "规则：只消解指代与省略，保持问题其余部分（问什么）原样；"
        "问题已自包含时 rewritten 填原问题。\n"
        '输出 JSON：{"rewritten": "<改写后的问题>", "refers_to": "<指代对象，无则空串>"}'
    )
    content = _stream_chat_content(prompt, temperature=0, max_attempts=1)
    if content is None:
        _im._LAST_LLM_ERROR = f"coref 改写调用失败（{_im._LAST_LLM_ERROR or '未知'}）"
        return None, ""
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        _im._LAST_LLM_ERROR = "coref 改写输出非 JSON"
        return None, ""
    try:
        data = json.loads(content[start:end + 1])
        return (str(data.get("rewritten") or "").strip(),
                str(data.get("refers_to") or "").strip())
    except Exception:
        _im._LAST_LLM_ERROR = "coref 改写输出解析失败"
        return None, ""


def _faithful(original: str, rewritten: str) -> bool:
    """保真检查：改写句须保留原问的实词主干（2-gram 60% 重叠）。

    护栏而非理解器：只拦"偷换问题语义"（持仓→业绩），不判断改写对错。
    """
    stop = ("是什么", "怎么样", "有哪些", "什么", "怎么", "哪些", "吗", "呢",
            "还有", "别的", "其他")
    body = original
    for s in stop:
        body = body.replace(s, "")
    # 代词/指示词也剔除（这部分本就该被替换）
    body = re.sub(r"[它他她这那该公司产品的只个位]+", "", body)
    grams = {body[i:i + 2] for i in range(len(body) - 1)} if len(body) >= 2 else set()
    if not grams:
        return True
    kept = sum(1 for g in grams if g in rewritten)
    return kept >= max(1, int(len(grams) * 0.6))
