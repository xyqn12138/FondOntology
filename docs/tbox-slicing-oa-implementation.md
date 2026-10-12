# T-BOX OA 修复记录

日期：2026-10-09。基于 OA 审批建议实施，不新增公开题专用词条。

## 已实施

- 意图解析接通 `critical_missing` 和预算原因，最多扩大一次字符/token 配额；
  扩大后仍丢失关键依赖时不调用模型，回退确定性解析。
- `IntentResult`、`QaAnswer`、报告 meta 和 Web API 透传 schema trace。
  区分类似预算丢失、检索淘汰、路径限额、本体不可用和未召回的状态。
- 对完整已加载 T-BOX 做匿名节点规范化和内容 hash，覆盖导入模块；
  快照 `ontology_hash` 从入口文件字节 hash 改为完整图内容 hash。
- 后置切片以 `SemanticPacket` 为选择单位。required 类、属性核心和
  domain/range 先于 required 约束、公理闭包及 optional 上下文。
- 递归表达 intersection、union、complement、restriction 和各类基数约束；
  嵌套 required 属性使整个表达式包成为 required。
- inverse/subProperty 的正向与反向声明及 property chain 采用队列固定点展开。
- 匿名节点规范化后输出 AST、restriction、axioms 和 triples；
  跨重载、插入顺序和进程确定性通过合成回归验证。
- 实际表达模型接收结构化后置切片，不再仅传类数量；
  不按字符串截断 JSON，实例事实仍受 claims 引用闸门约束。
- 检索记录 lexical top-k、作用域淘汰和逐次路径搜索/选择诊断。
- 意图评测的错误 RESOLVED 样本纳入分母；增加 unconditional、
  resolved-only、unresolved、wrong-resolved 和 fallback 输出。
- 离线 compare 支持显式 `--baseline` / `--candidate`；
  run 和 compare 的适用样本及替代连接分母一致。

## 复测与口径

新增合成回归位于 `tests/test_tbox_oa_regressions.py`，不依赖基金领域词条。
原有 44 题在 10000/1800/800 字符预算均为 44/44；
原有切片契约 23/23；确定性意图基准 16/16。
800 字符平均 571.5，核心精度代理 69.52%，未发生公开题召回退化。

2026-10-10 补验：OA 专项 14/14、切片契约 23/23、
E2E 6/6、意图回归 20/20；此前表达层 14/14、Web 11/11。
完整 301 项测试跑批持续较长时间且未取得最终汇总，已主动中止，
不能宣称全量测试通过。`git diff --check` 无错误。

后续增加 `tools/run_tests.py` 简略进度与耗时日志后，
2026-10-10 完整复跑 **302/302 通过，失败 0、错误 0、跳过 0**，
测试执行耗时 1762.164 秒（约 29 分 22 秒）。
日志：`artifacts/benchmarks/full-tests-20261010.log`。
此前未取得终态的结论由这次完整结果补足。
显著慢点：SchemaRetrieverTest 类初始化 446.90 秒、
latest 子查询单例 308.10 秒、首个 Find 查询 219.00 秒、
自然语言 find 单例 114.03 秒。共享只读 fixture 优化尚未实施；
这些耗时是诊断基线，并非已确定的内部根因。
注意：完整成功汇总输出后，Python 进程在退出清理阶段仍持续数分钟
且有 CPU 活动，最终主动终止。测试结果为通过，但进程没有取得正常
退出码；退出清理耗时还需独立定位。

新增 required_dependency_recall 只衡量 gold 明确标注的类、字段和连接单位；
package_closure_rate 只衡量已保留属性端点和路径包；
silent_missing_rate 不证明 gold 未标注依赖完整。
这些指标不应冒充完整 OWL 语义或端到端问答准确率。
原公开 holdout 已参与迭代，报告保留旧 split 便于历史比较，
但明确其不再是独立盲测集。

复测命令：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_tbox_oa_regressions.py
.venv\Scripts\python.exe tools\tbox_slice_bench.py --output artifacts\benchmarks\tbox-slicing\oa-candidate-20261009.json
.venv\Scripts\python.exe tools\tbox_slice_bench.py --baseline artifacts\benchmarks\tbox-slicing\current-20261009.json --candidate artifacts\benchmarks\tbox-slicing\oa-candidate-20261009.json --compare artifacts\benchmarks\tbox-slicing\oa-20261009
```

## 后续验收

2026-10-10 运行性能优化及当前语义能力边界，详见
[实施与运行评估](E:/LX/LX_fund/FondOntology/docs/tbox-runtime-assessment-20261010.md)。
优化全量首次复测 308/308，通过后正常退出；测试阶段 234.006 秒，
清理 5.82 秒。缓存引用保留、重复图复制和重复只读 fixture 已修复，
上文“尚未实施”的表述仅适用于原诊断基线。
最终复跑进一步共享 Web 测试数据栈：308/308，测试阶段 176.167 秒，
清理 3.65 秒，正常退出码 0；日志 `artifacts/benchmarks/full-tests-final-20261010.log`。
冻结裁剪基准三档仍为 44/44，132 份文本与 OA 候选完全一致。

- 真正不可见的 holdout 需由独立维护者建立，external 需领域专家提供；
  本轮合成测试不能取代二者。
- 尚未执行在线 full/current/candidate 三臂 3–5 次独立采样，
  不能沿用历史在线报告作为新版本验收结论。
- 生产 IR 的投影、计算、分组等能力扩展不在本轮修复中；
  本轮只修正已有槽位的依赖提取和表达层接线。
- 后置切片预算控制 `render_text`，结构化 JSON 因 IRI 和字段名存在额外开销；
  不能将该预算直接宣称为整个表达 prompt 的 token 上限。
- 路径搜索保留原有有界搜索策略；记录数量是实际观测候选数，
  当 capped=true 时不是未穷尽路径总数。

## 八项补修

2026-10-10 根据后续审查修复以下遗漏，原“核心修复通过”不代表不存在这些缺陷。

1. required 属性公理闭包新增的端点类纳入约束发现；表达式/类公理引入的类
   持续扫描到固定点，仍先选择 required 约束、后选择 optional。
2. 具名 `owl:Restriction` 支持渲染、嵌套遍历和 AST，不再仅允许 BNode。
3. 解释 JSON 的 classes 显式包含已保留的 `parents`，保留继承链。
4. AST literal 使用 value/datatype/language 结构，不再把 RDF 字面量全部压成字符串。
5. 连接的静默缺失按对应缺失边报告判断，不再用全局 critical_missing 掩盖；
   any 模式的每条备选链都需要对应阻断边报告。
6. 明确标注的 related、related_class、traversals 纳入槽位精确匹配评分。
7. intent-real 的 use_llm=None 先解析配置；模型返回 None 的兜底也记录结构化
   fallback，确定性快路径不计为模型失败回退。
8. BFS 即使 frontier 已空，候选数超 limit 后切片也报告 capped=true；
   恰好等于 limit 且无未搜索 frontier 时不误报。

新增 `tests/test_tbox_remaining_regressions.py` 13 项合成/评测回归，
独立运行 13/13；T-BOX 专项 61/61。冻结题和 gold 未修改。

## P2 复核补修与验收状态

2026-10-10：保留“全部修复完成”验收不通过的状态；上一轮遗漏两项：

- `exclusions` 现在参与整题通过与 Semantic Accuracy 的精确槽位评分。
  新反例覆盖未提供、空排除、排除错对象和同名不同 IRI，不能再给 100%。
- 统一 `is_expression_node`，用于 AST、切片入口、递归采集与渲染，
  支持具名 union/intersection/complement，含无显式 owl:Class 类型的表达式节点。
  嵌套表达式依赖作为完整包保留；required 包超预算时显式报告缺失，
  不能只留下名称并报告 degradation=none。

专项回归扩为 15 项，全部通过；冻结题和原断言未删除或修改。
本轮全量 323/323、失败/错误/跳过均为 0，测试阶段 204.881 秒，
清理 3.25 秒，正常退出码 0；日志 `artifacts/benchmarks/full-tests-p2-20261010.log`。
专项另行使用最新源码独立运行 15/15，覆盖具体排除对象 IRI 不匹配。
本轮三档公开题仍各 44/44、契约 23/23、OA 回归 14/14；
800 字符仍有 13/44 的 critical_missing，不能当作完整语义或端到端验收。
完整请求 JSON/token 预算与独立盲测仍未完成，本轮未声称关闭这两个缺口。

下一阶段按以下顺序推进，须分别记录真实验收结果：

1. 两项 P2 缺陷关闭与独立复核。
2. 完整请求预算：包含 system/user 消息、schema JSON、实例证据和输出预留；
   完整请求预算溢出目标为 0。
3. 任务依赖分级：必需缺失报告覆盖目标为 100%，不得靠整体报警代替逐依赖报告。
4. 独立端到端评测：错误槽位误判通过数目标为 0，比较执行正确率、
   每成功任务 token 与冷/热 P95。
5. 只有独立指标显示收益才引入精排；不照搬 BKN 展示图截断或未接入
   搜索主链路的 pruneProperties 作为成熟语义裁剪能力。
