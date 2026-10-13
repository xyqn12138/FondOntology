# RAG源数据冻结

2026-10-13按用户授权冻结当前43份已验收文档，源版本
`fund-rag-source-v1-20261013`，锁定记录为`rag_source_lock.json`。

`source_catalog.json`中的43个ready版本是本轮RAG唯一源文档集合。
目录内另三项仅保留追溯，不参与检索。锁定目录SHA256、文档成员及必要图像；
目录绑定的原件、全文、收据和转换记录仍逐项校验。禁止使用旧摘要补充权威正文。
导入时任何哈希失配均报错；恢复工具不能覆盖冻结目录为其他内容。

当前基线快照为`data-reviewed-20261013`，43个版本、4414个chunk，
派生数据库位于`artifacts/data-corpus/corpus.sqlite`。数据库丢失可从data重新构建，
不得以数据库替代源文档。快照成员哈希保存在锁定记录中。

```powershell
.venv/Scripts/python.exe -X utf8 tools/import_data_corpus.py
.venv/Scripts/python.exe -X utf8 tools/import_data_corpus.py --manifest-out artifacts/data-corpus/frozen-import.jsonl --db artifacts/data-corpus/corpus.sqlite --import-ready --snapshot-id data-reviewed-20261013
```

后续RAG实验固定该源版本与43份正文。切分、向量模型及检索策略可改变，
应另建派生索引/快照并记录参数；4414是当前切分基线，不限制新切分的chunk数量。
评估同时记录源版本、快照和题库版本，避免把数据更新误算为算法收益。
源文件增删、改正文或更新法规版本须发布新的源版本与锁定记录，显式说明差异，
不得静默替换本冻结基线。冻结不代表所有历史法规当前仍然有效。
