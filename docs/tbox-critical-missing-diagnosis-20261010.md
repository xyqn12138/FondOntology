# 800 字符档 critical_missing 根因定位

> **复测更新（2026-10-10）**：当前 `tools/tbox_slice_bench.py` 重跑 44 题在 800
> 字符档的 `strict_coverage=44/44`、`required_dependency_recall=1.0`、
> `package_closure_rate=1.0`、`silent_missing_rate=0`。因此旧的 13/44
> `critical_missing` 仍只能作为候选预算告警，不能当作必需语义缺失率；后续比较应
> 以 required/support/optional 分层指标为主。

本机复核日期：2026-10-10。对象：当前未提交工作树。只执行诊断、离线基准及内存消融，未修改生产实现或冻结 gold，未调用在线模型。

## 1. 结论

**13/44 表示 13 道题有召回候选包被 800 字符预算拒绝，不等于 13 道题丢失任务必需依赖。**

它来自前置 SchemaRetriever，不是后置 context.py 的 OWL/QueryPlan 切片。上一轮对后置表达式和 exclusions 的修复不会自动改变这个数字。本轮 remaining 回归 15/15，包括上述两项的新回归；本轮没有重跑完整测试集。

最新基准仍为三档 44/44。800 档 13 道告警题中，共有 31 个 critical 项；这些名称确实没有保留，不是本次发生了历史标记未清理。其中 30 项不在当前 gold 指定的类/字段/连接集合中，另 1 项 ratingForInvestor 属于备选连接，其另一合法连接 hasInvestorRiskRating 已保留。

这证明当前告警与评测采用不同口径，不证明 31 项全是无用噪声。部分可能是解释支持或尚未标注的业务依赖，需要任务合同/执行证据判断，不能因不在 gold 就直接删除。

## 2. 根因链

### 2.1 所有候选都被当成 critical

- E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:629 遍历全部 property_scores；接受失败即追加 critical，未区分显式字段、弱片段、定义命中、提示扩展。
- E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:650 对全部 class_scores 做同样处理。
- E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:287 将列表非空直接映射为 critical_missing。

因此分数 0.56 的弱匹配，与明确请求的字段，都具有“装不下则关键缺失”的身份。排序分数不是必要性证明。

### 2.2 弱数据属性通过自身 domain 扩大 scope

E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:476：

    if score >= 0.90 or self.ctx.properties[name].kind == "datatype":
        strong_domains.update(self.ctx.properties[name].domains)

任何已召回数据属性，无论分数多低，都把自身 domain 加入 strong_domains；随后按 scope 与 domain 交集过滤，这类字段自然能够通过自己扩大出来的作用域。作用域过滤因而不能有效约束这些弱属性。

随后 :492 的通用名称/代码/数量扩展、:499 的日期扩展，又在已经扩大的作用域中增加候选。比如报告问题引入投资资产代码，业绩期间问题同时加入基金成立日、终止日和备案日。

### 2.3 候选来源在进入选择器前被丢掉

E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:418 将候选的 source 丢弃，只保留 name→score。被淘汰的候选有来源记录，但被选中并参与预算竞争的候选缺少统一的来源、命中片段、需求角色信息。

因此预算阶段无法可靠区分“用户明确请求”“域内补全”“标签片段相似”“背景补充”。

### 2.4 多个候选包及路径竞争有限预算

路径为属性补充端点和祖先是正确方向，但对大量辅助候选也生成路径会放大包体积。13 道题进入渲染时有 1–12 条路径，其中多题达到 12 条；最终只能保留其中一部分。

E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:633 的 related 同时接受“包含该属性”及“终点落在其 domain”的路径，之后按长度等选择；它没有在此处显式保留原始源锚点与连接目的。后续应以任务连接目的选择路径包，不能仅靠终点相同就判断必须绑定。

这些因素共同造成：弱候选增多 → 域和路径扩张 → 800 字符装不下 → 所有被拒种子都被称为 critical。

## 3. 13 道题逐项

| 题号 | 被标为 critical 的项目 | 定位 |
|---|---|---|
| D08 | hasFundClassifier | 泛化分类支撑；风险字段已保留 |
| D20 | FundSemiAnnualReport | 年度报告问题召回中期报告，label_fragment 0.82 |
| D23 | trackingError、investmentFocus | 指数代码问题混入跟踪误差和投资重点 |
| D24 | hasDistributionMethod、distributionWithReinvestment、unitQuantity、FundDistributionMethod | 分红/收费问题混入数量字段及其他分红建模分支 |
| D25 | hasFundRoleAssignment、assignmentPlayedBy | 任职关系支持项；生效/失效字段已保留，需按任务连接目的判断是否必要 |
| D26 | riskLevelCode | 风险字段候选分支；gold 的风险关系与成立日期已保留，不能仅据 gold 断言它永远不需要 |
| H04 | feeName、hasFundFeeMode、unitQuantity | 金额和费率之外的费用名称、方式和份额数量 |
| H05 | investmentAssetTypeCode | 季报问题混入投资资产类型代码，片段命中后被通用代码规则提升 |
| H06 | hasFundRiskLevel、investorRiskRatingForFund、ratingForInvestor | 基金风险与投资者评级混杂；ratingForInvestor 的合法备选连接已保留 |
| H08 | sectionHasContent | 法规正文问题混入报告章节正文，label_fragment 0.79 |
| H10 | positionQuantity、indexCurrency | 份额数量/币种问题混入持仓数量与指数币种；unitQuantity/unitCurrency 已保留 |
| H12 | portfolioOfFund、investmentAssetTypeCode、fundNetAssetValue、positionAsOfDate、positionCurrency、positionMarketValue | 持仓资产/数量之外的广泛投资组合背景 |
| H13 | terminationDate、annualizedReturn、excessReturn、maximumDrawdown | 累计收益/期间问题混入基金终止日及其他业绩指标 |

全部 13 题的 missing_reason 是 budget_dropped；告警题实际文本 758–799 字符，未突破预算。当前 gold 类、属性与连接要求均满足。

## 4. 实测消融：不要用降告警代替正确性

### 4.1 只增加容量

| 字符上限 | critical 题数 | strict coverage | 全部 44 题平均字符 |
|---:|---:|---:|---:|
| 800 | 13 | 44/44 | 571.50 |
| 1000 | 7 | 44/44 | 648.52 |
| 1200 | 3 | 44/44 | 697.14 |
| 1400 | 1 | 44/44 | 728.18 |
| 1600 | 0 | 44/44 | 757.39 |
| 1800 | 0 | 44/44 | 774.27 |

1600 消除全部告警只说明容量能装下当前候选，不证明召回更精准或回答更正确。可以作为临时容量选择，不能作为根因修复。

### 4.2 只提高 scope 门槛也不安全

仅在进程内将 :478 改为 score >= 0.90，取消“任意 datatype 都扩大域”：

- 告警从 13 降到 7；
- strict coverage 从 44/44 下降为 41/44；
- D11 丢 valuationDate；
- H06 丢 investorRiskRatingCode；
- H09 丢 terminationDate。

所以不能直接去掉所有低分属性、统一提高阈值或将它们全部视为无关。正确的通用解法应允许“有明确业务域/字段角色支持的弱词法命中”成为必要候选。

## 5. 建议修复方案

### 第一阶段：建立必要性和来源合同

候选改为结构化对象，至少保留：

    name, kind, score, evidence_source, matched_span,
    anchor_classes, role, required_by, alternative_group

role 区分：

- required：问题明确要求的目标、字段、条件，以及完成这些要求的必要连接。
- support：支持理解的定义、同类指标、额外语义关联。
- optional：弱关联背景和邻域。

前置尚无 QueryPlan，required 应从问题锚点和受支持槽位解析产生；不确定时保留歧义/不确定状态，不虚构必需性。后置才使用已经验证的 QueryPlan 依赖。gold 只用于评测，禁止接入生产选择逻辑。

保留 candidate_budget_dropped 作为旧口径的可观测指标；新增 required_missing/support_dropped/optional_dropped。只有真正未满足的 required 包触发扩容或回退。不是只重命名字段或关掉报警。

### 第二阶段：收紧域扩张，按连接目的打包

1. 锚点域由明确类/实体类型、明确字段与已确认槽位产生，不能由每个弱属性的自身 domain 自我背书。
2. 弱字段先看与锚点域的适配，以及用户请求的字段角色；日期、代码、数量等通用词优先落到目标业务对象，不能全域扩展。
3. 对必要需求建立最小合法路径包，保留 source、target、purpose、direction。先给所有必要包分配预算，再用剩余空间装 support/optional。
4. 同一需求存在多个语义上有效的实现时建立备选组；满足一组即可，不要求同时保留每条反向/替代边。替代关系必须来自合同或已声明语义，不能仅凭名称猜测。
5. 以最终包满足情况计算缺失状态，不能仅看一次贪心接受是否失败，也不能仅看属性名字后来出现。

这与 BKN“相关性选择之后保护所选关系端点”的方向一致；不等于把全部粗召回候选都升级为必需。当前不应先扩大 Top-K 或引入远程 reranker。

### 第三阶段：补评测和发布门槛

- 保持冻结 44 题 gold 不变，800 档 strict coverage 不退化；该集合仍只是回归集，不冒充盲测。
- 加入通用同名字段干扰、相邻类别、日期/代码歧义、备选连接、真实不足预算等合成测试；加入独立维护的盲测。
- 人工标注必要包及合法替代关系，分别统计告警 precision/recall；不把“gold 没写”自动算误报。
- 真实必需包放不下时必须告警；可选字段被裁不能单独触发 required_missing。
- 同时报告 candidate_drop_rate、required_dependency_recall、false_alarm_rate、silent_missing_rate、expansion_rate、fallback_rate、每成功任务 token 和执行结果正确率。
- 修复前后使用同预算、同模型、同协议比较，明确误报下降不能以漏报和执行正确率下降为代价。

## 6. 两个容易误读的指标

E:/LX/LX_fund/FondOntology/tools/tbox_slice_bench.py:53 仅调用 retrieve，:135 直接复制 critical_missing；:117 的 strict_coverage 另按 gold 判定。因此当前不是评测器凭空算出了 13 个错误，而是生产标志的语义过宽。

E:/LX/LX_fund/FondOntology/fondontology/qa/schema_retriever.py:297 将正常选路 rejected 也归入 path_search_capped。13 题该字段都为 true，不能据此断言它们都因为 BFS 未穷尽而丢失关键连接。建议拆开 search_exhausted/search_capped、selection_rejected、budget_dropped。

线上 E:/LX/LX_fund/FondOntology/fondontology/qa/intent.py:1138 默认使用 10000 字符、6000 token，而不是本实验的 800 字符。因此 13/44 不能直接称为线上回退率；但 :1142/:1166 的扩容/回退依赖此标志，必要性分级仍应修正。

## 7. 本次证据

- E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/recheck-20261010.json：当前工作树新跑的三档离线报告及 hash。
- E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/critical-diagnosis-20261010.json：44 题完整 SchemaContext；13 题额外含渲染输入分数、候选路径、丢弃项及相关代码 hash。
- E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/critical-ablation-20261010.json：预算扫描与只读内存消融，记录失败题而非仅报告告警下降。

最终目标不是把 critical_missing 数字机械归零，而是让它准确回答：“当前请求必需的语义包是否真的不完整？”
