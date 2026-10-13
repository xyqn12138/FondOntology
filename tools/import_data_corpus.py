"""Import only verified ready entries from data/source_catalog.json, without network."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.corpus.data_catalog import artifact_output, build_catalog_records


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("data/source_catalog.json"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--document-id", action="append")
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--import-ready", action="store_true")
    parser.add_argument("--snapshot-id")
    parser.add_argument("--index-version", default="data-body-bm25-v1")
    args = parser.parse_args(argv)
    try:
        manifest = artifact_output(args.manifest_out, data_root=args.data_root) if args.manifest_out else None
        database = artifact_output(args.db, data_root=args.data_root) if args.db else None
        if database is not None and database == manifest:
            raise ValueError("Database and manifest must use separate artifact paths")
        if args.import_ready and (manifest is None or database is None or not args.snapshot_id):
            raise ValueError("--import-ready requires --manifest-out, --db and --snapshot-id")
        result = build_catalog_records(args.catalog, data_root=args.data_root,
                                       document_ids=args.document_id)
        if args.import_ready and not result["records"]:
            raise ValueError("Catalog has no ready documents; no fallback is permitted")
        if manifest:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n"
                                        for record in result["records"]), encoding="utf-8")
        output = {"catalog_sha256": result["catalog_sha256"], "ready": len(result["records"]),
                  "skipped": result["skipped"], "dry_run": not args.import_ready,
                  "documents": [record["doc_id"] for record in result["records"]]}
        if args.import_ready:
            repository = CorpusRepository(database)
            imported = repository.import_manifest(manifest)
            snapshot = repository.publish_snapshot(args.snapshot_id, imported["version_ids"],
                                                   kind="trusted", index_version=args.index_version)
            output.update({"import": imported, "snapshot": snapshot,
                           "verification": repository.verify_snapshot(args.snapshot_id)})
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (CorpusError, OSError, ValueError, UnicodeDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
