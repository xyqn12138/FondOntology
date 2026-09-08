# CNFO 智能问数 RAG 模块设计方案 V2

> 状态：设计稿 v2.0（2026-09-08，基于与需求方的方向对齐讨论重写，替代 v1）
> 决策记录：首发场景＝季报（经理观点/运作回顾）；暂不接入真实数据，模拟文档先行；Doc2Graph 本版只留接口。
> 定位：RAG 是图问数（Graph QA）的补位与增强路径，不是替代。

## 0. 已对齐的核心结论

1. **结构化数据文本化是伪需求**：把 A-BOX 三元组渲染成句子再检索回来，信息量为零。RAG 的价值密度只在密集文本（季报、招募书、法规原文）里。
2. **双引擎而非单引擎**：事实查询（枚举/聚合/排名）永远走图；解释理解（定义/观点/差异）走文本；复杂问题双通道并发。
3. **混合检索采用两级路由**：实体锚点命中时，图决定文本检索范围（锚定过滤）；无锚点的解释类问题才退化为全局文本池检索。理由：基金领域文本检索的第一失败模式是实体串台（基金简称高度相似），而现有引文闸门只校验 claim_id 越权、不校验 chunk 是否属于用户问的实体——串台的证据是合法证据，纯全局双轨方案无法拦截。
4. **文本入图到"元数据与指针"为止**：文档/章节/条文作为一等实体入图（可图查询、可过滤），chunk 正文存外部存储（可索引）。图是文本的路由器、过滤器、审计层，不是容器。
5. **CNFO 已有建模骨架但停在目录层**：`FundDocument` 四子类（合同/招募书/备案文件/定期报告）、`Regulation` 属性网络（`governedByRegulation`、`basisForRestriction`、`articleReference`…）都已存在，A-BOX 也有 5 个仿真法规实例和 120 条 Fund→Regulation 边；但 `FundPeriodicReport` 零实例、法规正文从未入图、`articleReference` 只是一个章名字符串。缺口是内容层与可寻址条文，不是类结构。

## 1. 问题域与路由契约

### 1.1 问题形态 → 通道映射

| 问题形态 | 通道 | 示例 |
|---|---|---|
| 枚举/聚合/排名/计数 | 图（现状不动） | "杨洋管理几只基金""R4以上的基金有哪些" |
| T-BOX 判链 | verify（现状不动） | "货币基金和债券基金互斥吗" |
| **带实体锚点的解释类** | **图定范围 + 文本检索**（两级路由·一级） | "云帆中证500的经理怎么看后市""介绍一下华曦新能源" |
| **带人物/机构锚点的解释类** | **图遍历展开 → 文本检索**（两级路由·一级） | "杨洋怎么看市场"（杨洋→他管的基金集合→其文档） |
| **无锚点解释类** | **全局文本池 + T-BOX 定义卡**（两级路由·二级） | "什么是R4""货基有什么监管限制" |
| 混合形态 | 图取事实 + 图定范围取文本，同 report | "介绍杨洋管理的基金" |

简单问题按意图分类走单通道；复杂问题双通道并发。注意"并发"的正确形态：不是两路全局检索，而是"图取事实 + 图定范围的文本检索"同时执行。延迟大头在生成层，图查询本身是确定性的，范围收窄让生成又快又准。

### 1.2 与现有架构的接缝

```
用户问题
   │
   ▼
intent.py（扩展 operation ∈ find | verify | explain）
   │    锚定结果（resolver / 实体提及）就是路由依据 —— 复用，不重写
   ▼
┌─ 图通道（现有）────────────┐   ┌─ 文本通道（新增）────────────────┐
│ 世界模型 → SPARQL → E#     │   │ 两级检索路由                      │
│ (确定性，无 LLM)           │   │  一级：锚定实体集合 → scope 过滤  │
│                            │   │  二级：全局池（BM25+向量）        │
└────────────┬───────────────┘   └────────────┬─────────────────────┘
             │                                │
             ▼                                ▼
      统一 Evidence Report（E# 与 R# 共存，kind=document 证据带正文与 locator）
             │
             ▼
   引用闸门（claim_id ⊆ evidence）+ 范围核查（chunk 归属 ∈ 图锚定集合）
             │
             ▼
   生成（复用 explainer，句级 claim_id）→ SSE delta 流式 → 证据面板
```

关键不变量：LLM 永不生成 SPARQL（现有原则）平移为 **LLM 永不决定检索命中，只组织已命中的内容**；终态 UCR=0 保证不破。

## 2. 三层文本模型：文本如何在本体系统中发挥作用

这是本设计的理论核心，回答"映射入图"映射的到底是什么。

| 层 | 入图内容 | 职责 | 存储位置 |
|---|---|---|---|
| **L1 语境层** | 文档、章节、法条作为一等实体（类型+元数据+结构关系） | 图可回答关于文档本身的问题；给检索提供结构化过滤维度 | triple store |
| **L2 指针层** | 图事实 ↔ 文本片段的双向引用 | 每个图事实可溯源到文本原文；每个文本抽取事实可回指 chunk | triple store（边）+ chunk 池（locator） |
| **L3 内容层** | chunk 正文 | 被检索、被引用、被展示 | 外部存储（JSONL + BM25/向量索引） |

**为什么正文不入图**：BM25/向量索引无法在 triple store 里工作；大 literal 拖垮图查询；塞进去等于双写两处都不好用。图持有文本的**身份、结构、引用关系**，不持有文本本身。

### 2.1 L1：文档与条文实体化

季报入图后的形态（模拟数据阶段即按此生成）：

```
# 文档实体
<FundPeriodicReport/qtr-2026q2-F006494>
    rdf:type            cnfo:FundPeriodicReport ;
    rdfs:label          "云帆中证500指数型证券投资基金2026年第2季度报告" ;
    cnfo:reportForFund  <abox/F006494> ;          # T-BOX 需新增
    cnfo:reportPeriod   "2026Q2" ;                # T-BOX 需新增
    cnfo:reportType     "quarterly" ;
    cnfo:disclosedVia   <DisclosureAct/xxx> .     # 可选：挂披露活动

# 章节实体（结构成分）
<ReportSection/qtr-2026q2-F006494-manager-report>
    rdf:type           cnfo:ReportSection ;       # T-BOX 需新增
    rdfs:label         "管理人报告" ;
    cnfo:sectionOf     <FundPeriodicReport/qtr-2026q2-F006494> ;
    cnfo:sectionTitle  "4 管理人报告" ;
    cnfo:sectionOrder  "4" .
```

条文实体化（升级现有 `articleReference`）：

```
<RegulationArticle/JL-004/art-15>
    rdf:type           cnfo:RegulationArticle ;   # T-BOX 需新增
    cnfo:articleOf     <Regulation/RegJL-004> ;
    cnfo:articleNumber "第十五条" ;
    cnfo:articleText   "…" .                       # 条文全文（短，可入图）
```

图因此获得的新能力（可回归测试的图查询）："云帆 2026 年披露了哪几份季报？""哪些投资限制的依据是《信息披露管理办法》第十五条？"——这些不再是 RAG 问题，是 SPARQL 问题。

### 2.2 L2：双向指针

**图→文本**（升级现有属性语义）：
- `FundInvestmentRestriction --basisForRestriction--> RegulationArticle --正文chunk--> 原文`，让图上每个投资限制可点开法条原文；
- 证据面板里 `kind=document` 的证据经 locator 回到 chunk，chunk 经元数据回到文档实体。

**文本→图**（Doc2Graph，本版留接口）：
```python
# fondontology/qa/rag/doc2graph.py —— 本版仅占位
def extract_facts(chunk: Chunk) -> list[ExtractedFact]:
    """chunk → 抽取事实（实体对齐到 CNFO 实体，带 chunk IRI provenance）。
    本版不实现；接口契约见 §6。"""

def import_extracted(facts: list[ExtractedFact], stack) -> ImportResult:
    """抽取事实 → enforce.import_records 语义导入（复用现有校验）。本版不实现。"""
```

正反两方向共用 fund_code / 条文编号主键，接口形状自然对齐。将来实现时，文本抽取的持仓数据与图上的持仓边可交叉校验，不一致即数据质量问题（数据源从模拟换真实时的审计手段）。

### 2.3 L3：chunk 池契约

```jsonl
{"chunk_id": "qtr-2026q2-F006494#s4-p2",
 "doc_id": "qtr-2026q2-F006494",          # = 图中文档实体 IRI 尾部
 "fund_code": "006494",                    # 锚定过滤主键
 "doc_type": "periodic_report",
 "period": "2026Q2",
 "section": "管理人报告",
 "text": "报告期内基金份额净值增长率为 X%……展望后市，本基金管理人认为……",
 "locator": {"source": "sim-gen", "entity": "FundPeriodicReport/qtr-2026q2-F006494"}}
```

章节是 chunk 的天然边界（季报章节结构是国标固定的），章节内语义段落二次切分（512~1024 token）。**元数据即过滤维度**："褚宇怎么看市场" = fund_code ∈ {他管的基金} AND section = 管理人报告。

## 3. 两级检索路由

### 3.1 一级：锚定过滤（主模式）

```
输入: question, anchored_entities（来自 intent 的 resolver/实体提及命中）
1) 图遍历展开锚点 → fund_code 集合
   基金锚点: {F006494} → {"006494"}
   人物锚点: 杨洋 → hasFundManager 反向 → {F006494, F006495} → 两只的文档
2) scope = 该 fund_code 集合的全部 chunk（索引侧 = 元数据倒排，O(scope)）
3) 范围内语义排序: BM25 + 向量（若配置）→ top_k=5
4) 确定性范围核查（闸门新增）: 命中 chunk 的 fund_code ∈ 锚定集合，否则丢弃
```

消灭实体串台的机制是物理性的：检索范围只含目标实体的文档，简称撞名不可能串。范围核查是审计冗余，供证据面板展示与 CI 断言。

### 3.2 二级：全局池检索（无锚点 fallback）

"什么是R4""货基有什么监管限制"——无实体可锚定：
- 语料池：T-BOX 定义卡（150 类 + 211 属性，上一版设计保留）＋ 法规条文池（L1 实体化后的条文正文）＋ 全部季报（观点汇总类）；
- 检索：BM25 + 向量全池 → top_k=5；
- 法条类优先走图指针：MoneyMarketFund → 图上关联的投资限制 → `basisForRestriction` → 条文 chunk（语义路由由图完成，比向量精确）。

### 3.3 检索层实现

- **BM25**：自实现字符 2-gram + 词元混合（中文无分词依赖，零新增依赖）；
- **向量（可选）**：Ark 兼容 `/embeddings`（doubao-embedding 系列，与现有 LLM 同供应商），`vectors.npy` + numpy 点积（~千级 chunk，不引入向量数据库）；
- 融合：RRF（锚定通道 rank 恒为 1）；
- 降级链：无向量 → BM25；空 query → 仅锚定；全空 → 诚实 UNRESOLVED。

## 4. 模拟语料：同源生成策略

关键纪律：**图与文档同源生成、双向一致**。模拟数据的价值恰恰是答案可预知、CI 无网络、交叉一致性可断言。

### 4.1 `tools/gen_sim_report.py`（新）

一次产出三样东西：

1. **文档正文**：markdown 季报，章节对齐真实季报结构（重要提示/产品概况/主要财务指标和净值表现/**管理人报告（运作回顾+未来展望）**/投资组合前十大重仓/份额变动）；40 只基金 × 2 个季度 = 80 份；
2. **A-BOX 三元组**：`FundPeriodicReport` 实例 + `ReportSection` 结构 + `reportForFund`/`reportPeriod` 边（并入 cnfo-sim-abox 或独立 sim-reports.ttl，倾向后者——保持报告数据可单独重建）；
3. **chunk 池**：按 §2.3 契约切分写入 `artifacts/cnfo/rag/chunks.jsonl`。

生成内容与图的一致性约束（同从 gen_sim_abox 的模拟源出）：季报中的基金经理名 = A-BOX `hasFundManager` 边；基金类型 = 类型链；规模数字 = A-BOX 数值属性；观点文本按经理/类型/风格参数化生成（保证同经理的跨季观点有连续性，可测"观点演变"类问题）。

### 4.2 法规正文补全（升级现有 5 个仿真法规）

每部法规生成 5-10 条可寻址条文（`RegulationArticle` 实体 + 条文正文），其中至少覆盖：信息披露义务、投资比例限制、适当性管理——这些条文内容与 `FundInvestmentRestriction`、`governedByRegulation` 现有边对得上。

### 4.3 T-BOX 小幅补充

| 增补 | 类型 | 说明 |
|---|---|---|
| `reportForFund` | ObjectProperty | FundPeriodicReport → Fund |
| `reportPeriod` / `reportType` | DatatypeProperty | "2026Q2" / quarterly·annual·semi |
| `ReportSection` | Class | 章节结构成分，sectionOf/sectionTitle/sectionOrder |
| `RegulationArticle` | Class | 可寻址条文，articleOf/articleNumber/articleText |
| `articleReference` 语义升级 | — | 从章名字符串 → 指向 RegulationArticle（保留旧值兼容） |

### 4.4 CI 可断言的交叉一致性

- 图中文档实体存在 ↔ chunk 池有该 doc_id 的 chunk ↔ chunk.fund_code 与 reportForFund 边一致；
- 季报正文中的基金经理名 = A-BOX `hasFundManager`；基金类型 = 类型链最深 3 层；
- 每条 `basisForRestriction` 指向的条文实体有非空 articleText，且对应 chunk 存在；
- 范围核查：一级检索结果 chunk 的 fund_code ∈ 锚定集合（断言）。

## 5. 证据合同与生成

### 5.1 RAG 证据（复用现有合同，仅加构造助手）

```python
{"id": "R1", "kind": "document",
 "source": ["sim-reports.ttl", "FundPeriodicReport/qtr-2026q2-F006494", "section:管理人报告"],
 "note": "云帆中证500 2026Q2 季报·管理人报告",
 "text": "<chunk 原文>",
 "scope": {"fund_codes": ["006494"], "anchored": true},   # 范围核查审计信息
 "premises": [], "derived": []}
```

`validate_citations` / `evidence_completeness` 零改动（只看 id 集合）；新增 `rag/verify_scope.py` 做 chunk 归属核查。

### 5.2 生成（完全复用 explainer 闸门）

- prompt 的"可用 claims"换成 RAG claims（句级 claim_id 引用 R#，支持数组形态）；规则追加"只可使用 claims 中出现的事实与措辞，不得补充外部知识"；
- 闸门越权 → 重试 → 模板回退（与现状一致）；
- **事后短语核查**（防 LLM 措辞级发挥）：答案中的实体名/类名必须出现在所引 chunk 或图锚点中，否则判违规回退模板（确定性）；
- 模板路径（无 key/回退）：define → 定义卡；describe → 档案事实逐条；compare → 两侧定义 + 图上互斥判定（无声明时明确输出"本体未声明互斥"，禁止推断性对比）；
- 混合形态：图查询出实体集合（E#），实体档案/季报 chunk 并入（R#），LLM 一次组织。

### 5.3 Web/UI（最小改动）

- 证据面板 `kind=document` 渲染：正文折叠 + locator 来源行 +「文档」徽标；
- `api_meta` 增加 `rag: {enabled, embedding_model, corpus_chunks, corpus_hash}`；
- SSE phase 新增 `retrieve`/`generate` code（文案透传，前端零改）；
- 推荐问题补 2 条 explain 形态。

## 6. 配置与 Doc2Graph 接口占位

```
RAG_ENABLED=1                # 总开关（默认开）
EMBEDDING_MODEL=             # 空=BM25-only；如 doubao-embedding-text-240715
EMBEDDING_BASE_URL=          # 缺省复用 OPENAI_BASE_URL
RAG_TOP_K=5
```

Doc2Graph 占位（`fondontology/qa/rag/doc2graph.py`，本版不实现）：

```python
@dataclass
class ExtractedFact:
    subject_iri: str      # 对齐到 CNFO 实体
    predicate_iri: str    # CNFO 属性
    object_value: str     # 实体 IRI 或字面量
    chunk_id: str         # provenance 回指
    confidence: float

def extract_facts(chunk: Chunk) -> list[ExtractedFact]: ...
def import_extracted(facts, stack) -> "ImportResult": ...   # 内部走 enforce.import_records
```

实现里程碑中它排在最后，接口先冻结，避免将来实现时改 chunk 契约。

## 7. 降级矩阵

| 配置 | 检索 | 生成 | 说明 |
|---|---|---|---|
| 无 LLM、无 embedding | 锚定+BM25 | 模板卡 | CI 用这档，全确定性 |
| 有 LLM、无 embedding | 锚定+BM25 | LLM+闸门 | 默认档 |
| 全配置 | +向量 | LLM+闸门 | 最佳档 |
| 语料缺失/损坏 | — | — | explain 答"文档索引未构建"；不影响 find/verify |
| 一级检索 scope 内空命中 | — | — | "该实体暂无相关文档"诚实话术 |

## 8. 实施里程碑

**M7-R1：T-BOX 补充 + 模拟季报同源生成（纯数据层，零问数改动）**
- reportForFund/reportPeriod/ReportSection/RegulationArticle 入 T-BOX；gen_sim_report.py 产出 80 份季报 + A-BOX 报告实体 + 法规条文 + chunks.jsonl；
- 验收：§4.4 交叉一致性 CI 全绿。

**M7-R2：explain 意图 + 两级检索 + 模板生成（零新依赖）**
- intent 加 explain 规则与 LLM schema 分支；retrieve.py 一级/二级路由 + BM25 + 范围核查；模板路径 define/describe/compare；
- 验收："什么是货币市场基金"→定义卡；"X和Y区别"→两侧定义+互斥判定；锚定类 describe 不串台（CI 断言范围核查）。

**M7-R3：LLM 表达接入（复用闸门 + 短语核查）**
- explain 走 explainer 闸门（R# 引用、数组形态）；SSE delta 流式；证据面板 document 渲染；
- 验收：citation 基准扩展 explain 用例 UCR=0；短语核查违规回退路径可测。

**M7-R4：向量召回（可选）**
- /embeddings 客户端 + vectors.npy + RRF 三路融合；
- 验收：BM25-only 与 +vector 双档回归绿；检索命中率对比（tools/rag_eval.py）。

**M7-R5：Doc2Graph 实现 + 评测收尾**
- extract_facts/import_extracted 落地（季报重仓表 → 持仓三元组，交叉校验）；
- qa_bench 新增 `--stage explain`（20 条：define 8 / describe 6 / compare 4 / 混合 2）；README 更新。

## 9. 测试计划

- `test_rag_corpus.py`：chunk 契约字段、章节切分边界、交叉一致性（§4.4 全项）；
- `test_rag_retrieve.py`：锚定必召回且范围核查零越界、BM25 中文命中、人物锚点图展开、全局池 fallback、RRF 排序、降级链；向量用 mock；
- `test_rag_answer.py`：模板快照；LLM mock 闸门（好引用过/坏 R# 回退/数组形态）；短语核查；混合 report 结构；
- `test_qa_intent.py` 扩展：explain 规则命中表、compare 从拒答改可答的回归；
- 既有 find/verify 测试零改动。

## 10. 风险与对策

| 风险 | 对策 |
|---|---|
| LLM 补充外部基金常识 | 引文闸门拦不住措辞级发挥 → 事后短语核查（§5.2）确定性拦截 |
| compare 无互斥声明时编造差异 | 模板明确"本体未声明互斥"；禁止 LLM 推断性对比 |
| 模拟语料与图不一致（生成器漂移） | 同源生成 + §4.4 CI 断言双向一致 |
| 模拟答案质量"假" | 接受：阶段一验证的是工程链路与评测框架，数据平面可插拔，真实数据进来只换输入 |
| 条文抽取/挂接错误污染图 | L2 指针全部经白名单校验（复用 validator）；条文实体与 chunk 的映射 CI 断言 |
| Ark /embeddings 不可用 | 向量层整体可选，R1-R3 不依赖 |

## 11. 明确不做（本版边界）

- 不接入真实数据源（巨潮/东财的采集与合规留给阶段二）；
- 不做通用网页/外部 PDF RAG；
- 不做多轮对话/指代消解；
- 不做"为什么"类推理问答（explain_type=reason 预留，拒答）；
- 不引入向量数据库/重排服务；
- Doc2Graph 只冻结接口，不实现。
