# 本体语义网实施与运行性能评估

日期：2026-10-10。以当前工作树、OA 文档、冻结离线评测和实际全量测试为依据。

## 实施结论

OA 的生产接线与后置切片修复已实现，并通过本轮回归；
当前适合继续进行独立端到端验收，不能宣称完成任意 OWL 语义保持裁剪。

| 能力 | 当前实施情况 | 验证边界 |
|---|---|---|
| 前置 schema 检索 | 类、字段、domain/range、连接路径成包裁剪，记录检索淘汰、路径限额与预算缺失 | 尚非完整 OWL 表达式视图 |
| 意图入口 | 预算丢失关键依赖时最多扩大一次，仍不足则确定性回退；trace 贯通答案、报告和 API | 不是所有未召回问题都能由预算重试解决 |
| 后置语义切片 | required 依赖优先；递归 OWL 表达式 AST；inverse/subProperty/property-chain 固定点提取 | 公理提取闭包不等于任意 OWL 蕴含等价 |
| 来源与确定性 | 完整 T-BOX 内容 hash，BNode 规范化，跨加载/进程合成回归 | 只覆盖已编写的回归场景 |
| 表达层 | 结构化后置切片接入模型，实例事实仍受 claims 引用闸门约束 | JSON 开销未纳入 render_text 字符预算 |
| 查询与证据 | 全量回归验证现有计划、实例查询、推理来源、Web 和解释流程 | 不等于独立真实问题端到端正确率 |

本轮冻结结果：10000/1800/800 字符预算均为 44/44 严格覆盖；
切片契约 23/23；OA 专项 14/14。
800 字符平均实际文本 571.5 字符，核心精度代理 69.52%。
与 OA 候选版本相比，132 份 render_text 完全一致，冻结 fixture hash 未变。
因此本轮缓存、索引和图复用优化没有造成该基准的语义输出退化。

需要保留的验收缺口：

- 800 字符仍有 13/44 题报告 `critical_missing`；标注依赖覆盖和其他关键包缺失可以同时存在。
- required_dependency_recall=100% 只覆盖 gold 标注依赖；package_closure_rate=100% 只覆盖保留的端点/路径包。
- 公开 holdout 已参与迭代，不能作为独立盲测；专家 external 集尚未建立。
- 尚未完成同模型、同协议 full/current/candidate 三臂的 3–5 次独立在线采样。
- ABOX 定向物化只执行代码支持的规则，不能冒充完整 OWL-RL 实例推理。
- 生产 IR 扩展、真实端到端结果精确性和完整 prompt token 上限仍需单独验收。

## 耗时与退出

已确认并修复的代码问题：

1. 全局 WeakKeyDictionary 的 value 持有 stack，间接强引用自己的弱键，
   导致 stack 和图不能随调用方释放。改为 stack 自身持有 index/context；
   新增弱引用回收测试验证整个对象组可被 GC 回收。
2. 推理物化图已包含 TBOX、ABOX，查询入口原来再次复制这些图。
   现在直接复用完整物化图，保留缓存失效逻辑。
3. 词汇索引原来构造并扫描完整合并图；现在直接读取 TBOX，
   实体索引仍读取 ABOX，并对多类型实体去重。完整查询图按需获取。
4. 同源只读 QA 用例按路径和 reasoner_profile 共享 stack/index，
   Web 用例注入共享 stack；导入/合并测试保留独立 stack。
5. 数据合并使索引、推理图、来源登记和推理计数失效；
   dataclasses.replace 不继承新增加的派生视图缓存。
6. 跑批输出初始化、单例进度、慢点和周期主线程栈；
   结束时释放 fixture/测试类持有的资源并显式回收，Web 客户端显式关闭。

| 指标 | 原诊断基线 | 最终优化全量 |
|---|---:|---:|
| 测试通过 | 302/302 | 308/308 |
| 测试阶段 | 1762.164 秒 | 176.167 秒 |
| SchemaRetrieverTest 初始化 | 446.90 秒 | 0.28 秒 |
| latest 子查询单例 | 308.10 秒 | 小于 0.01 秒 |
| 自然语言 find 单例 | 114.03 秒 | 2.18 秒 |
| 清理 | 数分钟后人工中止 | 3.65 秒 |
| 进程正常退出 | 未取得 | 退出码 0 |

增加的 6 项测试覆盖回收、身份复用、replace、物化图复用、
合并失效及共享/独立实例隔离；标准 unittest 单独运行也正常退出。
测试阶段耗时下降约 90.0%，约为原先的 1/10。
此前 234.006 秒的首次优化全量也已通过；最终复跑进一步复用了 Web 只读栈，
得到 176.167 秒。
单例包含热缓存和执行顺序收益，不应将其解释为独立冷启动提速倍数。
原退出卡住时未捕获调用栈，不能将旧现象唯一归因于 GC；
可以确认引用保留和重复复制已修复，优化全量已实际正常退出。

主要剩余慢点为独立导入/合并后首次查询（最终复跑约 23–25 秒），
期间诊断栈落在物化图复制与 RDFLib 图遍历，而非外部模型调用。
这些用例涉及内存写入，不应为了速度与只读测试共享可变实例。

## 复现与结果

```powershell
.venv\Scripts\python.exe -u tools\run_tests.py --stack-after 90
.venv\Scripts\python.exe -m unittest discover -s tests -p test_runtime_lifecycle.py -v
.venv\Scripts\python.exe tools\tbox_slice_bench.py --output artifacts\benchmarks\tbox-slicing\runtime-candidate-20261010.json
```

- 首次优化全量日志：`artifacts/benchmarks/full-tests-optimized-20261010.log`。
- 最终全量日志：`artifacts/benchmarks/full-tests-final-20261010.log`；
  308/308，清理 3.65 秒，进程正常退出码 0。
- 裁剪结果：`artifacts/benchmarks/tbox-slicing/runtime-candidate-20261010.json`。
- OA 候选对照：`artifacts/benchmarks/tbox-slicing/runtime-20261010/comparison.md`。
