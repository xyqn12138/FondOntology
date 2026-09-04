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
    """读取 LLM 配置；兼容常见别名：MODEL↔OPENAI_MODEL、API_BASE↔OPENAI_BASE_URL。"""
    return {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "").strip(),
        "OPENAI_BASE_URL": (os.environ.get("OPENAI_BASE_URL")
                            or os.environ.get("API_BASE") or "").strip(),
        "OPENAI_MODEL": (os.environ.get("OPENAI_MODEL")
                         or os.environ.get("MODEL") or "").strip(),
    }


def llm_configured() -> bool:
    cfg = llm_config()
    return bool(cfg["OPENAI_API_KEY"] and cfg["OPENAI_BASE_URL"] and cfg["OPENAI_MODEL"])