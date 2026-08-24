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

FIBO production T-BOX 还依赖 OMG Commons 和 LCC 的外部标准本体。首次使用时加 `--fetch-external`，程序只从 `www.omg.org` 和 `spec.edmcouncil.org` 下载并缓存这些依赖；后续运行可离线复用缓存。未加该参数时，如果存在未解析 imports，构建会明确失败。

## Scope for next phase

后续国内金融 ontology 调整建议以独立命名空间扩展 FIBO，保留 FIBO 原始 IRI，通过 `rdfs:subClassOf`、`rdfs:subPropertyOf`、`skos:notation` 和映射关系承接中国基金行业概念，避免直接修改上游 FIBO。
