# -*- coding: utf-8 -*-
"""CNFO 智能问数 Web UI（M6）启动入口。

用法：
    .venv\\Scripts\\python.exe tools\\qa_web.py
    .venv\\Scripts\\python.exe tools\\qa_web.py --port 8000
    .venv\\Scripts\\python.exe tools\\qa_web.py --no-llm
    python -m fondontology web --port 8000

选项：--source（QA T-BOX 入口）、--abox（A-BOX TTL）、--viewer-ttl（查看器 T-BOX）、
      --host / --port、--no-llm（强制模板表达）
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondontology.webui import run


if __name__ == "__main__":
    raise SystemExit(run())
