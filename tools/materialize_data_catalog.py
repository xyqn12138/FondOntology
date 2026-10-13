"""Restore full-text derivatives and source_catalog from explicit offline recovery records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.corpus.data_materialize import materialize_data


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--source-manifest", action="append")
    parser.add_argument("--mineru-state", action="append")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = materialize_data(args.data_root, source_paths=args.source_manifest,
                                  state_paths=args.mineru_state, write=args.write)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
