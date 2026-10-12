# RAG 检索消融与 DeepSeek 裁判复测（2026-10-12）

## 1. 审核结论

**保留 BM25 默认；批准 BM25 top-20 + rerank 作为显式可选实验方案，不批准全局替换或业务验收。**

没有一次性堆叠 HyDE、rewrite、向量、重排、父子切分。固定同一份 226 条官方法条快照、
同一 top-3 输出预算，对四种独立策略做消融。重排修复旧集唯一漏召回，但新留出集与
BM25 均为 18/18，尚不能证明普遍增益。新增网络延迟、供应商依赖是真实成本。

Ragas 裁判已显式切换为 `deepseek-v4.1-flash`，只复用现有凭证，不改变生产问答模型、
不写回 `.env`。关闭裁判 thinking 后两组各三题的九项评分全部有效，失败旧记录保留。

## 2. 预先约定的实验边界

- 计划：`evaluation/experiments/legal_retrieval_v2.json`；旧 32 题仅作已曝光回归/选择集。
- 快照：`official-laws-v1`；原件、整条正文及来源登记不变，当前法律效力仍未核验。
- 输出：完整父法条 top-3；模型候选预算 20；不裁短证据或偷偷加大 top-k。
- `bm25`：原整条词面检索，兼容原完整候选 trace。
- `parent_child`：按句界尽量切到 240 字符，不足句界时硬切；子块 BM25、父块去重，返回整条。
- `hybrid_rrf`：整条 BM25 与 dense 各取 20，等权 RRF，常数 60。不是父子+向量+重排组合。
- `bm25_rerank`：只重排 BM25 前 20 条；`qwen3.7-text-rerank`，不新增生成式查询。
- dense 使用已有 `qwen3.7-text-embedding-flash`。模型名是配置/服务响应记录，不保证永久不可变版本。

候选选择记录 `legal_retrieval_v2_selection.json` 于 **07:25:52 UTC** 写入，早于新留出集执行与查看。
选择依据是第一组冻结实现的 32 题结果；之后只加固 HTTP/响应校验记录与配对检查，
不改排名算法、题目或参数，再在统一代码身份下重跑。探索结果不覆盖，最终以
`artifacts/retrieval-v2/final-audited/` 为准。

留出集由另一子代理仅读原件编写并于 **07:05:04 UTC** 冻结：16 普通题、2 负控，
9 个多条文 AND 要求，25 个普通目标条文均未出现在旧集。题库/参考答案仍是同一 AI 团队的
source-authored draft，不是独立人工审校；本次曝光后不得继续称为未见盲集。

## 3. 四策略实测

全部采用同一代码、文档/日期范围、top-3；普通题分母 28，全量分母 32。

| 策略 | 全量检索门禁 | 普通题目标召回 | 普通题首目标 MRR | 平均证据字符/普通题 | 普通题 p50 / p95 ms | HTTP 次数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 31/32 | 98.21% | 96.43% | 632.0 | 0.37 / 0.60 | 0 |
| 父子 BM25 | 30/32 | 96.43% | 96.43% | 646.0 | 4.14 / 5.19 | 0 |
| dense + BM25 RRF | 31/32 | 98.21% | 98.21% | 531.3 | 见缓存分层 | 39 |
| BM25 + rerank | **32/32** | **100%** | **100%** | 626.5 | 288.99 / 466.72 | 28 |

四策略范围越界与执行错误均为 0；四个预期拒答负控均通过，不从分母剔除。
全量宏平均 recall 分别为 0.859375、0.84375、0.859375、0.875；无目标负控记 0，
所以它与普通题 recall 不同。AND 组覆盖与本轮 recall 同值；完整题通过数另列，不能混淆。
普通题 target-only precision 分别约 40.48%、39.29%、40.48%、41.67%，它只把 gold 目标算正例，
不代表其他法条一定无关，不能冒充人工完整相关性标注。

RRF 使用新空缓存，顺序运行中 4 题冷缓存、24 题混合缓存、4 题范围旁路：
冷缓存 p50/p95 为 1647.63/1840.95 ms；混合缓存为 313.73/835.13 ms。
混合指文档向量命中而新查询向量未命中，不是全暖查询。没有把这组总延迟称为纯冷启动或暖缓存性能。
所有延迟来自单次本机 trace，包含查询侧工作，不含 CLI 加载语料/初建索引，亦非并发吞吐基准。

### 原漏召回的定位与修复

`disclosure-01` 同时需要信息披露第 16、18 条。BM25 top-3 为 **39、16、31**；
第 18 条原本已经在 top-20 候选里，缺的不是语料，也不是数据库或 800 字符预算。
重排后 top-3 为 **16、18、39**，因此本轮是排序修复，而非新召回渠道的收益。
RRF 为 **16、39、40**，仍缺 18。父子 BM25 除此之外使 `private-01` 从
**27、53、17** 变成 **27、53、22**，丢失必要第 17 条。

因此本轮不采纳父子切分或 RRF 作默认。该结论只针对当前法条/参数；语料本身已经按完整法条
切分，不能由此推断长篇披露、招募说明书的章节父子结构无效。

## 4. 锁定候选后的留出验证

| 策略 | 全量门禁 | 普通题召回/组覆盖 | 负控 | 平均证据字符/普通题 | 普通题 p50 / p95 ms | HTTP 次数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 18/18 | 100% / 100% | 2/2 | 528.0 | 0.45 / 1.05 | 0 |
| BM25 + rerank | 18/18 | 100% / 100% | 2/2 | 552.3 | 272.10 / 443.55 | 16 |

没有调参后重跑留出集，没有改 gold。**未观察到留出集检索增益**，而重排证据长度略增、延迟明显增加。
32/32 不能包装成线上准确率；18/18 的小样本天花板也不能证明检索已解决。
当前更合理的是保留两种显式模式，扩大独立业务题覆盖后再决定默认，而不是按题号手工路由。

## 5. Ragas 裁判与成对结果

固定诊断题 `ops-01`、`sales-02`、`disclosure-01`；不是随机/代表性样本。
Ragas 0.4.3；每指标 90 秒、每调用最多 4096 输出 token、每组最多 18 调用。
两组均实际 18 调用、9/9 指标有效；完整原始摘录/上下文未截短。

先保留默认 thinking 的失败运行：15 调用、约 325.65 秒，faithfulness/recall 六项
`IncompleteOutputException`，只有 precision 三项有效，其他均值为 null。短连接探针显示
推理消耗输出预算，后续显式 `enable_thinking=false` 探针 HTTP 200、JSON 完整、无 reasoning 内容。
这支持“thinking 与结构化输出预算不适配”的诊断；原失败运行没有逐响应 finish_reason，
不能伪称已逐项证实都是 token 耗尽。没有靠增加预算或删除失败美化结果。

| 同一 DeepSeek、thinking 关闭 | BM25 | BM25 + rerank |
| --- | ---: | ---: |
| Context precision（3/3 有效） | 0.6667 | 约 1.0000 |
| Context recall（3/3 有效） | 0.8333 | 1.0000 |
| Faithfulness（3/3 有效） | 1.0000 | 1.0000 |
| 总用时 | 75.72 秒 | 79.30 秒 |

两组均记录返回模型、thinking 参数、用量、结束原因和阶段耗时；不保存裁判请求/响应正文或密钥。
供应商在候选三次响应中报告的 text_tokens 比 completion_tokens 多 1；原值保留，
不强行平账或以细项计算精确费用。baseline/candidate 报告总 token 分别为 32133/29966，
这里只是供应商用量记录，未换算价格。
baseline 使用此前已生成的三题 actual；本轮重新生成的 BM25 三行与其逐字相同，
`final-audited/baseline-row-equality.json` 保留验证。评分报告仍绑定原文件/trace，没有换头复用。
不能据此比较不同代码版本的端到端耗时；这里只比较相同裁判下的实际文本输入质量。

`disclosure-01` 的 BM25 context recall=0.5，重排后=1.0；但 baseline precision 从前一次
默认 thinking 的 0.5 变为关闭后的 0.0，说明裁判/参数也有敏感性。正式对比只用同配置的两组，
不拼接成功分数。Faithfulness 对原文摘录几乎是自证，**不是用户答案有用性、完整性或法律正确率**。
本轮没有评估新的生成式答案，也未验证该模型的高并发吞吐。

## 6. BKN 边界与真实溯源

沿用参考项目 `rules/ARCHITECTURE.md` 的单向依赖/可选能力、`bkn-trace/README.md`
“记录调用边界的一手事实，不从答案推断执行”的原则，不复制微服务或数据库栈。

- `corpus/`：固定来源、不可变正文、版本/快照；TTL 仍是本体语义真源。
- `document_scope.py`：先限定文档、版本、日期；未知/空范围不偷偷扩大检索。
- `document_retrieval.py`：独立策略；精确条号和不可解析范围先旁路，网络默认关闭。
- `document_providers.py`：显式授权的有界 HTTP 调用；HTTPS、不重定向、不落密钥；模型失败明确 error。
- `document_pipeline.py`：证据/答案编排；子块必须绑定父条文和原文 offset，回答仍返回完整父条文。
- `artifact_audit.py`：独立只读核对范围内成员、子块偏移/hash、通道次序、RRF 算术、缓存绑定和最终选取。
- `retrieval_comparison.py`：锁定实现、快照、范围/日期、候选/输出预算；模型裁判不反向进入生产检索。

特别修复了两个容易糊弄指标的点：HTTP 200 不等于有效模型输出，传输错误与 schema/向量校验错误
分开统计；未使用资源的坏 endpoint 不能阻断另一资源。缓存绑定快照、模型、请求类别和原文，
缓存向量 hash 校验；冷/混合/暖状态分开记录。

审计仍是 `local_artifact_consistency_only`：未独立重跑 dense/rerank 原始分数、BM25 分数或证明候选全集；
没有签名执行认证、当前法律效力认证、引用语义认证。仅记录 hash 也不是不可抵赖证据。
此功能仍是可审计文档 CLI，不宣称旧 Web/本体意图路由已经全面切换。

## 7. 复现与产物

项目根目录执行；先具备上一轮固定 corpus，重跑使用新输出目录，不覆盖已审核产物：

```powershell
.venv/Scripts/python.exe -X utf8 tools/document_rag.py --db artifacts/official-laws-v1/corpus.sqlite --snapshot official-laws-v1 --as-of 2026-10-12 --cases evaluation/cases/official_laws_v1_questions.json --top-k 3 --candidate-k 20 --retrieval-strategy bm25_rerank --allow-retrieval-network --output artifacts/retrieval-v2/reproduce/rerank.actual.json
.venv/Scripts/python.exe -X utf8 tools/compare_document_retrieval.py --corpus-db artifacts/official-laws-v1/corpus.sqlite --questions evaluation/cases/official_laws_v1_questions.json --oracle evaluation/cases/official_laws_v1_oracle.json --run bm25=artifacts/retrieval-v2/final-audited/bm25.actual.json --run rerank=artifacts/retrieval-v2/final-audited/bm25_rerank.actual.json --output artifacts/retrieval-v2/reproduce/comparison.json
artifacts/ragas-venv/Scripts/python.exe -X utf8 tools/evaluate_ragas.py --input artifacts/retrieval-v2/final-audited/ragas-bm25_rerank.actual.json --references artifacts/official-laws-v1/ragas-sample-references.json --metrics faithfulness,context_precision,context_recall --max-rows 3 --max-judge-calls 18 --timeout 90 --corpus-db artifacts/official-laws-v1/corpus.sqlite --verify-trace --reuse-project-model --judge-model deepseek-v4.1-flash --judge-thinking disabled --judge-thinking-param enable_thinking --output artifacts/retrieval-v2/reproduce/ragas-dry-run.json
```

最后一条默认 dry-run，显式加 `--execute` 才调用裁判。thinking 参数是此 endpoint 已实测支持的
显式选择，不自动推断其他厂商协议。比较命令退出 0 仅表示报告创建，不代表所有检索门禁通过；
验收仍使用确定性 evaluator 的退出码。独立策略切换见 CLI `--help`；RRF 额外给出新的缓存目录。

关键报告：`final-audited/ablation.json`、`holdout/comparison.json`、
`deepseek-baseline-no-thinking.ragas.json`、`deepseek-rerank-no-thinking.ragas.json`，
均位于 `artifacts/retrieval-v2/`。这些被 Git 忽略，干净克隆需要重新运行或分发数据产物。
可版本化的结果摘要和产物 SHA256 在 `evaluation/experiments/legal_retrieval_v2_results.json`。
`deepseek-baseline.ragas.json` 是必须保留的失败证据，不能替换成修复后的分数。

## 8. 验证与下一轮顺序

全量 `tools/run_tests.py`：561 项，**559 通过、2 可选依赖跳过、0 失败/错误**，264.76 秒；
隔离 Ragas 环境 21/21 通过，无额外模型调用。新旧题库各四文件冻结 hash 均未改变。
`git diff --check` 无空白错误。完整日志在 `artifacts/retrieval-v2/full-regression.log`。
单测次数不能当作新增业务用例数。

1. **先补有区分力的外置题库**：领域人员审校当前 draft；另外冻结真实用户改写、多意图、
   跨文档、未知答案、版本冲突和包含噪声的题。当前 18/18 的同语料新条文集仍可能偏容易。
2. **再按错误类型单独试验**：目标已在 top-20 而排后才优先重排；目标不在候选中才试 rewrite、
   子问题召回或 HyDE。不能看到一个难题就全栈开启，更不能按题号/目标条号特判。
3. **长文档才检验父子方案**：在正式披露/招募说明书中用章节做 parent、细粒度段落做 child，
   保留页码/offset/表格边界；与当前法条场景分层报告，限制完整父上下文预算。
4. **答案与裁判分离验证**：增加受引用约束的用户答案评测、拒答和多条文完整性；补人审和裁判
   重复性/错判检查后再设业务阈值。三题全分不作为门禁。
5. **最后考虑默认启用和路由**：根据未曝光题集的配对收益、p95/调用数和失败率选择方案；
   来源修订/废止链、上位法及真实披露的核验仍是前置工作，不被这次检索成绩替代。
