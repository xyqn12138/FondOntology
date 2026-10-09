# T-BOX 本体裁剪对比与改进路线

分析日期：2026-10-08（当前工作区日期）。本文中的“本项目”指 FondOntology，BKN Foundry 为参考项目。

代码基线：

- FondOntology：`7692188c9c922cbee3afe4690f9fb3acdcf081d5`
- BKN Foundry：`bb7885937ce76d2a833bb898e5f8393265d2f71b`

本文是改进建议，不代表已实施；本次仅新增本文档，不修改本体或业务代码。

## 1. 文档目的

本文比较两个项目的 T-BOX（本体语义网）裁剪实现：

- **FondOntology**：基金领域本体项目，当前本体约 148 个类、221 个属性，裁剪主要服务于 LLM 意图解析和查询结果上下文。
- **BKN Foundry**：通用知识网络平台，裁剪主要服务于 schema 搜索、关系类型路径查询和有限本体图展示。

本文只讨论 T-BOX：类、对象属性、数据属性、domain/range、类层级和 OWL 约束。实例数据、实例子图和 A-BOX 查询不属于本文改进对象。

本文结论基于当前代码静态分析，以及 FondOntology 现有回归测试和额外预算探针；不代表 BKN 的所有裁剪代码都已经在生产链路启用。

**核心结论**：优先修复“必需依赖静默丢失”和“切片结果不可观测”，再增强召回与 OWL 约束。基金项目已有完整 T-BOX 校验、继承感知路径和反向路径能力，应保留并复用，而不是整体替换为 BKN 的类型 Top-K 搜索。

这里的“语义闭合”指选定任务的属性、路径、端点及支撑信息相互一致，**不等于保证所有 OWL 蕴含的本体模块抽取**。BKN 的对象类型/关系类型也不能与 OWL 类/公理逐项等同。

## 2. 当前实现概览

### 2.1 FondOntology 的两层裁剪

FondOntology 目前存在两条不同的裁剪链路。

| 链路 | 代码 | 调用时机 | 结果用途 |
|---|---|---|---|
| 问题驱动 schema 上下文 | `fondontology/qa/schema_retriever.py` | LLM 意图解析前 | 生成问题相关的类、属性、路径文本 |
| 查询计划后的 ontology slice | `fondontology/qa/context.py` | QueryPlan 生成并执行后 | 返回 `local_context.ontology_slice`；表达模型当前仅获得类数量摘要 |

第一条链路由 `fondontology/qa/intent.py::_build_llm_intent` 正式调用。它的流程是：

```text
问题
  → VocabularyResolver 词法候选
  → 类/属性/实体 seed
  → 补直接父类
  → 补属性 domain/range
  → BFS 查找最多 3 跳的关系路径
  → 文本渲染
  → max_chars 行级裁剪
```

第二条链路由 `fondontology/qa/engine.py` 调用。它按以下优先级生成结构化切片：

```text
target + 祖先类
  → target 的直接子类
  → 计划使用属性的 domain/range
  → 类和属性摘要
  → OWL restriction 简表
```

这两条链路解决的问题不同，不能用一套 Top-K 逻辑替换。

当前 schema 召回允许利用实体类型作为 T-BOX seed；这不等于裁剪实例图。本文探针只加载 T-BOX，没有加载 A-BOX，避免把实例覆盖率混入裁剪能力判断。

### 2.2 BKN Foundry 的相关机制

BKN 中值得对比的实现有三类：

1. **问题相关 schema 召回**
   - `adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go`
   - 先粗召回对象类、关系类和行动类。
   - 关系端点补齐后再做范围过滤、相关性排序和 Top-K。
   - 选中关系后，强制把关系两端对象类补回，避免返回悬空关系。

2. **schema 响应裁剪**
   - `adp/context-loader/agent-retrieval/server/logics/knsearch/search_schema.go`
   - `limitObjectTypesKeepingRelationEndpoints` 先截取对象类，再补充返回关系的端点。
   - 预算优先服从相关性，同时保证基本结构自洽。

3. **有限本体图投影**
   - `adp/bkn/bkn-backend/server/logics/knowledge_network/overview_graph.go`
   - 支持节点预算、边预算、焦点对象类、扩展深度、概念分组和游标。
   - 返回 `Truncated`、总量和下一页游标，明确告诉调用方结果是否被裁剪。

需要特别注意：BKN 中 `pruneProperties` 虽然存在，但当前搜索主链路没有调用它。因此，它可以作为算法参考，不能直接视为已经验证的生产方案。

### 2.3 代码导航

基金项目链接指向本地代码；BKN 条目按 2.2 节的仓库相对路径定位。行号以本文代码基线为准。

| 项目 | 入口 | 重点 |
|---|---|---|
| FondOntology | [SchemaRetriever.retrieve](E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:83) | 候选、端点补齐、路径召回 |
| FondOntology | [SchemaRetriever._render](E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:289) | 行级字符裁剪 |
| FondOntology | [build_ontology_slice](E:/LX/LX_fund/FondOntology/fondontology/qa/context.py:49) | 计划依赖、required 排序、restriction |
| FondOntology | [OntologyContext.score_path](E:/LX/LX_fund/FondOntology/fondontology/qa/semantics.py:264) | 可复用的路径相关性评分 |
| FondOntology | [_build_llm_intent](E:/LX/LX_fund/FondOntology/fondontology/qa/intent.py:1126) | 局部 schema 的实际调用点 |
| FondOntology | [engine.py](E:/LX/LX_fund/FondOntology/fondontology/qa/engine.py:310) | 后置切片与表达模型之间的接线 |
| BKN | `concept_retrieval.go:292` / `selectObjectTypesForConceptRetrieval` | Top-K 后端点强制补齐 |
| BKN | `concept_retrieval.go:475` / `rankConcepts` | 粗召回、rerank、降级 |
| BKN | `concept_retrieval.go:820` / `pruneProperties` | 未接入搜索主链路 |
| BKN | `search_schema.go:350` / `limitObjectTypesKeepingRelationEndpoints` | 响应阶段再次补齐端点 |
| BKN | `overview_graph.go:325` / `ListOverviewGraph` | 展示投影预算、游标与截断状态 |

## 3. 对比结论

| 能力 | FondOntology | BKN Foundry | 判断 |
|---|---|---|---|
| 问题驱动的类/属性召回 | 有，确定性词法 + 少量 hints | 有，粗召回 + 可选 rerank | BKN 的两阶段排序值得借鉴 |
| domain/range 补齐 | 有 | 有，关系端点补齐 | FondOntology 语义方向正确 |
| 继承感知路径 | 有，支持反向路径和最多 3 跳 | 有，类型路径 BFS | FondOntology 对 LLM 语境更直接 |
| 关系端点完整性 | 部分有，路径会补端点，但渲染裁剪时可能丢失 | 明确保证关系端点存在 | BKN 的“必需依赖优先”应迁移 |
| 属性相关性排序 | 目前主要依赖词法命中和硬编码 hints | 对概念和关系统一 rerank | FondOntology 需要补通用排序层 |
| OWL 约束切片 | 有 restriction 设计，但实现不完整 | 主要围绕类型关系和权限 | FondOntology 应保留 OWL 语义优势 |
| 预算 | 通常按 `max_chars` 裁剪；token 主要是统计 | 检索 Top-K 可因补端点超限；展示有节点/边上限 | 区分软数量上限与模型硬预算 |
| 截断可观测性 | `build_ontology_slice` 有 `truncated`，`SchemaContext` 没有 | `Truncated`、总量、游标 | BKN 的契约更完整 |
| 失败补救 | 没有完整上下文重试 | 有降级排序和权限降级 | 可引入一次性扩大上下文 |
| 是否修改 T-BOX | 不修改 | 不修改 | 两者都正确 |

## 4. FondOntology 当前缺陷

### 4.1 高优先级：行级预算会删除语义必需项

位置：`fondontology/qa/schema_retriever.py::_render`

当前做法是先按固定区段输出：

```text
候选类
对象属性
数据属性
关系路径
问题条件词
```

超过 `max_chars` 后按行加入，放不下的行直接跳过。这个算法没有知道：

- `investmentFocus` 是实际过滤属性；
- `investmentFocus` 的 domain 是 `FundInvestmentStrategy`；
- `usesInvestmentStrategy` 是基金到策略类的必要连接；
- 一条关系路径中的每个属性和端点必须成组保留。

实际探针结果（仅加载 T-BOX，检查属性定义行，不调用在线 LLM）：

- 问题：`医药主题的股票型基金有哪些？`
- 完整本体语义视图：18,103 字符；
- 未触发预算的局部上下文：1,324 字符，8 类、8 属性、6 路径，较完整视图减少约 92.7%；
- `max_chars=800` 时，候选元数据仍包含 `investmentFocus` 和 `usesInvestmentStrategy`；
- 实际渲染为 792 字符，两个属性的定义行均被删除；`max_chars=500` 时为 499 字符，同样缺少这两行；
- 元数据仍是 8 类、8 属性、6 路径，没有截断字段；不能将这些列表当作最终文本的保留项清单。

这会产生“候选集合看似完整、发送给 LLM 的文本却语义不闭合”的不一致。

**影响**：模型可能无法判断过滤属性属于哪个类，也无法生成正确的跨类路径。

这里确认的是上下文缺失，不是已经证明在线问答失败。另外，`_render` 无条件保留问题和标题等头部，若头部本身超过 `max_chars`，仍会超限；因此它不是任意输入下的绝对字符硬上限。

### 4.2 高优先级：`SchemaContext` 没有记录截断和丢弃原因

`SchemaContext` 当前只记录：

- `classes`
- `properties`
- `paths`
- `conditions`
- `render_text`
- 字符/token 统计

它没有记录：

- 是否发生裁剪；
- 哪些类、属性、路径被丢弃；
- 被丢弃项是否是必要依赖；
- 当前预算是否无法容纳一个完整语义包；
- 使用了字符预算还是模型 tokenizer 预算。

因此，上层无法区分：

1. 本体中确实不存在该属性；
2. 属性存在但没有召回；
3. 属性召回了但被渲染预算丢弃；
4. 属性属于可选邻域，被有意降级。

### 4.3 高优先级：查询计划依赖提取不完整

位置：`fondontology/qa/context.py::build_ontology_slice`

当前 `used_props` 只从以下字段收集：

- `filters`
- `traversals`
- `projections`

但 QueryPlan 还可能通过以下字段依赖 T-BOX 属性或路径：

- `relation_path`
- `ordering`
- `aggregations`
- `date_ranges`
- `latest`
- `where`
- `optional`
- 嵌套条件中的 path/property

这意味着查询执行已经使用的属性，不一定进入 ontology slice；`required` 标志也无法覆盖所有真实依赖。

微型 RDF 探针中，计划仅通过 `relation_path` 使用 `zRequired`，返回 `counts.used_props=0`；该属性即使通过邻域被补回，也被标为 `required=false`。修复时应按计划字段结构提取，例如 `ordering.by`、`aggregations.measure_property`，不能把 `"agg"` 或普通条件值当作属性 IRI。

### 4.4 高优先级：`required` 标记没有成为排序规则

`build_ontology_slice` 给属性输出了 `required` 字段，但属性实际按 IRI 排序：

```python
for p in sorted(used_set, key=str):
```

所以在属性预算不足时，可选属性可能先于计划必需属性被保留。

微型 RDF 探针为 `Target` 声明 `aOptional` 和 `zRequired`，filter 使用 `zRequired`，设置 `max_properties=1`；实际只返回 `aOptional(required=false)`，必需属性被挤掉。

正确的优先级应为：

```text
required 计划属性
  > required 属性的 domain/range
  > required 路径端点
  > 当前类直接约束
  > 直接子类
  > 可选邻域
```

### 4.5 中高优先级：OWL restriction 读取会漏掉匿名节点

位置：`fondontology/qa/context.py` 的 restriction 遍历。

当前代码要求 restriction 节点满足：

```python
isinstance(r, URIRef)
```

但本体 Turtle 中的 `owl:Restriction` 通常是匿名 blank node。当前 `ontology/cnfo-fund.ttl` 已存在多个匿名 restriction，包含：

- `owl:hasValue`
- `owl:someValuesFrom`
- `owl:onProperty`

因此切片可能返回零条 restriction，即使目标类确实声明了约束。

微型 RDF 探针为目标类添加 BNode restriction 后，当前实现实际返回 0 条约束。

此外，当前 restriction 输出只保留 `some_values_from`，没有输出：

- `hasValue`
- `allValuesFrom`
- cardinality
- qualified cardinality
- 经 `equivalentClass` 等类表达式连接的约束

### 4.6 中优先级：token 预算只是观测值，不是硬限制

`SchemaRetriever` 以 `max_chars` 作为实际限制，`estimate_token_count` 只在最后统计 token。

`SliceBudget.max_context_tokens` 已定义，但 `build_ontology_slice` 不会依据它计算或截断渲染结果。字符和 token 的关系受中文、IRI、英文标识符和模型 tokenizer 影响，不能长期用固定比例替代真实预算。

其他预算契约也有偏差：`max_triples` 实际将类、属性和 restriction 摘要各按一个单位计算，并非 RDF 三元组计数；类/属性返回数可以先超过它，restriction 耗尽预算也不会更新 `truncated`。类循环还在预算判断前写入 `seen`，导致未返回的类可能参与后续属性与约束扩展。

### 4.7 中优先级：词法召回覆盖范围有限

当前召回主要来自：

- IRI/local name/label/alias；
- `_TYPE_SYNONYMS`；
- `_TYPE_HINTS`；
- `_PROPERTY_HINTS`；
- 简单子串匹配。

已经观察到以下问题（同一仅加载 T-BOX 的探针）：

- “规模最大的债券基金有哪些？”只返回 `BondFund/Fund/FundBusinessObject`，173 字符、0 属性；
- “最近一个月净值上涨最多的基金有哪些？”只返回 `Fund/FundBusinessObject`，176 字符、0 属性；
- 新增本体词汇需要同步修改 hints，存在规则维护分散问题；
- 类和属性定义文本尚未成为主要召回信号。

这不等于最终 QueryPlan 一定错误，但会使 LLM 看到的候选 schema 不完整。

### 4.8 中优先级：没有一次性语义补救路径

当前 LLM 意图解析失败后主要回落到确定性解析；尚没有以下机制：

```text
局部 schema
  → 白名单/依赖检查失败
  → 仅扩大一次 schema 范围
  → 重新解析
  → 仍失败则确定性回退
```

如果裁剪缺少必要关系，模型没有机会获得更完整的 T-BOX。

这里指“扩大语义上下文重试”缺失，不代表代码没有模型调用或格式解析重试。当前校验使用完整本体，不能把局部上下文列表收紧成唯一合法白名单，否则会误拒本体中合法但未被召回的字段。

### 4.9 中优先级：后置切片未完整进入表达模型

`engine.py` 构建了结构化 slice 并放入 `local_context`，但调用 `explainer.explain` 时仅传入 `context_summary=f"{len(slice_['classes'])} 类切片"`。不能据此声称属性定义、路径或 restriction 已送给表达模型。

这不是本轮已证实的答案错误，但影响改进收益：即便完善 `context.py`，也不会自动改善模型的语义解释。需要单独评估是否传入精简 T-BOX 摘要，同时保留证据引用闸门，不能把类型约束当作实例事实。

## 5. BKN 值得借鉴的机制

### 5.1 相关性选择后修复依赖闭合

BKN 的核心经验是：

1. 粗召回后补齐候选关系引用的对象，再执行范围过滤和排序；
2. 对象相关性 Top-K 优先占位；
3. 把选中关系的两端对象强制补回；
4. 端点补齐允许超过数量上限；响应层再次保护端点，不将裸 Top-K 当作最终结果。

FondOntology 应将其推广为“语义包”：

```text
一个任务相关属性包 =
属性本身
+ domain 类
+ range 类
+ 相关关系路径
+ 路径中间类
+ 关联 restriction（如果存在）
```

语义包内部不可拆分；只有可选包才能被预算丢弃。

应区分软 Top-K 与硬 token 限制：BKN 允许超对象数量，并不意味着基金项目可以突破模型上下文窗口。必要包装不下时，先压缩定义等非必需描述；仍装不下则返回 `budget_insufficient`、明确缺失项并降级，不输出未标记的残缺包。

前置 schema 尚没有 QueryPlan，只能把高置信问题候选及连接依赖列为“优先保留”；后置 slice 才能根据已验证计划确定 `required`。不要把所有召回候选都标成计划必需项。

### 5.2 粗召回与精排分层

BKN 的粗召回和 rerank 分离，适合迁移到基金项目：

- 粗召回：local name、label、altLabel、definition、同义词、代码表；
- 精排：问题与类/属性/路径的相关性；
- 结构修复：补父类、domain/range、路径端点；
- 最终预算：按必要性和相关性裁剪。

不建议第一阶段直接引入远程模型 rerank。FondOntology 可以先使用确定性打分，确保低延迟、可复现和容易回归。

### 5.3 明确截断契约

BKN 对分页和图裁剪返回明确的总量、游标和 `Truncated`。FondOntology 应让 schema 上下文也具备同等级别的可观测性。

建议增加以下契约。下例为字段示意而非实测响应：可选属性包被删除，没有删除计划必需项；token 预算尚未启用时显式给出 `null`。

```json
{
  "truncated": true,
  "dropped_required": false,
  "budget": {
    "max_chars": 800,
    "used_chars": null,
    "max_tokens": null,
    "used_tokens": null
  },
  "dropped": {
    "classes": [],
    "properties": ["optionalProperty"],
    "paths": []
  },
  "degradation": "optional_context_dropped"
}
```

### 5.4 权限/可见性与图结构分离

BKN 先构造可见范围，再搜索路径和裁剪图。FondOntology 当前没有复杂权限层，但应保留相同的边界思想：

```text
本体可用范围
  → 语义召回
  → 依赖闭包
  → 预算裁剪
  → 渲染
```

不要在最后一步才删除类或属性，否则容易出现路径、domain/range 或 restriction 悬空。

## 6. 推荐目标架构

建议区分三个职责，优先在现有 `VocabularyResolver`、`SchemaRetriever` 和 `build_ontology_slice` 内整理函数和数据流；不要求立即新增三个模块或重构公共接口。

### 6.1 Resolver：候选召回

输入：问题和对话上下文。

输出：

- 类候选及分数；
- 属性候选及分数；
- 关系路径候选及分数；
- 条件词；
- 候选来源（label、altLabel、definition、synonym、entity type 等）。

Resolver 不负责预算，也不负责最终删减。

### 6.2 Slice Planner：语义闭包

输入：候选；后置链路另有已验证的 QueryPlan。两条链路共用依赖展开规则，不共用未经区分的 required 判定。

输出：带优先级的语义包：

```text
required:
  target / related / filters / traversals / ordering / aggregation 所需概念
  relation_path 中每个属性和端点
  domain/range
  计划涉及的 restrictions
supporting:
  祖先类
  直接父子类
  inverse / equivalent / subProperty 支撑
optional:
  邻近类、补充定义、非必要兄弟路径
```

Slice Planner 应负责去重、闭包和一致性检查，但不负责字符串渲染。

### 6.3 Renderer：预算与降级

输入：带优先级的语义包。

输出：

- LLM 文本；
- 保留概念列表；
- 丢弃列表；
- 截断状态；
- 预算统计；
- 缺少必要项时的降级级别。

Renderer 不得把 required 属性和 optional 属性放在同一排序池中。

预算应覆盖最终序列化文本，而不只是候选项计数；前置 LLM 调用还应预留系统提示、示例、对话与输出空间，不能将整个模型窗口分配给 T-BOX。

## 7. 分阶段改进路线

### P0：修复裁剪契约和语义闭合

目标：不改变整体问答架构，先避免“静默丢关键依赖”。

建议 P0/P1 作为首轮交付，P2 随召回基准推进；P3 的 BNode 基础修复可提前，其余复杂公理支持逐项建设。P4 在缺失检测可靠后再做，避免对所有失败盲目扩大上下文。

任务：

1. 扩展 `SchemaContext`：
   - `truncated`
   - `critical_missing`（问题关键包是否缺失）
   - `retained_properties` / `retained_paths`（实际保留项）
   - `dropped_items`
   - `budget_used`
   后置 slice 另加 `required_properties/required_paths/dropped_required`，依据已验证计划标记，而不是把候选分数当作计划依据。
2. 将 `_render` 从行级跳过改为语义包选择。
3. 保证一条路径的属性、端点和必要 domain/range 同时保留。
4. `build_ontology_slice` 按 required 优先，而不是按 IRI 排序。
5. 明确 `max_chars` 与 token 预算的职责，暂时至少把 token 预算标为未启用，而不是伪装成硬上限。
6. 增加低预算回归测试。
7. 修复 `seen` 与已返回类集合不一致；重命名或落实 `max_triples` 的计数语义，把约束截断计入状态。

验收：

- `max_chars=800` 时，医药主题查询要么完整保留 `usesInvestmentStrategy` + `investmentFocus` 及连接依赖，要么明确关键包缺失和 `budget_insufficient`，不得静默删除。
- 属性预算不足时，required 属性不能被 optional 属性挤掉。
- 返回的每条关系路径不允许引用未返回的属性或端点。
- 标题或问题本身超预算时也必须显式失败或降级，不能悄悄超出硬限。

### P1：补齐 QueryPlan 依赖提取

目标：让后置 ontology slice 与真正执行的计划一致。

任务：

1. 统一递归提取 `filters/traversals/projections/relation_path/where/optional`。
2. 收集 `ordering`、`aggregations`、`date_ranges`、`latest` 中的属性依赖。
3. 每个依赖记录来源：
   - `filter`
   - `traversal`
   - `projection`
   - `ordering`
   - `aggregation`
   - `date_range`
   - `latest`
4. 对路径依赖补齐中间类和反向方向，补齐 `related.concept` 与 traversal 的显式类端点。
5. 决定后置 slice 是仅供 API 返回，还是也进入表达 prompt；若接入，只传精简摘要并继续以实例证据支持实例结论。

验收：

- 计划中出现的每个属性都能在 slice 的 `required_properties` 中找到。
- 路径查询和普通过滤查询的切片结果不会漏掉实际执行字段。

### P2：增强确定性召回和路径排序

目标：减少硬编码 hints 对新词汇的依赖。

任务：

1. 将 `skos:definition`、`rdfs:comment` 纳入检索信号；复用已有 label/altLabel 索引，不重复造标签机制。
2. 引入可解释的确定性粗排：
   - exact local/IRI
   - label/prefLabel
   - altLabel
   - definition/comment
   - 同义词
   - 子串长度
3. 复用 `OntologyContext.score_path` 对路径排序。
4. 对“规模、净值、收益、日期、风险、费用”等领域词建立本体词汇索引，而不是只维护散落 hints。
5. 将候选来源和分数写入调试信息，便于回归。
6. 启用与实际模型匹配的 tokenizer 预算，在最终文本上计数；没有匹配 tokenizer 时明确标记估算，保留独立字符保护上限。

验收：

- 新增一个属性定义或 altLabel 后，不修改 Python hints 即可被召回。
- 路径选择可解释：能说明为何选择某条路径。
- 对同一问题重复运行结果稳定。
- tokenizer 可用时，最终 T-BOX 文本不得超过分配预算；必需包容纳失败必须显式返回预算不足。

### P3：补齐 OWL 约束切片

目标：切片不只保留类和属性名，还能保留对语义判断有影响的约束。

任务：

1. 支持 `BNode` restriction。
2. 支持至少：
   - `owl:onProperty`
   - `owl:someValuesFrom`
   - `owl:allValuesFrom`
   - `owl:hasValue`
   - cardinality 相关约束
3. 根据任务保留相关 restriction：查询按 required property 关联，定义/对比/核验任务还需按目标类及相关公理关联。
4. 对 `equivalentClass`、`disjointWith`、`subPropertyOf` 和 property chain 做选择性补齐。
5. 增加“约束来源”和“声明/推理来源”字段，避免把推理结果误当作原始声明。

验收：

- 含匿名 restriction 的类能够被正确切片。
- `verify` 仍只读 T-BOX，不访问 A-BOX。
- 切片中的约束能够回溯到原始类和属性。

### P4：一次性自适应扩大和缓存

目标：在局部上下文不足时提高成功率，同时控制延迟。

任务：

1. 首次使用局部 slice。
2. 白名单/依赖检查发现必要项缺失时，只扩大一次：
   - 扩大字符/token 预算；
   - 增加一层邻域；
   - 补充定义和约束。
3. 第二次仍不完整则确定性回退，并把原因记录到 notes。
4. 复用已有缓存，再补齐键与失效策略：
   - `OntologyContext`
   - 候选索引
   - 常见问题的 slice 结果。
5. 评估前缀缓存和 ontology-as-tools，而不是在本阶段直接引入多轮 LLM 选择。

验收：

- 依赖缺失时最多增加一次模型解析调用。
- 本体版本变化会失效缓存。
- 失败路径不返回语义上不完整但未标记的上下文。

缓存键至少包含本体导入闭包的内容指纹、问题/上下文、预算与策略版本。当前 snapshot 的本体 hash 只计算入口文件，单独修改被导入模块可能不改变该值；不能直接拿它当完整 T-BOX 版本。未来启用权限时还应包含可见范围；启用实体类型 seed 时也需隔离相应实体索引版本。

## 8. 测试与基准建议

### 8.1 最小回归集

至少覆盖：

1. `医药主题的股票型基金有哪些？`
   - `EquityFund`
   - `FundInvestmentStrategy`
   - `usesInvestmentStrategy`
   - `investmentFocus`
2. `同时管理多个基金的基金经理有哪些？`
   - `FundManagerPerson`
   - `^hasFundManager`
3. `R4以上的基金有哪些？`
   - 风险属性及其相关代码语义
4. `最近一个月净值上涨最多的基金有哪些？`
   - 时间、净值、排序相关候选
5. `基金管理人和基金托管人有什么区别？`
   - 两侧定义卡、关系和角色类
6. 人为设置极小预算：
   - 只能丢 optional；
   - required 丢失必须显式标记。
7. 匿名 OWL restriction：
   - 不能因为 `BNode` 而返回空约束。

### 8.2 当前已执行验证

已执行：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_schema_retriever.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_qa_e2e.py -v
```

结果：

- `test_schema_retriever.py`：3/3 通过；
- `test_qa_e2e.py`：6/6 通过。

这些测试是现有行为回归，其中确定性 find 测试使用模拟 A-BOX。它们不能证明在线 LLM 答案正确，也不是 T-BOX 蕴含保持测试；本次额外预算和微型 RDF 探针只加载 T-BOX。尚未覆盖：

- 小预算下 required 依赖是否完整；
- `SchemaContext` 是否正确报告丢弃项；
- `relation_path`、`ordering`、`where` 等全部计划字段的依赖提取；
- 匿名 restriction；
- token 硬预算；
- 扩大上下文重试。

### 8.3 探针与后续指标

预算探针使用 `build_stack(Path("ontology/modules/cnfo-domain.ttl"))`，不传 A-BOX；构建 `OntologyIndex` 后，以 `SchemaRetriever(index, max_chars=cap).retrieve(question)` 分别测试 `cap=10000/800/500`。应同时检查 `render_text` 中的属性定义行与 `properties/paths`，避免把候选元数据误当作实际 prompt。本文数字是当前基线的一次确定性观测，不是性能统计。

在基金项目根目录执行以下 PowerShell 片段可复现字符预算探针：

```powershell
@'
from pathlib import Path
from fondontology.qa.graph import build_stack
from fondontology.qa.index import OntologyIndex
from fondontology.qa.schema_retriever import SchemaRetriever
index = OntologyIndex(build_stack(Path("ontology/modules/cnfo-domain.ttl")))
question = "\u533b\u836f\u4e3b\u9898\u7684\u80a1\u7968\u578b\u57fa\u91d1\u6709\u54ea\u4e9b\uff1f"
for cap in (10000, 800, 500):
    result = SchemaRetriever(index, max_chars=cap).retrieve(question)
    print(cap, result.char_count, len(result.properties))
    for prop in ("investmentFocus", "usesInvestmentStrategy"):
        print(prop, prop in result.properties, prop + "(" in result.render_text)
'@ | .venv\Scripts\python.exe -
```

微型图探针仅包含 `Target`、`Other` 两类，`aOptional`、`zRequired` 两个具有 domain/range 的对象属性，以及一个 BNode restriction。分别使用 filter、relation_path 和 `max_properties=1` 隔离三个缺陷，后续应固化为单元测试。

建立固定问题集，至少同时报告：

- 已验证计划的 required 属性/路径召回率，完整与小预算分别统计；
- 最终文本悬空引用率、元数据与文本一致率、未标记缺失次数；
- 实际 tokenizer 下上下文 token 分布和延迟；
- 局部解析失败率、一次扩大后的恢复率、额外模型调用数。

采用“完整上下文 / 当前裁剪 / 改进裁剪”三组对照，同问题、同模型、同提示配置评估。小预算缺陷修复的验收应依赖确定性结构检查，不依赖模型偶然答对。

## 9. 非目标与边界

本路线暂不包含：

- A-BOX 实例子图裁剪；
- 用实例频率替代 T-BOX 语义判断；
- 将 BKN 的展示型 `overview-graph` 直接搬入基金问数链路；
- 第一阶段引入远程 embedding/rerank 服务；
- 修改正式 T-BOX 文件或推理规则；
- 用裁剪后的上下文替代完整 T-BOX 作为 QueryPlan 校验依据。

最终原则：

```text
完整 T-BOX 负责语义正确性；
局部 T-BOX 负责模型上下文效率；
任何裁剪都不能破坏计划依赖和可解释的语义闭合。
```
