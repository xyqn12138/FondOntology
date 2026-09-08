# CNFO 智能问数 RAG 模块设计方案（M7）

> 状态：设计稿 v1.0（2026-09-08）
> 定位：图问数（Graph QA）的补位路径，不是替代。

## 0. 一句话设计

**RAG = 把 T-BOX 定义、实体档案这两类"文本化本体资产"纳入 Evidence 合同，用与现有 find/verify 完全相同的 Claim-Evidence Map + 引用闸门来回答解释类问题（什么是/介绍/区别），检索层复用现有词汇锚定并增加向量召回，终态 UCR 仍为 0。**

核心原则（继承自现有架构）：
- Ontology 不替 LLM 推理，给 LLM 提供世界模型——RAG 的"检索"不是网页检索，是**本体语义资产的检索**；
- LLM 永远只做表达，不做事实来源；每句话仍须挂 claim，每个 claim 仍须挂证据；
- 无 key / 无向量模型 → 确定性降级（BM25 + 模板），全链路可回归测试；
- LLM 永不生成 SPARQL 的原则平移为：**LLM 永不决定检索命中，只决定如何组织已命中的内容**。

## 1. 动机与问题域

### 1.1 当前链路的三个盲区（实测）

| 问法 | 现状行为 | 问题 |
|---|---|---|
| 「什么是货币市场基金？」 | find 语义，回答"共找到 4 个…实体列表" | 解释类问题被误路由为实体列举 |
| 「介绍一下云帆中证500指数基金」 | UNRESOLVED | 实体档案型问题无处可去 |
| 「货币市场基金和债券基金有什么区别？」 | 拒答（Phase 2 标记） | 对比类需要两边定义+互斥关系，图问数不覆盖 |

数据侧事实（决定 RAG 语料形态）：
- T-BOX（artifacts/cnfo/cnfo-fund-tbox.ttl）：150 类、211 属性、**393 中文 label、388 条 skos:definition**——文本密集，是 RAG 的主语料；
- A-BOX：280k 三元组、38k 实体，但 95% 是净值/日期类数值记录；**文本仅 520 个 rdfs:label**、1 条 description——A-BOX 本身不能直接当文档，须从图结构合成"实体档案"；
- 基金实体每只携带 40+ 属性（类型链、基金经理、管理公司、风险等级、基准、规模），足以合成高质量档案卡。

### 1.2 职责划分（Router 契约）

| 问题形态 | 归属 | 依据 |
|---|---|---|
| 有哪些/多少/谁/哪个/R4以上/管理多只 | Graph QA（现状不动） | 实体列举/聚合/排名是图的强项 |
| 是不是/是否互斥/是否等价 | verify（现状不动） | T-BOX 判链 |
| **什么是X / X是干什么的 / 介绍(一下)X / X和Y的区别 / 为什么** | **RAG（新增 kind=explain）** | 答案本体是定义与解释文本 |
| 混合形态（"介绍杨洋管理的基金"） | 混合：图查询取实体 + RAG 取类定义 | 两路证据并存于同一 report |

## 2. 总体架构

```
用户问题
   │
   ▼
intent.py（扩展：operation ∈ find | verify | explain）
   │  explain + topic（类 IRI / 实体 IRI，复用 resolver/锚点，三态不变）
   ▼
┌─────────────────────────────────────────────────────┐
│  RAG 路径（新模块 fondontology/qa/rag/）              │
│                                                      │
│  corpus.py ──→ 语料构建（离线）                       │
│   ├ 类卡（150）：label+定义+父/子类+关键属性+约束      │
│   ├ 属性卡（211）：label+domain/range+定义            │
│   └ 实体档案（~530）：从 A-BOX 图结构合成事实卡        │
│         ↓ 构建/增量更新（enforce 导入钩子）            │
│  store.py ──→ artifacts/cnfo/rag/                    │
│   ├ corpus.jsonl（chunk 原文 + locator）              │
│   ├ bm25.index（零依赖词法索引）                      │
│   └ vectors.npy + meta（可选，EMBEDDING_MODEL 配置）  │
│                                                      │
│  retrieve.py ──→ 混合检索                             │
│   锚点召回（resolver 精确命中，必选）                  │
│   + BM25（字符 n-gram，中文友好，零依赖）              │
│   + 向量余弦（可选，OpenAI 兼容 /embeddings）          │
│   → RRF 融合 → top_k=5 chunk + 分数                  │
│                                                      │
│  evidence 适配 ──→ chunk 变 evidence（kind=document） │
│  explain/generate ──→ LLM 组织答案（句级 claim_id     │
│   引用 R#，闸门校验；无 LLM → 档案卡模板渲染）         │
└─────────────────────────────────────────────────────┘
   │
   ▼  与 find/verify 同构的 QaAnswer（kind="explain"）
evidence 面板（UI 仅需支持 kind=document 的小样式）→ SSE delta 流式（复用）
```

## 3. 模块设计

### 3.1 `fondontology/qa/rag/corpus.py` —— 语料构建

**类卡**（每类一张，150 张）：
```
id:     cls:MoneyMarketFund
iri:    https://ontology.example.cn/cnfo/ontology/MoneyMarketFund
text:   货币市场基金（MoneyMarketFund）。定义：投资于货币市场工具的集合投资计划…
        父类：基金（Fund）。子类：无。关键属性：投资策略、风险等级（继承自 Fund）。
        本体约束：与封闭式基金互斥（若 T-BOX 声明 disjointWith）。
locator: {file: artifacts/cnfo/cnfo-fund-tbox.ttl, iri, fields: [label, definition, …]}
```
生成规则：`zh_label` + 本地名 + skos:definition + 直接父类（带中文 label）+ 直接子类前 5 + 自身声明的对象/数据属性前 8（含 domain/range 中文）+ disjointWith 约束。**不含实例**（实例归图问数）。

**属性卡**（每属性一张，211 张）：本地名 + 中文 label + 定义 + domain/range + 是否函数性/传递性（若有）。

**实体档案**（每实体一张，当前 ~530 个有 label 的实体；基金/经理/公司/投资者）：
```
id:     ent:F006494
text:   云帆中证500指数型证券投资基金（基金代码 006494，简称 云帆中证500）。
        类型：公募基金 · 开放式 · 股票型基金。基金经理：褚宇。基金管理人：云帆基金管理有限公司。
        风险等级：R3。业绩比较基准：中证500指数。运作方式：契约型开放式。
locator: {abox: cnfo-sim-abox.ttl, entity: F006494, generated_from: [type链, hasFundManager, …]}
```
合成规则：label + 代码 + 类型链（取最有路径上的 3 个中文类名）+ 一跳出向属性白名单（基金经理/管理公司/风险等级/基准/规模/币种，取中文 label 而非 IRI）+ 净值/日期**不进档案**（数值时效性内容归图查询）。

**构建与更新**：
- 离线命令：`python -m fondontology.qa.rag.corpus --rebuild`（或 tools/rag_corpus.py），写 `artifacts/cnfo/rag/corpus.jsonl`；
- 版本校验：语料头记录 `ontology_hash` / `abox_hash`（stack.snapshot 已有），加载时不匹配则告警（不自动重建，避免启动时 IO）；
- 增量：`enforce.import_records` 导入成功后追加/重写涉实档案（钩子在 enforce 返回前，只处理 imported 实体，秒级）。

### 3.2 `fondontology/qa/rag/store.py` —— 存储与索引

规模（~900 chunk）决定**不引入向量数据库**：
- `corpus.jsonl`：chunk 全文 + locator；
- BM25：自实现字符 2-gram + 词元混合的 BM25（中文无分词依赖；或直接用 jieba 如果愿意加依赖——默认不加）。索引即倒排 dict，pickle 落盘，启动毫秒级加载；
- 向量（可选）：`vectors.npy`（float32，900×d ≈ 数 MB）+ 行号映射。检索 = numpy 点积（numpy 需新增依赖，仅在配置 EMBEDDING_MODEL 时 import，延迟导入不污染核心链路）；
- 全部只读、进程内缓存，与 `_INDEX_CACHE` 同生命周期管理。

### 3.3 `fondontology/qa/rag/retrieve.py` —— 混合检索

```
输入: question, topic_iri(来自 intent 的锚点，可为空), k=5
1) 锚点召回（确定性，权重最高）:
   topic_iri 命中 cls:Foo → 该卡必进 top_k（RRF 中给 rank=1）
   topic_iri 命中 ent:Bar → 实体档案 + 其最有类型卡共两张必进
2) BM25 召回: 字符2gram BM25 → 前 20
3) 向量召回（可选）: question embedding → cosine 前 20
4) RRF 融合: score = Σ 1/(60+rank_i)，锚点通道 rank 恒为 1
5) 输出: [{chunk, score, channels:[anchor,bm25,vector]}]，去重（同 iri 只留最高分卡）
```
降级链：无向量模型 → 仅锚点+BM25；BM25 也失败（空 query）→ 仅锚点；锚点+检索全空 → 返回空，上层按 UNRESOLVED 诚实回答。

**检索质量的关键复用**：现有 `resolver.resolve_concept` / `_find_entity_mention` 已经是打磨过的中文→本体锚定器（含别名词表），RAG 检索的"精确层"不重写，直接调。

### 3.4 intent 扩展 —— explain 语义

`SemanticParse` 增加第三种 operation：
```
{"operation": "explain", "topic": "<类IRI或实体IRI>", "explain_type": "define|describe|compare|reason"}
```
- 确定性规则优先（与现有结构一致）：
  - 「什么是/何为/X是干什么的/X的定义」→ explain_type=define，topic 走 resolver；
  - 「介绍一下/介绍X/说说X」→ describe；
  - 「X和Y的区别/差异/对比」（现在被 Phase 2 拒答的）→ compare，topic=[X, Y]；
  - 「为什么」（无锚点）→ reason（本版可继续拒，预留）；
- LLM 解构：prompt 的 schema 加 explain 分支，输出仍过白名单（topic 必须是已知 IRI）；解析失败回落规则；
- 三态契约不变：AMBIGUOUS（"混合基金"多义）→ 澄清话术。

**Router 位置**：`engine.answer_question` 里 `intent["operation"] == "explain"` 分支 → `rag.answer_explain(...)`，与 find/verify 并列。快路径（锚点命中 + describe）不付 LLM 成本，复用现有 fast-path 思路。

### 3.5 `fondontology/qa/rag/answer.py` —— 答案生成（表达层复用）

**Evidence 合同扩展**（evidence.py 只加一个构造助手，不改校验器）：
```python
{"id": "R1", "kind": "document",
 "source": ["cnfo-fund-tbox.ttl", "MoneyMarketFund", "definition"],
 "note": "类卡：货币市场基金（含定义/层级/属性）",      # 摘要行
 "text": "<chunk 原文>",                              # 新字段：文档证据带正文
 "premises": [], "derived": []}
```
- `validate_citations` / `evidence_completeness` 零改动（它们只看 id 集合）；
- claim 由 RAG 路径自行构造（不走 EvidenceBuilder 的图逻辑）：
  - define：`「货币市场基金」的定义：投资于货币市场工具的…[R1]`（模板路径直接引用 chunk 的 definition 字段）；
  - describe：档案事实逐条成 claim（`云帆中证500 的基金经理是褚宇 [R2]`）；
  - compare：两侧定义各一 claim + 图上 disjointWith/共同父类证据（`E#`，verify 复用）混合。

**生成**：
- LLM 路径：**复用 explainer 的 `_llm_chat` + 闸门**，prompt 里的"可用 claims"换成 RAG claims，规则追加"只可使用 claims 中出现的事实与措辞，不得补充外部知识"；句级 claim_id（含数组形态）→ 引用 `R#`；闸门越权 → 重试 → 模板回退，与现在完全一致；
- 模板路径（无 key / 回退）：define 输出"定义卡"（定义 + 父类 + 关键属性），describe 输出"档案卡"（label + 类型 + 关键属性逐行）——确定性可回归；
- **混合形态**（"介绍杨洋管理的基金"）：图查询先出实体集合（find 链路），每实体的档案卡作为 document 证据并入同一 report，LLM 一次组织。这保证答案里"杨洋管理 2 只基金"有 E#（查询证据）、"是契约型开放式"有 R#（档案证据），各引各的。

### 3.6 `config.py` 与环境变量

```
RAG_ENABLED=1                     # 总开关（默认开）
EMBEDDING_MODEL=                  # 空=BM25-only；如 doubao-embedding-text-240715
EMBEDDING_BASE_URL=               # 缺省复用 OPENAI_BASE_URL（Ark 兼容 /embeddings）
RAG_TOP_K=5
```
所有键缺失/非法都有确定性缺省，`.env` 不配任何新键时系统照常运行（BM25 路径）。

### 3.7 Web/UI 改动（最小）

- 证据面板：`kind=document` 的证据渲染为可折叠正文（现有 `ev-item` 结构 + `<pre>` 展示 chunk 文本 + locator 来源行），加一个小徽标「文档」；
- `api_meta` 增加 `rag: {enabled, embedding_model, corpus_chunks, corpus_hash}`；
- SSE `phase` 事件新增 `retrieve`（检索中）`generate`（组织中）两个 code，前端无需改（phase 文案是透传的）；
- 推荐问题列表补 2 条 explain 形态（「什么是货币市场基金？」「介绍一下云帆中证500」）。

## 4. 数据契约汇总

| 契约 | 内容 | 不变量 |
|---|---|---|
| chunk | `{id, kind: class\|property\|entity, iri, text, locator}` | 纯函数从图生成，可重建 |
| 检索结果 | `[{chunk_id, score, channels}]` | 锚点命中必在结果内 |
| RAG evidence | `kind=document`，带 `text` 与 `locator` | id ∈ {R1..Rk}，与 E# 不冲突 |
| explain claim | 句子引用 R#（或 R#+E# 混合） | 引用 ⊆ evidence 集合（复用校验器） |
| QaAnswer | `kind="explain"`，其余字段同构 | UCR=0 终态保证不破 |

## 5. 降级矩阵（无中断路径）

| 配置 | 检索 | 生成 | 效果 |
|---|---|---|---|
| 无 LLM、无 embedding | 锚点+BM25 | 模板卡 | 全功能可回归（CI 用这档） |
| 有 LLM、无 embedding | 锚点+BM25 | LLM+闸门 | 默认档 |
| 全配置 | +向量召回 | LLM+闸门 | 最佳档 |
| 语料缺失/损坏 | 启动告警，explain 问题回答"文档索引未构建"（UNRESOLVED 话术） | | 不影响 find/verify |
| 检索空命中 | — | — | "未找到相关定义，试试问实体列表或换个说法" |

## 6. 实施里程碑（每步可独立合并、可回归）

**M7-R1：explain 意图 + 类卡语料 + BM25 + 模板（零新依赖，纯确定性）**
- intent 加 explain 规则与 LLM schema 分支；corpus.py 类卡+属性卡；store/retrieve BM25；answer.py 模板渲染 define/compare；
- 验收：「什么是货币市场基金」→ 定义原文 + [R1]；「X和Y区别」→ 两侧定义 + 互斥判定（若图上声明）；CI 全绿（无网络）。

**M7-R2：LLM 表达接入（复用闸门）**
- explain 走 explainer 闸门（R# 引用）；SSE delta 流式打通；证据面板 document 渲染；
- 验收：citation 基准新增 explain 用例，UCR=0；表达风格遵循已建立的"直接回答、禁止三元组腔"规则。

**M7-R3：实体档案 + describe + 混合证据**
- 实体卡生成（530 个）+ enforce 增量钩子；describe 模板与 LLM 路径；"介绍杨洋管理的基金"混合链路；
- 验收：档案事实全部可溯源到 chunk locator；导入新记录后即刻可问。

**M7-R4：向量召回（可选增强）**
- EMBEDDING_MODEL 配置 + /embeddings 客户端 + vectors.npy 构建/加载 + RRF 三路融合；
- 验收：BM25-only 与 +vector 双档回归均绿；检索命中率对比报告（tools/rag_eval.py，20 条 explain CQ）。

**M7-R5：评测与文档**
- qa_bench 新增 `--stage explain`（20 条：define 8 / describe 6 / compare 4 / 混合 2）；README 架构图更新。

## 7. 测试计划（确定性优先）

- `tests/test_rag_corpus.py`：类卡字段完整性（定义/父类/属性）、实体档案合成规则（类型链取最深 3 层、出向属性白名单）、语料 hash 校验；
- `tests/test_rag_retrieve.py`：锚点必召回、BM25 中文命中（"货币基金"→MoneyMarketFund 卡）、RRF 排序、空查询降级；embedding 检索用 mock 向量测（不依赖网络）；
- `tests/test_rag_answer.py`：模板路径全文快照；LLM 路径 mock `_llm_chat` 测闸门（好引用过/坏 R# 回退，复用 explainer 测试模式）；混合证据 report 结构；
- `tests/test_qa_intent.py` 扩展：explain 规则命中表、compare 从 Phase 2 拒答改为可答的回归；
- 既有 find/verify 测试**零改动**（Router 不动它们的语义）。

## 8. 风险与对策

| 风险 | 对策 |
|---|---|
| 定义文本不足（388 条定义覆盖 150 类，部分类无中文定义） | 类卡降级为 label+层级+属性；模板标注"暂无定义"；语料报告列出无定义类清单（供本体侧补写） |
| LLM 在 explain 路径"补充外部知识"（基金常识） | prompt 硬约束 + 闸门只能拦 claim_id 越权，拦不住措辞级发挥——增加**事后短语核查**：答案中的实体名/类名必须出现在所引 chunk 或图锚点中，否则判违规回退模板（新增 `rag/verify_phrases.py`，确定性） |
| compare 无 disjointWith 声明时 LLM 编造差异 | 证据只有两张类卡时，模板明确输出"本体未声明互斥；差异见各自定义"；禁止 LLM 推断性对比 |
| 实体档案时效（净值日变化） | 档案不含净值；enforce 钩子 + 全量重建双通道 |
| Ark /embeddings 不可用 | 向量层整体可选，R1-R3 不依赖 |

## 9. 明确不做（本版边界）

- 不做通用网页/文档 RAG（外部 PDF/公告）——语料边界就是本体自身资产；
- 不做多轮对话/指代消解；
- 不做"为什么"类推理问答（explain_type=reason 预留，本版拒答）；
- 不引入向量数据库/重排模型服务（规模不支持，900 chunk 用 numpy 足够）。
