"""Extract restrictions and class hierarchy from CNFO T-BOX."""
import rdflib
from rdflib.namespace import OWL, RDF, RDFS

NS = rdflib.Namespace("https://ontology.example.cn/cnfo/ontology/")


def local(uri) -> str:
    s = str(uri)
    return s.replace(str(NS), "") if s.startswith(str(NS)) else s


def main() -> None:
    g = rdflib.Graph()
    g.parse(r"E:\LX\LX_fund\FondOntology\ontology\modules\cnfo-domain.ttl", format="turtle")
    g.parse(r"E:\LX\LX_fund\FondOntology\ontology\cnfo-fund.ttl", format="turtle")

    print("== FundObject direct children ==")
    kids = sorted({local(s) for s in g.subjects(RDFS.subClassOf, NS.FundObject)})
    print(f"count={len(kids)}")
    print(", ".join(kids))
    print()

    print("== All owl:Restriction (owner | onProperty | quantifier | filler) ==")
    n = 0
    for r in g.subjects(RDF.type, OWL.Restriction):
        prop = g.value(r, OWL.onProperty)
        q = None
        for pred, label in (
            (OWL.someValuesFrom, "some"), (OWL.allValuesFrom, "only"),
            (OWL.hasValue, "value"), (OWL.cardinality, "exactly"),
            (OWL.minCardinality, "min"), (OWL.maxCardinality, "max"),
            (OWL.qualifiedCardinality, "q-exactly"),
            (OWL.minQualifiedCardinality, "q-min"),
            (OWL.maxQualifiedCardinality, "q-max"),
        ):
            v = g.value(r, pred)
            if v is not None:
                if isinstance(v, rdflib.URIRef):
                    q = (label, local(v))
                else:
                    q = (label, str(v))
                break
        on_class = g.value(r, OWL.onClass)
        if on_class is not None and q is not None:
            q = (q[0], f"{local(on_class)}", q[1]) if q[0].startswith("q-") else q
        owner = g.value(subject=None, predicate=RDFS.subClassOf, object=r)
        line = f"{local(owner) if owner else '?'} | {local(prop) if prop else '?'} | {q}"
        print(line)
        n += 1
    print(f"total={n}")


if __name__ == "__main__":
    main()