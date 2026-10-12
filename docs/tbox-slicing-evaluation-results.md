# T-BOX 裁剪独立评测与迭代结果

> 下文保留首次离线迭代的历史结果；用户后续授权在线 LLM 后的最新结果，
> 见 [在线评测与深层迭代](E:/LX/LX_fund/FondOntology/docs/tbox-online-evaluation-results.md)。
> 最新冻结集三档预算覆盖为 44/44，但在线小批仍有计划错误，不能等同问答准确率。

## 评测边界

本轮按照“先写任务 gold，再测基线，再修改实现”的顺序执行。
gold 来自基金任务和本体声明，不从裁剪输出生成，迭代中未删题、未修改期望。

- 44 道自然语言题，每道 10000 / 1800 / 800 字符：132 次评测。
- 28 道开发题，16 道留出观察题；41 道有正向语义需求，3 道空白/含糊/未知需求。
- 23 个独立契约测试方法，含多字段、多约束、多预算子测试。
- T-BOX-only：不加载实例图，不调用在线 LLM，不修改本体。
- 这些数值是上下文覆盖率，不是最终问答准确率。

规范见 [评测规范](E:/LX/LX_fund/FondOntology/docs/tbox-slicing-benchmark-spec.md)。
自然语言标注仍需领域专家复核；同一执行者设计和优化且数据集公开，留出组不能称为真正盲测。
题量有限，没有建立独立外部数据集或置信区间，不应外推为所有基金问题的效果。

冻结 SHA256：

```text
tbox_slicing_questions.json
4a8dcaaf2a2cb9d640abd723fc6c5340b662dd5d64495e68060ad3ad5bae884f
tbox_slice_contracts.ttl
abc92782d40a15aa99ad0a05028b1c89b3648e1ebf6478801a63364637e363a9
```

## 基线与最终效果

严格覆盖要求人工指定的类、属性、等价连接组全部进入**实际文本定义行**。
不能用候选元数据、原问题中的词，或显式报告失败来代替覆盖成功。
以下属性/连接召回只计算有对应期望的题，避免空集合抬高指标。

| 指标 | 10000 字符基线 | 10000 字符最终 | 800 字符基线 | 800 字符最终 |
|---|---:|---:|---:|---:|
| 全部题严格覆盖 | 26/44 (59.1%) | 39/44 (88.6%) | 20/44 (45.5%) | 36/44 (81.8%) |
| 41 道语义任务覆盖 | 23/41 (56.1%) | 36/41 (87.8%) | 17/41 (41.5%) | 33/41 (80.5%) |
| 属性召回（适用题） | 69.2% | 93.4% | 49.5% | 86.4% |
| 连接召回（适用题） | 74.0% | 92.0% | 70.0% | 88.0% |
| 文本结构安全 | 44/44 | 44/44 | 36/44 | 44/44 |
| 平均上下文字符 | 814.9 | 764.9 | 607.0 | 546.5 |

1800 字符最终覆盖同 10000 字符：39/44，平均 739.7 字符。
完整语义视图 18103 字符；最终平均压缩约 95.8% / 95.9% / 97.0%。
压缩只说明上下文长度，不保证保留所有 OWL 蕴含。
核心概念与结构支撑精度代理，10000 字符约 59.8% → 66.8%，800 字符约 59.4% → 70.6%。
这不是“无关概念全部已消除”：保留项中仍有可选邻域和词法噪声。

独立契约：**7/23 → 23/23**。
最终相对基线，三档预算均无严格覆盖退化题。
最终两个独立进程跑批的 132 份渲染文本一致，修复了 RDF 遍历顺序引起的等分路径波动。
原始 baseline 只有一次采样，不具备同等跨进程稳定性保证；中间轮次保留这种波动记录。

## 迭代轨迹

| 轮次 | 10000 字符严格覆盖 | 800 字符严格覆盖 | 独立契约 | 重点 |
|---|---:|---:|---:|---|
| baseline | 26/44 | 20/44 | 7/23 | 原实现 |
| iteration1 | 25/44 | 26/44 | 22/23 | 依赖采集、端点闭合、语义包预算、匿名约束 |
| iteration2 | 35/44 | 29/44 | 23/23 | 标签片段、定义检索、复用路径评分 |
| iteration3 | 39/44 | 35/44 | 23/23 | 对称词汇归一化、压制类别词噪声、减少重复路径 |
| final | 39/44 | 36/44 | 23/23 | 正向连接兼容、顺序确定化、约束先于可选邻域 |

第一轮大预算退化，第二轮“累计单位净值”和未知“血型”题退化，都保留在结果中。
未用删题或改 gold 消除退化；通过通用文本归一化、类别提及去噪和预算优先级修复。
本轮新增少量领域短语归一化（如规模/资产净值），不包含完整问句或逐题 IRI 答案表；
但任何人工规则都存在数据集适配风险，应继续用外部题验证。

## 代码改进

### 前置 SchemaRetriever

- 新增截断、关键包缺失、丢弃项、降级原因和预算观测。
- 返回 `classes/properties/paths` 改为实际保留项，不再返回渲染前候选。
- 属性、domain/range、祖先和连接路径成包选取；不能只保留裸属性。
- 移除重复问题文本，长输入与极小预算不会突破 schema 字符限。
- 新增可选 token 预算；当前运行环境没有 tiktoken，计数明确是启发式。
  没有验证实际线上模型的精确 token 上限，不声称已完成模型 tokenizer 对齐。
- 复用本体标签、altLabel、定义/comment，限制弱片段及类别词噪声。
- 复用路径相关性评分、优先短且正向的连接，限制候选扩展。
- 不再把“基金管理人”直接当作“基金经理”类。

### 后置 ontology slice

- 采集过滤、遍历、投影、relation_path、排序、聚合度量、日期、latest、where/OPTIONAL 依赖及显式类端点。
- 必需属性与端点先于可选子类/邻域，支持非 CNFO 测试命名空间。
- 读取匿名 some/all/hasValue/cardinality/qualified-cardinality；
  补充 equivalentClass、inverse、subProperty 和 property-chain 声明支撑。
- 用实际保留 RDF 三元组控制 `max_triples`，返回三元组及预算信息。
- 约束关联的必需项若装不下，显式报告缺失；不声称完成任意 OWL 模块抽取。
- 保留声明来源，未修改推理或 A-BOX 查询规则。

后置切片仍没有整体注入表达模型；本轮不改变证据引用闸门或执行架构。
完整 T-BOX 仍负责计划合法性校验。

## 残余问题

大预算仍有 5 题失败：

| ID | 需求 | 未满足 |
|---|---|---|
| D11 | 最近一个月净值上涨 | 没从时间表达推出 `valuationDate` |
| D15 | 基金费率和收费名称 | “收费名称”未对齐 `feeName`，基金目标及连接未完整召回 |
| D19 | 投资组合持仓 | `hasFundPortfolio` 未完整保留，虽有其他连接候选 |
| H04 | 份额类别费用金额 | `feeAmount` 同义表达缺口 |
| H05 | 季报覆盖日期 | 未将“哪段日期”展开为期间开始与结束属性 |

800 字符另有预算挤出：报告章节、投资者风险评级、业绩期间，以及复杂持仓路径。
缺失标记能发现“召回后被预算丢掉”，不能发现“压根没召回”的概念；
因此不能仅用 `critical_missing=false` 断言语义完整或直接启用 P4 自动重试。

结构检查还有局限：未验证路径在最终文本中是否能被 LLM 正确理解，
未做任意公理等价/蕴含测试；三元组中的 BNode ID 仅在当前图快照内可追踪。
定义/对比问题的实际生产入口可能绕过 SchemaRetriever，本评测只衡量该组件内容，不代表这些问答流程整体变化。

性能：基线问题检索约 4ms，最终单轮观测约 22–27ms；执行时并行回归有资源竞争。
检索器初始化及后置 slice 未纳入同一延迟指标，未做严谨性能基准。
下一步宜缓存词汇文档和预计算词法索引，但缓存必须考虑导入闭包版本。

## 复现与结果

相关回归（121 项）覆盖 schema、切片契约、确定性 E2E、find、聚合、查询 IR、
意图、T-BOX verify 和表达引用闸门，全部通过。
此外新增 RDF 插入顺序回归通过；最终版本再运行裁剪与意图重点回归，结果记录于本节末尾。
最终重点回归：`test_schema_retriever.py`、`test_tbox_slice_contracts.py`、
`test_schema_slicing_determinism.py`、`test_qa_intent.py`，共 **47/47 通过**。

在项目根目录执行：

```powershell
.venv\Scripts\python.exe tools/tbox_slice_bench.py --output artifacts/benchmarks/tbox-slicing/new-run.json
.venv\Scripts\python.exe tools/tbox_slice_bench.py --compare artifacts/benchmarks/tbox-slicing
.venv\Scripts\python.exe -m unittest discover -s tests -p test_tbox_slice_contracts.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_schema_slicing_determinism.py -v
```

121 项回归的实际执行入口：

```powershell
@'
import sys, unittest
suite = unittest.TestSuite()
for pattern in (
    "test_schema_retriever.py", "test_tbox_slice_contracts.py",
    "test_qa_e2e.py", "test_qa_find.py", "test_qa_aggregate.py",
    "test_query_ir.py", "test_qa_intent.py", "test_qa_verify.py",
    "test_qa_explainer.py",
):
    suite.addTests(unittest.defaultTestLoader.discover("tests", pattern=pattern))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'@ | .venv\Scripts\python.exe -
```

逐题原始文件：

- [baseline](E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/baseline.json)
- [iteration1](E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/iteration1.json)
- [iteration2](E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/iteration2.json)
- [iteration3](E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/iteration3.json)
- [final](E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/final.json)
- [逐题改进、退化与残余失败](E:/LX/LX_fund/FondOntology/artifacts/benchmarks/tbox-slicing/comparison.md)

结果目录被项目 `artifacts` 忽略规则覆盖，文件保留在本地，未自动加入 Git。
原始 JSON 包含每题文本和计数，支持重新聚合指标；gold SHA 在每轮均校验。
baseline 和中间轮次是在修改前即时运行保存，不是在优化后模拟原实现。
