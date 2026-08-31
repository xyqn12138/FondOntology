# FondOntology

中国基金领域本体项目。当前正式运行的是独立的 CNFO（China Fund Ontology）。

当前源文件参考本地 FIBO `SEC/Funds` 模块的基金、基金单位、基金组合、角色和约束建模方式，但不导入 FIBO 命名空间；类名和属性名以中国基金业务语境为准。

## Formal ontology

正式本体入口：ontology/modules/cnfo-domain.ttl

当前业务本体文件：ontology/cnfo-fund.ttl

正式发布文件：artifacts/cnfo/cnfo-fund-tbox.ttl

正式本体使用独立命名空间：https://ontology.example.cn/cnfo/ontology/

当前本体版本：`0.4.0`。v0.4.0 依据国内数据标准（JR/T 0304.1-2024、JR/T 0304.2-2024、JR/T 0176.4-2022）完成命名标准化：对齐中文标签（基金分红方式、基金组织形式、股票型基金、债券类投资资产、业绩比较基准、基金分类概念等），并为概念补充标准英文名称 `cnfom:standardName`、标准出处 `cnfom:standardRef` 标注与建议别名，详见 `E:\LX\LX_fund\基金行业文档\CNFO_命名标准化方案_V0.4.md`。该版本保留完整基金 T-BOX，并增加轻量模块入口和本地 `owl:imports` 装载接口。当前只登记基金领域入口和基金本体两个真实节点，不预先创建尚未建模的债务、权益、证券或 CIV 业务模块。

正式部署时应替换为项目长期持有的真实域名。

CNFO 当前覆盖基金、基金产品、基金财产、基金投资组合、基金份额、基金管理人角色、基金托管人角色、基金投资者、基金合同、基金活动、基金状态以及公募基金、私募基金、ETF、FOF、QDII 基金等国内基金概念。

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

查看器默认打开语义详情，可以查看 Class Definition、Hierarchy、Object Properties、Datatype Properties、Mappings、Logical Constraints 和 OWL Restrictions。`AllDisjointClasses` 互斥类组也会展开为语义约束。

左侧“模块目录”对应当前模块接口，支持按模块筛选概念；现在目录只展开到实际存在的“基金本体”，后续增加子模块后可继续展开。

查看器运行时会使用 `owlrl` 启用 OWL 2 RL 推理。语义详情中的属性关系按继承链分段展示：先显示当前类实际声明的关系，再逐层显示父类实际声明的关系；因此不会把父类属性平铺到子类区段，也不会把父类值域误判为子类的 Incoming 关系。原始直接父类和直接子类仍按 CNFO Turtle 源文件的一层声明展示。推理只在查看器内存中运行，不会修改正式发布的 T-BOX 文件。

Class Inspector 的中文定义来自类的 `skos:definition`，名称/别名来自 `rdfs:label`、`skos:prefLabel` 和 `skos:altLabel`。本体映射只展示源文件明确声明的 `owl:equivalentClass`、`skos:closeMatch` 和 `skos:relatedMatch`，不展示 OWL 推理生成的反身等价关系。

关系图作为可选视图，支持圆形和树型布局。关系图只使用 CNFO 正式本体数据。

## Semantica

本地查看器使用 Semantica 项目环境中的 FastAPI 运行能力和 RDF 解析能力。Ontology Hub 上传正式文件时使用 artifacts/cnfo/cnfo-fund-tbox.ttl，入口选择 Ontology Hub -> File Upload，格式选择 Turtle。

当前正式 CNFO 仍是 T-BOX，不包含具体基金产品、管理机构、净值记录和持仓实例。OWL restriction 用于表达开放世界下的结构语义；实际数据质量校验仍应在独立 A-BOX 和 SHACL 文件中完成。
