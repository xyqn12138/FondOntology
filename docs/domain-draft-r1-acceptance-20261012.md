# R1 草稿语义验收（2026-10-12）

## 结论与性质

**通过四项 P1 修订及随后顶层元数据兼容调整的 AI 语义验收，可以继续生成修订台账和新 freeze。** 本次检查的两套 R1 内容文件未发现范围、目标条文、AND 组或判定状态漂移，其余 46 题的 questions、oracle、references 逐题整行与原版相同。本通过结论以文末“结构兼容调整后的最终验收”列出的八个文件 SHA-256 为准；前面的初次哈希保留作历史记录。后续任何内容变动需要另行复核。

审核角色沿用任务指定的 **GPT-6 Astra / high**。这是同一 AI 协作过程中的领域文本复核，**非独立人工认证**，不表示审核者具有人类法律专业资格。全部 oracle authorship、reference 和修订元数据仍为 **draft**；`independent_human_review=false`；`exposed_regression=true`。本版本是**已曝光回归集**，既有 holdout/test 名称仅保留谱系或数据分组意义，修订并未恢复盲测资格。

**未做现行法效力核验。** 本次没有作外网法律检索，仅复核固定官方 HTML 对应版本及原题的四项勘误，不认证 2026-10-12 的现行法规适用、其他修订或配套规则。初审报告中的 P2 建议及人工审核要求仍保留，不能把本验收读作 50 题全部获正式领域认证。

## 只读边界与核验方法

本轮只读取了两套 R1 questions/oracle/references 和 README、相应原版 questions/oracle/references/freeze，以及四项问题关联的固定官方 HTML。没有读取实际答案、检索实现、评分、消融报告、父代理迭代报告或其他被测系统输出；未运行被测系统。法条核对通过读取固定 HTML、去除标签并定位条号完成，没有借助检索实现。

定位规则：Q 为对应 questions 的 `cases[id=题号]`，O 为 oracle 的 `rows[id=题号]`，R 为 references 的 `rows[id=题号]`。法条路径如下：

- 私募：`data/official-laws-v1/state-council-private-funds-2023.html`。
- 销售：`data/official-laws-v1/csrc-sales-2020.html`。
- 信披：`data/official-laws-v1/csrc-disclosure-2020.html`。

结构与字节检查结果：

- V1 保持 32 个、V2 保持 18 个相同且同序题 ID。
- 每题除 question 文本外的输入字段均相同，包含 as_of、doc_ids、version_ids 的存在状态和值。
- 每题除 source_notes 外的 oracle 行字段均相同，包含 expected_status、target_articles、required_groups、allowed_doc_ids、category、scenario 和 split。
- 四个指定 P1 之外，46 题的 Q/O/R 整行完全相同；没有借此次勘误悄改 P2 或扩大业务范围。
- 所有 reference 的 review_status 均为 draft；两个 oracle 的 authorship 保持 draft。
- 两份原 freeze 中登记的八个原版内容文件 SHA-256 全部匹配，原冻结内容未被本轮修订覆盖。
- 验收读取时 `official_laws_revision_r1.json` 和两份 R1 freeze 尚未存在。因此本报告不宣称台账字段、freeze 哈希和生成顺序已通过核验；这些是后续制作和完整性检查的事项。

## 四项 P1 的逐题语义验收

| 题 ID | 结果 | 修订与固定原文证据 | 目标及范围结论 |
| --- | --- | --- | --- |
| private-07 | 通过 | Q 改为“某责任主体”及其可用于承担相应责任的财产；R 明确“同一责任主体”，不推断基金独立财产承担管理人罚款。私募第60条为责任竞合时民事赔偿优先；第4条明确基金财产独立于管理人、托管人固有财产。原先的主体混淆已消除。 | 第60条仍为唯一目标且足以回答重写后的优先顺序问题；第4条只作审核背景，未悄加新 gold。Q/O/R改动均属于此 P1。 |
| holdout-sales-02 | 通过 | Q 明确连续开展基金销售业务满三个完整会计年度、最近一个会计年度保有量、取得基金从业资格人员；R/O同样精确。销售第37条第1款第1项及第5项提供相应业务期间、100亿元和5人的条件。 | 仍只判断已给三项，不认定全部分支设立条件满足；跨省限制及证监会例外保留；唯一目标第37条未变。 |
| holdout-disclosure-04 | 通过 | Q 未变；R完整保留第23条“误导性影响或者引起较大波动，以及可能损害…”的条件连接词，明确不另行假设较大波动；O说明条内“或者”不同于跨条证据AND。第22条大会披露内容未变。 | 第22条和第23条仍分设AND组；没有为答案增加题设事实，也没有把同一条文内部OR变成证据AND。 |
| holdout-challenge-02 | 通过 | Q删除2020-09-30时点的“已废止旧版本”定性，改禁用其他版本或文件；R/O明确第63条为2020-10-01新办法施行且旧办法同时废止。 | as_of及指定文档范围不变；unresolved、空目标和空组保留。拒绝回退属于用户范围限定，不再依赖错误的历史效力前提。 |

上述修订没有要求系统在没有材料支持时解释具体罚款主体、补充分支机构其他条件、断言传闻实际造成较大波动或以当时旧法代答，未引入新的事实义务。

## 其余 46 题逐题验收

本表“通过不变核对”指 Q/O/R 完整行与原题一致，继承初审的 draft 接受及 P2 保留意见；不是第二次全面适用法认证。

| 题 ID | 验收结果 | 范围／目标漂移 |
| --- | --- | --- |
| ops-01 | 通过不变核对 | 无 |
| ops-02 | 通过不变核对 | 无 |
| ops-03 | 通过不变核对，开放日措辞P2保留 | 无 |
| ops-04 | 通过不变核对 | 无 |
| ops-05 | 通过不变核对，引导性P2保留 | 无 |
| ops-06 | 通过不变核对 | 无 |
| ops-07 | 通过不变核对 | 无 |
| sales-01 | 通过不变核对 | 无 |
| sales-02 | 通过不变核对 | 无 |
| sales-03 | 通过不变核对 | 无 |
| sales-04 | 通过不变核对 | 无 |
| sales-05 | 通过不变核对，续期措辞P2保留 | 无 |
| sales-06 | 通过不变核对 | 无 |
| sales-07 | 通过不变核对 | 无 |
| disclosure-01 | 通过不变核对 | 无 |
| disclosure-02 | 通过不变核对 | 无 |
| disclosure-03 | 通过不变核对，款项定位P2保留 | 无 |
| disclosure-04 | 通过不变核对 | 无 |
| disclosure-05 | 通过不变核对 | 无 |
| disclosure-06 | 通过不变核对，公开媒介事实P2保留 | 无 |
| disclosure-07 | 通过不变核对 | 无 |
| private-01 | 通过不变核对 | 无 |
| private-02 | 通过不变核对，降低标准事实P2保留 | 无 |
| private-03 | 通过不变核对 | 无 |
| private-04 | 通过不变核对 | 无 |
| private-05 | 通过不变核对 | 无 |
| private-06 | 通过不变核对，依法调查前提P2保留 | 无 |
| challenge-01 | 通过不变核对 | 无 |
| challenge-02 | 通过不变核对 | 无 |
| challenge-03 | 通过不变核对 | 无 |
| challenge-04 | 通过不变核对 | 无 |
| holdout-ops-01 | 通过不变核对 | 无 |
| holdout-ops-02 | 通过不变核对 | 无 |
| holdout-ops-03 | 通过不变核对 | 无 |
| holdout-ops-04 | 通过不变核对 | 无 |
| holdout-sales-01 | 通过不变核对 | 无 |
| holdout-sales-03 | 通过不变核对 | 无 |
| holdout-sales-04 | 通过不变核对 | 无 |
| holdout-disclosure-01 | 通过不变核对 | 无 |
| holdout-disclosure-02 | 通过不变核对 | 无 |
| holdout-disclosure-03 | 通过不变核对 | 无 |
| holdout-private-01 | 通过不变核对 | 无 |
| holdout-private-02 | 通过不变核对 | 无 |
| holdout-private-03 | 通过不变核对 | 无 |
| holdout-private-04 | 通过不变核对 | 无 |
| holdout-challenge-01 | 通过不变核对 | 无 |

## README、元数据及冻结交接

两份 R1 README 均在开头明确为已曝光回归修订、仍 draft、非独立人工审核，说明原文档后续章节只是历史上下文。保留父版本盲测协议不会把 R1 重新标为未曝光测试；R1 新增 revision 元数据与该限制一致。四项修订原因与实际字段差异一致。README 中关于作者未读实际输出的陈述按作者声明记录，本验收没有通过读取实际输出验证该历史事实。

以下为初次通过语义验收的历史字节版本，路径均相对于 `evaluation/cases/`。随后四份 oracle/reference 移除顶层 revision 元数据，最终 freeze 应使用文末最终哈希表；此表仅保留初次复核历史。

| 文件 | SHA-256 |
| --- | --- |
| official_laws_v1_r1_questions.json | `09a9f74979b897dcf01a1fa88e30fc9ec30c7f9a7f0d370d8f03b2f145ae2a7b` |
| official_laws_v1_r1_oracle.json | `8ad055fefac1cfc6bdc3cff50fdbaed07bee8c17c2ae9fa4dfefc37ceeb9b720` |
| official_laws_v1_r1_references.json | `ffdd6d9f1f73b24b863078606eba05edd61d2348cd5c45ebe4f1c65cc3de828d` |
| official_laws_v1_r1_README.md | `9355b4c78f7a2fc4f0b9f132886a5d0f132b3f09166ef9ad06e62c8d05d7fbac` |
| retrieval_holdout_v2_r1_questions.json | `88c41cb10e39ad9104107ec5fd1c2a78d4a29b045c339950d45bf4ffa4714665` |
| retrieval_holdout_v2_r1_oracle.json | `067270408fea8988ce64c0faacc27c7b4f5a4287ffd3465ba9bf983adf33ed05` |
| retrieval_holdout_v2_r1_references.json | `e0b3b80be233bace00d4c1f8263166cea37e3d3d2cdcda322f348b71964dbfe9` |
| retrieval_holdout_v2_r1_README.md | `79334aea3966b5d8043ba5fefa4540318232a77bd51f2276552ac5eb63c05fc6` |

本轮仅写入本验收报告，完成后停止写入。后续回归结果不得回写此语义验收或反向改变已通过的法律标准答案。

## 结构兼容调整后的最终验收

初次验收后，父代理告知原有严格输入契约不接受 oracle/reference 顶层 `revision`。按追加任务，本复核只读检查了两套当前内容文件，不读取契约实现、实际输出、评分或父代理报告，也未提前读取仍在同步中的 ledger。父代理提供的兼容性原因作为任务背景记录，本复核不声称独立执行过加载器测试。

**最终内容验收通过。** 相对初次读取记录，四份 oracle/reference 移除顶层 `revision`；它们现在的顶层字段及非行元数据与各自父版本完全相同。逐一复核全部现有业务行：四项 P1 的 question、source_notes 和 reference 仍与初次验收显示的修订文字一致，其余46题Q/O/R整行仍与父版本相同，初次通过的目标、分组、日期、范围、状态及分组分类均未发生新改动。两份 questions 和两份 README 的字节 SHA 也与初次验收完全一致。

本次验证的是解析后字段与已读取的业务文字一致，并重新计算最终文件 SHA；不把文本重序列化后的字节相同当作未检验的事实。移除顶层块不撤销 README 中 draft、非独立人工审核、已曝光回归的限制。修订声明可由 README 和外置台账、freeze 承载；本报告只确认当前 README 已保留这些声明，**尚未验收外置 ledger/freeze**。

最终采用的八个内容 SHA-256 如下。实现者可以对这些精确版本生成 freeze；不得再使用上节四份已被替代的 oracle/reference 初次哈希。

| 最终文件（evaluation/cases/ 下） | 最终 SHA-256 |
| --- | --- |
| official_laws_v1_r1_questions.json | `09a9f74979b897dcf01a1fa88e30fc9ec30c7f9a7f0d370d8f03b2f145ae2a7b` |
| official_laws_v1_r1_oracle.json | `667e39b534bb4f0dd761a71acd7d1ad8d49b99138686c82106bc278ea0fe09a8` |
| official_laws_v1_r1_references.json | `89da556446c0dce4732b1d0222ae139d2d294bdfd93c0fc3b643e258eaf57b94` |
| official_laws_v1_r1_README.md | `9355b4c78f7a2fc4f0b9f132886a5d0f132b3f09166ef9ad06e62c8d05d7fbac` |
| retrieval_holdout_v2_r1_questions.json | `88c41cb10e39ad9104107ec5fd1c2a78d4a29b045c339950d45bf4ffa4714665` |
| retrieval_holdout_v2_r1_oracle.json | `a8d38d3c41bb928ec72c45b10f5d5347b9033ee15cd2a18ebece7809e75adade` |
| retrieval_holdout_v2_r1_references.json | `32e6f1bb9b2b18ae1384d5f59638467f23328410c07f88c198a8fb353b55df0d` |
| retrieval_holdout_v2_r1_README.md | `79334aea3966b5d8043ba5fefa4540318232a77bd51f2276552ac5eb63c05fc6` |

本追加复核仅更新本报告，未改题库、台账或冻结文件。仍为 AI 复核、draft、已曝光回归，非独立人工认证、未做现行法效力核验。完成追加后停止写入。
