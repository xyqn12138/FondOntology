# 候选必要性合同第一阶段

日期：2026-10-10。参考 `docs/tbox-critical-missing-diagnosis-20261010.md`。
本轮是第一阶段实施，不是审批全部关闭；冻结 gold 不参与生产逻辑。

## 已实施

- `SchemaCandidate` 保留 name/kind/score/evidence_source/matched_span、
  anchor_classes/role/required_by/alternative_group/uncertain。
- 显式标签、类型同义词、实体类型和锚点支持的字段角色生成需求合同；
  弱片段与推断补充维持 support/optional 或 uncertain，评分不是必要性证明。
- 预算先保护必需类和字段包；显式源对象访问字段的选路记录
  source/target/purpose 和 alternatives，不再仅用终点相同绑定。
- 最终必需满足检查读取保留类、端点、边及具体方向路径；
  属性名字后来出现不能替代完整路径。
- `critical_missing` 对应 `required_missing`；
  `candidate_budget_dropped` 保留旧种子包接受失败诊断，
  support_dropped/optional_dropped 分开输出，不因辅助项独立触发回退。
- BFS search cap、正常 selection_rejected、全局路径 selection cap 分开。
- 生产 intent trace 和离线结果接通这些字段。

## 口径与限制

旧 `dropped_items.critical` 暂留作兼容诊断，只表示种子包在贪心阶段曾被拒；
不再直接决定 critical_missing。最终 required_missing 是需求满足状态。
这些字段不是只读同一个布尔值的别名，预算选择顺序和路径检查也发生了变化。

SchemaCandidate 是首版合同，不是真实问题语义解析的完备证明：
锚点选择、弱字段必要性、替代路径合法性还需要业务合同与执行 gold 支撑。
路径 alternatives 当前仅来自已有搜索选择结果，未宣称建立任意语义等价组。
搜索完全未召回的路径尚未形成可靠 not_found/ambiguous 需求项，这是待补缺口；
不能从 required_missing 为空推断没有未召回的必要连接。
当字段在显式对象的 domain 已可用，不强制对其他召回类建立访问路径。

本轮没有直接取消“任意 datatype 扩大 strong_domains”的历史逻辑：
审批已证明简单改门槛会丢失日期和风险字段。
安全替换需独立角色/歧义规则、覆盖该消融的反例后再实施。
完整请求预算、独立盲测、告警 precision/recall 和端到端执行评测均未完成。
未标注必要包就不能计算可信 false_alarm_rate；不从公开 gold 缺项自动推导误报。

## 验证

新增 `tests/test_schema_candidate_contract.py`：
来源片段、支持项裁剪、不足预算、路径名字不足、正常选路非搜索限额。
5/5 通过，原测试断言未删改。

最新离线同预算复测三档均 44/44，契约 23/23。
800 档旧口径 candidate 告警 13/44，首版合同 required 告警 0/44；
平均字符约 572.1，核心精度代理约 69.57%。
这个 0 只适用于已建模需求和公开回归集，不能宣称完整必需依赖召回率 100%。

最终源码结果：`artifacts/benchmarks/tbox-slicing/candidate-contract-release-20261010.json`。
补验前源码全量 328/328，294.35 秒，清理 3.81 秒，退出码 0：
`artifacts/benchmarks/full-tests-candidate-contract-20261010.log`。
之后收紧了锚点匹配与路径源端检查；最终源码 schema 相关 16/16、
离线契约 23/23 与 OA 14/14 通过，未重复执行最终源码全量。

## 后续

1. 独立复核首版必要性合同，补弱字段域适配、日期/代码歧义与需求包盲测。
2. 安全替换弱字段自我扩域；按连接目的建立完整最小包与合法备选组。
3. 真实包缺失标注后测告警 precision/recall、silent_missing 和误判通过数。
4. 实施完整请求预算，再测执行精确性、每成功任务 token、冷/热 P95。
5. 以上有收益后再评估精排，不照搬 BKN 展示图截断或未接入主链路的剪枝。
