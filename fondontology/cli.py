from __future__ import annotations

import sys

from .fibo_tbox import run as run_fibo


def main(argv: list[str] | None = None) -> int:
    """Use the browser by default and retain the ontology build CLI."""
    args = list(sys.argv[1:] if argv is None else argv)
    fibo_commands = {"inspect", "build", "ingest", "export-explorer"}
    fibo_options = {
        "--fibo-root",
        "--entrypoint",
        "--output",
        "--manifest",
        "--explorer-output",
        "--external-cache",
        "--fetch-external",
        "--allow-unresolved",
    }
    uses_fibo_cli = any(
        argument in fibo_commands or argument.split("=", 1)[0] in fibo_options
        for argument in args
    )
    if not uses_fibo_cli:
        from .explorer import run as run_explorer

        return run_explorer(args[1:] if args and args[0] in {"viewer", "serve"} else args)
    return run_fibo(args)
