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


def rag_enabled() -> bool:
    """RAG explain 扩展总开关（M7-R3b 起默认开启）。

    LLM 表达接入完成（R3b）：describe/regulation/code 走闸门+短语核查，
    模板回退兜底，答案观感达到演示标准，故默认开启。
    define/compare/classify 是一等能力不受本开关控制（读 T-BOX）。
    关闭方式：.env 设 RAG_ENABLED=0（或 false/off）。
    """
    raw = os.environ.get("RAG_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "off", "disabled", "")


def _env(*keys: str) -> str:
    """大小写不敏感地读环境变量（.env 里 EMBEDDING_MODEL/embedding_model 混用兼容）。"""
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v.strip()
    # 全量扫描兜底（键大小写不定）
    lower_map = {k.lower(): v for k, v in os.environ.items()}
    for k in keys:
        v = lower_map.get(k.lower())
        if v:
            return v.strip()
    return ""


def embedding_config() -> dict:
    """Embedding 检索配置（M7-R4）。

    键（大小写不敏感，兼容 embedding_MODEL/EMBEDDING_MODEL 等写法）：
    - EMBEDDING_MODEL：模型名（如 qwen3.7-text-embedding-flash）
    - EMBEDDING_URL / EMBEDDING_BASE_URL：OpenAI 兼容 /embeddings 基址；
      回退链：DASHSCORE_URL（阿里 MaaS compatible-mode）→ OPENAI_BASE_URL
    - EMBEDDING_KEY / EMBEDDING_API_KEY：鉴权；回退 DASHSCORE_API_KEY → OPENAI_API_KEY
    """
    _reload_dotenv()
    model = _env("EMBEDDING_MODEL", "embedding_model", "embedding_MODEL")
    url = _env("EMBEDDING_URL", "EMBEDDING_BASE_URL",
               "embedding_URL", "embedding_BASE_URL") \
        or _env("DASHSCORE_URL", "dashscore_URL") \
        or _env("OPENAI_BASE_URL")
    key = _env("EMBEDDING_KEY", "EMBEDDING_API_KEY",
               "embedding_KEY", "embedding_API_KEY") \
        or _env("DASHSCORE_API_KEY", "dashscore_API_KEY") \
        or _env("OPENAI_API_KEY")
    return {"EMBEDDING_MODEL": model, "EMBEDDING_URL": url, "EMBEDDING_KEY": key}


def embedding_configured() -> bool:
    cfg = embedding_config()
    return bool(cfg["EMBEDDING_MODEL"] and cfg["EMBEDDING_URL"] and cfg["EMBEDDING_KEY"])


# rerank 端点：MaaS 实例无 OpenAI 兼容 /rerank（实测 404），
# 唯一可用路径为同 host 的原生协议 text-rerank（对扁平 payload 也兼容）
_NATIVE_RERANK_PATH = "/api/v1/services/rerank/text-rerank/text-rerank"


def rerank_config() -> dict:
    """Rerank 配置（M7-R4 扩展）。

    - RERANK_MODEL：模型名（如 qwen3.7-text-rerank）
    - 端点：默认从 DASHSCORE_URL 的 host 推导（{host}/api/v1/services/
      rerank/text-rerank/text-rerank）；RERANK_URL 可整体覆盖
    - 鉴权：KEY 回退链 RERANK_KEY → DASHSCORE_API_KEY → EMBEDDING_KEY
      → OPENAI_API_KEY
    """
    _reload_dotenv()
    model = _env("RERANK_MODEL", "rerank_model", "rerank_MODEL")
    key = _env("RERANK_KEY", "RERANK_API_KEY", "rerank_KEY") \
        or _env("DASHSCORE_API_KEY", "dashscore_API_KEY") \
        or _env("EMBEDDING_KEY") or _env("OPENAI_API_KEY")
    url = _env("RERANK_URL", "rerank_URL")
    if not url:
        from urllib.parse import urlparse
        base = _env("DASHSCORE_URL", "dashscore_URL") or _env("OPENAI_BASE_URL")
        if base:
            parsed = urlparse(base.rstrip("/"))
            url = f"{parsed.scheme}://{parsed.netloc}{_NATIVE_RERANK_PATH}"
    return {"RERANK_MODEL": model, "RERANK_URL": url, "RERANK_KEY": key}


def rerank_configured() -> bool:
    cfg = rerank_config()
    return bool(cfg["RERANK_MODEL"] and cfg["RERANK_URL"] and cfg["RERANK_KEY"])


def _reload_dotenv() -> None:
    """运行中重读 .env（load_dotenv 仅 import 时执行一次）。"""
    try:
        from dotenv import dotenv_values
        raw = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
        for k, v in (raw or {}).items():
            os.environ.setdefault(k, v if v is not None else "")
    except Exception:
        pass