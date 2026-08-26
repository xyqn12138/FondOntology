"""Build the China fund ontology extension on top of the FIBO T-BOX."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS


CNFO_BASE_IRI = "https://ontology.example.cn/cnfo/ontology/"


@dataclass(frozen=True)
class CnfoTBoxConfig:
    fibo_path: Path = Path("artifacts/fibo/fibo-prod-tbox.ttl")
    extension_path: Path = Path("ontology/cnfo-fund.ttl")
    output_path: Path = Path("artifacts/cnfo/cnfo-fibo-fund-tbox.ttl")
    manifest_path: Path = Path("artifacts/cnfo/cnfo-fibo-fund-tbox-manifest.json")
    explorer_output_path: Path = Path("artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json")


class CnfoFundTBox:
    """Merge a maintained CNFO extension with the generated FIBO baseline."""

    def __init__(self, config: CnfoTBoxConfig):
        self.config = config

    @staticmethod
    def _project_path(path: Path) -> Path:
        return path if path.is_absolute() else Path.cwd() / path

    def _load_graphs(self) -> tuple[Graph, Graph]:
        fibo_path = self._project_path(self.config.fibo_path)
        extension_path = self._project_path(self.config.extension_path)
        if not fibo_path.is_file():
            raise FileNotFoundError(
                f"FIBO baseline not found: {fibo_path}. Run the FIBO build first."
            )
        if not extension_path.is_file():
            raise FileNotFoundError(f"CNFO extension not found: {extension_path}")

        fibo = Graph()
        fibo.parse(fibo_path, format="turtle")
        extension = Graph()
        extension.parse(extension_path, format="turtle")
        return fibo, extension

    def build(self) -> dict[str, object]:
        fibo, extension = self._load_graphs()
        merged = Graph()
        for prefix, namespace in fibo.namespaces():
            merged.bind(prefix, namespace)
        for prefix, namespace in extension.namespaces():
            merged.bind(prefix, namespace)
        merged += fibo
        merged += extension

        output_path = self._project_path(self.config.output_path)
        manifest_path = self._project_path(self.config.manifest_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        merged.serialize(destination=output_path, format="turtle")

        cnfo_classes = set(extension.subjects(RDF.type, OWL.Class))
        cnfo_object_properties = set(extension.subjects(RDF.type, OWL.ObjectProperty))
        cnfo_datatype_properties = set(extension.subjects(RDF.type, OWL.DatatypeProperty))
        inherited_classes = {
            (str(subject), str(parent))
            for subject, parent in extension.subject_objects(RDFS.subClassOf)
            if str(subject).startswith(CNFO_BASE_IRI)
        }
        manifest = {
            "ontology": "China Fund Ontology (CNFO)",
            "fibo_path": str(self._project_path(self.config.fibo_path)),
            "extension_path": str(self._project_path(self.config.extension_path)),
            "output_path": str(output_path),
            "triple_count": len(merged),
            "fibo_triple_count": len(fibo),
            "cnfo_triple_count": len(extension),
            "cnfo_class_count": len(cnfo_classes),
            "cnfo_object_property_count": len(cnfo_object_properties),
            "cnfo_datatype_property_count": len(cnfo_datatype_properties),
            "cnfo_fibo_inheritance_count": len(inherited_classes),
            "cnfo_namespace": CNFO_BASE_IRI,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return manifest

    def export_explorer(self) -> dict[str, object]:
        source_path = self._project_path(self.config.output_path)
        if not source_path.is_file():
            self.build()

        graph = Graph()
        graph.parse(source_path, format="turtle")
        edge_predicates = (
            RDFS.subClassOf,
            RDFS.subPropertyOf,
            RDFS.domain,
            RDFS.range,
            OWL.equivalentClass,
            SKOS.closeMatch,
            SKOS.relatedMatch,
        )
        type_predicates = (
            OWL.Class,
            RDFS.Class,
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
            RDF.Property,
            RDFS.Datatype,
        )

        resources: set[URIRef] = set()
        for resource_type in type_predicates:
            resources.update(
                subject
                for subject in graph.subjects(RDF.type, resource_type)
                if isinstance(subject, URIRef)
            )
        for predicate in edge_predicates:
            resources.update(
                subject
                for subject in graph.subjects(predicate, None)
                if isinstance(subject, URIRef)
            )
            resources.update(
                target
                for target in graph.objects(None, predicate)
                if isinstance(target, URIRef)
            )

        def local_name(value: URIRef | str) -> str:
            text = str(value).rstrip("/#")
            return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text

        def first_label(resource: URIRef, predicate) -> str:
            values = list(graph.objects(resource, predicate))
            zh_values = [
                value for value in values if getattr(value, "language", None) == "zh"
            ]
            return str((zh_values or values)[0]) if values else ""

        def compact_type(resource: URIRef) -> str:
            types = set(graph.objects(resource, RDF.type))
            if OWL.Class in types or RDFS.Class in types:
                return "owl:Class"
            if OWL.ObjectProperty in types:
                return "owl:ObjectProperty"
            if OWL.DatatypeProperty in types:
                return "owl:DatatypeProperty"
            if OWL.AnnotationProperty in types:
                return "owl:AnnotationProperty"
            if RDF.Property in types:
                return "rdf:Property"
            if RDFS.Datatype in types:
                return "rdfs:Datatype"
            return "ontology_resource"

        nodes: list[dict[str, object]] = []
        for resource in sorted(resources, key=str):
            label = first_label(resource, SKOS.prefLabel) or first_label(resource, RDFS.label)
            comments = [str(value) for value in graph.objects(resource, RDFS.comment)]
            resource_type = compact_type(resource)
            source = "CNFO" if str(resource).startswith(CNFO_BASE_IRI) else "FIBO"
            nodes.append(
                {
                    "id": str(resource),
                    "type": resource_type,
                    "content": label or local_name(resource),
                    "properties": {
                        "iri": str(resource),
                        "label": label or local_name(resource),
                        "rdfs:comment": comments[0] if comments else "",
                        "rdf:type": resource_type,
                        "local_name": local_name(resource),
                        "source": source,
                    },
                }
            )

        node_ids = {node["id"] for node in nodes}
        predicate_labels = {
            RDFS.subClassOf: "rdfs:subClassOf",
            RDFS.subPropertyOf: "rdfs:subPropertyOf",
            RDFS.domain: "rdfs:domain",
            RDFS.range: "rdfs:range",
            OWL.equivalentClass: "owl:equivalentClass",
            SKOS.closeMatch: "skos:closeMatch",
            SKOS.relatedMatch: "skos:relatedMatch",
        }
        edges: list[dict[str, object]] = []
        for predicate in edge_predicates:
            for source, target in graph.subject_objects(predicate):
                if not isinstance(source, URIRef) or not isinstance(target, URIRef):
                    continue
                if str(source) not in node_ids or str(target) not in node_ids:
                    continue
                edges.append(
                    {
                        "source": str(source),
                        "target": str(target),
                        "type": predicate_labels[predicate],
                        "weight": 1.0,
                        "properties": {"predicate": str(predicate)},
                    }
                )

        output_path = self._project_path(self.config.explorer_output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"graph_id": "cnfo-fibo-fund-tbox", "nodes": nodes, "edges": edges}
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return {
            "output_path": str(output_path),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cnfo_node_count": sum(
                node["properties"]["source"] == "CNFO" for node in nodes
            ),
            "fibo_node_count": sum(
                node["properties"]["source"] == "FIBO" for node in nodes
            ),
            "edge_types": {
                edge_type: sum(edge["type"] == edge_type for edge in edges)
                for edge_type in predicate_labels.values()
            },
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the China fund ontology on top of FIBO"
    )
    parser.add_argument("command", choices=["build", "export-explorer"])
    parser.add_argument("--fibo", type=Path, default=Path("artifacts/fibo/fibo-prod-tbox.ttl"))
    parser.add_argument("--extension", type=Path, default=Path("ontology/cnfo-fund.ttl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/cnfo/cnfo-fibo-fund-tbox.ttl"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/cnfo/cnfo-fibo-fund-tbox-manifest.json"))
    parser.add_argument("--explorer-output", type=Path, default=Path("artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = CnfoTBoxConfig(
        fibo_path=args.fibo,
        extension_path=args.extension,
        output_path=args.output,
        manifest_path=args.manifest,
        explorer_output_path=args.explorer_output,
    )
    tbox = CnfoFundTBox(config)
    result = tbox.build() if args.command == "build" else tbox.export_explorer()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
