"""Legacy Markdown audit/selection import for frozen benchmark reproduction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.corpus import CorpusError, CorpusRepository
from fondontology.corpus.markdown_inventory import (
    build_repository_records,
    inventory_markdown,
    load_selection,
)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--import-selected", action="store_true")
    parser.add_argument("--kind", choices=("research", "trusted"))
    parser.add_argument("--snapshot-id")
    parser.add_argument("--index-version", default="bm25-2gram-v1")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        outputs = [path.resolve() for path in (args.report, args.manifest_out) if path]
        if any(path.is_relative_to(root) for path in outputs):
            raise ValueError("Audit output and generated manifest must be outside the source root")
        if len(outputs) != len(set(outputs)):
            raise ValueError("Report and generated manifest must use separate output paths")
        if args.selection and args.selection.resolve() in outputs:
            raise ValueError("Outputs must not overwrite the selection manifest")
        if args.db and (args.db.resolve().is_relative_to(root)
                        or args.db.resolve() in outputs
                        or args.selection and args.db.resolve() == args.selection.resolve()):
            raise ValueError("Database must be separate from sources, selection, and outputs")
        if args.import_selected and not args.selection:
            raise ValueError("--selection is required with --import-selected")
        report = inventory_markdown(args.root)
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.selection:
            return 0
        selections = load_selection(args.selection)
        records = build_repository_records(args.root, selections)
        print(json.dumps({"selection": {"count": len(records), "dry_run": not args.import_selected,
                                       "kind": args.kind, "documents": records}},
                         ensure_ascii=False, indent=2))
        if args.kind:
            for record in records:
                if args.kind == "trusted" and (
                    record["authority"] != "authoritative_original"
                    or record["status"] != "verified" or not record["issued_date"]
                ):
                    raise ValueError("trusted requires verified originals with an explicit issued_date")
                if args.kind == "research" and (
                    record["authority"] != "research_note" or record["status"] == "quarantined"
                ):
                    raise ValueError("research requires non-quarantined research_note selections")
        if args.manifest_out:
            args.manifest_out.write_text(
                "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
                encoding="utf-8",
            )
        if args.import_selected:
            if not args.db:
                raise ValueError("--db is required with --import-selected")
            if not args.manifest_out:
                raise ValueError("--manifest-out is required with --import-selected")
            if not args.kind or not args.snapshot_id:
                raise ValueError("--kind and --snapshot-id are required with --import-selected")
            repository = CorpusRepository(args.db)
            result = repository.import_manifest(args.manifest_out)
            snapshot = repository.publish_snapshot(
                args.snapshot_id, result["version_ids"], kind=args.kind,
                index_version=args.index_version,
            )
            print(json.dumps({"import": result, "snapshot": snapshot,
                              "verification": repository.verify_snapshot(args.snapshot_id)},
                             ensure_ascii=False, indent=2))
        return 0
    except (CorpusError, OSError, ValueError, UnicodeDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
