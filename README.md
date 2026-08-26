# FondOntology

国内金融 ontology 的第一阶段以 FIBO 作为 T-BOX 基础，并使用 Semantica 进行导入。当前入口为 FIBO production T-BOX，不包含 FIBO reference data、examples 和 metadata load 文件。

## Source

默认从以下本地目录读取 FIBO：

```text
E:\LX\LX_fund\基金行业文档\D_国际标准参考\FIBO\FIBO registry\fibo
```

也可以通过环境变量 `FIBO_ROOT` 或命令行参数 `--fibo-root` 指定目录。FIBO registry 的 `catalog-v001.xml` 用于将 `owl:imports` 离线解析到本地文件。

## Commands

使用项目虚拟环境运行：

直接启动本体浏览器：

```powershell
.venv\Scripts\python.exe main.py
```

以下两种写法也可以直接启动本体浏览器：

```powershell
.venv\Scripts\python.exe fondontology\explorer.py
.venv\Scripts\python.exe -m fondontology.explorer
```

如果需要运行 FIBO 构建命令，才使用后面的构建命令。

```powershell
.venv\Scripts\python.exe -m fondontology.fibo_tbox inspect
.venv\Scripts\python.exe -m fondontology.fibo_tbox build
.venv\Scripts\python.exe -m fondontology.fibo_tbox inspect --fetch-external
.venv\Scripts\python.exe -m fondontology.fibo_tbox ingest --fetch-external
```

`build` 会生成：

- `artifacts/fibo/fibo-prod-tbox.ttl`：解析完整 import closure 后的本地 T-BOX RDF 图
- `artifacts/fibo/fibo-prod-tbox-manifest.json`：源版本、文件数、三元组数和未解析 import 清单

`ingest` 会先构建 T-BOX，再调用 `semantica.ontology.ingest_ontology` 载入合并后的 Turtle 图。生成文件属于本地构建产物，不提交外部 FIBO 源码。

## Visualization

当前默认使用类中心的本体浏览器，不再把整个 ontology 强行铺成一张图。浏览器每次只显示当前类、直接父类、直接子类和当前类的直接属性；点击任意类即可把它切换为新的中心类，继续展开下一层。

先生成国内基金合并 T-BOX：

```powershell
.venv\Scripts\python.exe -m fondontology.fibo_tbox build
.venv\Scripts\python.exe -m fondontology.cnfo_tbox build
```

启动本体浏览器：

```powershell
.venv\Scripts\python.exe -m fondontology.explorer
```

打开 <http://127.0.0.1:5173>。默认中心类是 `基金`，可以在左侧搜索 `公募基金`、`私募基金`、`ETF` 或 `Fund`，然后点击结果或中间的父子类卡片继续浏览。右侧显示中文定义、IRI、来源层和 FIBO 对齐关系。

页面下方只有一张圆形关系图：当前类固定在圆心，所有一层邻近类沿圆周分布。继承关系、管理关系、组合关系、合同关系等都统一显示为带关系名称的连线。点击任意圆周节点后，该类会成为新的中心类并重新加载一层关系；右上角可以缩放或重置视图。

如果确实需要使用原始 Semantica 全图界面，可以显式指定旧模式：

```powershell
.venv\Scripts\python.exe -m fondontology.explorer --mode graph --graph artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json
```

浏览器后端接口位于 `/api/ontology/summary`、`/api/ontology/search` 和 `/api/ontology/class`。服务默认只监听本机地址。

FIBO production T-BOX 还依赖 OMG Commons 和 LCC 的外部标准本体。首次使用时加 `--fetch-external`，程序只从 `www.omg.org` 和 `spec.edmcouncil.org` 下载并缓存这些依赖；后续运行可离线复用缓存。未加该参数时，如果存在未解析 imports，构建会明确失败。

## Scope for next phase

后续国内金融 ontology 调整建议以独立命名空间扩展 FIBO，保留 FIBO 原始 IRI，通过 `rdfs:subClassOf`、`rdfs:subPropertyOf`、`skos:notation` 和映射关系承接中国基金行业概念，避免直接修改上游 FIBO。

## China fund T-BOX

当前已经提供一版专注基金领域的中国扩展层：

- `ontology/cnfo-fund.ttl`：可维护的国内基金扩展源文件；
- `artifacts/cnfo/cnfo-fibo-fund-tbox.ttl`：FIBO 基线与 CNFO 扩展的合并发布文件；
- `artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json`：用于 Semantica Explorer 的图文件。

国内扩展使用独立的 `cnfo` 命名空间，当前示例为 `https://ontology.example.cn/cnfo/ontology/`。正式部署时应替换为项目长期持有的域名。CNFO 通过 `rdfs:subClassOf` 继承 FIBO，不直接修改 FIBO 源文件。

先生成 FIBO 基线，再生成中国基金 T-BOX：

```powershell
.venv\Scripts\python.exe -m fondontology.fibo_tbox build
.venv\Scripts\python.exe -m fondontology.cnfo_tbox build
.venv\Scripts\python.exe -m fondontology.cnfo_tbox export-explorer
```

启动 Explorer 时指定国内合并图：

```powershell
.venv\Scripts\python.exe -m fondontology.explorer --graph artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json
```

打开 `http://127.0.0.1:5173`，可以搜索 `公募基金`、`私募基金`、`基金管理人角色`、`基金净值记录`、`ETF` 或 `QDII 基金`。Ontology Hub 应上传 `artifacts/cnfo/cnfo-fibo-fund-tbox.ttl`，入口选择 `Ontology Hub -> File Upload`，格式选择 `Turtle`。

这一版是基金领域 T-BOX，不包含具体基金产品、机构、净值和持仓实例；也没有把投资比例、合格投资者条件和备案条件硬编码为 OWL 类约束，后续可在独立的 SHACL 文件中补充。

## China fund T-BOX

当前已经提供一版专注基金领域的中国扩展层：

- `ontology/cnfo-fund.ttl`：可维护的国内基金扩展源文件；
- `artifacts/cnfo/cnfo-fibo-fund-tbox.ttl`：FIBO 基线与 CNFO 扩展的合并发布文件；
- `artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json`：用于 Semantica Explorer 的图文件。

国内扩展使用独立的 `cnfo` 命名空间，当前示例为 `https://ontology.example.cn/cnfo/ontology/`。正式部署时应替换为项目长期持有的域名。CNFO 通过 `rdfs:subClassOf` 继承 FIBO，不直接修改 FIBO 源文件。

先生成 FIBO 基线，再生成中国基金 T-BOX：

```powershell
.venv\Scripts\python.exe -m fondontology.fibo_tbox build
.venv\Scripts\python.exe -m fondontology.cnfo_tbox build
.venv\Scripts\python.exe -m fondontology.cnfo_tbox export-explorer
```

启动 Explorer 时指定国内合并图：

```powershell
.venv\Scripts\python.exe -m fondontology.explorer --graph artifacts/cnfo/cnfo-fibo-fund-tbox-explorer.json
```

打开 `http://127.0.0.1:5173`，可以搜索 `公募基金`、`私募基金`、`基金管理人角色`、`基金净值记录`、`ETF` 或 `QDII 基金`。Ontology Hub 应上传 `artifacts/cnfo/cnfo-fibo-fund-tbox.ttl`，入口选择 `Ontology Hub -> File Upload`，格式选择 `Turtle`。

这一版是基金领域 T-BOX，不包含具体基金产品、机构、净值和持仓实例；也没有把投资比例、合格投资者条件和备案条件硬编码为 OWL 类约束，后续可在独立的 SHACL 文件中补充。
页面下方只有一张圆形关系图：当前类固定在圆心，所有一层邻近类沿圆周分布。继承关系、管理关系、组合关系、合同关系等都统一显示为带关系名称的连线。点击任意圆周节点后，该类会成为新的中心类并重新加载一层关系；右上角可以缩放或重置视图。
