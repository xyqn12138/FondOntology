"""确定性答案模板（M3）：无 LLM 也可完整作答；LLM 接入（M4/M5）只替换表达层。

模板产出中文可读答案 + 证据引用（[E#]），全部内容来自 Evidence Report，
不引入任何未取证的内容。
"""
from __future__ import annotations

from .evidence import zh_label


def render_find(report: dict, slice_: dict | None = None) -> str:
    lines: list[str] = []
    claims = report.get("claims", [])
    c1 = next((c for c in claims if c.get("type") == "count"), None)
    if c1:
        lines.append(f"{c1['claim']} [{' '.join(c1.get('evidence', []))}]")
    c2 = next((c for c in claims if c.get("type") == "fact"), None)
    if c2:
        lines.append(f"{c2['claim']} [{' '.join(c2.get('evidence', []))}]")
    for c in claims:
        if c.get("type") == "classification":
            lines.append(f"- {c['claim']} [{' '.join(c.get('evidence', []))}]")
    lines.append("")
    lines.append("（答案由确定性模板生成，所有陈述均已取证；尚未使用 LLM。）")
    if slice_ and slice_.get("truncated"):
        lines.append("（注：本体切片因预算截断，后端证据完整。）")
    return "\n".join(lines)


def render_verify(result) -> str:
    verdict = result.answer
    zh = {
        "ENTAILED": "可以证明成立",
        "CONTRADICTED": "与本体声明冲突（不成立）",
        "UNKNOWN": "本体中不能证明为真（开放世界：不视为为假）",
        "INVALID_REQUEST": "请求无效",
    }
    head = f"「{result.subject}」{_rel(result.relation)}「{result.object}」：{zh.get(verdict, verdict)}"
    if verdict == "INVALID_REQUEST":
        return f"{head}（原因：{result.reason or '未知'}）"
    lines = [head]
    if result.chain:
        for edge in result.chain:
            lines.append(f"  {_s(edge.get('s'))} --{edge.get('p', '')}--> {_s(edge.get('o'))}")
    if result.note:
        lines.append(f"（提示：{result.note}）")
    lines.append("（答案由确定性 T-BOX 判链生成，未使用 LLM。）")
    return "\n".join(lines)


def render_invalid(reasons: list[str]) -> str:
    return "请求无法编译为有效查询（INVALID_REQUEST）：\n" + "\n".join(f"  - {r}" for r in reasons)


def _rel(relation: str) -> str:
    return {
        "subClassOf": "是…的子类",
        "equivalentClass": "与…等价",
        "disjointWith": "与…互斥",
        "subPropertyOf": "是…的子属性",
        "domainOf": "是…的 domain",
        "rangeOf": "是…的 range",
    }.get(relation, relation)


def _s(v) -> str:
    if v is None:
        return ""
    s = str(v)
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1] if s.startswith("http") else s