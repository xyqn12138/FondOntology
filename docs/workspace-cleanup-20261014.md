# 工作区清理审计（2026-10-14）

本轮按调用关系、入口和数据用途清理，不按文件名包含 old、legacy 或文件日期批量删除。

## 已删除

以下6个文件此前已移出正式运行路径，全文引用扫描未发现运行时导入或工具入口依赖：

- `archive/tools/extract_inventory.py`
- `archive/tools/extract_pdfs.py`
- `archive/tools/extract_restrictions.py`
- `archive/tools/gen_v05_report.py`
- `archive/tools/std_mapping.py`
- `archive/tools/v05_defs.py`

`ontology/cnfo-fund.ttl`仍有关于早期生成脚本的历史注释；保留这些注释作为生成来源，
不是要求恢复旧脚本为当前入口。删除前内容可按路径从Git历史读取，例如：

```powershell
git show 54f9c3e:archive/tools/std_mapping.py
```

## 不应当作为残留删除

| 内容 | 保留原因 |
| --- | --- |
| `data/`原件、全文、来源收据、转换记录、冻结文件 | 43份文档的权威来源和核验链，不能当缓存清除 |
| `artifacts/data-corpus/corpus.sqlite` | 冻结快照的可复现派生索引，不是另一套法条来源 |
| `evaluation/cases/real_user_qa_v1/` | 冻结44题；新架构迭代不能改变题面或金标准 |
| 旧题库、历史实际输出、评测报告、命题与核验记录 | 历史审计证据，不作为当前自然问题基线，也不冒充垃圾 |
| `qa/rag/retrieve.py`、`answer.py`、`embedder.py`、`reranker.py` | 图谱解释链仍消费，不能因文档RAG有同名能力就误删 |
| `tools/qa_bench.py`、本体裁剪基准 | 仍提供确定性内部回归和诊断，不等同独立业务验收 |
| 旧采集/入库工具 | 历史复现与维护用途；不能绕过当前来源目录获得权威资格 |
| `.env`、`.venv`、`uv.lock` | 配置、运行环境及依赖锁，不在本轮清理范围 |

Python缓存仅可在工作区代码目录清理；不递归扫虚拟环境、data或artifacts删除未知文件。
生成文件并不天然等于可删文件，引用收据、向量缓存和基准结果有不同保存要求。

## 冻结检查

- 来源版本：`fund-rag-source-v1-20261013`，43份文档、基线4414个chunk。
- 快照：`data-reviewed-20261013`。
- `source_catalog.json` SHA256：`68e1e977ebae02c1d6659111a211a6c8579a57496f788c29ad5a542c19688800`。
- `rag_source_lock.json` SHA256：`2a853a9eea422044ad4858d4cda4c4a8d9489d6a0cb9466c456f30c0c47fd900`。
- `tools/build_natural_qa_release.py --validate`通过：44题，题面来源线索0；正向依据覆盖24/43份文档。

本次清理未重新采集、转换、切分或发布来源，也未修改冻结题库。
