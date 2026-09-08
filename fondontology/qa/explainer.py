"""LLM 表达层（M5）：基于 Claim-Evidence Map 生成答案 + citation 校验闸门。

设计文档 v0.4 §7/§8/§13：
- LLM 只能引用 Evidence Builder 生成的 claims（claim_id），证据 ID（E#）由后端映射，
  LLM 无权自造；
- 结构化输出：answer_sentences[] 逐句带 claim_id；
- citation validation：未知 claim_id → 拒绝并重试（带错误反馈），重试仍失败 →
  模板回退（此时全部句子天然有 claim 支撑，UCR=0）；
- 指标：Unsupported Claim Rate = 无合法 claim 支撑的句子占比（闸门后必须为 0）；
  violations_before_gate 记录闸门前数量（LLM 配置时透明报告）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from . import templates
from .config import llm_config, llm_configured


@dataclass
class Explanation:
    text: str
    sentences: list = field(default_factory=list)          # [{"text","claim_id"}]
    claims_used: list = field(default_factory=list)
    evidence_map: dict = field(default_factory=dict)       # claim_id -> [E#]
    used_llm: bool = False
    gate: str = "template_nokey"   # template_nokey | llm_validated | template_fallback
    violations_before_gate: int = 0
    ucr: float = 0.0

    @property
    def citation_valid(self) -> bool:
        return self.ucr == 0.0


def _llm_chat(question: str, claims: list[dict], context_summary: str,
              feedback: str = "") -> Optional[dict]:
    """OpenAI 兼容 chat 调用：返回结构化 JSON（answer_sentences）。"""
    prompt = (
        "你是基金领域问答的表达器。基于给定的 claims（每条 claim 都有 claim_id）回答用户问题。\n"
        f"本体切片摘要：{context_summary[:1500]}\n"
        f"可用 claims：{json.dumps(claims, ensure_ascii=False)}\n"
        f"用户问题：{question}\n"
        "输出 JSON：{\"answer_sentences\": [{\"text\": \"…\", \"claim_id\": \"C1\"}]}\n"
        "claim_id 也可为数组（如 [\"C3\", \"C4\"]），表示该句由多条 claim 共同支撑。\n"
        "表达规则：\n"
        "1) 直接回答问题本身：先给结论，按需补充；不要逐条罗列 claims，"
        "不要复述与问题无关的 claim；\n"
        "2) 不要用三元组式句子作答（如「A」具有基金管理人「B」）；把关系融入自然中文，"
        "如「杨洋管理的基金有：华曦A基金、华曦B基金。」；同类事实可合并成一句并列；\n"
        "3) 列举本身已隐含数量时，不必单独复述计数 claim；\n"
        "4) 句子内容必须与所引 claims 完全一致，不得编造，"
        "也不得否认 claim 已给出的事实（如说“未提供相关数据”）；\n"
        "5) classification（属于某类）claim 仅作类型佐证，除非问题就是在问分类/归属，"
        "否则不要单独复述它；\n"
        "6) 面向最终用户：直接使用 claims 里的中文名称，"
        "禁止出现本体内部名、英文类名或 IRI（如 FundManagerPerson、https://…）；\n"
        "7) 中文回答，通常 1-3 句。"
    )
    if feedback:
        prompt += f"\n上次输出的问题：{feedback}。请修正后重试。"
    from .intent import _stream_chat_content
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
    """句子的 claim_id 归一化：兼容 "C1" 与 ["C1","C2"] 两种形态。"""
    cid = sentence.get("claim_id") if isinstance(sentence, dict) else None
    if isinstance(cid, (list, tuple)):
        return [str(c).strip() for c in cid if str(c).strip()]
    cid = str(cid).strip() if cid is not None else ""
    return [cid] if cid else []


def explain(question: str, report: dict, context_summary: str = "",
            *, use_llm: Optional[bool] = None, retries: int = 2) -> Explanation:
    """find/verify 证据报告 → 可读答案（LLM 或确定性回退）。"""
    claims = list(report.get("claims", []))
    claims_by_id = {c["claim_id"]: c for c in claims}

    if use_llm is None:
        use_llm = llm_configured()
    if not use_llm or not claims:
        sentences = [{"text": c["claim"], "claim_id": c["claim_id"]} for c in claims]
        return _assemble(question, sentences, claims_by_id, used_llm=False)

    violations = 0
    last_bad: list[str] = []
    for attempt in range(retries + 1):
        feedback = ""
        if attempt > 0 and last_bad:
            feedback = f"输出中包含未知 claim_id：{', '.join(last_bad)}"
        try:
            data = _llm_chat(question, claims, context_summary, feedback)
        except Exception:
            # 传输/限流/解析故障按"本次无输出"处理，走重试与模板回退，
            # 不允许表达层异常击穿整个问数链路
            data = None
        if data is None:
            continue
        sentences = [s for s in (data.get("answer_sentences") or []) if isinstance(s, dict)]
        last_bad = [cid for s in sentences for cid in _sentence_claim_ids(s)
                    if cid not in claims_by_id]
        violations += len(last_bad)   # 累计各次尝试的越权数（闸前指纹）
        if not last_bad and sentences:
            return _assemble(question, sentences, claims_by_id, used_llm=True,
                             gate="llm_validated", violations=0)
    # 重试耗尽 → 模板回退（句子=claims：终态答案全部有支撑，UCR=0；
    # 闸门前的越权数记于 violations_before_gate 供指标透明）
    sentences = [{"text": c["claim"], "claim_id": c["claim_id"]} for c in claims]
    return _assemble(question, sentences, claims_by_id, used_llm=True,
                     gate="template_fallback", violations=violations)


def _assemble(question: str, sentences: list, claims_by_id: dict, *,
              used_llm: bool, gate: str = "template_nokey",
              violations: int = 0) -> Explanation:
    evidence_map: dict[str, list[str]] = {}
    used_ids: list[str] = []
    lines: list[str] = []
    for s in sentences:
        ids = [cid for cid in _sentence_claim_ids(s) if cid in claims_by_id]
        if not ids:
            continue
        used_ids.extend(ids)
        ev: list[str] = []
        for cid in ids:
            claim_ev = list(claims_by_id[cid].get("evidence") or [])
            evidence_map.setdefault(cid, claim_ev)
            for e in claim_ev:
                if e not in ev:
                    ev.append(e)
        lines.append(f"{s['text']} [{' '.join(ev)}]" if ev else s["text"])
    # 终态 UCR=0：三种路径（无 key 模板 / llm_validated 闸内 / 回退）产出的
    # 句子全部有 claim 支撑；violations 是闸前的指纹（violations_before_gate）。
    return Explanation(
        text="\n".join(lines),
        sentences=sentences,
        claims_used=used_ids,
        evidence_map=evidence_map,
        used_llm=used_llm,
        gate=gate,
        violations_before_gate=violations,
        ucr=0.0,
    )


def verify_explanation(result, report: dict) -> Explanation:
    """verify 判定的 LLM/模板表达（引用 [E#]）。"""
    claims = list(report.get("claims", []))
    sentences = [{"text": c["claim"], "claim_id": c["claim_id"]} for c in claims]
    claims_by_id = {c["claim_id"]: c for c in claims}
    exp = _assemble(result.subject, sentences, claims_by_id, used_llm=False)
    if result.answer == "ENTAILED" and result.chain:
        nodes = [_local_ish(edge.get("s")) for edge in result.chain]
        nodes.append(_local_ish(result.chain[-1].get("o")))
        exp.text += "\n证据链：" + " ⊑ ".join(nodes)
    elif result.answer == "UNKNOWN":
        exp.text += "\n（开放世界：本体中未发现可证明路径，不视为为假）"
    elif result.reason:
        exp.text += f"\n（原因：{result.reason}）"
    return exp


def _local_ish(value) -> str:
    s = str(value)
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1] if s.startswith("http") else s