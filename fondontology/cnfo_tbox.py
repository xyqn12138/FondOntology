"""Build the independent China fund ontology T-BOX."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .ontology_loader import load_ontology_graph


CNFO_BASE_IRI = "https://ontology.example.cn/cnfo/ontology/"
CNFO_MODULE_BASE_IRI = "https://ontology.example.cn/cnfo/module/"


@dataclass(frozen=True)
class CnfoTBoxConfig:
    source_path: Path = Path("ontology/modules/cnfo-domain.ttl")
    output_path: Path = Path("artifacts/cnfo/cnfo-fund-tbox.ttl")
    manifest_path: Path = Path("artifacts/cnfo/cnfo-fund-tbox-manifest.json")
    explorer_output_path: Path = Path("artifacts/cnfo/cnfo-fund-tbox-explorer.json")


class CnfoFundTBox:
    """Build and export the independent CNFO T-BOX."""

    def __init__(self, config: CnfoTBoxConfig):
        self.config = config

    @staticmethod
    def _project_path(path: Path) -> Path:
        return path if path.is_absolute() else Path.cwd() / path

    def _load_graph(self) -> Graph:
        source_path = self._project_path(self.config.source_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"CNFO source not found: {source_path}")
        return load_ontology_graph(source_path)

    @staticmethod
    def _in_cnfo_namespace(resources) -> set[URIRef]:
        return {
            resource
            for resource in resources
            if isinstance(resource, URIRef) and str(resource).startswith(CNFO_BASE_IRI)
        }

    def _module_summary(self, graph: Graph) -> dict[str, object]:
        module_base = CNFO_MODULE_BASE_IRI
        module_type = URIRef(f"{module_base}OntologyModule")
        module_file = URIRef(f"{module_base}moduleFile")
        module_kind = URIRef(f"{module_base}moduleKind")
        module_parent = URIRef(f"{module_base}moduleParent")
        modules = []
        for module in sorted(graph.subjects(RDF.type, module_type), key=str):
            if not isinstance(module, URIRef):
                continue
            parent = graph.value(module, module_parent)
            modules.append({
                "iri": str(module),
                "file": str(graph.value(module, module_file) or ""),
                "kind": str(graph.value(module, module_kind) or ""),
                "parent": str(parent) if isinstance(parent, URIRef) else "",
            })
        return {"count": len(modules), "items": modules}

    def build(self) -> dict[str, object]:
        graph = self._load_graph()
        output_path = self._project_path(self.config.output_path)
        manifest_path = self._project_path(self.config.manifest_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=output_path, format="turtle")
        classes = self._in_cnfo_namespace(graph.subjects(RDF.type, OWL.Class))
        object_properties = self._in_cnfo_namespace(graph.subjects(RDF.type, OWL.ObjectProperty))
        datatype_properties = self._in_cnfo_namespace(graph.subjects(RDF.type, OWL.DatatypeProperty))
        restrictions = set(graph.subjects(RDF.type, OWL.Restriction))
        subproperties = self._in_cnfo_namespace(graph.subjects(RDFS.subPropertyOf, None))
        inverse_properties = self._in_cnfo_namespace(graph.subjects(OWL.inverseOf, None))
        disjoint_class_pairs = self._in_cnfo_namespace(graph.subjects(OWL.disjointWith, None))
        disjoint_class_groups = set(graph.subjects(RDF.type, OWL.AllDisjointClasses))
        module_summary = self._module_summary(graph)
        manifest = {
            "ontology": "China Fund Ontology (CNFO)",
            "status": "independent",
            "source_path": str(self._project_path(self.config.source_path)),
            "output_path": str(output_path),
            "triple_count": len(graph),
            "class_count": len(classes),
            "object_property_count": len(object_properties),
            "datatype_property_count": len(datatype_properties),
            "restriction_count": len(restrictions),
            "subproperty_count": len(subproperties),
            "inverse_property_count": len(inverse_properties),
            "disjoint_class_pair_count": len(disjoint_class_pairs),
            "disjoint_class_group_count": len(disjoint_class_groups),
            "module_count": module_summary["count"],
            "modules": module_summary["items"],
            "cnfo_namespace": CNFO_BASE_IRI,
            "external_ontology_iris": [],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest

    def inspect(self) -> dict[str, object]:
        graph = self._load_graph()
        classes = self._in_cnfo_namespace(graph.subjects(RDF.type, OWL.Class))
        object_properties = self._in_cnfo_namespace(graph.subjects(RDF.type, OWL.ObjectProperty))
        datatype_properties = self._in_cnfo_namespace(graph.subjects(RDF.type, OWL.DatatypeProperty))
        module_summary = self._module_summary(graph)
        return {
            "ontology": "China Fund Ontology (CNFO)",
            "status": "independent",
            "source_path": str(self._project_path(self.config.source_path)),
            "triple_count": len(graph),
            "class_count": len(classes),
            "object_property_count": len(object_properties),
            "datatype_property_count": len(datatype_properties),
            "restriction_count": len(set(graph.subjects(RDF.type, OWL.Restriction))),
            "subproperty_count": len(self._in_cnfo_namespace(graph.subjects(RDFS.subPropertyOf, None))),
            "inverse_property_count": len(self._in_cnfo_namespace(graph.subjects(OWL.inverseOf, None))),
            "disjoint_class_pair_count": len(self._in_cnfo_namespace(graph.subjects(OWL.disjointWith, None))),
            "disjoint_class_group_count": len(set(graph.subjects(RDF.type, OWL.AllDisjointClasses))),
            "module_count": module_summary["count"],
            "modules": module_summary["items"],
            "cnfo_namespace": CNFO_BASE_IRI,
            "external_ontology_iris": [],
        }

    def export_explorer(self) -> dict[str, object]:
        source_path = self._project_path(self.config.output_path)
        if not source_path.is_file():
            self.build()
        graph = Graph()
        graph.parse(source_path, format="turtle")
        edge_predicates = (
            RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range,
            OWL.equivalentClass, OWL.disjointWith, SKOS.closeMatch, SKOS.relatedMatch,
        )
        type_predicates = (
            OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
            OWL.AnnotationProperty, RDF.Property, RDFS.Datatype,
        )
        resources: set[URIRef] = set()
        for resource_type in type_predicates:
            resources.update(
                s for s in graph.subjects(RDF.type, resource_type)
                if isinstance(s, URIRef) and not str(s).startswith(CNFO_MODULE_BASE_IRI)
            )
        for predicate in edge_predicates:
            resources.update(
                s for s in graph.subjects(predicate, None)
                if isinstance(s, URIRef) and not str(s).startswith(CNFO_MODULE_BASE_IRI)
            )
            resources.update(
                o for o in graph.objects(None, predicate)
                if isinstance(o, URIRef) and not str(o).startswith(CNFO_MODULE_BASE_IRI)
            )

        def local_name(value: URIRef | str) -> str:
            text = str(value).rstrip("/#")
            return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text

        def first_label(resource: URIRef, predicate) -> str:
            values = list(graph.objects(resource, predicate))
            zh_values = [value for value in values if getattr(value, "language", None) == "zh"]
            return str((zh_values or values)[0]) if values else ""

        def compact_type(resource: URIRef) -> str:
            types = set(graph.objects(resource, RDF.type))
            if OWL.Class in types or RDFS.Class in types: return "owl:Class"
            if OWL.ObjectProperty in types: return "owl:ObjectProperty"
            if OWL.DatatypeProperty in types: return "owl:DatatypeProperty"
            if OWL.AnnotationProperty in types: return "owl:AnnotationProperty"
            if RDF.Property in types: return "rdf:Property"
            if RDFS.Datatype in types: return "rdfs:Datatype"
            return "ontology_resource"

        nodes: list[dict[str, object]] = []
        for resource in sorted(resources, key=str):
            label = first_label(resource, SKOS.prefLabel) or first_label(resource, RDFS.label)
            comments = [str(value) for value in graph.objects(resource, RDFS.comment)]
            nodes.append({
                "id": str(resource), "type": compact_type(resource),
                "content": label or local_name(resource),
                "properties": {
                    "iri": str(resource), "label": label or local_name(resource),
                    "rdfs:comment": comments[0] if comments else "",
                    "rdf:type": compact_type(resource), "local_name": local_name(resource), "source": "CNFO",
                },
            })
        node_ids = {node["id"] for node in nodes}
        predicate_labels = {
            RDFS.subClassOf: "rdfs:subClassOf", RDFS.subPropertyOf: "rdfs:subPropertyOf",
            RDFS.domain: "rdfs:domain", RDFS.range: "rdfs:range",
            OWL.equivalentClass: "owl:equivalentClass", OWL.disjointWith: "owl:disjointWith",
            SKOS.closeMatch: "skos:closeMatch", SKOS.relatedMatch: "skos:relatedMatch",
        }
        edges: list[dict[str, object]] = []
        for predicate in edge_predicates:
            for source, target in graph.subject_objects(predicate):
                if isinstance(source, URIRef) and isinstance(target, URIRef):
                    if str(source) in node_ids and str(target) in node_ids:
                        edges.append({
                            "source": str(source), "target": str(target),
                            "type": predicate_labels[predicate], "weight": 1.0,
                            "properties": {"predicate": str(predicate)},
                        })
        for group in graph.subjects(RDF.type, OWL.AllDisjointClasses):
            members: list[URIRef] = []
            head = graph.value(group, OWL.members)
            while head and head != RDF.nil:
                member = graph.value(head, RDF.first)
                if isinstance(member, URIRef):
                    members.append(member)
                head = graph.value(head, RDF.rest)
            for index, source in enumerate(members):
                for target in members[index + 1:]:
                    if str(source) in node_ids and str(target) in node_ids:
                        edges.append({
                            "source": str(source), "target": str(target),
                            "type": "owl:disjointWith", "weight": 1.0,
                            "properties": {"predicate": str(OWL.disjointWith), "source_group": "owl:AllDisjointClasses"},
                        })
        output_path = self._project_path(self.config.explorer_output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"graph_id": "cnfo-fund-tbox", "nodes": nodes, "edges": edges}, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "output_path": str(output_path), "node_count": len(nodes), "edge_count": len(edges),
            "cnfo_node_count": len(nodes),
            "edge_types": {edge_type: sum(edge["type"] == edge_type for edge in edges) for edge_type in predicate_labels.values()},
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the independent China fund ontology")
    parser.add_argument("command", choices=["inspect", "build", "export-explorer"])
    parser.add_argument("--source", type=Path, default=Path("ontology/modules/cnfo-domain.ttl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/cnfo/cnfo-fund-tbox.ttl"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/cnfo/cnfo-fund-tbox-manifest.json"))
    parser.add_argument("--explorer-output", type=Path, default=Path("artifacts/cnfo/cnfo-fund-tbox-explorer.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tbox = CnfoFundTBox(CnfoTBoxConfig(args.source, args.output, args.manifest, args.explorer_output))
    if args.command == "inspect":
        result = tbox.inspect()
    elif args.command == "build":
        result = tbox.build()
    else:
        result = tbox.export_explorer()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
