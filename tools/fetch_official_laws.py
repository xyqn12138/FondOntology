"""Download only pinned official HTML sources, then prepare an offline manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.corpus.official_sources import prepare_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("evaluation/corpora/official-laws-v1.sources.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/official-laws-v1"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args(argv)
    try:
        outputs = [args.manifest.resolve(), args.report.resolve()]
        if (len(set(outputs)) != len(outputs) or args.registry.resolve() in outputs
                or any(path.is_relative_to(args.output_dir.resolve()) for path in outputs)):
            raise ValueError("Manifest/report must be separate from registry and cached sources")
        result = prepare_sources(args.registry, args.output_dir, download=args.download)
        for path in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text("".join(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
                                         for record in result["records"]), encoding="utf-8")
        args.report.write_text(json.dumps({key: result[key] for key in ("report", "registry_sha256")},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"documents": len(result["records"]), "report": result["report"]}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as error:
        print(f"Official acquisition failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
