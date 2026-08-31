"""Load a CNFO module and its local owl:imports without network access."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph
from rdflib.namespace import OWL, RDF


def _candidate_module_paths(source_path: Path) -> set[Path]:
    """Find local module files next to a source entry point."""
    roots = {source_path.parent}
    if source_path.parent.name == "modules":
        roots.add(source_path.parent.parent)
    roots.add(source_path.parent / "modules")
    paths = {source_path}
    for root in roots:
        if root.is_dir():
            paths.update(root.glob("*.ttl"))
    return {path.resolve() for path in paths if path.is_file()}


def load_ontology_graph(source_path: Path | str) -> Graph:
    """Load *source_path* and all resolvable local ontology imports.

    FIBO-style imports use stable ontology IRIs rather than filesystem paths.
    CNFO keeps that semantic form while resolving those IRIs against the local
    module directory, so development and release builds remain deterministic.
    Unknown imports are intentionally ignored instead of being fetched.
    """
    entry_path = Path(source_path).expanduser().resolve()
    if not entry_path.is_file():
        raise FileNotFoundError(f"Ontology source not found: {entry_path}")

    parsed: dict[Path, Graph] = {}
    ontology_to_path: dict[str, Path] = {}
    for path in _candidate_module_paths(entry_path):
        graph = Graph()
        graph.parse(path, format="turtle")
        parsed[path] = graph
        for ontology in graph.subjects(RDF.type, OWL.Ontology):
            ontology_to_path.setdefault(str(ontology), path)

    if entry_path not in parsed:
        graph = Graph()
        graph.parse(entry_path, format="turtle")
        parsed[entry_path] = graph

    combined = Graph()
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in visited:
            return
        graph = parsed.get(path)
        if graph is None:
            graph = Graph()
            graph.parse(path, format="turtle")
            parsed[path] = graph
        visited.add(path)
        for triple in graph:
            combined.add(triple)
        imports = {
            str(import_iri)
            for ontology in graph.subjects(RDF.type, OWL.Ontology)
            for import_iri in graph.objects(ontology, OWL.imports)
        }
        for import_iri in sorted(imports):
            imported_path = ontology_to_path.get(import_iri)
            if imported_path is not None:
                visit(imported_path)

    visit(entry_path)
    return combined
