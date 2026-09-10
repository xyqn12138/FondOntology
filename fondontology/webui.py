# -*- coding: utf-8 -*-
"""CNFO 智能问数 Web UI（M6）：FastAPI + 单页 HTML。

界面布局模仿常见 AI 聊天工具（ChatGPT 风格）：
- 左侧边栏：智能问数 / 本体查看器 两个模块，客户端切换（仅替换主区内容，不整页跳转）；
- 智能问数：聊天主区 + 推荐问题 + 流式答案（SSE）+ 证据溯源折叠面板；
- 本体查看器：复用 fondontology.viewer 的 OntologyViewerSession，其页面
  （/viewer/?embed=1）通过 iframe 内嵌进主区；API 路由注册在根域（同源可调），
  查看器前端零改动。

问答接口：
- POST /api/qa/ask                 JSON 问答（一次返回完整答案，便于 curl/测试）
- GET  /api/qa/ask/stream?q=...    SSE 流式问答（phase 阶段 + delta 增量文本 + answer 终态）
- GET  /api/meta                   系统/本体/数据/LLM 状态
- GET  /api/qa/suggestions         推荐问题
- GET  /viewer/                    本体查看器页面（iframe 内嵌用 ?embed=1；也可独立访问）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse, StreamingResponse)
from pydantic import BaseModel, Field

from . import viewer as viewer_mod
from .qa.config import llm_config, llm_configured, rag_enabled
from .qa.engine import QaAnswer, answer_question
from .qa.graph import DataStack, build_stack

UI_DIR = Path(__file__).with_name("ui_static")
_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TBOX = _ROOT / "ontology" / "modules" / "cnfo-domain.ttl"
DEFAULT_ABOX = _ROOT / "artifacts" / "cnfo" / "abox" / "cnfo-sim-abox.ttl"
DEFAULT_VIEWER_TTL = _ROOT / "artifacts" / "cnfo" / "cnfo-fund-tbox.ttl"

# 推荐问题：全部在确定性路径实测可答（无 key 也能跑通）；
# LLM 启用时意图解构覆盖面更广，可自行追加。
SUGGESTIONS = [
    {"q": "交易型开放式指数基金有哪些？",
     "hint": "分类列举 · find"},
    {"q": "货币市场基金有哪些？",
     "hint": "分类列举 · find"},
    {"q": "有多少只开放式基金？",
     "hint": "计数 · find"},
    {"q": "同时管理多只基金的基金经理是谁？",
     "hint": "聚合 + 排名 · aggregate"},
    {"q": "魏辉管理的基金有什么？",
     "hint": "实体锚点 + 推理 · find"},
    {"q": "R4以上的基金有哪些？",
     "hint": "属性过滤 · find"},
    {"q": "交易型开放式指数基金是不是开放式基金？",
     "hint": "T-BOX 判链 · verify"},
]


# 常用系统谓词的中文译名（RDF/RDFS/OWL 命名空间内固定映射）
_PRED_ZH = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "类型是",
    "http://www.w3.org/2000/01/rdf-schema#subClassOf": "子类于",
    "http://www.w3.org/2000/01/rdf-schema#label": "名称",
    "http://www.w3.org/2002/07/owl#equivalentClass": "等价于",
    "http://www.w3.org/2002/07/owl#disjointWith": "互斥于",
    "http://www.w3.org/2002/07/owl#inverseOf": "互逆于",
}
_CNFO_NS = "https://ontology.example.cn/cnfo/ontology/"
_CNFOA_NS = "https://ontology.example.cn/cnfo/abox/"


def _translate_evidence(ans: QaAnswer, stack) -> None:
    """证据 source 三元组的 IRI 翻译为中文（展示层友好）。

    就地给 report.evidence 每条加 source_zh（与 source 并存：原文保留可审计，
    展示用翻译）。实体 → A-BOX label；类/属性 → T-BOX label；系统谓词 →
    固定译名表；无法翻译 → 本地名（去掉命名空间的最后一段）。
    """
    rep = ans.report
    if not rep or not rep.get("evidence"):
        return
    from rdflib import RDFS, SKOS, URIRef

    def _zh(iri: str) -> str:
        if not iri or not iri.startswith("http"):
            return str(iri)
        if iri in _PRED_ZH:
            return _PRED_ZH[iri]
        # 属性优先（cnfo 命名空间下属性与类同名空间，先查属性 label）
        u = URIRef(iri)
        for g in (stack.tbox, stack.abox):
            for pred in (SKOS.prefLabel, RDFS.label):
                for o in g.objects(u, pred):
                    return str(o)
        # 剩余：本地名兜底
        return iri.rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1]

    for ev in rep["evidence"]:
        src = ev.get("source")
        if not isinstance(src, list) or not src:
            continue
        # 典型形态：[主语IRI, 谓词IRI, 宾语IRI]（declared/inference）
        # 或 [kind, targetIRI]（query）；仅对 3 元组形态翻译
        if len(src) >= 3 and all(isinstance(x, str) for x in src[:3]):
            ev["source_zh"] = [ _zh(src[0]), _zh(src[1]), _zh(src[2]) ]
        elif ev.get("kind") == "query" and len(src) >= 2:
            ev["source_zh"] = ["查询", _zh(src[1])]
        # 其余形态不翻译（chunk locator 等自有展示逻辑）


def _qa_answer_dict(ans: QaAnswer) -> dict:
    """QaAnswer → 可 JSON 序列化的 dict（report/explanation 均为纯 JSON 结构）。"""
    return {
        "kind": ans.kind,
        "status": ans.status,
        "text": ans.text,
        "claims": list(ans.claims),
        "cited_evidence": list(ans.cited_evidence),
        "report": ans.report,
        "local_context": ans.local_context,
        "verdict": ans.verdict,
        "explanation": ans.explanation,
        "intent_status": ans.intent_status,
        "rewritten_question": getattr(ans, "rewritten_question", None),
    }


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


class AskRequest(BaseModel):
    question: str = Field(default="")
    use_llm: Optional[bool] = None
    context: Optional[dict] = None   # 对话上文（指代消解）：last_question/last_answer/last_entities


def _context_entities(ans) -> list[str]:
    """从答案中提取本轮话题实体（下轮指代消解的上文候选）。

    提取优先级（可靠性降序）：
    1. 结果实体（report._inner.entity_labels——find 类查询返回的对象，
       『这个基金』通常指代它，而非提问锚定的人）；
    2. 锚定实体（plan.source.entity 的 IRI → entity_labels 反查，
       describe 类锚定的基金/经理）；
    3. explain 的意图锚点（entity_anchors）；
    4. compare_entities 模板的来源标记（「X：…」行首）。
    历史教训：不按冒号切普通答案文本兜底（曾把半句话当实体污染 coref）。
    """
    ents: list[str] = []
    rep = ans.report or {}
    labels: dict = (rep.get("_inner") or {}).get("entity_labels") or {}
    # 1) 结果实体（查询命中的对象）
    for label in list(labels.values()):
        if label:
            ents.append(label)
    # 2) 锚定实体（IRI 反查 label；结果与锚点相同时去重）
    src = (rep.get("plan") or {}).get("source") or {}
    anchor_iri = src.get("entity") if isinstance(src, dict) else None
    if anchor_iri:
        label = labels.get(anchor_iri)
        if label and label not in ents:
            ents.append(label)
    # 3) explain 意图锚点
    for a in (rep.get("entity_anchors") or []):
        if isinstance(a, dict) and a.get("label") and a["label"] not in ents:
            ents.append(a["label"])
    # 4) compare_entities 模板来源标记
    if not ents:
        for line in (ans.text or "").split("\n")[:3]:
            if "：" in line and 3 <= len(line.split("：")[0]) <= 20:
                head = line.split("：")[0].strip("（")
                if 3 <= len(head) <= 20 and not any(c in head for c in "？?，。"):
                    ents.append(head)
                    break
    return ents[:2]


def create_web_app(*,
                   tbox_source: Path = DEFAULT_TBOX,
                   abox_ttl: Optional[Path] = DEFAULT_ABOX,
                   viewer_ttl: Path = DEFAULT_VIEWER_TTL,
                   stack: Optional[DataStack] = None,
                   viewer_session=None,
                   default_use_llm: Optional[bool] = None) -> FastAPI:
    """构建统一 Web 应用（智能问数 + 本体查看器模块）。

    可传入预先构建的 stack / viewer_session（测试复用，避免重复加载数据）。
    """
    if stack is None:
        stack = build_stack(tbox_source, abox_ttl)
    if viewer_session is None:
        viewer_session = viewer_mod.OntologyViewerSession(viewer_ttl)

    if not UI_DIR.is_dir():
        raise FileNotFoundError(f"UI assets not found: {UI_DIR}")

    app = FastAPI(title="CNFO 智能问数", version="0.1.0", docs_url=None,
                  redoc_url=None, openapi_url=None)

    # 问答执行串行化：engine 的索引/推理缓存不是线程安全的，
    # 本地单用户场景用一把全局锁把 QA 执行排成队列即可。
    qa_lock = threading.Lock()
    _entity_count_cache: dict = {}

    def _abox_entity_count() -> int:
        if "count" not in _entity_count_cache:
            try:
                from rdflib import RDF
                g = stack.abox
                n = len({s for s in g.subjects(RDF.type, None)})
            except Exception:
                n = 0
            _entity_count_cache["count"] = n
        return _entity_count_cache["count"]

    # ------------------------------------------------------------------
    # 元信息与推荐问题
    # ------------------------------------------------------------------
    @app.get("/api/meta")
    def api_meta():
        summary = viewer_session.summary()
        cfg = llm_config()
        configured = llm_configured()
        rag = rag_enabled()
        return {
            "app": "CNFO 智能问数",
            "module": "qa",
            "ontology": {
                "iri": stack.snapshot.ontology_iri,
                "version": stack.snapshot.ontology_version,
                "hash": stack.snapshot.ontology_hash,
                "class_count": summary["class_count"],
                "property_count": summary["property_count"],
                "module_count": summary["module_count"],
            },
            "data": {
                "abox_file": Path(stack.snapshot.abox_file).name,
                "abox_hash": stack.snapshot.abox_hash,
                "entity_count": _abox_entity_count(),
            },
            "llm": {
                "configured": configured,
                "model": cfg["OPENAI_MODEL"] or "",
                "base_url": cfg["OPENAI_BASE_URL"] or "",
                "mode": "llm" if configured else "template",
            },
            "rag": {
                "enabled": rag,
                "toggleable": True,
            },
            "engine": {
                "default_use_llm": default_use_llm,
                "suggestion_count": len(SUGGESTIONS),
            },
        }

    @app.get("/api/rag/status")
    def api_rag_status():
        return {"enabled": rag_enabled()}

    @app.post("/api/rag/toggle")
    def api_rag_toggle():
        """运行时切换 RAG explain 扩展（无需重启服务）。

        环境变量是进程级的：qa_lock 串行化问答请求，切换与问答不会交错；
        引擎侧 rag_enabled() 每次问答即时读取，开关立即生效。
        """
        import os
        with qa_lock:
            os.environ["RAG_ENABLED"] = "0" if rag_enabled() else "1"
        return {"enabled": rag_enabled()}

    @app.get("/api/qa/suggestions")
    def api_suggestions():
        return {"suggestions": SUGGESTIONS}

    # ------------------------------------------------------------------
    # 问答：JSON（非流式）
    # ------------------------------------------------------------------
    @app.post("/api/qa/ask")
    def api_ask(payload: AskRequest):
        question = payload.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="问题为空")
        use_llm = payload.use_llm if payload.use_llm is not None else default_use_llm
        with qa_lock:
            ans = answer_question(question, stack, use_llm=use_llm,
                                  context=payload.context)
            _translate_evidence(ans, stack)
        return {"question": question, "answer": _qa_answer_dict(ans),
                "context_entities": _context_entities(ans)}

    # ------------------------------------------------------------------
    # 问答：SSE 流式（EventSource 兼容；首字节立即到达 → phase 事件）
    # ------------------------------------------------------------------
    @app.get("/api/qa/ask/stream")
    async def api_ask_stream(q: str, use_llm: Optional[bool] = None,
                             ctx: Optional[str] = None):
        question = (q or "").strip()
        if not question:
            return JSONResponse({"error": "问题为空"}, status_code=400)
        effective_llm = use_llm if use_llm is not None else default_use_llm
        # 对话上文（指代消解）：ctx 为 JSON 编码字符串（EventSource 仅 GET）
        context: Optional[dict] = None
        if ctx:
            try:
                context = json.loads(ctx)
            except Exception:
                context = None
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def put(kind: str, payload) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, (kind, payload))

        def worker() -> None:
            try:
                with qa_lock:
                    ans = answer_question(
                        question, stack, use_llm=effective_llm,
                        context=context,
                        on_phase=lambda code, msg: put("phase", {"code": code, "message": msg}),
                        on_text_delta=lambda chunk: put("delta", {"text": chunk}))
                _translate_evidence(ans, stack)
                put("answer", {"answer": _qa_answer_dict(ans),
                               "context_entities": _context_entities(ans)})
            except Exception as exc:  # 服务端兜底：不击穿连接，错误经 SSE 下发
                put("error", {"message": f"{type(exc).__name__}: {exc}"})
            finally:
                put("done", None)

        threading.Thread(target=worker, daemon=True, name="qa-ask-stream").start()

        async def event_gen():
            while True:
                kind, payload = await queue.get()
                if kind == "phase":
                    yield _sse("phase", payload)
                elif kind == "delta":
                    yield _sse("delta", payload)
                elif kind == "answer":
                    yield _sse("answer", payload)
                elif kind == "error":
                    yield _sse("error", payload)
                elif kind == "done":
                    yield _sse("done", {})
                    break

        return StreamingResponse(
            event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ------------------------------------------------------------------
    # 本体查看器模块（原 viewer 作为独立模块保留，侧边栏切换）
    # ------------------------------------------------------------------
    viewer_mod.register_viewer_api(app, viewer_session)

    @app.get("/viewer")
    def viewer_root_redirect():
        return RedirectResponse(url="/viewer/")

    @app.get("/viewer/")
    def viewer_page(embed: str = ""):
        """本体查看器页面：既作统一 UI 的 iframe 内嵌体，也可独立访问。

        统一 Web UI 的主区通过 iframe（/viewer/?embed=1）嵌入本页，模块切换由
        宿主侧边栏完成，因此 embed=1 时不注入「返回智能问数」悬浮按钮——注入了
        反而会在 iframe 内跳转，把整个聊天壳嵌进 iframe。直接访问 /viewer/ 或
        独立运行 python -m fondontology.viewer 时仍注入返回按钮，不会出现死链。
        """
        html = (viewer_mod.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        if embed == "1":
            return HTMLResponse(html)
        # 固定定位的悬浮返回按钮：不依赖查看器内部布局（其 topbar 有 min-width:1120
        # 且可能被窄视口裁切），任何窗口尺寸下都可见、可点。
        back_link = (
            '<a href="/" style="position:fixed;bottom:20px;right:20px;z-index:1000;'
            'color:#fff;text-decoration:none;font-size:13px;font-weight:650;'
            'padding:9px 16px;border-radius:999px;background:var(--teal-dark,#0c504e);'
            'box-shadow:0 4px 14px rgba(12,80,78,.35);display:inline-flex;align-items:center;gap:6px" '
            'title="返回智能问数">← 返回智能问数</a>'
        )
        if '<div class="app-shell">' in html:
            html = html.replace('<div class="app-shell">',
                                back_link + '<div class="app-shell">', 1)
        return HTMLResponse(html)

    # ------------------------------------------------------------------
    # 智能问数入口
    # ------------------------------------------------------------------
    @app.get("/")
    def index():
        return FileResponse(UI_DIR / "index.html")

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CNFO 智能问数 Web UI（M6）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--source", type=Path, default=DEFAULT_TBOX,
                        help="QA T-BOX 入口（默认 ontology/modules/cnfo-domain.ttl）")
    parser.add_argument("--abox", type=Path, default=DEFAULT_ABOX,
                        help="QA A-BOX TTL（默认 artifacts/cnfo/abox/cnfo-sim-abox.ttl）")
    parser.add_argument("--viewer-ttl", type=Path, default=DEFAULT_VIEWER_TTL,
                        help="查看器 T-BOX（默认 artifacts/cnfo/cnfo-fund-tbox.ttl）")
    parser.add_argument("--no-llm", action="store_true",
                        help="强制模板表达（等价 use_llm=False）")
    parser.add_argument("--rag", action="store_true",
                        help="启用 RAG 解释类问答扩展（explain/定义/介绍/对比；默认关闭）")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    import os

    import uvicorn

    if args.rag:
        os.environ["RAG_ENABLED"] = "1"
    default_use_llm = False if args.no_llm else None
    app = create_web_app(
        tbox_source=args.source,
        abox_ttl=args.abox,
        viewer_ttl=args.viewer_ttl,
        default_use_llm=default_use_llm,
    )
    from .qa.config import rag_enabled
    print(f"CNFO 智能问数 Web UI：http://{args.host}:{args.port}")
    print(f"  QA 本体：{args.source} + {args.abox.name}")
    print(f"  查看器： {args.viewer_ttl}（http://{args.host}:{args.port}/viewer/）")
    print(f"  LLM 模式：{llm_config().get('OPENAI_MODEL') or '未配置（确定性模板）'}")
    print(f"  RAG 扩展：{'开启' if rag_enabled() else '关闭（RAG_ENABLED=1 或 --rag 开启）'}")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        timeout_graceful_shutdown=5,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
