"""QA 配置：.env 读取（OpenAI 兼容，仅 M4 意图解构使用）。"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:  # pragma: no cover - dotenv 缺失时退化为环境变量
    pass

_KEYS = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")


def llm_config() -> dict:
    return {k: os.environ.get(k, "").strip() for k in _KEYS}


def llm_configured() -> bool:
    cfg = llm_config()
    return bool(cfg["OPENAI_API_KEY"] and cfg["OPENAI_BASE_URL"] and cfg["OPENAI_MODEL"])