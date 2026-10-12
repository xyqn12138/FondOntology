"""Compare named actual artifacts with a fixed corpus and source-authored oracle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.evaluation.retrieval_comparison import compare_runs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-db", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--run", action="append", required=True, help="NAME=ACTUAL_JSON")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        runs = {}
        protected = [args.corpus_db, args.questions, args.oracle]
        for declaration in args.run:
            name, separator, filename = declaration.partition("=")
            if not separator or not name or not filename or name in runs:
                raise ValueError("Run declarations must have unique nonempty NAME=FILE")
            path = Path(filename)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            trace_path = Path(envelope["provenance"]["trace_path"])
            protected.extend([path, trace_path if trace_path.is_absolute() else path.parent / trace_path])
            runs[name] = path
        if any(args.output.resolve() == path.resolve()
               or (args.output.exists() and path.exists() and args.output.samefile(path))
               for path in protected):
            raise ValueError("Comparison output must not overwrite its inputs")
        result = compare_runs(args.corpus_db, args.questions, args.oracle, runs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                               encoding="utf-8")
        print(json.dumps({"output": str(args.output.resolve()), "runs": list(runs), "acceptance": False}))
        return 0
    except (ValueError, KeyError, OSError) as error:
        print(f"Comparison unavailable ({type(error).__name__}); details withheld", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
