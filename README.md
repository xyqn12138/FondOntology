# FondOntology

中国基金领域本体项目。当前正式运行的是独立的 CNFO（China Fund Ontology）。

**基金智能问数系统**按 Ontology 三阶段生命周期构建（重构后架构）：

```
                Ontology（CNFO T-BOX）
                   │
     ┌─────────────┼─────────────┐
     ↓                           ↓
Stage 2 Semantic Enforcement   Stage 3 Semantic Querying
（数据导入语义控制层）           （查询期语义世界模型）
     │                           │
 Raw Records ──enforce──→ Graph  用户问题
 （类型/关系/属性约束、           ↓
  继承闭环、验证）          semantics.OntologyContext
     │                     （类层级+关系+domain/range 语义视图）
     ↓                           ↓
 Semantic Graph ──────────→ intent（LLM 语义解析为主/规则兜底）
     ↑                       ↓
     └──定向物化推理      query_planner（约束感知：domain/range 校验）
       （propertyChain）      ↓
                          sparql_builder（聚合 GROUP BY/HAVING、
                           排名 ORDER BY/LIMIT、计数）
                               ↓
                          evidence → explainer（证据链 + 引用闸门）
```

关键能力（确定性可回归，LLM 为增强）：
- **聚合约束**："同时管理多个基金的基金经理有什么？" →
  `FundManagerPerson ^hasFundManager→ Fund，COUNT(基金) >= 2`（GROUP BY/HAVING）
- **排名**："在管基金最多的基金经理是谁？" → `ORDER BY COUNT DESC LIMIT 1`
- **计数**："有多少位基金经理" → `select=count`
- **关系约束**：planner 经 `OntologyContext` 逐跳校验 domain/range 闭包，
  语义非法的过滤/路径在计划级拒绝（INVALID）
- **关系路径终点过滤**："医药基金有哪些？" → `EquityFund ─usesInvestmentStrategy→
  FundInvestmentStrategy`，`investmentFocus CONTAINS "医药"` 落在策略上
  （属性属于谁，过滤就落在谁上面）
- **记录类不作 target**："货币基金收益怎么样？" → target=MoneyMarketFund
  （FundPerformanceRecord 只作 related）
- **LLM 语义解析**：prompt 注入完整本体语义视图（类层级、类间关系、数据属性
  分组），输出 SemanticParse 后过本体白名单 + domain/range 校验才采纳；
  传输层走流式（stream）调用——非流式在复杂问题长推理（实测 145s）下会读超时；
  未配置/失败/限流自动回落确定性规则与模板表达（终态 UCR=0）

回归与基准：

    .venv\Scripts\python.exe -m unittest discover -s tests -p 'test_qa_*.py'
    .venv\Scripts\python.exe tools\qa_bench.py --stage find      # 16 条 find CQ
    .venv\Scripts\python.exe tools\qa_bench.py --stage e2e       # 13 条端到端 CQ
    .venv\Scripts\python.exe tools\qa_bench.py --stage verify    # 72 条 verify CQ
    .venv\Scripts\python.exe tools\qa_bench.py --stage intent    # 16 条 intent CQ
    .venv\Scripts\python.exe tools\qa_bench.py --stage intent-real  # 10 条真实口语问法（LLM 路径 100%）
    .venv\Scripts\python.exe tools\qa_bench.py --stage citation  # 11 条 NL 问答（UCR=0）

**数据导入（Stage 2 生产路径）**：`fondontology.qa.enforce.import_records`
把原始记录批量约束为合法语义三元组并入数据栈，失败记录按条跳过并给出词表级
错误；导入后问数链路即刻可答（含聚合问法）：

    from fondontology.qa.enforce import import_records
    r = import_records([{"person": "张三", "fund_code": "110011",
                         "fund_name": "星河成长混合型证券投资基金", "fund_type": "混合型",
                         "operation_mode": "开放式", "organization_form": "契约型",
                         "risk_level": "R3", "management_company": "星河基金管理有限公司",
                         "aum": "32.5亿"}], stack)
    # r["imported"] / r["failed"] / r["validations"]

**仓库整理**：本体构建期脚手架（extract_*/std_mapping/v05_defs/gen_v05_report）
已归档至 `archive/tools/`（非运行链路）；`cnfo-sim.sqlite` 为可选关系镜像
（`tools/gen_sim_abox.py --sqlite` 开启，问数/浏览器均不消费）。

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

## 仿真数据（A-BOX）

`tools/gen_sim_abox.py` 根据当前最新版本体（0.5.3，经 `load_ontology_graph` 运行时加载）生成一批仿真业务数据，写入 Turtle A-BOX，并内置 SHACL 数据质量校验：

    .venv\Scripts\python.exe tools\gen_sim_abox.py

产出：
- `artifacts\cnfo\abox\cnfo-sim-abox.ttl` —— 标准 **A-BOX Turtle 图**（默认导出，
  问数链路的实际数据源）。
  只含实例数据，不含任何 T-BOX 词汇声明；图头声明 `cnfo-a:CNFOSimulatedAbox a
  owl:Ontology`，并通过 `owl:imports` 关联 `cnfo:CNFODomain` / `cnfo:CNFOFundOntology` /
  `cnfom:CNFOModuleVocabulary`，即 T-BOX 与 A-BOX 正式分离。
- `artifacts\cnfo\abox\cnfo-sim.sqlite` —— 规范化关系镜像（**可选**，`--sqlite`
  开启；问数/浏览器均不消费）：Fund / FundUnit / NavRecord / FundPortfolio /
  PortfolioPosition / FundRoleAssignment / FundParty / Investor / FundAccount /
  FundPosition / FundFee / FundPerformance / FundBenchmark / MarketIndex /
  Regulation 等；`cnfc_code` 与 `lifecycle_status` 表直接来自本体图中的受控
  代码表与状态类，`meta` 表记录本体版本与生成参数。
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

**Semantic Enforcement（数据导入语义控制层）**：`qa/enforce.py` 把一条松散
记录（dict/JSON）约束成合法语义三元组——类型约束（"混合型"→HybridFund 等，
本体词表非自由文本）、关系约束（domain/range 校验，不允许 Fund managedBy
Fund）、属性约束（字段必须命中 CNFO/CNFC 词表，未知字段拒绝）、继承闭环
（子类→祖先链显式补全）、aum→净值记录映射；产出可并入数据栈（`merge_into_stack`）
后由推理层物化 `hasFundManager`，问数链路即刻可答：

    from fondontology.qa.enforce import SemanticEnforcer
    raw = {"person": "张三", "fund_code": "110011", "fund_name": "星河成长混合型证券投资基金",
           "fund_type": "混合型", "operation_mode": "开放式", "organization_form": "契约型",
           "risk_level": "R3", "management_company": "星河基金管理有限公司", "aum": "32.5亿"}
    r = SemanticEnforcer(stack).enforce(raw)   # r.ok / r.errors / r.validations
    SemanticEnforcer(stack).merge_into_stack(r)
    answer_question("张三管理的基金有哪些？", stack).text   # → 星河成长混合型证券投资基金

全部数据为仿真虚构，与真实机构、个人无关。可按需调整规模：
`--funds 40 --days 356 --seed 20260826`。可用 `--no-export-ttl` 关闭 TTL 导出。

数据建模语义约定（与本体/SHACL 一致）：
- **基金必有管理主体**：每只基金经 `hasFundManagerRole → roleInFund → rolePlayedBy → 管理公司`
  角色链闭合（SHACL `FundShape.hasFundManagerRole minCount 1` 兜底）；基金经理自然人与该角色
  `playsFundRole`（与 `rolePlayedBy` 互逆），OWL-RL 物化 `propertyChainAxiom` 即得
  `hasFundManager` 快捷关系。
- **经理允许无在管基金**：模型保留 4 位"在职未分派"经理自然人（仅类型+姓名、无
  `playsFundRole` 边），属合法存在而非数据缺陷。全数据集一致性以"审计"为准绳：
  基金管理链闭合率 40/40；ABOX 孤立业务实体仅限这 4 位有意保留的经理。
- **经理多管（真实业务常态）**：第 3 个四分位区段的基金复用第 1 个区段同位次
  基金的经理实体（人名抽取与随机源不变，数据集可复现），形成 10 位经理各管
  2 只、20 位经理各管 1 只的分布——"同时管理多个基金的基金经理"类聚合问法
  在仿真数据上有正例。

## Web UI（M6：智能问数 + 本体查看器）

统一 Web 界面（FastAPI + 单页 HTML），左侧边栏可在两个模块间切换：

- **智能问数**：ChatGPT 风格聊天界面。`POST /api/qa/ask`（JSON）与
  `GET /api/qa/ask/stream`（SSE 流式：phase → answer → done）接入
  `engine.answer_question` 全链路（意图 → 计划 → 检索 → 证据 → 表达），
  每条答案附「证据与溯源」折叠面板（Claims + Evidence + SPARQL + 表达闸门）；
- **本体查看器**：复用 `fondontology.viewer` 的 `OntologyViewerSession`，独立页面
  `/viewer/` 经 iframe 嵌入，API 路由（`/api/ontology/*`）注册在根域，查看器前端零改动。

启动：

    .venv\Scripts\python.exe tools\qa_web.py               # http://127.0.0.1:5173
    .venv\Scripts\python.exe tools\qa_web.py --port 8000 --no-llm
    python -m fondontology web --port 8000

打开 http://127.0.0.1:5173，侧边栏底部「模块」区域切换智能问数 / 本体查看器。
右下脚标可切换表达模式（自动 / 强制 LLM / 模板）。接口回归见
`tests/test_qa_web.py`（10 例：meta/suggestions/JSON 问答/SSE 事件/查看器复用）。

## Build

新环境（或重建虚拟环境）后先安装项目包，使 `fondontology` 可被直接导入，且不再依赖运行目录：

    uv pip install -e .

已安装后即可直接运行测试脚本（任意目录均可），例如：

    .venv\Scripts\python.exe tests\test_cnfo_shacl.py

## 本体查看器（独立运行）

除智能问数 Web UI 内嵌的 `/viewer/` 外，本体查看器也可独立启动：

    .venv\Scripts\python.exe main.py viewer
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

