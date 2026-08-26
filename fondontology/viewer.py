"""A class-centric ontology browser for the independent CNFO T-BOX."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from owlrl import DeductiveClosure, OWLRL_Semantics


CNFO_BASE_IRI = "https://ontology.example.cn/cnfo/ontology/"
CNFO_NAMESPACE = CNFO_BASE_IRI
BUILTIN_NAMESPACE_PREFIXES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2001/XMLSchema#",
)
STATIC_DIR = Path(__file__).with_name("viewer_static")


class OntologyViewerSession:
    """Index the ontology for direct class-neighborhood browsing."""

    def __init__(self, ttl_path: Path | str):
        self.ttl_path = Path(ttl_path).expanduser().resolve()
        if not self.ttl_path.is_file():
            raise FileNotFoundError(f"Ontology Turtle file not found: {self.ttl_path}")
        self.source_graph = Graph()
        self.source_graph.parse(self.ttl_path, format="turtle")
        self.graph = Graph()
        self.graph += self.source_graph
        DeductiveClosure(
            OWLRL_Semantics,
            axiomatic_triples=False,
            datatype_axioms=False,
        ).expand(self.graph)
        self.class_ids = self._find_classes()
        self.property_ids = self._find_properties()
        self._ancestor_cache: dict[URIRef, set[URIRef]] = {}

    def _find_classes(self) -> set[URIRef]:
        classes = {
            subject
            for rdf_type in (OWL.Class, RDFS.Class)
            for subject in self.graph.subjects(RDF.type, rdf_type)
            if isinstance(subject, URIRef)
        }
        classes.update(
            subject
            for subject, _target in self.graph.subject_objects(RDFS.subClassOf)
            if isinstance(subject, URIRef)
        )
        classes.update(
            target
            for _subject, target in self.graph.subject_objects(RDFS.subClassOf)
            if isinstance(target, URIRef)
        )
        return {resource for resource in classes if str(resource).startswith(CNFO_NAMESPACE)}

    def _find_properties(self) -> set[URIRef]:
        properties: set[URIRef] = set()
        for rdf_type in (
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
            RDF.Property,
        ):
            properties.update(
                subject
                for subject in self.graph.subjects(RDF.type, rdf_type)
                if isinstance(subject, URIRef)
            )
        properties.update(
            subject
            for subject in self.graph.subjects(RDFS.domain, None)
            if isinstance(subject, URIRef)
        )
        return {resource for resource in properties if str(resource).startswith(CNFO_NAMESPACE)}

    def _ancestors(self, iri: URIRef, include_self: bool = True) -> set[URIRef]:
        """Return the RDFS class closure used for display-time inference."""
        cached = self._ancestor_cache.get(iri)
        if cached is None:
            ancestors: set[URIRef] = {iri}
            pending = [iri]
            while pending:
                current = pending.pop()
                for parent in self.graph.objects(current, RDFS.subClassOf):
                    if not isinstance(parent, URIRef) or parent not in self.class_ids:
                        continue
                    if parent not in ancestors:
                        ancestors.add(parent)
                        pending.append(parent)
            cached = ancestors
            self._ancestor_cache[iri] = cached
        return set(cached) if include_self else cached - {iri}

    def _ancestor_order(self, iri: URIRef) -> list[URIRef]:
        """Return the class closure from the current class upward."""
        ordered: list[URIRef] = []
        seen: set[URIRef] = set()
        queue: list[URIRef] = [iri]
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            ordered.append(current)
            parents = sorted(
                parent for parent in self.graph.objects(current, RDFS.subClassOf)
                if isinstance(parent, URIRef) and parent in self.class_ids
            )
            queue.extend(parents)
        return ordered

    def _property_schema(self, property_iri: URIRef) -> tuple[set[URIRef], set[URIRef]]:
        domains = {
            value for value in self.source_graph.objects(property_iri, RDFS.domain)
            if isinstance(value, URIRef)
        }
        ranges = {
            value for value in self.source_graph.objects(property_iri, RDFS.range)
            if isinstance(value, URIRef)
        }
        return domains, ranges

    @staticmethod
    def _local_name(value: URIRef | str) -> str:
        text = str(value).rstrip("/#")
        return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text

    def _values(self, resource: URIRef, *predicates) -> list[str]:
        values: list[str] = []
        for predicate in predicates:
            values.extend(str(value) for value in self.graph.objects(resource, predicate))
        return list(dict.fromkeys(values))

    def _literal_values(self, resource: URIRef, *predicates) -> list[dict[str, str | None]]:
        values: list[dict[str, str | None]] = []
        for predicate in predicates:
            for value in self.graph.objects(resource, predicate):
                values.append({
                    "value": str(value),
                    "language": getattr(value, "language", None),
                })
        return values

    def _label(self, resource: URIRef) -> str:
        values = self._literal_values(resource, SKOS.prefLabel, RDFS.label)
        zh = [item["value"] for item in values if item["language"] == "zh"]
        return (zh or [item["value"] for item in values] or [self._local_name(resource)])[0]

    def _definition(self, resource: URIRef) -> str:
        values = self._literal_values(resource, SKOS.definition, RDFS.comment)
        zh = [item["value"] for item in values if item["language"] == "zh"]
        return (zh or [item["value"] for item in values] or [""])[0]

    def _source(self, resource: URIRef) -> str:
        resource_text = str(resource)
        if resource_text.startswith(CNFO_NAMESPACE):
            return "CNFO"
        if resource_text.startswith(BUILTIN_NAMESPACE_PREFIXES):
            return "内置类型"
        return "外部参考"

    def _node(self, resource: URIRef | str) -> dict[str, object]:
        iri = URIRef(str(resource))
        return {
            "iri": str(iri),
            "local_name": self._local_name(iri),
            "label": self._label(iri),
            "definition": self._definition(iri),
            "source": self._source(iri),
            "is_class": iri in self.class_ids,
        }

    def _nodes(self, resources) -> list[dict[str, object]]:
        return sorted(
            (self._node(resource) for resource in resources if isinstance(resource, URIRef)),
            key=lambda item: (item["source"] != "CNFO", str(item["label"]).lower()),
        )

    def search(self, query: str, scope: str, limit: int) -> list[dict[str, object]]:
        normalized = query.strip().lower()
        candidates = self.class_ids
        if scope == "cnfo":
            candidates = {item for item in candidates if self._source(item) == "CNFO"}

        ranked: list[tuple[int, dict[str, object]]] = []
        for resource in candidates:
            node = self._node(resource)
            haystack = " ".join(
                [
                    str(node["label"]),
                    str(node["local_name"]),
                    str(node["iri"]),
                    self._definition(resource),
                    *self._values(resource, SKOS.altLabel),
                ]
            ).lower()
            if normalized and normalized not in haystack:
                continue
            label = str(node["label"]).lower()
            local_name = str(node["local_name"]).lower()
            rank = 0 if label == normalized else 1 if local_name == normalized else 2
            if str(node["source"]) == "CNFO":
                rank -= 1
            ranked.append((rank, node))
        ranked.sort(key=lambda item: (item[0], str(item[1]["label"]).lower()))
        return [node for _rank, node in ranked[: max(1, min(limit, 100))]]

    def _property_node(self, resource: URIRef, inferred_from: URIRef | None = None) -> dict[str, object]:
        types = {str(value) for value in self.source_graph.objects(resource, RDF.type)}
        if str(OWL.DatatypeProperty) in types:
            property_type = "datatype"
        elif str(OWL.AnnotationProperty) in types:
            property_type = "annotation"
        else:
            property_type = "object"
        domains = [self._node(value) for value in self.source_graph.objects(resource, RDFS.domain) if isinstance(value, URIRef)]
        ranges = [self._node(value) for value in self.source_graph.objects(resource, RDFS.range) if isinstance(value, URIRef)]
        return {
            "iri": str(resource),
            "label": self._label(resource),
            "local_name": self._local_name(resource),
            "source": self._source(resource),
            "type": property_type,
            "domains": domains,
            "ranges": ranges,
            "inferred": inferred_from is not None,
            "inherited_from": self._node(inferred_from) if inferred_from is not None else None,
        }

    def _properties_for(self, iri: URIRef) -> dict[str, list[dict[str, object]]]:
        direct_domain: dict[URIRef, URIRef | None] = {}
        direct_range: dict[URIRef, URIRef | None] = {}
        for property_iri in self.property_ids:
            domains, ranges = self._property_schema(property_iri)
            for ancestor in self._ancestor_order(iri):
                if ancestor in domains and property_iri not in direct_domain:
                    direct_domain[property_iri] = None if ancestor == iri else ancestor
            for ancestor in self._ancestor_order(iri):
                if ancestor in ranges and property_iri not in direct_range:
                    direct_range[property_iri] = None if ancestor == iri else ancestor
        return {
            "outgoing": [self._property_node(item, direct_domain[item]) for item in sorted(direct_domain, key=str)],
            "incoming": [self._property_node(item, direct_range[item]) for item in sorted(direct_range, key=str)],
        }

    def _property_groups_for(self, iri: URIRef) -> dict[str, dict[str, list[dict[str, object]]]]:
        properties = self._properties_for(iri)
        groups: dict[str, dict[str, list[dict[str, object]]]] = {
            "object": {"outgoing": [], "incoming": []},
            "datatype": {"outgoing": [], "incoming": []},
            "annotation": {"outgoing": [], "incoming": []},
        }
        for direction in ("outgoing", "incoming"):
            for property_node in properties[direction]:
                property_type = str(property_node["type"])
                groups.setdefault(property_type, {"outgoing": [], "incoming": []})[direction].append(property_node)
        return groups

    def _restriction_node(self, restriction: BNode | URIRef) -> dict[str, object]:
        property_iri = self.graph.value(restriction, OWL.onProperty)
        property_node = self._property_node(property_iri) if isinstance(property_iri, URIRef) else None
        cardinality_predicates = (
            (OWL.qualifiedCardinality, "exactly"),
            (OWL.cardinality, "exactly"),
            (OWL.minQualifiedCardinality, "at least"),
            (OWL.minCardinality, "at least"),
            (OWL.maxQualifiedCardinality, "at most"),
            (OWL.maxCardinality, "at most"),
        )
        value_predicates = (
            (OWL.someValuesFrom, "some"),
            (OWL.allValuesFrom, "only"),
            (OWL.hasValue, "value"),
            (OWL.hasSelf, "self"),
        )
        cardinality: dict[str, str] | None = None
        for predicate, operator in cardinality_predicates:
            value = self.graph.value(restriction, predicate)
            if value is not None:
                cardinality = {"operator": operator, "value": str(value)}
                break
        value_constraint: dict[str, object] | None = None
        for predicate, operator in value_predicates:
            value = self.graph.value(restriction, predicate)
            if value is not None:
                if isinstance(value, URIRef) and value in self.class_ids:
                    value_constraint = {"operator": operator, "target": self._node(value)}
                else:
                    value_constraint = {"operator": operator, "value": str(value)}
                break
        if cardinality is not None and property_node is not None:
            description = f"{property_node['local_name']} {cardinality['operator']} {cardinality['value']}"
        elif value_constraint is not None and property_node is not None:
            target = value_constraint.get("target")
            target_label = target["label"] if isinstance(target, dict) else value_constraint.get("value", "")
            description = f"{property_node['local_name']} {value_constraint['operator']} {target_label}"
        elif property_node is not None:
            description = str(property_node["local_name"])
        else:
            description = "OWL restriction"
        return {
            "iri": str(restriction),
            "property": property_node,
            "cardinality": cardinality,
            "value_constraint": value_constraint,
            "description": description,
        }

    def _restrictions_for(self, iri: URIRef) -> list[dict[str, object]]:
        expressions: dict[BNode | URIRef, URIRef] = {}
        for ancestor in self._ancestor_order(iri):
            for expression in self.graph.objects(ancestor, RDFS.subClassOf):
                if isinstance(expression, (BNode, URIRef)) and expression not in expressions:
                    expressions[expression] = ancestor
            for expression in self.graph.objects(ancestor, OWL.equivalentClass):
                if isinstance(expression, (BNode, URIRef)) and expression not in expressions:
                    expressions[expression] = ancestor
        restrictions = [
            {
                **self._restriction_node(expression),
                "inferred": ancestor != iri,
                "inherited_from": self._node(ancestor) if ancestor != iri else None,
            }
            for expression, ancestor in expressions.items()
            if isinstance(expression, (BNode, URIRef))
            and (expression, RDF.type, OWL.Restriction) in self.graph
        ]
        return sorted(restrictions, key=lambda item: str(item["description"]))

    def detail(self, iri_text: str) -> dict[str, object]:
        iri = URIRef(unquote(iri_text))
        if iri not in self.class_ids:
            raise KeyError(f"Class not found: {iri}")
        # Keep the visible neighborhood to one declared layer. The inferred graph
        # contains transitive subClassOf triples, which are useful for inheritance
        # but would make grandparents look like direct parents.
        parents = [
            item for item in self.source_graph.objects(iri, RDFS.subClassOf)
            if isinstance(item, URIRef) and item in self.class_ids
        ]
        children = [
            item for item in self.source_graph.subjects(RDFS.subClassOf, iri)
            if isinstance(item, URIRef) and item in self.class_ids
        ]
        relations: list[dict[str, object]] = []
        for parent in parents:
            relations.append({
                "direction": "outgoing",
                "predicate": str(RDFS.subClassOf),
                "label": "subClassOf",
                "target": self._node(parent),
            })
        for child in children:
            relations.append({
                "direction": "incoming",
                "predicate": str(RDFS.subClassOf),
                "label": "subClassOf",
                "target": self._node(child),
            })
        for property_iri in self.property_ids:
            domains, ranges = self._property_schema(property_iri)
            property_label = self._local_name(property_iri)
            property_label_zh = self._label(property_iri)
            domain_source = next((ancestor for ancestor in self._ancestor_order(iri) if ancestor in domains), None)
            range_source = next((ancestor for ancestor in self._ancestor_order(iri) if ancestor in ranges), None)
            if domain_source is not None:
                for target in ranges:
                    if target in self.class_ids:
                        relations.append({
                            "direction": "outgoing",
                            "predicate": str(property_iri),
                            "label": property_label,
                            "label_zh": property_label_zh,
                            "inferred": domain_source != iri,
                            "inherited_from": self._node(domain_source) if domain_source != iri else None,
                            "target": self._node(target),
                        })
            if range_source is not None:
                for source in domains:
                    if source in self.class_ids:
                        relations.append({
                            "direction": "incoming",
                            "predicate": str(property_iri),
                            "label": property_label,
                            "label_zh": property_label_zh,
                            "inferred": range_source != iri,
                            "inherited_from": self._node(range_source) if range_source != iri else None,
                            "target": self._node(source),
                        })
        for predicate, label in (
            (OWL.equivalentClass, "equivalentClass"),
            (OWL.disjointWith, "disjointWith"),
            (SKOS.closeMatch, "closeMatch"),
            (SKOS.relatedMatch, "relatedMatch"),
        ):
            for target in self.graph.objects(iri, predicate):
                if isinstance(target, URIRef) and target in self.class_ids:
                    relations.append({
                        "direction": "outgoing",
                        "predicate": str(predicate),
                        "label": label,
                        "target": self._node(target),
                    })
            for source in self.graph.subjects(predicate, iri):
                if isinstance(source, URIRef) and source in self.class_ids:
                    relations.append({
                        "direction": "incoming",
                        "predicate": str(predicate),
                        "label": label,
                        "target": self._node(source),
                    })
        alignments: list[dict[str, object]] = []
        for predicate, label in (
            (OWL.equivalentClass, "等价类"),
            (SKOS.closeMatch, "近似匹配"),
            (SKOS.relatedMatch, "相关匹配"),
        ):
            for target in self.graph.objects(iri, predicate):
                if isinstance(target, URIRef):
                    alignments.append({"relation": label, "predicate": str(predicate), "target": self._node(target)})
            for source in self.graph.subjects(predicate, iri):
                if isinstance(source, URIRef):
                    alignments.append({"relation": label, "predicate": str(predicate), "target": self._node(source)})
        property_groups = self._property_groups_for(iri)
        logical_constraints: list[dict[str, object]] = []
        for predicate, label in ((OWL.disjointWith, "disjointWith"), (OWL.complementOf, "complementOf")):
            for target in self.graph.objects(iri, predicate):
                if isinstance(target, URIRef):
                    logical_constraints.append({
                        "relation": label,
                        "target": self._node(target),
                    })
            for source in self.graph.subjects(predicate, iri):
                if isinstance(source, URIRef):
                    logical_constraints.append({
                        "relation": label,
                        "target": self._node(source),
                    })
        return {
            "current": self._node(iri),
            "parents": self._nodes(parents),
            "children": self._nodes(children),
            "hierarchy": {
                "parents": self._nodes(parents),
                "children": self._nodes(children),
            },
            "relations": relations,
            "properties": self._properties_for(iri),
            "object_properties": property_groups["object"],
            "datatype_properties": property_groups["datatype"],
            "annotation_properties": property_groups["annotation"],
            "restrictions": self._restrictions_for(iri),
            "alignments": alignments,
            "mappings": alignments,
            "logical_constraints": logical_constraints,
            "labels": self._literal_values(iri, RDFS.label, SKOS.prefLabel, SKOS.altLabel),
            "definitions": self._literal_values(iri, RDFS.comment, SKOS.definition),
            "annotations": {
                "types": self._values(iri, RDF.type),
                "subclasses": [str(item["iri"]) for item in self._nodes(parents)],
            },
        }

    def summary(self) -> dict[str, object]:
        cnfo_count = sum(self._source(item) == "CNFO" for item in self.class_ids)
        return {
            "ontology_file": str(self.ttl_path),
            "triple_count": len(self.graph),
            "source_triple_count": len(self.source_graph),
            "inference": {
                "enabled": True,
                "profile": "OWL 2 RL",
                "engine": "owlrl",
                "closure_triple_count": len(self.graph),
            },
            "class_count": len(self.class_ids),
            "property_count": len(self.property_ids),
            "cnfo_class_count": cnfo_count,
            "external_runtime_dependency": False,
        }


def create_viewer_app(session: OntologyViewerSession) -> FastAPI:
    if not STATIC_DIR.is_dir():
        raise FileNotFoundError(f"Viewer assets not found: {STATIC_DIR}")
    app = FastAPI(title="Fund Ontology Browser", version="0.1.0")

    @app.get("/api/ontology/summary")
    async def ontology_summary():
        return session.summary()

    @app.get("/api/ontology/search")
    async def ontology_search(
        q: str = Query(default=""),
        scope: str = Query(default="all"),
        limit: int = Query(default=30, ge=1, le=100),
    ):
        if scope not in {"all", "cnfo"}:
            raise HTTPException(status_code=400, detail="Invalid ontology scope")
        return {"query": q, "scope": scope, "results": session.search(q, scope, limit)}

    @app.get("/api/ontology/class")
    async def ontology_class(iri: str):
        try:
            return session.detail(iri)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/")
    async def root():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")
    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the class-centric fund ontology browser")
    parser.add_argument("--ttl", type=Path, default=Path("artifacts/cnfo/cnfo-fund-tbox.ttl"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = OntologyViewerSession(args.ttl)
    import uvicorn

    uvicorn.run(create_viewer_app(session), host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
