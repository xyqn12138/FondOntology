"""Build and ingest the FIBO production T-BOX through a local OASIS catalog."""

from __future__ import annotations

import argparse
import json
import os
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS


FIBO_BASE_IRI = "https://spec.edmcouncil.org/fibo/ontology/"
CATALOG_NS = "urn:oasis:names:tc:entity:xmlns:xml:catalog"


@dataclass(frozen=True)
class FiboTBoxConfig:
    """Paths and output settings for the FIBO production T-BOX."""

    fibo_root: Path
    entrypoint: str = "AboutFIBOProd-TBoxOnly.rdf"
    output_path: Path = Path("artifacts/fibo/fibo-prod-tbox.ttl")
    manifest_path: Path = Path("artifacts/fibo/fibo-prod-tbox-manifest.json")
    external_cache_path: Path = Path("artifacts/fibo/external")
    fetch_external: bool = False
    allow_unresolved: bool = False


class FiboTBox:
    """Resolve, merge, serialize, and ingest the FIBO production T-BOX."""

    def __init__(self, config: FiboTBoxConfig):
        self.config = config
        self.fibo_root = config.fibo_root.expanduser().resolve()
        self.catalog_path = self.fibo_root / "catalog-v001.xml"
        self.catalog = self._load_catalog()
        self.external_cache_path = self._project_path(config.external_cache_path)

    def _load_catalog(self) -> dict[str, Path]:
        if not self.catalog_path.is_file():
            raise FileNotFoundError(f"FIBO catalog not found: {self.catalog_path}")

        tree = ET.parse(self.catalog_path)
        mappings: dict[str, Path] = {}
        for element in tree.getroot().iter(f"{{{CATALOG_NS}}}uri"):
            iri = element.attrib.get("name")
            relative_path = element.attrib.get("uri")
            if not iri or not relative_path:
                continue
            local_path = (self.catalog_path.parent / relative_path).resolve()
            if local_path.is_file():
                mappings[iri] = local_path
        return mappings

    def _resolve_import(self, iri: str, source_path: Path) -> Path | None:
        """Resolve an ontology IRI using the catalog, cache, or optional fetch."""
        if iri in self.catalog:
            return self.catalog[iri]

        cached_path = self._external_cache_file(iri)
        if cached_path.is_file():
            return cached_path

        parsed = urlparse(iri)
        if self.config.fetch_external and parsed.scheme in {"http", "https"}:
            return self._fetch_external(iri, cached_path)

        if parsed.scheme in {"http", "https"} and iri.startswith(FIBO_BASE_IRI):
            candidate = (self.fibo_root / iri.removeprefix(FIBO_BASE_IRI)).with_suffix(".rdf")
            if candidate.is_file():
                return candidate.resolve()

        relative_candidate = (source_path.parent / iri).resolve()
        if relative_candidate.is_file() and self._is_allowed_source(relative_candidate):
            return relative_candidate
        return None

    def _external_cache_file(self, iri: str) -> Path:
        digest = hashlib.sha256(iri.encode("utf-8")).hexdigest()[:16]
        local_name = urlparse(iri).path.rstrip("/").split("/")[-1] or "ontology"
        return self.external_cache_path / f"{local_name}-{digest}.rdf"

    def _fetch_external(self, iri: str, destination: Path) -> Path:
        parsed = urlparse(iri)
        if parsed.netloc not in {"www.omg.org", "spec.edmcouncil.org"}:
            raise ValueError(f"Refusing to fetch an unapproved ontology host: {parsed.netloc}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        request = Request(iri, headers={"User-Agent": "FondOntology-FIBO-TBox/0.1"})
        with urlopen(request, timeout=60) as response:
            content = response.read()
        destination.write_bytes(content)
        return destination

    def _is_allowed_source(self, path: Path) -> bool:
        try:
            path.relative_to(self.fibo_root)
            return True
        except ValueError:
            try:
                path.relative_to(self.external_cache_path.resolve())
            except ValueError:
                return False
            return True

    def _parse_closure(self) -> tuple[Graph, list[Path], list[str]]:
        entrypoint = (self.fibo_root / self.config.entrypoint).resolve()
        if not entrypoint.is_file():
            raise FileNotFoundError(f"FIBO T-BOX entrypoint not found: {entrypoint}")

        graph = Graph()
        visited: set[Path] = set()
        queue: list[Path] = [entrypoint]
        unresolved: list[str] = []

        while queue:
            current = queue.pop()
            if current in visited:
                continue
            if not self._is_allowed_source(current):
                raise ValueError(f"Refusing to load a file outside approved ontology roots: {current}")

            visited.add(current)
            source_graph = Graph()
            public_id = current.as_uri()
            source_graph.parse(current, format="xml", publicID=public_id)
            graph += source_graph

            for imported_iri in source_graph.objects(None, OWL.imports):
                imported_path = self._resolve_import(str(imported_iri), current)
                if imported_path is None:
                    unresolved.append(str(imported_iri))
                elif imported_path not in visited:
                    queue.append(imported_path)

        return graph, sorted(visited), sorted(set(unresolved))

    def build(self) -> dict[str, object]:
        graph, files, unresolved = self._parse_closure()
        output_path = self._project_path(self.config.output_path)
        manifest_path = self._project_path(self.config.manifest_path)
        if unresolved and not self.config.allow_unresolved:
            raise ValueError(
                "T-BOX has unresolved imports. Run with --fetch-external or explicitly use "
                "--allow-unresolved. Missing imports: " + ", ".join(unresolved)
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        graph.serialize(destination=output_path, format="turtle")
        class_count = len(set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class)))
        object_property_count = len(set(graph.subjects(RDF.type, OWL.ObjectProperty)))
        datatype_property_count = len(set(graph.subjects(RDF.type, OWL.DatatypeProperty)))
        manifest = {
            "entrypoint": str((self.fibo_root / self.config.entrypoint).resolve()),
            "catalog": str(self.catalog_path),
            "fibo_root": str(self.fibo_root),
            "source_file_count": len(files),
            "triple_count": len(graph),
            "class_count": class_count,
            "object_property_count": object_property_count,
            "datatype_property_count": datatype_property_count,
            "unresolved_imports": unresolved,
            "external_cache_path": str(self.external_cache_path),
            "fetch_external": self.config.fetch_external,
            "output_path": str(output_path),
            "source_files": [str(path) for path in files],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def ingest_with_semantica(self):
        """Build the local artifact and pass it through Semantica's ontology API."""
        from semantica.ontology import ingest_ontology

        manifest = self.build()
        ontology = ingest_ontology(manifest["output_path"], method="file", format="turtle")
        return manifest, ontology

    def _project_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def inspect(self) -> dict[str, object]:
        graph, files, unresolved = self._parse_closure()
        return {
            "entrypoint": str((self.fibo_root / self.config.entrypoint).resolve()),
            "catalog": str(self.catalog_path),
            "source_file_count": len(files),
            "triple_count": len(graph),
            "class_count": len(
                set(graph.subjects(RDF.type, OWL.Class))
                | set(graph.subjects(RDF.type, RDFS.Class))
            ),
            "unresolved_imports": unresolved,
            "external_cache_path": str(self.external_cache_path),
            "fetch_external": self.config.fetch_external,
        }


def default_fibo_root() -> Path:
    return Path(
        os.environ.get(
            "FIBO_ROOT",
            r"E:\LX\LX_fund\基金行业文档\D_国际标准参考\FIBO\FIBO registry\fibo",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the FIBO production T-BOX for Semantica")
    parser.add_argument("command", choices=["inspect", "build", "ingest"])
    parser.add_argument("--fibo-root", type=Path, default=default_fibo_root())
    parser.add_argument("--entrypoint", default="AboutFIBOProd-TBoxOnly.rdf")
    parser.add_argument("--output", type=Path, default=Path("artifacts/fibo/fibo-prod-tbox.ttl"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fibo/fibo-prod-tbox-manifest.json"))
    parser.add_argument("--external-cache", type=Path, default=Path("artifacts/fibo/external"))
    parser.add_argument("--fetch-external", action="store_true", help="Fetch missing OMG/LCC imports into the local cache")
    parser.add_argument("--allow-unresolved", action="store_true", help="Build even when imports cannot be resolved")
    return parser


def run(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    config = FiboTBoxConfig(
        fibo_root=args.fibo_root,
        entrypoint=args.entrypoint,
        output_path=args.output,
        manifest_path=args.manifest,
        external_cache_path=args.external_cache,
        fetch_external=args.fetch_external,
        allow_unresolved=args.allow_unresolved,
    )
    tbox = FiboTBox(config)

    if args.command == "inspect":
        print(json.dumps(tbox.inspect(), indent=2))
    elif args.command == "build":
        print(json.dumps(tbox.build(), indent=2))
    else:
        manifest, ontology = tbox.ingest_with_semantica()
        print(json.dumps({
            "manifest": manifest,
            "semantica": {
                "ontology_uri": ontology.data.get("uri"),
                "class_count": len(ontology.data.get("classes", [])),
                "property_count": len(ontology.data.get("properties", [])),
            },
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
