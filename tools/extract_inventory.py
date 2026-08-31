"""Extract full inventory of CNFO ontology: classes, object props, datatype props + labels."""
import re
import sys
from collections import OrderedDict

import rdflib

NS = rdflib.Namespace("https://ontology.example.cn/cnfo/ontology/")


def main() -> None:
    g = rdflib.Graph()
    g.parse(r"E:\LX\LX_fund\FondOntology\ontology\cnfo-fund.ttl", format="turtle")
    g.parse(r"E:\LX\LX_fund\FondOntology\ontology\modules\cnfo-domain.ttl", format="turtle")

    out = []
    out.append("# CNFO 本体概念清单（类 / 对象属性 / 数据属性）")
    out.append("")

    classes = OrderedDict()
    objprops = OrderedDict()
    dataprops = OrderedDict()

    for s, p, o in g:
        if not str(s).startswith(str(NS)):
            continue
        if p == rdflib.RDF.type:
            if o == rdflib.OWL.Class:
                classes[str(s).replace(str(NS), "")] = None
            elif o == rdflib.OWL.ObjectProperty:
                objprops[str(s).replace(str(NS), "")] = None
            elif o == rdflib.OWL.DatatypeProperty:
                dataprops[str(s).replace(str(NS), "")] = None

    def label_of(entity):
        for o in g.objects(NS[entity], rdflib.RDFS.label):
            if getattr(o, "language", None) == "zh":
                return str(o)
        for o in g.objects(NS[entity], rdflib.RDFS.label):
            return str(o)
        return ""

    def altlabels_of(entity):
        return sorted({str(o) for o in g.objects(NS[entity], rdflib.SKOS.altLabel)})

    def parent_of(entity):
        for o in g.objects(NS[entity], rdflib.RDFS.subClassOf):
            if isinstance(o, rdflib.URIRef) and str(o).startswith(str(NS)):
                return str(o).replace(str(NS), "")
        return ""

    def domain_range(entity, is_obj):
        doms = [str(o).replace(str(NS), "") for o in g.objects(NS[entity], rdflib.RDFS.domain)]
        rngs = [str(o).replace(str(NS), "") for o in g.objects(NS[entity], rdflib.RDFS.range)]
        return doms, rngs

    out.append(f"## 类（{len(classes)}）")
    for name in sorted(classes):
        parent = parent_of(name)
        alts = altlabels_of(name)
        line = f"- {name} | {label_of(name)}"
        if parent:
            line += f" | parent: {parent}"
        if alts:
            line += f" | alt: {', '.join(alts)}"
        out.append(line)

    out.append("")
    out.append(f"## 对象属性（{len(objprops)}）")
    for name in sorted(objprops):
        doms, rngs = domain_range(name, True)
        alts = altlabels_of(name)
        line = f"- {name} | {label_of(name)}"
        if doms:
            line += f" | domain: {','.join(doms)}"
        if rngs:
            line += f" | range: {','.join(rngs)}"
        if alts:
            line += f" | alt: {', '.join(alts)}"
        out.append(line)

    out.append("")
    out.append(f"## 数据属性（{len(dataprops)}）")
    for name in sorted(dataprops):
        doms, rngs = domain_range(name, False)
        alts = altlabels_of(name)
        line = f"- {name} | {label_of(name)}"
        if doms:
            line += f" | domain: {','.join(doms)}"
        if rngs:
            line += f" | range: {','.join(rngs)}"
        if alts:
            line += f" | alt: {', '.join(alts)}"
        out.append(line)

    text = "\n".join(out)
    with open(r"E:\LX\LX_fund\FondOntology\artifacts\cnfo_inventory.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"written: {len(text)} chars, classes={len(classes)}, objprops={len(objprops)}, dataprops={len(dataprops)}")


if __name__ == "__main__":
    main()
