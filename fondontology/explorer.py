"""Run the independent CNFO ontology viewer (served standalone)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in {None, ""}:
    # Allow direct file execution as well as module execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve the independent CNFO ontology viewer"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument(
        "--ttl",
        type=Path,
        default=Path("artifacts/cnfo/cnfo-fund-tbox.ttl"),
        help="Independent CNFO Turtle ontology used by the class-centric viewer",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if __package__ in {None, ""}:
        from fondontology.viewer import OntologyViewerSession, create_viewer_app
    else:
        from .viewer import OntologyViewerSession, create_viewer_app
    import uvicorn

    session = OntologyViewerSession(args.ttl)
    uvicorn.run(
        create_viewer_app(session),
        host=args.host,
        port=args.port,
        log_level="info",
        timeout_graceful_shutdown=5,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
