# FondOntology

中国基金领域本体项目。当前正式运行的是独立的 CNFO（China Fund Ontology）。

规划中的"基金智能问数系统"（LLM 语义解构 + T-BOX 语义编译器 + A-BOX 查询 + 证据链）
设计见 `artifacts/cnfo-qa-system-design.md`（v0.4 冻结稿）。

**M1 已落地**（确定性语义链，无需 LLM）：`fondontology/tbox/`（taxonomy/constraints/
inference）+ `fondontology/qa/verify.py`（verify 四状态：ENTAILED/CONTRADICTED/
UNKNOWN/INVALID_REQUEST）。回归与基准：

    .venv\Scripts\python.exe -m unittest discover -s tests -p 'test_qa_verify.py'
    .venv\Scripts\python.exe tools\qa_bench.py --stage verify   # 72 条 CQ，100%

**M2 已落地**（查询链）：`qa/graph.py`（TBOX/ABOX 分层 + GraphSnapshot）、
`qa/query_planner.py`（Semantic Query IR v1 草案）、`qa/sparql_builder.py`
（QueryPlan→SPARQL 纯函数）、`qa/abox_query.py`（实例检索 + explicit/inferred
类型证据 + 局部子图）：

    .venv\Scripts\python.exe tools\qa_bench.py --stage find      # 16 条 find CQ，100%

**M3 已落地**（确定性端到端）：`qa/evidence.py`（Claim-Evidence Map + premises/
derived 证据链 + 引用校验）、`qa/context.py`（Ontology Slice 预算与截断）、
`qa/templates.py`（无 LLM 模板作答）、`qa/engine.py`（手工 Intent →
QueryPlan → SPARQL → 证据 → 模板）；**QueryPlan v1.0 已冻结**
（`artifacts/qa/query_plan.schema.json`）：

    .venv\Scripts\python.exe tools\qa_bench.py --stage e2e       # 12 条端到端 CQ，100%

**M4 已落地**（NL→Intent）：`qa/index.py`（词汇索引）、`qa/resolver.py`
（string→candidates，含实体代码/受控归一化）、`qa/validator.py`（白名单）、
`qa/lexicon.py`（"R4以上/国内"等确定性归一化）、`qa/intent.py`（LLM 解构 +
Candidate Selection 协议 + resolution 三态；无 key 走确定性路径，有 key 走
OpenAI 兼容接口且输出须过白名单）。`.env` 提供
`OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL`（兼容别名：`MODEL`、`API_BASE`；
`BASE_URL` 可写完整端点 `…/chat/completions`）后 LLM 路径自动启用（意图候选选择、
答案表达与引用闸门均走真 LLM，实测 `gate=llm_validated`、UCR=0）：

    .venv\Scripts\python.exe tools\qa_bench.py --stage intent    # 14 条 intent CQ，100%（Semantic Accuracy 10/10）

**M5 已落地**（LLM 表达 + 引用闸门 + NL 全链路）：`qa/explainer.py`（LLM 逐句
claim_id 结构化表达；知越权引用 → 带反馈重试 → 模板回退，终态 UCR=0）、
`qa/engine.py::answer_question()`（自然语言 → intent → QueryPlan → SPARQL →
证据 → 表达 全链路入口）、`tools/qa_cli.py`（单问 / REPL）：

    .venv\Scripts\python.exe tools\qa_bench.py --stage citation  # 10 条 NL 问答，UCR=0，引用零越权
    .venv\Scripts\python.exe tools\qa_cli.py "有哪些交易型开放式指数基金"
    .venv\Scripts\python.exe tools\qa_cli.py --repl             # 交互式问数
    .venv\Scripts\python.exe tools\qa_cli.py --detail "R4以上的基金有哪些"
    .venv\Scripts\python.exe tools\qa_cli.py "钱强的基金有什么？"   # 投资者实体锚点 → 持仓链查询
    .venv\Scripts\python.exe tools\qa_cli.py "魏辉的基金有什么？"   # 基金经理锚点 → playsFundRole→roleInFund 链

库级调用入口：

    from fondontology.qa.graph import build_stack
    from fondontology.qa.engine import answer_question
    stack = build_stack("ontology/modules/cnfo-domain.ttl", "artifacts/cnfo/abox/cnfo-sim-abox.ttl")
    ans = answer_question("开放式基金与封闭式基金是否互斥", stack)
    print(ans.text, ans.verdict, ans.explanation)   # 含 gate/UCR 报告
    ans = answer_question("钱强的基金有什么？", stack)   # 锚点问题：投资者 → 持仓 → 份额 → 基金

当前源文件参考本地 FIBO `SEC/Funds` 模块的基金、基金单位、基金组合、角色和约束建模方式，但不导入 FIBO 命名空间；类名和属性名以中国基金业务语境为准。

## Formal ontology

正式本体入口：ontology/modules/cnfo-domain.ttl

当前业务本体文件：ontology/cnfo-fund.ttl

正式发布文件：artifacts/cnfo/cnfo-fund-tbox.ttl

正式本体使用独立命名空间：https://ontology.example.cn/cnfo/ontology/

当前本体版本：`0.5.3`。v0.5.0 为语义契约完善版本：① 完善基础抽象（`FundBusinessObject` 基金业务对象、`FundAccount` 基金账户与 6 个代码取值类）；② 全部 143 项属性补齐中文定义（`skos:definition`），形成属性关系契约；③ 代码表语义化——`ontology/modules/cnfo-fund-codes.ttl` 提供 6 套 SKOS 受控代码表（基金运作方式/组织形式/分红方式/风险等级/私募基金类型/收费方式，依据 JR/T 0304.2-2024），新增 6 个代码引用属性，类与代码概念建立 `skos:closeMatch`，`isOpenEnded`/`isPrivate` 等标注为兼容属性；④ 数据质量层独立——`ontology/shacl/cnfo-fund-shapes.ttl`（SHACL）与 `artifacts/cnfo/abox/`（示例 A-BOX，参考 `artifacts/cnfo/cnfo-fund-sample-abox.ttl`）与 T-BOX 分离。v0.5.1 纠正持仓公共属性的 domain：新增 `FundPositionRecord` 基金持仓记录作为 `FundPosition` 与 `PortfolioPosition` 的共同父类，消除示例数据触发的交叉类型推断。v0.5.2 补齐跨境基金与代理基础概念：新增 `CrossBorderFund`、内地/香港互认基金层级、`FundAgent` 基金代理人机构主体、`FundAgentRole` 基金代理人角色及基金关联关系。v0.5.3 根据本体专家审查补齐基金经理人/托管人、基金账户与持仓、基金份额级净值、业绩、费用、监管规则、基准指数和投资者风险评级等语义链接；新增资产轴互斥、关键标识、等价类和业务闭环 SHACL 约束。当前 T-BOX 包含 143 个类、143 个对象属性和 61 个数据属性。v0.4 命名标准化与 V0.5 构建详情见 `E:\LX\LX_fund\基金行业文档\CNFO_命名标准化方案_V0.4.md` 与 `基金本体建模_V0.5_构建报告.md`。

正式部署时应替换为项目长期持有的真实域名。

CNFO 当前覆盖基金、基金产品、基金财产、基金投资组合、基金份额、基金管理人角色、基金托管人角色、基金代理人主体/角色、基金投资者、基金合同、基金活动、基金状态以及公募基金、私募基金、ETF、FOF、QDII、内地与香港互认基金等国内基金概念。

模块层使用独立的技术命名空间 `https://ontology.example.cn/cnfo/module/` 描述模块层级、文件、顺序和术语归属，不计入 CNFO 业务类和属性统计。新增业务模块时，只需新增 Turtle 文件、声明 `owl:imports` 和模块元数据，现有构建器、API 和左侧目录即可递归加载。

## 仿真数据（A-BOX / SQLite）

`tools/gen_sim_abox.py` 根据当前最新版本体（0.5.3，经 `load_ontology_graph` 运行时加载）生成一批仿真业务数据，写入 SQLite 轻量数据库，并内置 SHACL 数据质量校验：

    .venv\Scripts\python.exe tools\gen_sim_abox.py

产出：
- `artifacts\cnfo\abox\cnfo-sim.sqlite` —— 规范化镜像本体核心类与关系的仿真 A-BOX：
  Fund / FundUnit / NavRecord / FundPortfolio / PortfolioPosition / FundRoleAssignment /
  FundParty / Investor / FundAccount / FundPosition / FundFee / FundPerformance /
  FundBenchmark / MarketIndex / Regulation 等；`cnfc_code` 与 `lifecycle_status`
  表直接来自本体图中的受控代码表与状态类，`meta` 表记录本体版本与生成参数。
- `artifacts\cnfo\abox\cnfo-sim-abox.ttl` —— 标准 **A-BOX Turtle 图**（默认导出）。
  只含实例数据，不含任何 T-BOX 词汇声明；图头声明 `cnfo-a:CNFOSimulatedAbox a
  owl:Ontology`，并通过 `owl:imports` 关联 `cnfo:CNFODomain` / `cnfo:CNFOFundOntology` /
  `cnfom:CNFOModuleVocabulary`，即 T-BOX 与 A-BOX 正式分离。
- `artifacts\cnfo\abox\cnfo-sim-explorer.json` —— Semantica Explorer 图（默认导出，
  nodes/edges 格式与 `cnfo-fund-tbox-explorer.json` 一致；为可浏览性不含约 3.5 万条
  净值记录节点）。**不含 owl:Ontology 数据集头节点**：Semantica 的
  `/api/ontology/registry` 会把图中每个 owl:Ontology 节点推断为一个“本体”条目，
  若把 A-BOX 数据集头放进图里，Ontology 面板就会显示“CNFO 仿真 A-BOX…0 Classes”，
  掩盖真正的 T-BOX。A-BOX 数据集头只保留在 `cnfo-sim-abox.ttl` 中。
- `artifacts\cnfo\abox\cnfo-sim-session.json` —— **T-BOX + A-BOX 合并会话图**（默认
  导出）。合并 `cnfo-fund-tbox-explorer.json` 与 A-BOX 图，补齐 T-BOX 本体节点
  （`cnfo:CNFODomain`，标签与版本取自 T-BOX）并给类/属性节点标注 `scheme_uri`，
  因此 Ontology 面板显示设计好的 T-BOX（如：CNFO 基金领域入口，143 类 / 204 属性），
  A-BOX 实例作为普通图数据浏览。
- 默认在内存中对 A-BOX + T-BOX 合并图运行 SHACL 校验（`--validate-days` 控制
  净值记录保留窗口，默认最近 15 个估值日，用于控制 SPARQL 校验成本；
  SQLite / TTL 中始终写入全量净值序列）。

**推理层（已启用）**：问数引擎在显式图之上做**定向物化推理**（`qa/graph.py` 的
`require_abox_inferred()`）——只传播本体声明的 `propertyChainAxiom`
（`hasFundManagerRole∘rolePlayedBy→hasFundManager` 等 4 条链）与
`playsFundRole→rolePlayedBy` 逆关系，产物登记在 `inference_registry`
（三元组 → 规则名 + 前提三元组）。查询图 = TBOX + 显式 ABOX + 推理产物。
问答证据链据此给"由什么推出"：锚点类问题（如"魏辉的基金"）直接走推理物化的
快捷边（`^hasFundManager`），证据显示 `rule=property_chain:…` 且能逐条展开前提。

全部数据为仿真虚构，与真实机构、个人无关。可按需调整规模：
`--funds 40 --days 356 --seed 20260826`。可用 `--no-export-ttl` / `--no-explorer-json` /
`--no-session-json` 关闭对应导出。

数据建模语义约定（与本体/SHACL 一致）：
- **基金必有管理主体**：每只基金经 `hasFundManagerRole → roleInFund → rolePlayedBy → 管理公司`
  角色链闭合（SHACL `FundShape.hasFundManagerRole minCount 1` 兜底）；基金经理自然人与该角色
  `playsFundRole`（与 `rolePlayedBy` 互逆），OWL-RL 物化 `propertyChainAxiom` 即得
  `hasFundManager` 快捷关系。
- **经理允许无在管基金**：模型保留 4 位"在职未分派"经理自然人（仅类型+姓名、无
  `playsFundRole` 边），属合法存在而非数据缺陷。全数据集一致性以"审计"为准绳：
  基金管理链闭合率 40/40；ABOX 孤立业务实体仅限这 4 位有意保留的经理。

### 加载进 Semantica

- **Explorer 图（推荐）**：T-BOX 与 A-BOX 一起浏览用合并会话图（Ontology 面板显示
  设计好的 T-BOX，实例作为数据）：

      .venv\Scripts\python.exe fondontology\explorer.py --mode graph --graph artifacts\cnfo\abox\cnfo-sim-session.json

  只浏览 A-BOX 实例可用 `--graph artifacts\cnfo\abox\cnfo-sim-explorer.json`（此时
  Ontology 面板为空——A-BOX 不是本体，属预期行为）。也可在 Explorer 的 Import 页面
  上传 JSON（`POST /api/import`）。
- **Ontology Hub 上传 Turtle**：`POST /api/ontology/load` 支持 Turtle 文件。T-BOX 通过
  OntologyIngestor 提取类/属性；纯 A-BOX（无类声明）会走通用 RDF 解析回退路径，实例
  与关系会成为图节点/边。建议先上传 T-BOX（`cnfo-fund-tbox.ttl`）再上传 A-BOX
  （`cnfo-sim-abox.ttl`）。注意 Hub 会把每个上传文件登记为一个本体条目，A-BOX 条目
  会显示 0 类（它是数据集不是本体）；要按“本体 + 数据”的方式浏览，请用上面的
  会话图或 /api/import。
- **代码方式**：SPARQL / 校验可把 T-BOX 与 A-BOX 合并加载（`load_ontology_graph`
  或直接 `rdflib` 解析两个文件后合并）。
- **把任意 TTL 转成 Explorer 图**：`--graph` 只接受 JSON（`GraphSession.from_file`
  仅支持 JSON）。可用生成器内置的通用转换：

      .venv\Scripts\python.exe tools\gen_sim_abox.py --ttl-to-json artifacts\cnfo\abox\cnfo-sim-abox.ttl --ttl-skip NAV --tbox artifacts\cnfo\cnfo-fund-tbox.ttl

  `--tbox` 合并 T-BOX（代码概念有类型和中文标签）；`--ttl-skip` 按局部名前缀
  排除节点（模拟数据约 3.5 万条净值记录应排除，否则超出 SPARQL 的 50k 上限）；
  输出 `<同名>.explorer.json`，再用 `--mode graph --graph <该文件>` 加载。

### 网页端 SPARQL（Explorer SPARQL 工作台）

工作台把会话图投影为两个命名空间：
- `ent:`（`http://semantica.local/entity/` + 节点 ID）——实体；节点的单一
  `type` 成为 `rdf:type` 断言（基金节点统一为 `ent:cnfo:Fund`，子类型在节点
  属性 `rdf:type` 中，可用 `prop:cnfo:fundTypeCode` 过滤）。
- `prop:`（`http://semantica.local/prop/` + 谓词）——关系边与节点数据属性
  （键形如 `cnfo:fundCode`、`cnfo:hasFundUnit`）；节点 content 提供
  `rdfs:label`。

注意事项：每个 `PREFIX` 必须单独一行（服务端只读校验按行剥离声明）；
只允许 SELECT / ASK / CONSTRUCT / DESCRIBE；净值记录未进入会话图
（`a ent:cnfo:NetAssetValueRecord` 计数为 0），净值查询请用 TTL + rdflib。

```sparql
# 1) 全部基金（代码/名称/成立日期）
PREFIX ent: <http://semantica.local/entity/>
PREFIX prop: <http://semantica.local/prop/>
SELECT ?f ?code ?name ?inc WHERE {
  ?f a ent:cnfo:Fund ; prop:cnfo:fundCode ?code ; rdfs:label ?name .
  OPTIONAL { ?f prop:cnfo:inceptionDate ?inc . }
} LIMIT 20

# 2) 基金 -> 份额类别 -> 分红方式（含 C 类）
PREFIX ent: <http://semantica.local/entity/>
PREFIX prop: <http://semantica.local/prop/>
SELECT ?fname ?ucode ?dist WHERE {
  ?f a ent:cnfo:Fund ; rdfs:label ?fname ; prop:cnfo:hasFundUnit ?u .
  ?u prop:cnfo:fundUnitCode ?ucode ; prop:cnfo:hasFundDistributionMode ?d .
  ?d rdfs:label ?dist .
} LIMIT 20

# 3) 基金管理人/托管人（角色 -> 主体）
PREFIX ent: <http://semantica.local/entity/>
PREFIX prop: <http://semantica.local/prop/>
SELECT ?fname ?mgr ?dep WHERE {
  ?f a ent:cnfo:Fund ; rdfs:label ?fname ;
     prop:cnfo:hasFundManagerRole ?rm ; prop:cnfo:hasFundDepositaryRole ?rd .
  ?rm prop:cnfo:rolePlayedBy ?pm . ?pm rdfs:label ?mgr .
  ?rd prop:cnfo:rolePlayedBy ?pd . ?pd rdfs:label ?dep .
}

# 4) 投资者 -> 持仓 -> 份额 -> 基金
PREFIX ent: <http://semantica.local/entity/>
PREFIX prop: <http://semantica.local/prop/>
SELECT ?inv ?unit ?fund ?qty WHERE {
  ?i a ent:cnfo:Investor ; rdfs:label ?inv ; prop:cnfo:holdsFundPosition ?pos .
  ?pos prop:cnfo:positionInFundUnit ?u ; prop:cnfo:positionQuantity ?qty .
  ?u prop:cnfo:fundUnitCode ?unit ; prop:cnfo:issuedByFund ?f .
  ?f rdfs:label ?fund .
} LIMIT 20

# 5) 按类型统计（BOND/EQUITY/ETF/FOF/QDII/MONEY/...）
PREFIX ent: <http://semantica.local/entity/>
PREFIX prop: <http://semantica.local/prop/>
SELECT ?t (COUNT(?f) AS ?n) WHERE {
  ?f a ent:cnfo:Fund ; prop:cnfo:fundTypeCode ?t .
} GROUP BY ?t ORDER BY ?t

# 6) 已终止基金
PREFIX ent: <http://semantica.local/entity/>
PREFIX prop: <http://semantica.local/prop/>
SELECT ?fname ?inc ?term WHERE {
  ?f a ent:cnfo:Fund ; rdfs:label ?fname ; prop:cnfo:inceptionDate ?inc ;
     prop:cnfo:terminationDate ?term .
}
```

## Build

新环境（或重建虚拟环境）后先安装项目包，使 `fondontology` 可被直接导入，且不再依赖运行目录：

    uv pip install -e .

已安装后即可直接运行测试脚本（任意目录均可），例如：

    .venv\Scripts\python.exe tests\test_cnfo_shacl.py

使用项目虚拟环境：

    .venv\Scripts\python.exe main.py inspect
    .venv\Scripts\python.exe main.py build
    .venv\Scripts\python.exe main.py export-explorer

以上命令只构建 CNFO。

也可以直接使用 CNFO 模块：

    .venv\Scripts\python.exe -m fondontology.cnfo_tbox inspect
    .venv\Scripts\python.exe -m fondontology.cnfo_tbox build
    .venv\Scripts\python.exe -m fondontology.cnfo_tbox export-explorer

## Browser

直接启动本体查看器：

    .venv\Scripts\python.exe main.py

也可以使用：

    .venv\Scripts\python.exe fondontology\explorer.py
    .venv\Scripts\python.exe -m fondontology.explorer

打开：http://127.0.0.1:5173

在 Windows 下请使用启动终端中的 `Ctrl+C` 停止查看器。查看器对优雅关闭最多等待 5 秒，
用于释放正在处理的请求；若通过任务管理器或外部进程工具停止服务，应按进程树终止实际
Uvicorn 子进程，否则由 `uv` 管理的虚拟环境可能留下子进程。检查端口占用可使用：
`Get-NetTCPConnection -LocalPort 5173`。

查看器默认打开语义详情，可以查看 Class Definition、Hierarchy、Object Properties、Datatype Properties、Mappings、Logical Constraints 和 OWL Restrictions。`AllDisjointClasses` 互斥类组也会展开为语义约束。

左侧“模块目录”对应当前模块接口，支持按模块筛选概念；现在目录只展开到实际存在的“基金本体”，后续增加子模块后可继续展开。

查看器运行时会使用 `owlrl` 启用 OWL 2 RL 推理。语义详情中的属性关系按继承链分段展示：先显示当前类实际声明的关系，再逐层显示父类实际声明的关系；因此不会把父类属性平铺到子类区段，也不会把父类值域误判为子类的 Incoming 关系。原始直接父类和直接子类仍按 CNFO Turtle 源文件的一层声明展示。推理只在查看器内存中运行，不会修改正式发布的 T-BOX 文件。持仓公共属性统一声明在 `FundPositionRecord` 上，避免 `FundPosition` 与 `PortfolioPosition` 因复用字段产生交叉类归属；`owlrl` 结果不替代后续 HermiT 的严格 DL 交叉认证。

Class Inspector 的中文定义来自类的 `skos:definition`，名称/别名来自 `rdfs:label`、`skos:prefLabel` 和 `skos:altLabel`。本体映射只展示源文件明确声明的 `owl:equivalentClass`、`skos:closeMatch` 和 `skos:relatedMatch`，不展示 OWL 推理生成的反身等价关系。

关系图作为可选视图，支持圆形和树型布局。关系图只使用 CNFO 正式本体数据。

## Semantica

本地查看器使用 Semantica 项目环境中的 FastAPI 运行能力和 RDF 解析能力。Ontology Hub 上传正式文件时使用 artifacts/cnfo/cnfo-fund-tbox.ttl，入口选择 Ontology Hub -> File Upload，格式选择 Turtle。

当前正式 CNFO 仍是 T-BOX，不包含具体基金产品、管理机构、净值记录和持仓实例。OWL restriction 用于表达开放世界下的结构语义；实际数据质量校验仍应在独立 A-BOX 和 SHACL 文件中完成。
