# FondOntology

中国基金领域本体项目。当前正式运行的是独立的 CNFO（China Fund Ontology）。

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

## Build

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
