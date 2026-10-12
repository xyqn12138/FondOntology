"""Offline document corpus management; never changes TBOX or ABOX."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.corpus import CorpusError, CorpusRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    importer = commands.add_parser("import")
    importer.add_argument("manifest", type=Path)
    publisher = commands.add_parser("publish")
    publisher.add_argument("snapshot_id")
    publisher.add_argument("version_ids", nargs="+")
    publisher.add_argument("--kind", choices=("trusted", "research", "regression"), default="trusted")
    publisher.add_argument("--index-version", default="bm25-2gram-v1")
    lister = commands.add_parser("list")
    lister.add_argument("--versions", action="store_true")
    verifier = commands.add_parser("verify")
    verifier.add_argument("snapshot_id")
    arguments = parser.parse_args(argv)
    try:
        repository = (CorpusRepository(arguments.db) if arguments.command == "init"
                      else CorpusRepository.open_existing(arguments.db))
        if arguments.command == "init":
            result = {"db": str(repository.db_path), "initialized": True}
        elif arguments.command == "import":
            result = repository.import_manifest(arguments.manifest)
        elif arguments.command == "publish":
            result = repository.publish_snapshot(
                arguments.snapshot_id, arguments.version_ids, kind=arguments.kind,
                index_version=arguments.index_version,
            )
        elif arguments.command == "list":
            result = repository.list_versions() if arguments.versions else repository.list_snapshots()
        else:
            result = repository.verify_snapshot(arguments.snapshot_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get("ok") is False else 0
    except (CorpusError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
