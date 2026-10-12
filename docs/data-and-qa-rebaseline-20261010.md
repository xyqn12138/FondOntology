# 数据与 QA 体系重建审查方案

审查日期：2026-10-10。本文记录的是重基线审查与设计建议；下方“实施更新”记录同一工作区
随后完成的增量实现，不能把合成回归结果解释为真实业务验收。

范围：当前工作区的数据来源、运行时 RAG、业务题库、评分器，以及本地参考项目 BKN 的可迁移原则。

## 实施更新（2026-10-10）

本轮已在不替换 T-BOX/ABOX Turtle 真源的前提下完成第一条可重建闭环：

- `fondontology/corpus/` 提供不可变文档版本、原件 bytes、章节/chunk、实体链接、快照和日期过滤；
- `fondontology/qa/rag/` 可从既有 SQLite snapshot 读取证据，strict 模式不回退到仿真 reports TTL，引用带版本、哈希和定位；
- `fondontology/evaluation/` 与 `tools/evaluate_qa.py` 使用外置 JSON/JSONL gold，SQLite 只保存运行结果；
- `tools/qa_bench.py` 保留旧回归但增加 acceptance/负控边界，避免 count-only、空 report 或丢槽位被误报为业务通过；
- 当前新增资料和 gold 仍是合成契约 fixture，真实法规、基金披露、研究资料及独立业务审校尚未导入，业务上线审批仍不通过。

## 后续实施更新（2026-10-12）

已将用户核验的三份教材 PDF（264 页）经授权上传 MinerU，并发布到 SQLite
`textbooks-v1` 研究快照（6268 chunks）。原件及派生 JSON 可恢复，重启和幂等导入
已验证；并非官方法规/披露快照。发现正文和表格跨页合并、36个正文/图块未索引，
均明确保留质量缺口。自然语言探索题仍未命中文档证据；因此只通过摄取与研究检索
通道，不通过精确引用或用户业务问答。明细及量化见 `pdf-corpus-validation-20261012.md`。

## 1. 结论与优先级

用户指出的方向成立，但根因不应简化成“没有数据库、测试数量少、必须把 Python 全改成 JSON”。真正的问题是：

1. **数据没有独立来源闭环**：运行时文本主要由仿真 ABOX 反向生成，真实资料没有经过可追溯的摄取与发布。
2. **评测存在假阳性**：错误输出可以得到 100%，增加同类用例不会自动改善验收能力。
3. **资产边界不清**：语义模型、业务事实、文档证据、测试 gold 和生成产物没有统一的版本与消费契约。

建议暂停以旧题库通过率批准“真实业务可用”，而不是停止所有研发。先修验收口径并打通一条真实资料链路，再讨论更强检索模型、向量数据库和更多裁剪优化。

## 2. 核查结果

下列路径均为本次工作区的绝对路径；行号对应审查时的文件。

| 问题 | 核查结果 | 证据 |
| --- | --- | --- |
| 数据主链路 | TBOX/ABOX 通过 RDFLib 图加载；SQLite 是可选生成镜像，问数不消费 | `E:/LX/LX_fund/FondOntology/fondontology/qa/graph.py:186`；`E:/LX/LX_fund/FondOntology/tools/gen_sim_abox.py:1502` |
| 文档资料 | `data` 目录有 46 个文件；未发现当前摄取代码消费这些文件。部分是摘要、摘编和研究笔记，不能直接等同于核验后的官方全文 | `E:/LX/LX_fund/FondOntology/data/L1_监管强制规则/公开募集证券投资基金宣传推介材料管理暂行规定.md:20` 明示部分内容未完整获取 |
| 当前 RAG | 406 个 chunk：400 个仿真季报章节、6 个法规条文模板；生成器与仿真事实同源 | `E:/LX/LX_fund/FondOntology/tools/gen_text_assets.py:2`；`E:/LX/LX_fund/FondOntology/fondontology/qa/rag/store.py:124` |
| 业务题库 | 已有 8 份 JSON、174 条 case，并非全部硬编码；但题目口径、入口、断言强度不一致 | `E:/LX/LX_fund/FondOntology/tools/qa_bench.py:34` |
| 所谓 E2E | 一组测试从手工 Intent 进入，适合作为确定性集成测试，不是用户自然语言 E2E | `E:/LX/LX_fund/FondOntology/tools/qa_bench.py:123`；`E:/LX/LX_fund/FondOntology/tests/test_qa_e2e.py:22` |
| 可复现性 | `artifacts` 被忽略；当前 benchmark 未被 Git 跟踪，新增 slicing fixture 也尚未跟踪。部分数据依赖测试缺资料时跳过 | `E:/LX/LX_fund/FondOntology/.gitignore:16`；`E:/LX/LX_fund/FondOntology/tests/test_rag_explain.py:38`；`E:/LX/LX_fund/FondOntology/tests/test_text_assets.py:88` |

这些材料目前可以证明生成器、规则及语义组件之间的一致性，不能单独证明真实法规/披露问答的正确率。174 个 case、44 个切片题和 Python 测试方法数也不能相加后称为独立业务验收题数。

### 2.1 三个已复现的评分器假阳性

本次使用项目虚拟环境，通过内存 mock 注入错误模块输出，调用现有 benchmark runner。没有改变磁盘题库，没有调用在线模型。下列是**评分器负控实验**，不表示实际执行器在真实运行中必然产生这些错误。

| 负控输入 | 实际评测结果 | 根因 |
| --- | --- | --- |
| find 的实体全部替换为错误 ID，保持 count 相同，evidence 为空 | 1/1，100%，exit=0，证据断言 0 条 | `E:/LX/LX_fund/FondOntology/tools/qa_bench.py:91` 主要比较 count |
| intent_real 的 R02 只返回 EquityFund，删除 2025 年、增长超过 20%、经理变更条件 | 1/1，Semantic Accuracy=100%，exit=0 | gold 仅标注目标类型，`E:/LX/LX_fund/FondOntology/tools/qa_bench.py:262` 仅检查已有期望字段 |
| e2e 返回正确状态和计数文案，但 report=None | 1/1，exit=0，仍打印 Evidence Completeness 100% | `E:/LX/LX_fund/FondOntology/tools/qa_bench.py:132` 只有 report 存在才检查完整度 |

因此，之前的“全绿”需要限定为旧回归契约通过；不能据此批准业务准确性。这里指的是验收机制薄弱，不推断开发者的主观意图。

### 2.2 真实语料接入前应一起处理的运行时耦合

- `E:/LX/LX_fund/FondOntology/fondontology/qa/rag/store.py:124` 使用全局单例，首次加载后不再区分后续传入路径；接入多个 corpus snapshot 时可能继续返回旧语料。
- `E:/LX/LX_fund/FondOntology/fondontology/qa/rag/answer.py:256` 和 `E:/LX/LX_fund/FondOntology/fondontology/qa/rag/answer.py:335` 另行读取固定仿真 reports TTL。只把 chunks 放进 SQLite，并不会完成运行时迁移。
- `E:/LX/LX_fund/FondOntology/fondontology/qa/rag/answer.py:265` 范围为空时退回全量；`E:/LX/LX_fund/FondOntology/fondontology/qa/rag/answer.py:276` 检索为空时取前三条。真实资料中应区分硬约束与软召回：实体、有效时间等硬约束不得悄悄放宽；没有足够证据应明确不足，而不是用无关条文补齐答案。

## 3. 目标架构：先分职责，不先堆数据库

### 3.1 四类数据与唯一真源

| 数据类别 | 第一阶段真源 | 运行时/派生产物 | 不允许的做法 |
| --- | --- | --- | --- |
| TBOX、SHACL、代码表 | Git 管理的 TTL/OWL | RDFLib 语义图、切片与索引 | 为了“有数据库”而重写为关系表 |
| 现有 ABOX 事实 | 暂保留当前 TTL 数据集，明确 synthetic 标签 | 查询图、定向推理、证据 | TTL 与 SQLite 同时可人工编辑且无主从契约 |
| 真实文档证据 | 不可变原文文件 + SQLite 文档/版本目录 | sections、chunks、BM25/可选向量索引 | 把生成正文、研究摘要冒充官方原文 |
| QA gold | 版本化 JSON/JSONL；盲集使用受控独立仓库 | SQLite 审阅/运行记录、统计报表 | JSON 和 SQLite 各维护一套可编辑答案 |

后续若真实业务事实规模、更新频率或事务需求要求持久化，再单独迁移为“业务记录库 → 确定性 RDF 投影”。切换后 ABOX TTL 是导出件，而不是第二个主数据库。无需在本轮同时引入 PostgreSQL、图数据库、向量数据库和消息队列。

### 3.2 最小文档库

建议第一阶段 SQLite 表：

- `documents`：稳定 document_id、文档类型、发布主体、标题、所属业务实体。
- `document_versions`：不可变 version_id、来源地址、原件位置及 SHA256、发布日期、生效/失效区间、获取时间、修订关系、全文/摘编/仿真标识、授权信息、核验状态。
- `sections`：条款/章节/表格层级、原件页码或结构锚点、正文/表格内容、抽取质量。
- `chunks`：version_id、section_id、文本区间、切块器版本、文本哈希；不能仅按正文哈希跨文档合并身份。
- `entity_links`：chunk/section 到本体 IRI、实体 ID 的映射，带映射方法、置信度和审校状态。
- `ingestion_runs`：输入清单、抽取器/切块器版本、错误、计数、核验结果。
- `corpus_snapshots` 与成员表：一次发布包含哪些不可变文档版本和索引版本。

评测运行结果可放独立的 `evaluation.sqlite`，记录 `eval_runs`、`case_results`、逐项断言与失败分类。原始 gold 不回写修改。

### 3.3 摄取与发布链路

官方原件/披露原件 → 来源与版本登记 → 解析/OCR → 条款、章节、表格定位 → 核验 → 切块与实体链接 → 索引 → 原子发布 corpus snapshot → QA 查询与引用回溯。

关键约束：

1. 新版本追加，不覆盖旧文；生效时间、报告期间、披露日期、获取时间分别保存，不能混用。
2. 抽取失败、未知有效日期、未经核验的资料进入隔离状态；不能默认发布为可信有效来源。
3. 研究笔记可用于建模参考，但不能作为监管结论唯一依据；仿真资料只进入明确的 regression snapshot。
4. 用 `DocumentRepository` / `CorpusSnapshot` 注入运行时；缓存按快照、分词/embedding 配置标识区分，不再靠固定文件路径和进程单例。
5. 第一阶段可保留现有中文 2-gram BM25，由 SQLite 提供 chunk 数据。存储迁移与检索算法替换分开验收，不能假设换成 FTS5 就自动解决中文检索。
6. 索引损坏或新批导入失败不影响当前快照；旧快照能重放、切回，引用仍可恢复。

验收必须看到：**一份新导入的真实原件，经重启后仍能被真实 QA 命中，答案可定位回原件，而不依赖仿真 reports TTL。**

### 3.4 补资料的顺序

先按用户任务补最小闭环，不按文件数量堆材料：

1. 选少量经核验的官方法规/规则原文，覆盖定义、适用范围、义务、例外、修订/有效期。
2. 选少量真实基金合同、招募说明书、定期报告、临时/更正公告，覆盖同一实体的跨文档、跨期间对照。
3. 保留表格、单位、脚注、页码；净值、费率等不能只抽出一个孤立数字。
4. 每份资料至少关联一个业务用例和一个证据定位核验；无法支撑任务的资料不计入该任务覆盖率。

具体法规现行有效性及内容仍需在摄取时到发布机构核验；本次是代码与数据管线审核，不是对现有摘编法律内容的有效性背书。

## 4. 测试重建：视角与执行层分开设计

### 4.1 系统、业务、用户三种视角

| 视角 | 必测任务 | 反例/边界 |
| --- | --- | --- |
| 系统 | TBOX 闭包、SHACL、IR、查询、摄取幂等、快照切换、缓存、证据定位、预算、并发 | 坏文件、重复 ID、缺索引、失效来源、超时、部分导入失败、跨快照串数据 |
| 业务 | 点查、关联、多跳、聚合/排序、时点/最新、法规/披露问答、比较/定义 | A/C 份额混淆、日期错配、单位错误、同名实体、例外条款、修订冲突、空结果 |
| 用户 | 口语、同义词、错别字、不完整问题、多轮指代、澄清、可读引用 | 不可回答、信息不足、无关问题、文档提示注入、越范围请求、错误拒答 |

先形成“任务 × 资料类型 × 时间语义 × 预期状态”的适用覆盖矩阵。不机械穷举全笛卡尔积；必需格由业务负责人确定，高风险格优先。现阶段不支持的能力明确为 capability gap，不能删除问题中的条件后算成功。

### 4.2 四个执行层

| 层 | 用途与入口 | 数据/模型依赖 | 运行政策 |
| --- | --- | --- | --- |
| S0 单元/语义契约 | 纯函数、OWL/闭包、匹配器、评分器负控 | 小型 fixture、mock；无网络 | 每次改动可运行；算法 fixture 可以保留 Python |
| S1 离线集成 | 导入 → 库 → 索引；Intent → 查询 → 证据 | 可重建的小型 RDF/SQLite fixture | 必需依赖缺失即失败；旧手工 Intent E2E 归入此层 |
| S2 业务验收 | 自然语言 → 实际执行 → 结果与证据 | 版本锁定的真实 corpus；按 suite 明确是否需模型 | 小型 smoke + 完整验收；规则、mock、在线结果分开 |
| S3 用户 E2E | API/UI、多轮、真实模型与用户场景 | 受控环境、真实模型 | 手动/定期运行；缺配置标 unavailable/blocked，不能冒充通过 |

业务题目、期望结果和证据标注外置；通用 runner、matcher、算法测试仍保留 Python。无需为目录好看而立即更换 unittest，先用按 case_id 的 subTest 也可以。

建议新增目录职责（以下是拟议结构，不是已经创建）：

```text
tests/
  unit/                 纯算法和评分器负控
  contracts/            本体、协议、数据契约
  integration/          导入、查询、证据集成
  e2e/                  真实用户入口
  fixtures/             小型可重建输入及原文样本
evaluation/
  schemas/              case / manifest / result 的 JSON Schema
  cases/legacy/         原题库保留并标明局限
  cases/development/    新业务开发题集
  manifests/            题集、语料、模型运行配置锁定
  runners/              统一调用与运行记录
  matchers/             通用判定逻辑
```

盲测题集不放在调参者可反复查看的 development 目录；对外部题集只保存允许公开的 manifest、数量和校验标识。

## 5. 用例数据合同与评分器

### 5.1 case 必填语义

- 身份与血缘：case_id、schema_version、suite、split、task_family、scenario_group、来源/标注者/审校状态。
- 用户输入：question 或 turns、as_of、允许的工具/能力边界、dataset_snapshot。
- 预期状态：可回答、空结果、澄清、证据不足、拒绝；答案状态与意图解析状态分别记录。
- 预期答案：实体集合、字段/数值、单位/币种、日期、顺序、数值容差。
- 必需语义：过滤、排除、时间、聚合、排序等不可遗漏条件；等价计划可接受，不把某条实现路径当唯一正确答案。
- 证据：文档版本 + 原件页/条/表格定位 + 必需事实；允许等价证据组。chunk ID 可作辅助，不把重切块后的新 ID 自动视作答案错误。
- 失败行为：何时澄清、拒答、超时，什么降级允许，什么约束禁止放宽。

Schema 校验在执行前完成，未知断言字段、不支持的 matcher、缺少必需 gold 必须报错。不得采用“期望写了才检查，否则默认成功”作为业务覆盖定义。

JSON/JSONL 是可 review 的 gold 真源；SQLite 只导入这些数据用于查询/审阅，并保存实际运行结果。若未来选 SQLite 作为 gold 编辑系统，应另立唯一编辑入口和规范导出机制，不能两边随意修改。

### 5.2 评分器先过负控

新 runner 接受真实业务用例之前，必须拒绝以下变异输出：

1. count 相同但实体全部错误，或实体重复填满数量。
2. 漏年份、阈值、经理变更、排除、排序、份额类型或单位。
3. 状态为成功但没有必需的结果或证据。
4. 引用 ID 存在，但原文不支持结论；引用过期或错误版本。
5. expected 出现未知字段，或 gold 不完整。
6. 可回答题一律拒答，以及歧义题不澄清就猜测答案。

匹配优先级：结构化结果与执行结果 > 事实—证据支持 > 语言表述。关键词检查仅作辅助；引用白名单只能证明引用存在，不能证明事实受到支持。模型裁判不能单独替代结构化断言及人工校准。

### 5.3 独立性与运行记账

- gold 由原件和独立业务审校得到，禁止由被测系统输出回填；答案和 expected 不进入 RAG 语料或模型请求。
- 数据划分按文档、实体、期间、模板族分组；同一合成模板换同义词不算独立盲测。
- 已用于分析与调参的 holdout 转为 regression；需要新的盲集，不再宣称原集未见。
- 每轮冻结 eligible cases，逐题记 pass/fail/error/timeout/skip/not_run；不能把跳测和异常从发布指标分母中隐去。
- 每次记录代码 commit + dirty diff/hash、ontology、corpus、case set、prompt、模型标识/配置、预算、fallback、重试、缓存模式和实际输出。在线非确定性需重复试验，不能承诺逐字复现。

## 6. 如何量化效果

### 6.1 指标与门槛

以下是拟议验收口径，不是本项目已经达到的结果。

| 层面 | 主指标与分母 | 第一阶段门槛 |
| --- | --- | --- |
| 数据可追溯 | 已发布真实文档中，来源/原件哈希/版本/可恢复原件位置完整的比例 | 100%；缺元数据的文档不能发布 |
| 证据定位 | 验收标注证据中，可从引用恢复到正确原件版本与页/条/表格的比例 | 验收集 100%；抽样检查必须报告抽样量，不能称全库 100% |
| 运行时闭环 | 导入、重启持久化、版本切换、失败回滚、查询命中契约 | 必需合同全部通过 |
| 评分可信度 | 负控错误输出被正确拒绝的比例；未知字段处理 | 定义的负控集 100% 被拒绝；未知断言报错 |
| 检索 | gold evidence Recall@k、MRR/nDCG、硬范围/有效版本命中率 | 先建立真实语料基线；关键证据漏检逐题归因，范围/版本违规不允许静默放行 |
| 本体裁剪 | 必需依赖召回、关系端点闭合、悬空引用、预算违规 | 契约集必需依赖/端点 100%，悬空引用 0；必要上下文超预算须显式扩容或返回不足 |
| 业务成功 | 同时满足状态、结果、必需条件、证据的 case 数 / 冻结 eligible case 数 | 先测新基线；发布阈值按任务风险预先批准，不能看结果后修改 |
| 结果正确 | 实体集合 Exact Match/P/R、数值与单位正确、日期及排序正确 | 分任务报告，不能只报 count；聚合均值不能掩盖高风险失败 |
| 拒答/澄清 | 可回答题错误拒答率；不可回答题无证据作答率；歧义题正确澄清率 | 三类分别报告，禁止一律拒答刷分 |
| 陈述支持 | 无支持事实陈述数 / 已审查事实陈述数；同时报告每题错误率及被回答比例 | 验收集观察到的无支持陈述为 0；不把有限样本 0 解释为总体风险 0 |
| 工程成本 | 冷/热 P50/P95、输入/输出 token、fallback/扩容率、全部运行成本 / 成功任务数 | 同配置配对比较；成功数为 0 时不报有限“每成功成本” |

`critical_missing` 应拆成 required/support/optional 丢失和候选误标；此前 800 字符档 13/44 不应直接被解释为 13 道业务失败。不能只扩大预算或放松 critical 定义后宣布业务质量提升，必须用执行结果与独立证据验证。

### 6.2 比较实验

1. 先建 40–60 道覆盖主要任务的 pilot，目的是暴露链路问题，不是证明泛化或法律合规。
2. 锁定同一真实 corpus、题集、模型、提示词、预算策略与机器环境；保留现有方案和候选方案逐题配对结果。
3. 区分两条实验轴：数据/测试基础设施改造，与 schema 裁剪算法改造。前者若换了题库，不与历史旧题通过率直接同比。
4. 裁剪消融可比较 full schema、current、candidate，但必须执行相同用户链路并评结果/证据，不能用 schema-level plan 代替实际查询成功。
5. 报告提升题、退化题、错误阶段、各任务分层结果；给成功率置信区间。后续按 pilot 的配对差异、风险与预先声明的非劣界确定正式样本量。
6. 分开记录检索缺证据、裁剪缺依赖、意图漏条件、计划错误、执行错误、回答不受支持，避免统一计入 critical_missing。

## 7. 与 BKN 对齐的边界

本地参考：`E:\LX\bkn-foundry\adp\execution-factory\tests\README.md:5` 将单元、smoke、完整 AT 分层，并明确 canonical test location、所需环境及外部数据；这值得迁移，但不代表其外部数据管理已满足本项目全部可复现要求。

语义检索参考：`E:\LX\bkn-foundry\adp\context-loader\agent-retrieval\server\logics\knsearch\concept_retrieval.go:132` 先补关系端点再 scope/rank/select；`E:\LX\bkn-foundry\adp\context-loader\agent-retrieval\server\logics\knsearch\concept_retrieval.go:292` 和 `E:\LX\bkn-foundry\adp\context-loader\agent-retrieval\server\logics\knsearch\search_schema.go:350` 保护选中关系的端点。

应对齐：召回 → 必需依赖闭合 → 明确范围 → 相关性排序 → 预算选择 → 可追踪的缺失/降级；对象与关系要共同参与相关性判断。测试对齐分层、统一入口、数据合同和运行依赖。

不应照搬：BKN 的微服务、消息队列与全部存储栈；对象 Top-K 也不等于模型 token 硬预算。BKN 允许补端点超过对象数量限制，而本项目遇到硬字符/token 限额时必须完整保留依赖包、受控扩容或明确不足，不能截掉端点后继续称为有效切片。

## 8. 推荐实施顺序与每阶段完成条件

| 阶段 | 交付 | 完成条件 |
| --- | --- | --- |
| P0 先修信任基础 | 旧基线标 legacy；规范 case/result schema；修三项评分假阳性；资产 manifest 与依赖检查 | 负控全部拒绝，必需用例缺资料不能假绿；保留旧基线且说明口径变化 |
| P1 真实资料最小闭环 | 文档 SQLite 迁移、摄取、版本/定位、快照；Repository 接入 RAG | 真实原件能从导入走到自然语言回答；重启、更新、失败回滚、原件定位全部验收 |
| P2 重建业务验收 | 系统/业务/用户覆盖矩阵；独立 gold；通用 runner/matcher；受控盲集 | 执行结果、证据、拒答都有独立 oracle；新基线可在干净环境重建 |
| P3 恢复优化实验 | 同题同源对照；召回/裁剪/排序消融；延迟与成功成本 | 必需语义不退化且业务成功/成本改善有配对证据 |
| 按需后续 | ABOX 事实持久化、向量/重排、多用户服务 | 必须由规模、更新、并发或质量瓶颈驱动，不能仅为技术栈完整而引入 |

迁移期保留旧测试和旧数据，新增分层并行验证；不批量删除、不改 gold 迎合代码、不将全部算法测试机械搬进 JSON。

## 9. 审查记录与限制

- 审查基于带未提交修改的工作区，HEAD 为 `dce13d952fc8192746abd83f37a8f71bde3d3610`，不能仅凭此 commit 复现所有本地内容。
- 负控使用 `.venv\Scripts\python.exe`、`unittest.mock` 和内存 case loader，三项错误输出均得到 exit=0；未调用外部模型。
- 未重跑全量测试、未进行真实 corpus 业务验收、未核验资料所摘录的现行法律内容。历史通过数不作为本次重新测试结果。
- 关键文件 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `E:/LX/LX_fund/FondOntology/tools/qa_bench.py` | `2D848E268C2334ABE789F8A81AA893EF042127A3FD36238E716E0FD8E89833F6` |
| `E:/LX/LX_fund/FondOntology/artifacts/qa/benchmarks/find.json` | `2EC0F36FF5189AEC0711BFE8268F23BE1BC62B3E414EB63E6BF3777DFC75711D` |
| `E:/LX/LX_fund/FondOntology/artifacts/qa/benchmarks/intent_real.json` | `65267F8AE423BEEDC83A67733EC35F73AEC92350F63879D2421EE085141147D8` |
| `E:/LX/LX_fund/FondOntology/artifacts/qa/benchmarks/e2e.json` | `BCCBFD47846E12D76C1856E375E109E8D934C3941B2643EDA8A277B857D318D5` |
