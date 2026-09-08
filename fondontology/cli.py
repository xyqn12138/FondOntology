from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """智能问数 Web UI 为默认入口；viewer 可独立启动。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "viewer":
        from .explorer import run as run_explorer

        return run_explorer(args[1:])
    from .webui import run as run_webui

    return run_webui(args)
