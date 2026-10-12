# 法条 Markdown → SQLite → 独立文档 RAG → Ragas 审核

## 结论与批准范围

本轮按用户要求暂停三份教材 PDF，保留前轮产物；实际使用 `data/`，不是 `date/`。
用户授权复用已有模型、仅跑小样本。本轮一次性运行三题、三个指标，没有反复重跑挑分。

**可以进入研究迭代，不能批准为权威法规库、用户端完整 RAG 或业务效果达标。**
最重要的问题不是“缺一个数据库产品”，而是来源/版本治理、检索字段和法条切分、
独立业务 gold、真实执行证据、评分边界没有全部闭合。Ragas 不会自动解决这些问题。

## 实际交付

1. `fondontology/corpus/markdown_inventory.py` 与 `tools/import_legal_markdown.py`：
   只读清点；外置 selection 固定 path/SHA/身份/日期/核验声明；默认 dry-run，
   显式选择才导入发布。拒绝路径越界、哈希漂移、重复 JSON key、未知 envelope 字段、
   非有限数与不合法日期，不从施行日猜发布日期。
2. `fondontology/qa/rag/document_pipeline.py` 与 `tools/document_rag.py`：
   显式 DB/snapshot/as_of/实体范围的 BM25 文档入口；默认摘录，无生成模型。
   保留实际上下文、版本、section/字符范围、哈希、日期、警告和耗时。
   空范围不回退全库，也不借旧向量/TTL 检索补结果。
3. `fondontology/evaluation/ragas_runner.py` 与 `tools/evaluate_ragas.py`：
   可选独立评测依赖；默认不联网；显式预算/超时/固定分母；JSON 和 SQLite 留档。
   问题与 reference 分离，gold 不进入生产检索或生成。

没有改 `.env`，没有输出/复制密钥到代码，没有修改参考项目，没有提交 Git。
本轮三个编写子代理均按用户要求使用 `gpt-6.1-sol` / high，主代理审核并真实执行。

## 数据不是“有官方链接就已核验”

清点 42 份 Markdown 的机器诊断：35 份检测到不完整信号、1 份完整性待确认、
6 份未分类，0 份满足自动标记完整原文的条件。这是清点规则输出，**不是逐篇法律审校结论**。
例如基金法、私募条例、运作办法等存在条号缺口或摘编标志；部分文件元数据与正文
版本矛盾。不能整目录自动升为 `authoritative_original/verified`。

本轮仅选择：

| 材料 | 日期处理 | 定位与身份 |
|---|---|---|
| 公开募集开放式证券投资基金流动性风险管理规定 | issued_date=null；施行日声明 2017-10-01 | 条号连续仍不等于全文核验；research/unverified |
| 公开募集证券投资基金运作管理办法 | 发布日声明 2014-07-07、施行日声明 2014-08-08 | 检出 44/59 条，属于不完整材料；research/unverified |

selection：`evaluation/corpora/legal-md-pilot.selection.json`。
发布到 `artifacts/legal-md-pilot/corpus.sqlite`，快照 `legal-md-pilot-v1`，
**2 个文档版本、31 个 chunk**，快照与原件/块校验通过。
成员 SHA256：`f39aa23b179bbc60aad69c0672f3404feda88dc9aa6f37ef4ef81121427e2b2c`。

源 PDF 只用于小样本条文文本对照，未作为本轮入库材料；对应 SHA 记录在
`evaluation/cases/legal_md_pilot_README.md`。没有完成整篇/发布日期/现行效力核验。
`as_of=2026-10-12` 只是对已存日期的过滤，并不证明该日法律仍然有效。
流动性文件必须显式 `--include-undated-research`，不伪造历史可得性。

## 冻结题库与一次真实评分

问题：`evaluation/cases/legal_md_pilot_questions.json`；参考：
`evaluation/cases/legal_md_pilot_references.json`。在第一次检索前按原文编写并冻结，
分别问风险定义与目标、不办理赎回期限及例外、巨额赎回 10% 边界及处理。
reference 保持 **draft**：由实施团队按源编写，不是独立审校 gold，更不是盲测集。

配置：BM25-only，top_k=3，31 个候选块；无生成、无 embedding、无 reranker。
三题都返回摘录，状态 `retrieved`；目标条文排名分别 **2、2、3**。
这是三个源导向题的人工定位检查，不能外推全库 Recall@3 或用户成功率。

Ragas 实跑时间：2026-10-12 04:05:38–04:12:27 UTC，约 409 秒。
裁判 `qwen3.8-flash`，Ragas 0.4.3；单指标超时 90 秒，每次最多 4096 输出 token，
最多 18 次 judge 调用，实际 **15 次**，串行，无失败重试。

| 指标 | 题 1 | 题 2 | 题 3 | 固定分母汇总 |
|---|---:|---:|---:|---|
| Context precision | 0.500 | 0.500 | 0.333 | **0.444，3/3 有效** |
| Context recall | 1.000 | 1.000 | 1.000 | **1.000，3/3 有效** |
| Faithfulness | timeout | timeout | timeout | **null，0/3 有效，3/3 超时** |
| Response relevancy | 未选 | 未选 | 未选 | 未配置独立 embedding，不报分 |

Context precision 是排序敏感的相关上下文评判，不等于简单“正确片段比例”；
context recall 是裁判相对短 reference 的覆盖判断，不是权威全文或独立业务覆盖率。
摘录拼接本来就接近所给上下文，即使 faithfulness 高也不能证明生成/回答质量。
本次该指标全部超时，**没有任何可报告的忠实度均值**。
总计 9 个请求评分项仅 6 项有效，CLI 正确退出 1；没有删去超时题换取成功。

结合已安装官方实现及调用计数可以进一步定位：precision 的 9 个上下文需要
9 次调用，recall 的 3 题需要 3 次；15 次总调用只剩每题一次 Faithfulness。
Faithfulness 先提取陈述、再做 NLI，因此三题都在 **statement extraction 调用链**
超时，未进入后续 NLI。该计数是 `agenerate` 入口数，不是服务端成功 HTTP 次数；
仍不能区分服务等待、模型生成、结构化解析，也不能据此认定 thinking 是根因。

记录：

- `artifacts/legal-md-pilot/inventory.json`、`import-manifest.jsonl`、`import.log`。
- `artifacts/legal-md-pilot/extractive.actual.json`、`extractive.actual.traces.jsonl`。
- `artifacts/legal-md-pilot/ragas-extractive.json`、`ragas.sqlite`。
- `artifacts/legal-md-pilot/ragas-execution.log`。

主代理独立核对了本次 actual 声明的 trace SHA、三题四个核心字段逐项对应和 gold
没有进入 actual rows，均一致。但评测器本身仍明确 `provenance_verification=declared_only`，
没有自动核验任意输入的 trace/snapshot 绑定，不应据自声明认证第三方录制结果。

## 已定位的真实检索问题

1. **法名不等于文档范围。** `answer_document` 把完整问题交给 BM25，未建立
   `doc_ids/version_ids` 范围；其他法规引用同一法名就可能排在目标法规前。
2. **元数据抢占正文 top-k。** Markdown 标题、发布机关、来源组成独立短块，
   与正文同权索引，BM25 长度归一化进一步帮助它上排。题 1 元数据块的得分全部
   来自法名词元；题 3 第二名也是元数据，而非能回答业务问题的正文。
3. **800 字符切块不是法条切块。** 当前按 Markdown 标题分节后硬切，未尊重
   条/款和例外边界，实际存在半句开头、半句结尾以及多个条文挤在一起。
   这里的文档 chunk 800 字符，**与旧 TBOX 裁剪 800 字符预算不是同一评测对象**。
4. **数字写法不统一。** `10%` 与“百分之十”没有等价检索表达；阈值的“超过”
   和“不低于”更不能只靠词面匹配判定。

只读诊断删除问题中的法名会改善题 2、3，却让题 1 目标退到第三名。
因此不能以“删法名”或“把 top-k 调大”作为根因修复，也不能只拿这三题调参。

## 与 BKN Foundry 对齐的下一轮顺序

参考本地项目，不复制其部署复杂度：

- `E:/LX/bkn-foundry/rules/ARCHITECTURE.md:9`：模块可选及职责边界；本仓保持
  corpus、retrieval/answer、evaluation 分离，TTL 语义真源与 SQLite 文档库并存。
- `E:/LX/bkn-foundry/adp/context-loader/agent-retrieval/server/logics/knsearch/concept_retrieval.go:132`
  及 `search_schema.go:350`：召回、依赖闭合、范围与预算应分开，不能裁出悬空关系。
  BKN 为保端点可超过 top-k，不能直接等同本仓硬 token 预算。
- `E:/LX/bkn-foundry/bkn-trace/README.md:13`：记录真实调用事实，不从答案反推证据；
  执行完成、证据可恢复、来源核验、答案被支持是不同状态。
- `E:/LX/bkn-foundry/rules/TESTING.md:27`：单测、集成、业务/API验收和性能分层；
  该文档自称目标态，不把规范文本当作对方已经完成的验收结果。

建议按以下依赖顺序推进：

1. **P0 数据与独立 gold。** 先补这两篇的完整官方版本、有效性证据和逐条映射，
   不把摘要补字后直接冒充原文。业务审校者提供 40–60 题 pilot，按文档家族/版本
   划分开发集与盲集，而不是随机拆同篇问题。披露资料另建文档类型及实体/报告期约束。
2. **P1 文档检索 v2。** 唯一法名定位 → 显式 doc/version 范围 → 条/款正文检索；
   歧义/未知文档不静默扩大范围。元数据作为独立字段，不争抢答案正文名额。
   法条级父子 chunk 保留原始 offset、长条的必要邻接内容，发布新 chunker/index 版本。
3. **P1 评测可运行性。** 给 Faithfulness 增加阶段计时/调用计数，下一次直接记录
   statement extraction 与 entailment 的耗时，而非依赖总调用数事后推断。
   独立裁判未自动继承生产 thinking 参数；需明确记录 provider 参数再做有界诊断。
   生产配置的 `auto` 实际发 `thinking={type:disabled}`，不是服务商自动探测；
   只有 qwen 模式使用 `enable_thinking=false`，不能未验证就归因或切参数。
   后续生成短答案必须单独限制输出/总时长并保留失败，不靠裁剪 actual 来美化评测。
4. **P2 真正用户链路。** 设计图事实/文档/混合任务的入口契约再接旧 QA/Web。
   当前独立 CLI 跑通不等于旧意图路由已修好。生成引用 ID 存在也不等于语义支持。
5. **P3 再比较本体裁剪。** 在相同快照、gold、模型和预算下比较 full/current/candidate；
   分开报告语义依赖缺失、文档召回错误、执行错误和答案错误。旧 `13/44 critical_missing`
   仅是旧题库诊断，不能与本轮 Ragas 分数合并或宣称同比提升。

无需本轮新增微服务、Kafka、OpenSearch、Redis、MariaDB 或 Kubernetes。
先把 Python 模块、SQLite、JSON/JSONL 契约和实际业务验收做扎实。

## 量化面板与放行原则

以下是下一轮提议，阈值需要业务方批准，不能把三题分数直接设成目标：

| 层面 | 必报指标 | 分母/门禁 |
|---|---|---|
| 数据 | 来源核验覆盖、全文/条款覆盖、版本日期完备、原件恢复/定位正确 | 分别以文档、条款、抽检定位数为分母；不把 hash 正确当来源正确 |
| 系统 | 范围逃逸、过期证据误入、快照漂移、无证据作答、超时/失败 | 已知硬隔离/篡改负控必须全部通过；错误不能移出分母 |
| 检索 | 独立证据标注的 Recall@k、MRR/nDCG、例外条款联合覆盖、元数据占位率 | 同一冻结集、同一 top-k/字符预算；按场景分层 |
| 业务 | 答案与引用联合成功、阈值/单位/例外准确、错误拒答、正确拒答 | 缺证据/冲突/历史版本单独设题，业务审校确认 |
| 用户 | 问法改写一致性、多轮指代、澄清质量、任务完成、延迟与调用成本 | 从真实入口执行；不能用手工指定意图替代 |
| Ragas | precision/recall/faithfulness/relevancy + 有效评分覆盖率 | 逐项固定分母，缺分则均值 null；与确定性门禁并列，不合成掩盖失败的总分 |

同时保留正控、负控和故障注入；“无证据”“未知版本”“边界恰好等于阈值”
不能只由程序旧行为反推答案。成本目前只记录请求/输出上限，不伪造未采集的账单 token。

## 复现方式

在项目根目录，先创建被忽略的输出目录。下列命令默认不调用模型：

```powershell
New-Item -ItemType Directory -Force artifacts/legal-md-pilot | Out-Null
.venv/Scripts/python.exe -X utf8 tools/import_legal_markdown.py --root data --report artifacts/legal-md-pilot/inventory.json --selection evaluation/corpora/legal-md-pilot.selection.json --manifest-out artifacts/legal-md-pilot/import-manifest.jsonl --db artifacts/legal-md-pilot/corpus.sqlite --import-selected --kind research --snapshot-id legal-md-pilot-v1
.venv/Scripts/python.exe -X utf8 tools/document_rag.py --db artifacts/legal-md-pilot/corpus.sqlite --snapshot legal-md-pilot-v1 --as-of 2026-10-12 --cases evaluation/cases/legal_md_pilot_questions.json --top-k 3 --allow-nontrusted --include-undated-research --output artifacts/legal-md-pilot/extractive.actual.json
uv venv artifacts/ragas-venv
uv pip install --python artifacts/ragas-venv/Scripts/python.exe "ragas==0.4.3" "langchain-community==0.3.31"
artifacts/ragas-venv/Scripts/python.exe -X utf8 tools/evaluate_ragas.py --input artifacts/legal-md-pilot/extractive.actual.json --references evaluation/cases/legal_md_pilot_references.json --metrics faithfulness,context_precision,context_recall --max-rows 3 --max-judge-calls 18 --timeout 90 --output artifacts/legal-md-pilot/ragas-dry-run.json
```

隔离环境只装评分依赖，不改变主 `.venv`。最小安装命令锁直接依赖，不保证所有
间接依赖字节一致；真实报告另记录相关包版本。项目 `.[ragas]` 和 `uv.lock` 也已更新，
共享依赖 rich 由 15.0.0 解析到 14.3.4；保留原 huggingface-hub 1.28.0，未安装到主环境。
Ragas 0.4.3 配 community 0.4.2 实测因缺失 `chat_models.vertexai` 导入失败，故 pin 0.3.31，
没有修改 site-packages 或伪造兼容模块。

真实执行需 `RAGAS_JUDGE_API_KEY/MODEL/BASE_URL` 并显式 `--execute`。本轮经授权
由 Python 读取 `fondontology.qa.config.llm_config()`，仅在子进程内把已有值映射给
对应 `RAGAS_JUDGE_*`，未保存密钥。裁判不隐式继承 embedding 凭据。
后续实验应使用新的输出文件名，保留本次失败基线。

## 验证

- 新清点模块 17 项测试通过；独立文档入口 8 项通过。
- Ragas 隔离环境 15 项测试通过，包含真实官方 metric 类配 mock judge/embedding 的负控，
  不是把 mock 分数当线上结果。主环境缺可选依赖的两项会显式 skip。
- 真实 3 × 3 评分为 6 个有效、3 个 timeout，和离线测试通过是两回事。
- 最终完整离线回归 **474 项：472 通过，0 失败，0 错误，2 可选依赖 skip**，
  303.85 秒；日志 `artifacts/legal-md-pilot/full-regression-final.log`。
  这两项已在隔离 Ragas 环境的 15/15 测试中实际执行通过，未将 skip 冒充通过。
  测试进程使用虚拟模型配置并阻止非本机网络，不调用真实业务模型。
- `compileall`、`git diff --check`、`uv lock --check` 通过；隔离评分环境
  `uv pip check` 验证 98 个已安装包依赖一致。未宣称主环境已按新 lock 重装验收。

剩余风险：普通 `--generate` 仍复用没有总 deadline/输出预算的旧流式函数，
本轮未调用；未修复旧 Web 路由，未完成独立业务验收，未校验全库现行效力。
