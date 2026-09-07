from __future__ import annotations

import sys

from .cnfo_tbox import main as run_cnfo


def main(argv: list[str] | None = None) -> int:
    """Use the browser by default and retain the ontology build CLI."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"inspect", "build", "export-explorer"}:
        return run_cnfo(args)
    if args and args[0] in {"web", "serve-qa"}:
        from .webui import run as run_webui

        return run_webui(args[1:])
    from .explorer import run as run_explorer

    return run_explorer(args[1:] if args and args[0] in {"viewer", "serve"} else args)
