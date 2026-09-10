# CNFO 智能问数 RAG 模块设计方案 V3.1

> 状态：v3.1（2026-09-09；**R3 已全部落地**：R3a 主判反转 / R3b LLM 表达 / R3c 评测——
> 基准：explain CI 档 14/14、LLM 档 20/20，回归 73 项全过。RAG 默认开启。
> 待办：R4 向量召回（已落地）、R5 Doc2Graph（真实数据阶段）。）
> 决策记录：首发场景＝季报；暂不接入真实数据，模拟文档先行；Doc2Graph 本版只留接口。
> 定位：RAG 接管**答案存在于文本而非图中**的问题域，与图问数构成双引擎，不是替代。

## 0. 与 v2 的差异（为什么改版）

v2 定稿后系统发生了两次架构演进，RAG 的坐标因此改变：

1. **操作词表从 {find, verify} 扩展为四操作**：classify（枚举类层级）与 define（T-BOX 定义卡）在 v2 之后落地为一等能力——**它们读 T-BOX，不依赖 RAG 开关**。原 v2 归给"RAG define 卡"的一部分职责（什么是X）已被更轻的 T-BOX 直读承接；
2. **实测覆盖复盘**（2026-09-09）：五类探测问法中，结构性问题（find/classify/define/verify）全部闭环；剩余 unresolved 的三类（观点/法规限制/代码概念解释）**全部是"答案在文本中"的问题**——RAG 的价值边界由此清晰。

RAG 的定位校准为一句话：**把图的语义推理扩展到文本的语义证据**。图答"是什么、有哪些、是否"；文本答"怎么看、有什么限制、什么意思"。

### 0.1 当前实测覆盖基线（v3 的出发点）

| 探测问法 | 当前行为 | 判定 |
|---|---|---|
| 货币市场基金有哪些 | find，实例清单 [E#] | ✅ 闭环 |
| 基金有哪些分类 | classify，12 维度带定义 [R#] | ✅ 闭环（M7 新增） |
| 什么是ETF | define，定义卡 [R#] | ✅ 闭环（M7 新增，含"指什么/是什么意思/何为"等问法与口语容差） |
| ETF是不是开放式基金 | verify，ENTAILED 判链 | ✅ 闭环 |
| 魏辉管理的基金有什么 | find，锚点+推理链 [E#] | ✅ 闭环 |
| 云帆中证500的经理怎么看后市 | unresolved | ❌ 嵌套锚点问题（"X的经理"需先锚定基金再展开到经理本人），R3a 由 LLM entity_label 判别承接 |
| 货币基金有什么监管限制 | **误路由**：find 列了 4 只基金 | ❌ RAG 路由缺口 + 误答（比不答更糟） |
| R4是什么意思 | unresolved | ❌ 代码概念 define 缺口（R3a） |
| 2025年收益最高的基金 | unresolved | ⏸ IR 表达部件缺口（Phase 2，非 RAG 领地） |

## 1. 四操作架构下的 RAG 工作位置

### 1.1 问题域 → 通道映射（v3 修订版）

| 问题形态 | 通道 | 依赖 RAG 开关 | 示例 |
|---|---|---|---|
| 枚举/聚合/排名/计数 | **find**（图，A-BOX 查询） | 否 | "杨洋管理几只基金" |
| 类层级枚举（schema 问题） | **classify**（T-BOX 直读） | 否 | "基金有哪些分类" |
| 类定义 | **define**（T-BOX 定义卡） | 否 | "什么是ETF""开放型基金指什么" |
| 类关系判定 | **verify**（T-BOX 判链） | 否 | "ETF是不是开放式基金" |
| **实体档案/观点类** | **explain·describe**（锚定过滤 + chunk 检索） | **是** | "云帆中证500的经理怎么看后市""介绍一下华曦新能源" |
| **法规限制类** | **explain·regulation**（条文检索） | **是** | "货币基金有什么监管限制" |
| **代码概念解释** | **explain·code**（图指针 → 条文/代码表） | **是** | "R4是什么意思" |
| 对比类 | **explain·compare**（两侧定义卡，T-BOX 直读） | **否**（v3.1 起一等能力，见 §1.2.1） | "基金经理和托管人有什么区别" |
| 时间序列/多跳否定 | Phase 2（IR 扩展，非 RAG） | — | "2025年收益最高的基金" |

**分层原则**：读 T-BOX 的（classify/define）是一等能力，永久可用——T-BOX 是图的固定部分，"系统答不了本体里明摆着的问题"是架构缺陷不是功能取舍；依赖 chunk 池的（describe/regulation/code）受 `RAG_ENABLED` 开关控制——chunk 池是扩展数据面，演示基线期间默认关闭，前端可实时切换。

### 1.2 架构接缝（v3.1 修正：如实反映三段式现状与 R3a 目标态）

**当前代码实态**（v3 曾误写为"LLM 主判已落地"）：

```
用户问题
   │
   ▼
① compare 守卫（RAG 关闭时 compare 类直接拒答，见 §1.2.1）
   ▼
② 锚点快路径（确定性规则；实体锚点成链时不付 LLM 成本）
   ▼
③ LLM 判别（use_llm 时）
   │   schema 当前只教 find/verify/classify/define；explain 分支只接 define
   │   输出过白名单（target/property 必须是图上真实术语）
   ▼
④ 确定性规则兜底（LLM 不可用/失败/输出非法时）
   │   classify → define → explain(describe/compare) → verify → find 规则链
   ▼
operation ∈ {find, verify, classify, explain(+explain_type)}
```

**R3a 目标态（意图层主判反转）**：③ 的 schema 扩展为 explain_type 全集
（define/describe/regulation/code/compare）+ `section_hint`（LLM 按问法语义
填检索章节提示，替代正则）+ `entity_label`（嵌套锚点：「X的经理怎么看」→
LLM 判别锚点应为经理本人）。规则层角色重新定义：**新问法不再写规则**——
规则只保留为无 key/LLM 失败时的安全网与测试基线。

```
┌─ 图通道 ──────────────────────┐   ┌─ 文本通道（RAG 开关后）────────────┐
│ find:   SPARQL → E#           │   │ describe:  锚定过滤 → 范围内 BM25  │
│ classify: 类层级 → R#(定义卡)  │   │ regulation: 条文 chunk 检索        │
│ define:  定义卡 → R#          │   │ code:      articleCitesCode 指针   │
│ verify:  判链 → E#            │   │            → 条文正文 / 代码表 label │
└──────────────┬────────────────┘   └──────────────┬─────────────────────┘
               ▼                                   ▼
        统一 Evidence Report（E# 与 R# 共存；kind=document 证据带正文与 locator）
               ▼
   引用闸门（claim_id ⊆ evidence）+ 范围核查（chunk 归属 ∈ 锚定集合）
               ▼
   生成（R3b 起 LLM 表达；当前确定性模板）→ SSE delta 流式 → 证据面板
```

#### 1.2.1 compare 的开关归属（v3.1 勘误）

v3 表格把 compare 标为"依赖 RAG 开关"，但 compare 读的是 **T-BOX 定义卡**
（两侧定义 + 互斥判定），按本项目分层原则（读 T-BOX 的是一等能力）应与
define 同类。**R3a 决策：compare 脱离 RAG 开关，成为一等能力**；RAG 关闭时
仅 compare 中的"文本侧补充"不可用，定义卡对比照常可答。同时注意：R3b 把
`RAG_ENABLED` 默认翻转后，compare 不再有默认拒答形态（原 Phase 2 拒答话术
彻底退役）。

关键不变量不变：**LLM 永不生成 SPARQL，也永不决定检索命中**；LLM 判"问的
是什么"（意图），本体/检索层决定"答案是什么"；终态 UCR=0。

## 2. 三层文本模型（v2 定稿，v3 不变，此处只记状态）

| 层 | 入图内容 | 状态 |
|---|---|---|
| **L1 语境层** | 文档/章节/条文一等实体（FundQuarterlyReport 三子类、ReportSection、RegulationArticle，v0.6.0 入 T-BOX） | ✅ 已落地 |
| **L2 指针层** | 图↔文本双向引用（reportForFund、articleOf、articleCitesCode） | ✅ 已落地（articleCitesCode 的消费方是 R3a 的 code 路径） |
| **L3 内容层** | chunk 正文外部存储 | ✅ 已落地（406 条：80 季报×5 章节 + 6 条文） |

同源生成纪律不变：季报与 A-BOX 由同一 SimModel 投影，图与文本一致性是生成方式的数学性质，`tests/test_text_assets.py` 8 项 CI 断言双向一致。

## 3. RAG 实现的价值（v3 校准表述）

1. **信息补全**：观点、监管依据、操作细则在业务上天然是文本形态。经理的完整论述拆成三元组即失去语境；法规条文的条件语义（"完全按指数构成比例的可不受限"这类 but-clause）三元组无法建模——文本是这些信息唯一无损的载体；
2. **图无法索引的知识形态**：同源数据面下，图问数答"经理是谁"（E#），RAG 答"经理怎么说"（R#），证据同构互补；
3. **明确不解决**：精确枚举/聚合（find 领地）、类关系判定（verify）、时间序列与多跳否定（IR 扩展领地，Phase 2）。RAG 的检索是"召回相关文本"，不做精确计数——用 RAG 答"有几只基金"是错误设计。

## 4. R3 里程碑（v3 修订，替代 v2 的 R3/R4 排序）

**R3a：意图层主判反转 + 路由补全（✅ 已落地，v3.1 重写，替代 v3 的句式补丁清单）**

交付物是**架构反转**而非四条句式规则——新问法从此不再需要写正则：

1. **LLM schema 扩展为 explain_type 全集**：define/describe/regulation/code/compare
   判别准则写进 prompt（语义准则而非句式枚举："判断用户想知道什么——定义用 define；
   某个具体对象的情况/观点用 describe；监管限制用 regulation；代码等级含义用 code；
   两者差异用 compare"），每类一个 few-shot 示例；
2. **`section_hint` 字段交给 LLM**：检索章节提示由 LLM 按问法语义填
   （"怎么看后市"→ 管理人报告），替代确定性正则；
3. **`entity_label` 嵌套锚点判别**：「X的经理怎么看」由 LLM 判别锚点应为
   经理本人；「杨洋怎么看后市」LLM 填经理名，检索层经 `fund_codes_for_entity`
   图遍历展开到他管的基金集合（防串台完全体）；
4. **regulation/code 生成路径**：regulation 检索范围锁定条文 chunk；
   code 先沿 `articleCitesCode` 图指针直达条文（"R4"的正确答案=适当性指引第八条），
   无指针降级代码表 label；
5. **compare 脱离 RAG 开关**（一等能力，§1.2.1）；compare 守卫与 Phase 2 拒答话术退役；
6. **规则层降级为安全网**：现有 define/classify/explain 规则保留，服务于
   无 key 模式与 LLM 失效兜底；确定性回归测试全部走规则路径（CI 无网络），
   LLM 路径用 mock 锁 schema 契约。

验收：§0.1 基线表全部 ✅ 或明确"Phase 2 不支持"，零误路由；新增 LLM schema
契约测试（mock）+ 规则兜底回归。

**R3b：LLM 表达接入（复用闸门模式，✅ 已落地）**

- explain（describe/regulation/code）走 LLM 表达：chunk 内容作为 claims 输入，句级 claim_id 引用 R#（含数组形态），闸门越权重试→模板回退；事后短语核查（答案实体名 ⊆ 所引 chunk ∪ 图锚点）确定性拦截措辞级发挥；
- 模板路径保留为无 key/回退档（现有输出即回退形态）；
- 验收后 `RAG_ENABLED` 默认值翻转为开启（当前默认关闭是演示基线保护）。

**R3c：评测收尾（✅ 已落地）**

- `qa_bench --stage explain`：20 条 CQ（describe 8 / regulation 4 / code 4 / compare 4），断言检索命中率与 UCR=0；
- 更新演示话术与 README。

**R4：向量召回 + Rerank 精排（✅ 已落地，2026-09-09/10 更新）**

- 配置：.env 的 EMBEDDING_MODEL/EMBEDDING_URL/EMBEDDING_KEY（大小写不敏感，
  Ark coding 端点 doubao-embedding-vision，2048 维，批量上限 10/请求）；
- 实现：rag/embedder.py（/embeddings 客户端 + vectors.npy 构建/加载，
  429 指数退避 + 批间限速；chunk 池哈希校验防过期）；retrieve.py 三路
  加权 RRF（锚定 2.5 强先验 / dense 1.2 / BM25 0.8，section_hint 优先级
  高于融合）；构建命令 gen_text_assets.py --build-vectors；
- 实测：语义改写场景（「经理对未来市场怎么看」「重仓持有哪些股票」）
  BM25 全错 → dense 全对；LLM 档基准 20/20 全 llm_validated
  （R3c 时 17 validated / 3 fallback，fallback 归零）；
- 降级：embedding 未配置/网络失败/向量过期 → BM25-only，不阻断问答；
- rerank 精排（2026-09-10 追加）：qwen3.7-text-rerank @ dashscope 原生
  text-rerank API；接入位置 RRF 粗排（top_k×2）→ rerank 精排取 top_k；
  让位规则：section_hint 场景与 ≤5 条小集合不精排（确定性信号优先于
  模型分数，小集合收益低于网络往返）；失败降级保持 RRF 序；
- 服务商切换（2026-09-10）：embedding 由 Ark doubao → 阿里 MaaS
  qwen3.7-text-embedding-flash（1024 维，批量 25），config 回退链
  EMBEDDING_* → DASHSCORE_* → OPENAI_*；
- 配置：EMBEDDING_MODEL / RERANK_MODEL / DASHSCORE_URL / DASHSCORE_API_KEY。

当前 406 条 chunk BM25 召回已足够（实测命中）；真实季报语料（数百份×数十章节）上线后评估 `/embeddings` + RRF 三路融合。

**R5：Doc2Graph 实现（接口已冻结，真实数据阶段）**

## 5. 测试计划（增量）

- `test_rag_explain.py` 扩展：regulation/code 句式命中、人物锚点展开检索、误路由回归（"X有什么限制"不得走 find）；
- `test_classify.py` 已含 define 意图/容差/LLM 分支（R3a 复用该模式）；
- R3b：LLM mock 闸门（好引用过/坏 R# 回退/数组形态）+ 短语核查违规回退；
- 既有 find/verify/classify/define 测试零改动。

## 6. 风险与对策（v3 增量）

| 风险 | 对策 |
|---|---|
| 路由规则再次与自然语言变体缠斗（v2→v3 的教训：「指什么」曾误入 classify） | LLM 主判优先（schema 已教四操作判别），确定性规则只兜底；规则命中后仍按 explain_type 分发，不再由单一正则决定 operation |
| "X有什么限制"与 find"X有什么"句式近邻误路由 | regulation 句式要求显式"限制/监管/规定"语义词，弱词（"有什么"）不触发 |
| 代码概念检索空命中（条文未覆盖的代码） | 降级链：条文 → 代码表 label → 诚实"无解释文本" |
| LLM 表达在 describe 长文本上发挥过度 | 短语核查 + 闸门双保险（v2 §5.2 设计保留） |

## 7. 明确不做（v3 边界）

- 不接入真实数据源（阶段二）；
- 不做通用网页/外部 PDF RAG；
- 不做多轮对话/指代消解；
- 时间序列/多跳否定/SUM/AVG（IR 表达部件扩展，Phase 2，与 RAG 平行推进不混入）；
- 不引入向量数据库（R4 前不评估）；
- Doc2Graph 只冻结接口。

## 附：v2 → v3 差异索引

| # | v2 | v3 |
|---|---|---|
| 1 | operation ∈ {find, verify, explain}，explain 统一挂 RAG | 四操作；classify/define 一等能力（T-BOX 直读、不受开关控制），describe/regulation/code/compare 挂 RAG 开关 |
| 2 | define 是 RAG 的一种 explain_type（定义卡） | define 独立规则 + 口语容差，LLM schema 明确"定义问法不用 find/classify" |
| 3 | RAG 默认关闭（演示保护） | 维持，但 R3b 验收后翻转默认开启 |
| 4 | R3=LLM 表达 | R3 拆为 R3a 路由补全（新增 regulation/code/嵌套锚点）→ R3b LLM 表达 → R3c 评测；R4 向量、R5 Doc2Graph 顺延 |
| 5 | 覆盖面靠设计推演 | §0.1 实测基线表锚定（五类探测问法定期回归） |
| 6 | （v3.1 勘误）§1.2 曾把"LLM 主判"写成已落地 | §1.2 如实拆分"当前实态（三段式）"与"R3a 目标态（主判反转）"；R3a 交付物从四条句式规则改写为架构反转 |
| 7 | （v3.1 勘误）compare 曾标"依赖 RAG 开关" | §1.2.1：compare 读 T-BOX 定义卡，按分层原则脱离开关成为一等能力；R3b 默认翻转后 compare 永久可答 |
