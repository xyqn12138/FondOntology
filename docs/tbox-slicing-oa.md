我基于当前工作树、BKN Foundry 对照代码和最新离线复测，建议后续重点从“继续补词”转向“生产接线、依赖闭包和评测可信度”。

当前结果已经不错，但不能把 `44/44` 直接当成语义完整：

- 当前工作树在 `10000/1800/800` 字符预算下均为 **44/44 严格覆盖**。
- T-BOX 契约 **23/23**，依赖回归 **7/7**，在线评测结构校验 **7/7**。
- 完整视图约 **18,103 字符**；800 字符平均 **571.5 字符**，压缩约 **96.84%**。
- 800 字符核心精度代理约 **69.52%**，说明召回大幅改善，但噪声尚未同步下降。
- 800 字符下仍有 **13/44** 题被标记 `critical_missing`，`44/44` 与关键依赖丢失同时存在，说明当前 gold 覆盖指标还不够严格。

## 一、BKN 值得迁移的部分

BKN 最值得借鉴的是这条流程：

```text
粗召回
→ 补齐关系依赖和端点
→ 作用域过滤
→ 相关性排序
→ 最终预算裁剪
→ 返回截断状态和来源
```

对应实现可参考：

- [concept_retrieval.go](E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go:132)
- [concept_retrieval.go](E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go:292)
- [search_schema.go](E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/search_schema.go:350)

但不建议直接复制：

- `pruneProperties` 目前不是 BKN 搜索主链路的成熟能力。
- `overview_graph` 的 `Truncated` 只表示展示投影被截断，不能直接当作问答语义损失率。
- BKN 的对象类型、关系类型不等价于 OWL 类、属性、公理闭包。

FondOntology 应保留现有的 OWL 语义能力，再采用 BKN 的“依赖闭合优先”思想。

## 二、P0：先修生产接线

### 1. 让预算状态真正影响意图解析

当前 [intent.py](E:/LX/LX_fund/FondOntology/fondontology/qa/intent.py:1131) 只取：

```python
semantic_view = schema_context.render_text
```

`critical_missing`、`degradation`、`dropped_items` 和 `max_tokens` 没有进入决策。

建议改为：

```text
局部 schema
→ 判断是否因预算丢失关键依赖
→ 最多扩大一次上下文
→ 仍不足则显式降级或确定性回退
```

需要区分：

- `budget_dropped`
- `retrieval_rejected`
- `path_search_capped`
- `ontology_unavailable`
- `not_found`

不能把所有低置信召回都触发重试。

建议新增追踪字段：

```json
{
  "schema_version": "...",
  "ontology_version": "...",
  "candidate_count": 20,
  "retained_classes": 8,
  "retained_properties": 10,
  "dropped_required": false,
  "degradation": "none",
  "expansion_attempted": false
}
```

### 2. 分开评价前置和后置裁剪

当前后置切片在 [engine.py](E:/LX/LX_fund/FondOntology/fondontology/qa/engine.py:310) 生成，但表达模型只收到：

```python
context_summary=f"{len(slice_['classes'])} 类切片"
```

因此 `context.py` 的改进目前不会直接改善表达模型输入。

应拆成两条指标链：

```text
问题 → SchemaRetriever → LLM 意图 → QueryPlan
```

和：

```text
QueryPlan → ontology slice → 表达/解释模型
```

如果希望后置切片改善解释质量，应传入精简结构化切片，例如类、属性、domain/range、restriction 和 `dropped_required`，但不能让本体切片替代实例证据。

## 三、P0/P1：修复后置切片的语义闭包

### 1. required 约束当前没有真正优先

[context.py](E:/LX/LX_fund/FondOntology/fondontology/qa/context.py:191) 按字典序处理 restriction，`relevant=True` 只影响丢失标记，不影响保留顺序。

已复现：

```text
Target 同时包含 aOptional 和 zRequired
required = zRequired
max_triples = 8
结果：保留 aOptional，丢失 zRequired
```

应改成：

```text
required classes
→ required properties
→ required domain/range
→ required paths
→ required restrictions
→ required axioms
→ optional descendants/neighbors
```

所有选择单位应是不可拆分的 `SemanticPacket`，而不是单条 RDF 三元组。

### 2. 嵌套 OWL 表达式没有完整渲染

[context.py](E:/LX/LX_fund/FondOntology/fondontology/qa/context.py:87) 只检查类直接关联的 restriction。

以下结构目前会丢语义：

```text
equivalentClass(
  intersectionOf(
    Base,
    someValuesFrom(p, Other)
  )
)
```

当前结果可能只保留随机 BNode，而不返回内部 restriction。

建议实现统一的 OWL expression AST，递归支持：

- `intersectionOf`
- `unionOf`
- `complementOf`
- `someValuesFrom`
- `allValuesFrom`
- `hasValue`
- cardinality
- qualified cardinality

递归计算依赖时，只要内部 `onProperty` 属于 required 集合，整个表达式包都应标记为 required。

### 3. 属性公理需要固定点闭包

[context.py](E:/LX/LX_fund/FondOntology/fondontology/qa/context.py:200) 当前只扫描一轮出边。

需要支持：

```text
p inverseOf q
q inverseOf p

p subPropertyOf q
q subPropertyOf r

property chain
```

建议使用队列和 `visited` 做固定点展开，同时检查正向和反向声明。公理包也必须参与预算排序，不能只在属性本体存在时附带读取。

### 4. 修复跨加载确定性

[context.py](E:/LX/LX_fund/FondOntology/fondontology/qa/context.py:92) 等位置把 BNode ID 直接写入：

- restriction JSON
- `render_text`
- triples
- 公理输出

同一个 Turtle 文件重新 `Graph.parse` 两次，结果可能不同。

建议使用结构化匿名节点规范化：

```text
BNode → expression structural hash
```

验收要求：

- RDF 三元组插入顺序变化：结果一致；
- Turtle 重新加载：结果一致；
- 跨进程运行：结果一致；
- 输出 hash 一致。

## 四、P1：补齐检索可观测性

当前还有预算前静默淘汰：

- [schema_retriever.py](E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:365) 的类/属性 top-k；
- [schema_retriever.py](E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:498) 的路径 top-k。

这些候选不会进入 `dropped_items`，所以 `critical_missing=False` 不能证明完整。

建议分别记录：

```json
{
  "retrieval_rejected": [
    {"name": "x", "score": 0.42, "source": "definition"}
  ],
  "path_search_capped": true,
  "path_candidates_before_limit": 31,
  "path_candidates_retained": 12,
  "budget_dropped": []
}
```

路径记录还应带：

```text
source
target
purpose
preferred_property
score
selection_reason
```

这样才能解释“为什么选择这条路径”。

## 五、量化指标设计

建议把效果拆成五层，不再只看一个 `strict_coverage`。

| 层级 | 指标 | 计算方式 | 发布门槛 |
|---|---|---|---:|
| 召回 | Required Dependency Recall | 保留 gold 依赖 / gold 依赖总数 | 100% |
| 闭包 | Semantic Package Closure | 完整保留的依赖包 / 依赖包总数 | 100% |
| 结构 | Dangling Reference Rate | 悬空引用 / 引用总数 | 0 |
| 结构 | Silent Missing Rate | 缺失但未标记 / gold 依赖总数 | 0 |
| 确定性 | Cross-load Hash Match | 相同输入输出 hash 一致率 | 100% |
| 预算 | Budget Overflow Rate | 超过字符/token 上限的请求比例 | 0 |
| 效率 | Compression | `1 - slice_tokens / full_tokens` | 持续报告 |
| 噪声 | Semantic Precision | 相关保留项 / 全部保留项 | 不低于当前 69.52% |
| 意图 | Slot Exact Match | target、related、path、filter、time、order、aggregation 全部正确 | 分任务报告 |
| 查询 | Valid QueryPlan Rate | 通过完整 T-BOX 校验的计划 / 全部计划 | 分任务报告 |
| 结果 | Execution Exactness | 查询结果与人工 gold 一致率 | 端到端主指标 |
| 证据 | UCR | 无依据声明 / 全部声明 | 0 |
| 成本 | Tokens per Success | 每个成功任务的输入输出 token | 趋势指标 |
| 延迟 | P50/P95 | 冷启动、热缓存分别统计 | 趋势指标 |

当前离线结果可以作为基线：

- `strict_coverage`: 44/44；
- `contracts`: 23/23；
- 800 字符平均长度：571.5；
- 800 字符压缩率：96.84%；
- 800 字符核心精度代理：69.52%。

但应新增：

```text
required_dependency_recall
package_closure_rate
silent_missing_rate
nested_expression_recall
axiom_closure_recall
cross_load_determinism
```

## 六、评测器本身也要先修

### 1. 修复 Semantic Accuracy 分母

[qa_bench.py](E:/LX/LX_fund/FondOntology/tools/qa_bench.py:245) 目前只有整题通过后才增加 `resolved`，会导致条件准确率被高估。

应改为：

```text
分母 = 所有实际 RESOLVED 且有目标标注的样本
分子 = 其中 target、relation、filter、temporal、aggregation 均正确的样本
```

同时报告：

- unconditional accuracy；
- resolved-only accuracy；
- unresolved rate；
- wrong-resolved rate；
- fallback rate。

### 2. 修复 benchmark compare 的固定文件名

[tbox_slice_bench.py](E:/LX/LX_fund/FondOntology/tools/tbox_slice_bench.py:175) 只比较：

```text
baseline / iteration1 / iteration2 / iteration3 / final
```

它不会自动纳入当前工作树结果。建议改为显式参数：

```powershell
--baseline baseline.json
--candidate current-20261009.json
```

同时统一属性召回和连接召回的分母口径。

### 3. 建立独立测试集

当前 44 道冻结题已经被多轮优化使用，不能继续作为唯一验收集。

建议新增：

```text
development：当前公开 44 题
holdout：优化者不可见
external：领域专家独立编写
```

按以下任务族分层：

- 类层级和分类；
- 关系方向与多跳路径；
- 时间和 latest；
- 聚合与排序；
- OWL restriction、公理和 verify；
- 拒答、未知字段、含糊问题。

在线模型实验使用 full/current/candidate 三臂，同一问题、同一模型、同一 prompt 协议，每题进行 3–5 次独立采样，缓存只能用于复现，不能当作独立重复实验。

历史 `online-v1-20261008/report.json` 记录的 `5/11` 联合通过只能作为诊断结果，因为它保存的 `schema_retriever.py` hash 与当前工作树不同；不能作为当前版本验收结论。

## 七、建议实施顺序

### 第一阶段：生产安全

1. 接通 `critical_missing` 和 `degradation`。
2. 增加一次定向上下文扩大。
3. 增加 schema trace 和完整本体版本 hash。
4. 修复评测器分母和 compare 参数。

### 第二阶段：后置切片正确性

1. SemanticPacket 依赖包模型。
2. required restriction 优先级。
3. OWL expression AST。
4. inverse/subProperty/property-chain 固定点闭包。
5. BNode 结构化规范化。

### 第三阶段：端到端收益

1. 将 post-plan slice 接入真正的解释模型上下文。
2. 扩展生产 IR 的投影、时间、计算和分组字段。
3. 以有效 QueryPlan 率、执行结果正确率和证据忠实度为主指标。
4. 最后再考虑 reranker、embedding 或更复杂的自适应策略。

最重要的判断是：当前召回问题已经基本解决，下一轮不应继续围绕公开题集增加领域词条。优先修复依赖包闭合、预算状态接线、OWL 表达式递归和评测口径，才能把“裁剪文本看起来完整”推进到“裁剪后仍能稳定生成正确查询”。