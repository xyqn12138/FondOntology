# T-BOX 补修审批与后续验收路线

复核日期：本机 2026-10-10（UTC+08:00）。审核对象为当前未提交工作树，不是仅审核 HEAD。

- FondOntology HEAD：`dce13d952fc8192746abd83f37a8f71bde3d3610`。
- BKN Foundry HEAD：`bb7885937ce76d2a833bb898e5f8393265d2f71b`。
- 本次仅审核、执行验证、生成评审记录与证据文件；未修改生产代码或原测试。

## 一、审批结论

**暂不批准“八项补修完全闭环”；保留两项 P2，修复后复审。**

上一轮八项问题中，七项的原始反例已修复，意图槽位评分项仅部分修复；另发现具名组合表达式的采集遗漏。没有发现 P0/P1 级问题的直接证据，也不把这些解释上下文问题扩大为完整 T-BOX 查询执行必然出错。

本轮不是空实现：全量测试正常退出，冻结 gold 未变，检查到的原测试改动没有删断言或降低预期。但“321 项全过”和“44/44”仍不能证明未覆盖的语义场景正确。

## 二、需修复的两项问题

### P2-1：exclusions 仍被意图评分器忽略

位置：`C:/Users/dgbb0u/FondOntology/tools/qa_bench.py:253`。

精确匹配列表已补 related、related_class、traversals，但没有上一轮指出的 exclusions。这是已有生产槽位，不是要求新增能力：意图解析会写入排除实体，查询生成会使用它生成排除条件。

独立复现：expected 要求排除 F005659，actual 的 exclusions 为空；当前仍返回退出码 0、1/1 通过、Semantic Accuracy=100%。这会将“其他基金”错误地包含当前基金的意图判为正确。

在项目根目录执行：

    .venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'tests'); from test_tbox_remaining_regressions import RemainingEvaluationTests; code,out,_=RemainingEvaluationTests().run_intent({'exclusions':['https://ontology.example.cn/cnfo/abox/F005659']},{'exclusions':[]}); print(code,out)"

修复要求：将 exclusions 纳入槽位比较，按其集合语义确定是否规范化顺序；补齐缺失、错误实体、正确实体三类用例。对于 expected 中不认识的语义键，应明确拒绝或报告不支持，不应静默忽略。

验收：缺失/错误 exclusions 必须失败且计入 wrong-resolved；正确 exclusions 通过。不能只新增正确示例。

### P2-2：具名 union/intersection/complement 的定义被采集器漏掉

位置：`C:/Users/dgbb0u/FondOntology/fondontology/qa/context.py:219`。

expression_ast 已支持具名 Boolean 表达式，但 expression_packet 只递归 BNode 与具名 Restriction；具名普通 Class 只走 class_packet，因此其组合定义被截断。相关入口判断也应同步检查 context.py:105、context.py:269。

在默认充足预算下，以 Target 为目标、required 为投影属性，输入以下结构：

    @prefix : <https://ontology.example.cn/cnfo/ontology/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    :Target a owl:Class; owl:equivalentClass [owl:intersectionOf (:NamedUnion :Rule)] .
    :NamedUnion a owl:Class; owl:unionOf (:One :Two) .
    :One a owl:Class . :Two a owl:Class .
    :Rule a owl:Restriction; owl:onProperty :required; owl:someValuesFrom :One .
    :required a owl:ObjectProperty .

完整图 AST 的第一个成员是 union(One, Two)；切片 AST 中它退化为 NamedUnion 的 IRI 字符串，unionOf 三元组消失，却返回 degradation=none、dropped_required=false。这不是预算取舍，而是未采集到已有表达式定义。

修复要求：统一 OWL 表达式识别函数，让采集、依赖发现与描述使用相同判断，并保留循环保护。不是继续只给某一种 RDF 节点类型打补丁。

验收：具名/匿名 union、intersection、complement 的语义 AST 一致，覆盖直接根节点与嵌套成员；充足预算不漏成员，小预算完整保留或明确报告整个表达式包被丢弃，不留下伪完整状态。

## 三、已通过与复测证据

| 核验项 | 本次结果 | 解释边界 |
|---|---|---|
| 全量 unittest | 321/321；失败 0、错误 0、跳过 0；退出码 0 | 测试阶段 241.723 秒；清理 3.38 秒 |
| 新 remaining 回归 | 13/13，且包含于本次全量 | 不覆盖上述两个遗漏 |
| 冻结公开题 | 10000/1800/800 字符三档均 44/44 | 是标注覆盖，不是端到端准确率 |
| 切片契约 / OA 回归 | 23/23、14/14 | 当前离线 benchmark 只自动装载这两组 |
| 文本与旧候选比较 | 132/132 与 eight-fixes、runtime-candidate 相同 | 说明前置公开集没有回退，不证明新收益 |
| 800 字符档 | 平均 571.5；核心精度代理 69.52%；critical_missing 13/44 | gold 覆盖与更广的关键项缺失可同时成立 |
| 冻结 gold | 两个 fixture SHA-256 与历史记录一致 | 未通过改题获得分数提升 |
| git diff --check | 无差异格式错误 | Git 提示 LF/CRLF 转换，不是测试失败 |

已修复的原始反例包括：公理端点类的约束发现、具名 Restriction、继承 parents、typed/language literal、连接静默缺失判分、自动 LLM 模式回退统计、路径 capped 漏报。related/related_class/traversals 的判分也确实有效，不能因 exclusions 遗漏否认这些修复。

独立证据文件：

- `C:/Users/dgbb0u/FondOntology/artifacts/benchmarks/approval-20261010-full-tests.log:1011`：全量汇总与正常清理记录。
- `C:/Users/dgbb0u/FondOntology/artifacts/benchmarks/tbox-slicing/approval-20261010.json:1`：本次离线结果、gold 与代码 hash。
- `C:/Users/dgbb0u/FondOntology/artifacts/benchmarks/approval-20261010-probes.json:1`：独立反例、边界探针及相关文件 hash；这些探针记录当前行为，不表示行为正确。

注意：原 eight-fixes JSON 虽然所记录的七个文件 hash 均吻合，但它没有自动运行 remaining 测试，也没有记录 qa_bench.py 和 remaining 测试的 hash。不能单凭该 JSON 证明八项全部闭环。本次全量日志与独立探针补充了这部分证据。

## 四、不作为阻塞缺陷的边界

### 1. 不把整个公理闭包都升级为 required

探针显示：只请求 p，p inverseOf q，q 的端点类存在 q 的 restriction；小预算可以保留 p/q/端点类、丢弃该 restriction，并报告 optional_context_dropped。

这不足以直接判 bug：现行 required 来自 QueryPlan，未证明 q 的全部限制都是本次任务必需，而且它并非无告警丢失。因此撤回“所有闭包成员约束必需”的无条件判断，不用它否决本轮修复。

真正要补的是依赖分类合同：区分 plan_required、实际转换或解释证明链所需的 dependency_required、optional 背景，并记录来源与方向。只有证明相关的依赖才传播必需性。

另一个边界探针：12 个兄弟属性共享一个父属性，计划仅请求 property0，默认会保留 13 个属性；max_properties=4 时核心仍在、整体公理包无法装下而报告 dropped_required。此行为符合原 OA 的双向固定点要求，不是本轮私自偏离；但提示下一阶段应收紧“任务必要闭包”，而非继续扩大无向连通分量。

### 2. 真实模型请求预算仍未闭环，但文档已经披露

当前后置预算控制 render_text，实际解释模型收到结构化 JSON。独立简单探针在 30 的配额下，render_text 估算 15、JSON 估算 241；本机使用 char_heuristic，这不是模型计费 token 的精确测量，只用于证明预算对象不一致。

实施文档已经明确这一限制，不能指控为本轮暗中伪装完成；但上线验收仍需单独解决。

### 3. 没有当前版本的独立在线收益证明

没有执行真实在线 full/current/candidate 三臂 3–5 次独立采样。本次没有调用收费在线模型。公开 44 题已经用于多轮迭代，不再是独立盲测；历史在线报告不能替代当前版本验收。

## 五、对齐 BKN 的路线，而不是照搬功能名

BKN 当前主链路的可核实参考：

- E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go:132：召回后补引用端点，再作用域过滤、排序与选择。
- E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go:292：选择高相关对象，并保全所选关系端点；对象数量是软边界。
- E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go:475：候选对象与关系统一精排。
- E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/search_schema.go:350：响应构造时再次保全关系端点。

应迁移的是“相关性选择不能破坏依赖、失败必须可追踪”的机制。OWL 公理/表达式保留是本项目自己的合同，BKN 的对象/关系 schema 不能替代它。BKN 的软对象数量上限也不能作为突破模型硬上下文窗口的理由。

不要把以下内容包装为可直接复用的成熟能力：pruneProperties 只有定义与测试调用，未接入上述主链路；overview_graph 的截断是展示图投影，不是语义保真或 prompt token 保证；实例检索的融合方法不等于 schema 检索已采用的排序方法。当前也没有证据需要迁移整套微服务、权限或消息基础设施。

## 六、下一轮执行顺序与量化门槛

以下是建议验收合同，不是已经取得的结果。

| 顺序 | 交付内容 | 可量化验收 |
|---|---|---|
| A：先闭环本次补修 | 修 exclusions 评分与具名组合表达式；补负例与版本记录 | 每个已支持且被标注的槽位做错误值变异，错误通过数=0；具名/匿名表达式合同全部通过；原冻结 gold 不变 |
| B：最终消费预算 | 分别核算前置意图、后置解释的完整序列化请求；为输出预留额度 | 在声明支持的模型/tokenizer 下，完整输入+输出预留不超过模型窗口；超预算请求不发送；未知 tokenizer 明确告警/采用保守策略 |
| C：约束依赖扩张 | 区分直接任务依赖、证明支持与可选邻域；依赖包选择后再控制可选项 | 足够预算下任务必需召回=100%、悬空引用=0；不足预算下缺失必需项报告覆盖=100%；记录依赖扩张倍数及闭包 P50/P95 |
| D：证明业务收益 | 独立维护盲测/专家外部题集；同模型、同协议 full/current/candidate 三臂，每题 3–5 次真实采样 | 主指标为执行结果 Exact Match、错误 RESOLVED、证据支持率；同时报告输入/输出 tokens、每成功任务 token、冷/热 P50/P95 与配对置信区间 |
| E：有证据再精排 | 在同一候选集上做现有词法/路径排序与 reranker 消融 | 预先冻结质量非劣界与成本目标；仅当准确性不退化、成本或延迟有可复现收益时引入额外组件 |

指标口径必须明确：

- 不把任意 OWL 蕴含等价作为当前包裁剪的隐含承诺；对已经声明支持的表达式/公理形态做独立合同。
- 现有 package_closure_rate 只验证端点和路径，不代表组合表达式全部闭合；需要另加表达式成员覆盖/原子保留指标。
- 预算无法容纳必需语义时，应显式扩大一次或降级，而不是硬凑“必需召回 100%”。同时报告降级率和恢复成功率。
- 800 档的 69.52% 是相关性代理，不是专家标注的精确率；只能做同口径趋势对比。
- 本次全量与离线跑批有并行重叠，241.723 秒不是严格串行性能基准，不能据此宣称性能回退或加速。
- 线上重复采样不能由重复读取缓存冒充；保存模型、prompt、代码、本体、数据集版本及每次调用结果。

最终复审条件：两项 P2 的负例确实失败、修复后通过；完整回归正常退出；再将“本轮缺陷关闭”与“整体上线收益验收”分别签收，避免一次全绿覆盖全部承诺。
