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
    """读取 LLM 配置；兼容常见别名：MODEL↔OPENAI_MODEL、API_BASE↔OPENAI_BASE_URL。

    LLM_THINKING=false（默认）时关闭推理模型的深度思考：意图解析/表达是
    结构化任务，thinking 只会把秒级响应拖成分钟级（实测 145s+）。
    支持 Ark/DeepSeek 的 thinking={"type":"disabled"} 与通义的
    enable_thinking=false 两种参数形态，由 LLM_THINKING_PARAM 切换。
    """
    return {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "").strip(),
        "OPENAI_BASE_URL": (os.environ.get("OPENAI_BASE_URL")
                            or os.environ.get("API_BASE") or "").strip(),
        "OPENAI_MODEL": (os.environ.get("OPENAI_MODEL")
                         or os.environ.get("MODEL") or "").strip(),
        "THINKING": (os.environ.get("LLM_THINKING") or "false").strip().lower(),
        "THINKING_PARAM": (os.environ.get("LLM_THINKING_PARAM")
                           or "auto").strip().lower(),
    }


def llm_thinking_override() -> dict:
    """关闭深度思考需要并入请求体的额外字段（空 dict = 保持服务商默认）。"""
    cfg = llm_config()
    if cfg["THINKING"] in ("1", "true", "on", "enabled"):
        return {}
    param = cfg["THINKING_PARAM"]
    if param in ("auto", "ark", "deepseek", "thinking"):
        return {"thinking": {"type": "disabled"}}
    if param in ("qwen", "dashscope", "enable_thinking"):
        return {"enable_thinking": False}
    return {}


def llm_configured() -> bool:
    cfg = llm_config()
    return bool(cfg["OPENAI_API_KEY"] and cfg["OPENAI_BASE_URL"] and cfg["OPENAI_MODEL"])