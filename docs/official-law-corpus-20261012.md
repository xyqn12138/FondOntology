# 官方法条 V1：来源、范围、整条检索与独立评分审核

> 2026-10-13 口径纠正：本文保留历史记录。旧题大量提前提供法名、版本，成绩仅支持
> 带法源提示的受限文档检索；不能证明真实自然问题的全库召回。文中的显式 doc/version
> 建议仅适用于用户主动指定范围的请求。普通问题应检索权限与日期允许的全部正文。

## 审批结论

**允许继续作为受限文档检索基线，不批准为法律问答业务验收。**
四份官方原件、226 条完整法条、32 道来源独立编写的外置问题和只读产物审计已接通。
最终 top-3/top-5 均有一题漏召回，评分退出 1；三题 Ragas 仍有超时。
没有新增数据库产品、微服务或自动生成实体事实；TTL 继续作为本体语义真源。

## 1. 数据范围与来源核验

| 固定文档 ID | 来源版本 | 发布主体/载体 | 条数 | 日期完备性 |
| --- | --- | --- | ---: | --- |
| `csrc-operations-2014` | 公开募集证券投资基金运作管理办法，2014 | 证监会官网 | 59 | 发布、施行已登记 |
| `csrc-disclosure-2020` | 公开募集证券投资基金信息披露管理办法，2020 修订文本 | 证监会官网 | 42 | 修订发布日期已登记；修订施行日尚未独立核验 |
| `csrc-sales-2020` | 公开募集证券投资基金销售机构监督管理办法，2020 | 国务院公报刊载证监会令 | 63 | 发布、施行已登记 |
| `state-council-private-funds-2023` | 私募投资基金监督管理条例，2023 | 中国政府网 | 62 | 发布、施行已登记 |

官方 URL、原始 SHA256、正文 DOM selector、标题/日期声明锚点在
`evaluation/corpora/official-laws-v1.sources.json`。四份均保留
`validity_status=not_checked_current`：**官方来源不等于当前仍有效**。
信息披露原办法的 2019 年施行日期不能倒推为 2020 年修订版本的可用起点。

`official_sources.py` 仅允许登记的 HTTPS 官方主机；不接受重定向、凭据、查询参数。
下载受大小/超时约束；必须显式 `--download`。本地缓存必须原件与回执成对、hash 一致，
不会静默覆盖。正文必须唯一，标题/日期锚点存在，条号连续完整。
网页即使只改模板也可能触发原始 SHA 拒绝；应人工复核并创建新来源版本，而不是删校验。

原件保存于被 Git 忽略的 `data/official-laws-v1/`，原始 bytes 同时进入 SQLite。
回执记录实际获取时间、HTTP 状态、TLS 策略与字节数。它们是本地运行记录，
不是签名证明；来源判断不能仅靠任何人都能填写的 URL、hash 或 `verified` 字段。
所有来源均需进入版本登记流程，不能据此自动信任任意 manifest。

`trusted` 在这份快照中只指已固定的官方获取来源和结构校验结果，不认证法律效力。
其覆盖是四份所选版本，而非全部基金法体系；尚未补齐基金法上位法、修订/废止链、
监管问答及基金产品披露。当前题目明确限定入库版本，不回答现行法全集问题。

## 2. 法条切分与模块边界

发布位置 `artifacts/official-laws-v1/corpus.sqlite`；快照 `official-laws-v1`，
索引标识 `legal-body-bm25-v1`，成员 hash：

```text
0d45f5b7aa81b860fe94a85007a750006047572c818457d5c7f4a2b73d50b10e
```

- `corpus/official_sources.py`：获取与来源结构校验，不回答问题。
- `corpus/legal_text.py`、`corpus/store.py`：不可变原件/版本、正文规范化、整条边界和快照。
- `qa/rag/document_scope.py`：先做文档、版本、日期、实体范围约束，再提供可检索正文。
- `qa/rag/document_pipeline.py`：在约束范围内检索和记录真实候选/证据；生成是可选阶段。
- `evaluation/artifact_audit.py`：独立 HTMLParser、只读 SQLite、`query_only`，不调用生产检索。
- `evaluation/legal_retrieval.py`、`ragas_runner.py`：分别承担确定性检索评分和模型诊断。

`official-html-v1` 保留原件、规范化文本和提取回执；`legal-article-v1` 一条一个 chunk。
226/226 条字符长度与 offset 匹配，无标题 metadata 占据检索名额；1 条长 1008 字符，
超过软目标 800 但没有截断，标记 `oversized=true`。800 不是此通道的硬 token 预算。
披露 HTML 尾部 12 个 NUL 被确定性移除并在回执中计数，原始 bytes 未改变。
连续条号与字符恢复通过是结构验证，不等于每句话已由法律人员逐字审校。

范围中的 `None` 与 `[]` 不同；后者禁止检索。未知、歧义、范围冲突不会扩大范围。
直接条号请求使用 locator，分数为 null，不伪造 BM25 分数；多条请求缺一条即 unresolved。
条号范围语法暂不支持，明确返回原因；明确请求超过 top-k 会记录预算排除项。
自然语言范围解析采用有界语法，并非完整中文理解；只有用户主动指定范围时才传显式 doc/version ID。
`article_budget_sufficient` 只检查明确条号请求，不认证自然问题所需证据齐全。

## 3. 与 BKN 对齐，而非复制部署栈

| 本地参考 | 本项目迁移原则 | 仍不宣称的能力 |
| --- | --- | --- |
| `E:/LX/bkn-foundry/rules/ARCHITECTURE.md`，Layers and dependencies | 可选模块、单向依赖；语料/查询/评价分离，关闭模型不妨碍检索 | 未迁移其微服务、公开 API 治理或全部权限能力 |
| `E:/LX/bkn-foundry/bkn-trace/README.md`，What it records | 记录输入、范围、候选、证据、版本、耗时、失败，不从答案反推调用事实 | 当前 JSONL 不是带身份保护和签名的集中 trace 服务 |
| `E:/LX/bkn-foundry/rules/TESTING.md` | 合成单测、快照集成、业务题库、模型诊断分层 | 对方规范也不能当作其已经通过验收的证明 |

没有必要引入 Redis、OpenSearch、Kafka 或另一个关系数据库。要解决的是证据和契约，
不是增加部署依赖。独立 CLI 接通也不表示旧 Web/意图路由已经具备完整文档问答能力。

审计会核对实际行与 trace、题目绑定、成员/原件/规范化 hash、版本身份、整条切片、
范围与候选排名/选择记录的一致性。`verified=true` 的语义是
`local_artifact_consistency_only`：**没有重新运行 BM25、复算范围解析或证明候选全集，
也没有认证执行真实性、官方来源身份、法律效力或答案语义**。这些状态不得合并。

## 4. 外置题库与确定性指标

题库分为 questions、oracle、references、README；冻结时间
`2026-10-12T05:11:06+00:00`，四文件 SHA 在
`evaluation/cases/official_laws_v1_freeze.json`。冻结后未改目标条款或参考答案。
交接消息的 references hash 多写了一个尾字符（65 位），已在 freeze 中记录更正并复算
未修改文件的 64 位 SHA；另外三文件与交接 hash 一致，不掩盖这项登记错误。
作者未看 actual/trace，但属于同一 AI 团队，并复用了生产法条提取器，仍有共同错误风险。
所有 oracle/reference 维持 `draft`；不冒充人类独立审校或认证盲测。

32 题含系统/业务/用户三层，28 道正常题、4 道范围/日期负控，7 道多条文 AND 问题。
按文档家族预划分 dev/test 各 14，challenge 4；28/32 题不提供条号。
问题只传调用输入，目标条文及答案不进入生产链路。已检查过 test 失败后，这套题今后
应称公开回归基线；后续调优需要新的未接触评测集，不能继续称“盲测”。

最终产物为 `artifacts/official-laws-v1/audited.actual.json` 及配套 traces，
评分为 `audited.retrieval.json`；top-5 对照带 `audited-top5` 前缀。

| 固定分组 | 题数 | 检索门禁满足 | 宏平均目标条文 recall | required-group coverage |
| --- | ---: | ---: | ---: | ---: |
| 全量（包括无目标负控） | 32 | 31/32 | 85.94% | 85.94% |
| 预定义正常题 | 28 | 27/28 | 98.21% | 98.21% |
| dev | 14 | 14/14 | 100% | 100% |
| test | 14 | 13/14 | 96.43% | 96.43% |
| challenge | 4 | 4/4 | 0（无目标） | 0（无目标） |

全量 first-target MRR=0.84375；状态匹配 32/32；范围越界 0/32；执行错误 0/32。
这些是检索结果，不是答案正确率。全量分母不删 unresolved/error，空目标负控 recall=0
而非假造为 1；另列预定义正常题与挑战题，避免把两种任务混成一个不透明总分。
评分自动输出 by_category/by_split/by_expected_status；未声明分组也保留，空组率为 null。

### 唯一未通过题：`disclosure-01`

问题同时问年报、季报期限/媒介与年报审计。必要原文是第 16 和第 18 条。
实际排序第 39 条处罚第 1、第 16 条第 2、第 31 条档案第 3、第 18 条第 16。
top-k 从 3 增至 5 仍漏第 18 条；不是数据缺失或 800 字符截断。
候选分数表现与词面检索偏向“财务会计报告/审计”、未覆盖“季报→季度报告”一致；
这是基于 trace 的诊断假设，尚未做消融证明，不能宣称已解决。

已修复另一个真正范围缺陷：带自然前缀的法名被忽略，导致在指定销售文档里代答运作法条。
修复由合成 Alpha/Beta 测试覆盖，不新增题目 ID 或目标条号特判；正文引用与明确请求分开，
无法归类的显式范围法名条号请求拒绝代答。修复中一次“请仅依据”识别回归也被最终复跑发现并修正。

## 5. 三题 Ragas：诊断，而非放行

用户授权复用现有模型，本次仅在进程内映射配置，不保存/显示密钥。
固定选择 `ops-01`、`sales-02`、`disclosure-01`：两道成功检索及已观察到的漏召回。
这是看过检索结果后的有意诊断，不是随机样本，也不覆盖全部四份法条。
selection、子集 questions/references 和独立生成的 actual/trace 位于 artifacts。
不是把 32 行 actual 裁成三行后复用旧 trace；`--max-rows` 只是上限，不是抽样器。

运行前通过只读 trace 审计。裁判 `qwen3.8-flash`，Ragas 0.4.3；每指标 90 秒、
每调用 4096 输出 token、最多 18 调用，实际 16 次。未隐式传递生产 thinking 参数。
约 541 秒，3 题 × 3 指标共 9 项，5 项有效、4 项超时，CLI 退出 1。

| 指标 | 有效覆盖 | 超时 | 汇总均值 |
| --- | ---: | ---: | --- |
| Context precision | 3/3 | 0/3 | 约 1.000 |
| Context recall | 2/3 | 1/3 | null |
| Faithfulness | 0/3 | 3/3 | null |

有效的 recall 分别为 sales-02=1.0、disclosure-01=0.57143；不得去掉 ops-01 超时后
计算一个“全样本 recall”。ContextPrecision 不是相关块数量/总块数量，约 1.0 并不否认
第 18 条缺失，也不是整段生成答案合格。高分与确定性门禁失败必须同时展示。

阶段遥测定位：ops-01、disclosure-01 的 StatementGeneratorOutput 各超时 90 秒；
sales-02 声明拆解约 49.5 秒、得到 24 项声明，NLI 在剩余约 40.5 秒预算处取消。
因此不是简单认定“全是 NLI 慢”或只提高预算；要分别验证短答案生成、裁判结构化输出与
服务商参数兼容性。当前评分对象仍是原样摘录，不是生成式用户答案；不截短 actual 美化评分。

小样本是在范围语法最后收紧前生成，保留其真实代码 hash；三个完整输出行与最终运行逐字一致。
未把旧 Markdown 的三题结果混入，也不声称从旧分数到本轮分数是同比提升。

## 6. 复现

从项目根目录执行。新环境按下面步骤创建；已有快照直接 verify/检索，避免重复发布：

```powershell
.venv/Scripts/python.exe -X utf8 tools/fetch_official_laws.py --download --manifest artifacts/official-laws-v1/import-manifest.jsonl --report artifacts/official-laws-v1/acquisition.json
.venv/Scripts/python.exe tools/corpus_cli.py --db artifacts/official-laws-v1/corpus.sqlite init
$imported = .venv/Scripts/python.exe -X utf8 tools/corpus_cli.py --db artifacts/official-laws-v1/corpus.sqlite import artifacts/official-laws-v1/import-manifest.jsonl | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Import failed' }
.venv/Scripts/python.exe tools/corpus_cli.py --db artifacts/official-laws-v1/corpus.sqlite publish official-laws-v1 $imported.version_ids --kind trusted --index-version legal-body-bm25-v1
.venv/Scripts/python.exe tools/corpus_cli.py --db artifacts/official-laws-v1/corpus.sqlite verify official-laws-v1
.venv/Scripts/python.exe -X utf8 tools/document_rag.py --db artifacts/official-laws-v1/corpus.sqlite --snapshot official-laws-v1 --as-of 2026-10-12 --cases evaluation/cases/official_laws_v1_questions.json --top-k 3 --output artifacts/official-laws-v1/audited.actual.json
.venv/Scripts/python.exe -X utf8 tools/evaluate_legal_retrieval.py --actual artifacts/official-laws-v1/audited.actual.json --corpus-db artifacts/official-laws-v1/corpus.sqlite --questions evaluation/cases/official_laws_v1_questions.json --oracle evaluation/cases/official_laws_v1_oracle.json --output artifacts/official-laws-v1/audited.retrieval.json --verify-trace
```

获取默认是离线校验；已缓存时可去掉 `--download`。原件/产物不提交 Git，干净克隆必须
显式获取或由数据负责人分发原件与回执，网页变化须重新核验，不能自动重锁 hash。
当前最后一条退出 1 是有一项检索失败，不要把它改成 0 以通过 CI。

## 7. 下一轮顺序和门禁

1. **来源适用性 P0**：逐来源补修订/废止/施行证据及审校者；未知有效性继续隔离，
   不把 null withdrawn_date 当作永未废止。补上位法和正式披露时保留文档家族/版本/报告期。
2. **多意图检索 P1**：在新 dev 问题上试一般性缩略词展开、子问题召回与受预算约束的合并，
   与原 BM25 配对对照。记录每次扩展、子查询、候选合并及舍弃原因，不按法规条号硬补。
   同时报告 AND 组完整率、噪声、首目标 MRR、证据字符/token、延迟，禁止只提高 top-k。
3. **题库独立性 P1**：领域人员复核现有 draft；新增不同措辞、版本/范围矛盾和跨文档题，
   文档家族分组冻结，再由另一审校者建新盲集。不能从 actual 反推 gold。
4. **裁判与用户答案 P1/P2**：先保留 90 秒失败作为基线，分开量化声明生成/NLI；若更换裁判
   或参数，新建 run ID 和配置，不能拼接不同裁判的成功行。用户生成答案需独立输出/时长预算。
5. **最后再比较本体裁剪**：在同一真实 corpus、独立题库和预算下比较 full/current/candidate；
   图查询、文档检索、生成错误分别归因，不拿旧 13/44 critical_missing 与本轮 recall 合并。

放行建议：来源/适用时点有明确审校，范围负控全通过，必要条文 AND 组不遗漏，产物审计通过，
生成引用语义经独立验证；Ragas 每指标固定分母且有效覆盖足够。阈值应由业务方认可，
不能把本轮小样本成绩反过来当标准。当前不满足完整业务放行条件。

## 8. 验证记录

来源/HTML/文档/审计等 focused tests 55/55 通过；范围及 pipeline 30/30 通过；
新增分组评分审计 tests 16/16 通过；隔离 Ragas 环境 15/15 通过（纯测试，不追加模型调用）。
最终全量回归 530 项：528 通过、2 项可选依赖 skip、零失败/错误，耗时约 259 秒；
日志保存在 `artifacts/official-laws-v1/full-regression-final.log`，未将 skip 算作通过。
这些是代码测试次数，不是新增的独立业务题数。`git diff --check` 未发现空白错误。
