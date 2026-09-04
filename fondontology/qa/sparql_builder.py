"""SPARQL Builder：QueryPlan → SPARQL（纯函数，LLM 永不生成 SPARQL）。

设计文档 v0.4 §10：每个算子（type closure / filter / traversal / projection /
ordering / pagination）独立可单测。输出用完整 IRI（尖括号形式），不依赖前缀绑定。

语义 IR v1 source 槽位（锚点模式）：根为固定 IRI，沿 traversals 走到结果变量
（锚点模式的最后一跳），类型闭包/过滤/排除/投影/排序全部作用于结果变量。
"""
from __future__ import annotations

_RDF_TYPE = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
_RDFS_SUBCLASS = "<http://www.w3.org/2000/01/rdf-schema#subClassOf>"
_RDFS_LABEL = "<http://www.w3.org/2000/01/rdf-schema#label>"


def _iri(uri: str) -> str:
    return f"<{uri}>"


def _like_iri(value: str) -> bool:
    return "://" in value


def build_select(plan: dict) -> str:
    """find 计划 → SELECT DISTINCT <结果变量> WHERE { … }。"""
    src = (plan.get("source") or {}).get("entity")
    hops = plan.get("traversals") or []
    result_var = f"?h{len(hops)}" if (src and hops) else "?entity"

    lines = [f"SELECT DISTINCT {result_var} WHERE {{"]

    target = plan.get("target", {}).get("concept")
    if target:
        # rdf:type/rdfs:subClassOf* —— 类型闭包（M2 用显式图即可，无需物化闭包）
        lines.append(f"  {result_var} {_RDF_TYPE}/{_RDFS_SUBCLASS}* {_iri(target)} .")

    # traversals：逐跳链；锚点模式根为固定 IRI，普通模式根为结果变量
    prev = f"<{src}>" if src else result_var
    for i, trav in enumerate(hops, start=1):
        var = f"?h{i}"
        prop = _iri(trav['property'])
        if trav.get("inverse"):
            lines.append(f"  {prev} ^{prop} {var} .")
        else:
            lines.append(f"  {prev} {prop} {var} .")
        prev = var
        flt = trav.get("filter")
        if flt and flt.get("kind") == "label" and flt.get("value"):
            # 标签带语言标记（@zh），需 STR() 比较
            lbl = f"?lbl{i}"
            lines.append(f"  {var} {_RDFS_LABEL} {lbl} .")
            lines.append(f"  FILTER(STR({lbl}) = {flt['value']!r})")
        elif flt and flt.get("kind") == "iri" and flt.get("value"):
            lines.append(f"  {var} {_iri(flt['value'])} .")

    # filters：对象属性值给 IRI 则做三元组模式，否则做字面量 FILTER；in 支持列表
    for i, f in enumerate(plan.get("filters") or []):
        prop, value = f["property"], f.get("value", "")
        if isinstance(value, list):
            var = f"?v{i}"
            lines.append(f"  {result_var} {_iri(prop)} {var} .")
            rendered = [(_iri(v) if _like_iri(v) else repr(v)) for v in value]
            lines.append(f"  FILTER({var} IN ({', '.join(rendered)}))")
            continue
        if _like_iri(value):
            lines.append(f"  {result_var} {_iri(prop)} {_iri(value)} .")
        else:
            var = f"?v{i}"
            lines.append(f"  {result_var} {_iri(prop)} {var} .")
            if f.get("operator", "eq") == "eq":
                lines.append(f"  FILTER({var} = {value!r})")
            else:
                lines.append(f"  FILTER({var} {f.get('operator')} {value!r})")

    # projections（可选绑定；SELECT 仍以结果变量为主键）
    for i, prop in enumerate(plan.get("projections") or []):
        lines.append(f"  OPTIONAL {{ {result_var} {_iri(prop)} ?p{i} }}")

    # exclusions：实体显式排除（"其他/除外/不包括"）
    for exc in plan.get("exclusions") or []:
        lines.append(f"  FILTER({result_var} != {_iri(exc)})")

    lines.append("}")

    # ordering：默认按结果变量稳定排序；支持指定属性（需其在 projections 中）
    order_by = []
    for o in plan.get("ordering") or []:
        prop = o.get("property")
        pidx = None
        for i, p in enumerate(plan.get("projections") or []):
            if p == prop:
                pidx = i
                break
        if pidx is not None:
            order_by.append(f"?p{pidx}" + (" DESC" if o.get("direction") == "desc" else ""))
    if not order_by:
        order_by.append(result_var)
    lines.append("ORDER BY " + " ".join(order_by))

    pag = plan.get("pagination") or {}
    if pag.get("limit"):
        lines.append(f"LIMIT {int(pag['limit'])}")
    if pag.get("offset"):
        lines.append(f"OFFSET {int(pag['offset'])}")

    return "\n".join(lines)