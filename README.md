# FondOntology

中国基金领域本体项目。当前正式运行的是独立的 CNFO（China Fund Ontology）。

## Formal ontology

正式本体源文件：ontology/cnfo-fund.ttl

正式发布文件：artifacts/cnfo/cnfo-fund-tbox.ttl

正式本体使用独立命名空间：https://ontology.example.cn/cnfo/ontology/

正式部署时应替换为项目长期持有的真实域名。

CNFO 当前覆盖基金、基金产品、基金财产、基金投资组合、基金份额、基金管理人角色、基金托管人角色、基金投资者、基金合同、基金活动、基金状态以及公募基金、私募基金、ETF、FOF、QDII 基金等国内基金概念。

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

查看器默认打开语义详情，可以查看 Class Definition、Hierarchy、Object Properties、Datatype Properties、Mappings、Logical Constraints 和 OWL Restrictions。

查看器运行时会使用 `owlrl` 启用 OWL 2 RL 推理。属性定义在父类时，子类详情会显示该属性，并标记为“继承”；原始直接父类和直接子类仍按 CNFO Turtle 源文件的一层声明展示。推理只在查看器内存中运行，不会修改正式发布的 T-BOX 文件。

关系图作为可选视图，支持圆形和树型布局。关系图只使用 CNFO 正式本体数据。

## Semantica

本地查看器使用 Semantica 项目环境中的 FastAPI 运行能力和 RDF 解析能力。Ontology Hub 上传正式文件时使用 artifacts/cnfo/cnfo-fund-tbox.ttl，入口选择 Ontology Hub -> File Upload，格式选择 Turtle。

当前正式 CNFO 是 T-BOX，不包含具体基金产品、管理机构、净值记录和持仓实例。后续可以在独立 A-BOX 和 SHACL 文件中加入实例与监管约束。
