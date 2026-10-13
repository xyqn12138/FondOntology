# 法条原件与恢复全文

本目录是本项目法条语料的唯一权威来源入口。恢复情况与逐份全文链接见
`SOURCE_RECOVERY.md`；独立模型审核记录见 `SOURCE_REVIEW.md`。`source_catalog.json` 是显式白名单，
不通过遍历全部 Markdown、读取旧 SQLite 或引用旧采集清单扩大权威范围。
权威来源资格与现行法律效力是两项判断；恢复指定版本不等于确认它目前有效。

- `_sources/`：从登记来源取得的原件、来源网页、下载收据和哈希。
- `_fulltext/`：从原件转换的全文 Markdown、图片及转换记录，按内容哈希留存。
- `source_catalog.json`：逐文档关联原件与全文、版本日期、转换证据、验收状态。
- `_recovery/`：本次来源选择、旧摘要对应关系和恢复依据。
- `_converted/`：本地 MinerU/Word 中间结果，不作为独立来源。
- 原 `L0`～`L3` 文档：旧摘录、摘要和遗留文件，保留追溯，不能替代恢复全文。

`ready` 才可导入权威快照。`converted_unverified` 表示已有转换正文但仍存在
完整性、图表、日期或来源问题；`downloaded` 表示原件已取得但尚未得到可验收
转换；`unresolved` 表示未确认对应原件。具体原因在目录每项 `failure_reason` 中。
所有版本均保留来源、发布日期和适用日期，不能通过改元数据让旧文本冒充新版。

已纠正的来源问题包括：互联互通旧链接返回 2016 版，现另取 2022 年第 200 号令
附件；评价办法使用 2020 修订原件；销售结算资金规定使用含完整附录的 Word；
2013 年 QDII 外汇规定纠正旧摘要年份；国标 GB/T 39662-2020 与中国结算
2026 年操作接口分开登记。2018 年管理人登记须知于 2023-05-01 废止，保留历史。
AMBERS 混合摘要尚无单一对应原件；上交所代码指南当前取得的是中国证券网转载，
不能作为发行者原发通过。信用衍生品公式和技术接口缺失表格需要专门核验。

PDF 已通过 MinerU 转换；未提取块、公式和图片问题须按原件核对，
条号数量、机器页索引或文件哈希不能证明逐字准确。Word 表格保留 HTML 结构，
修订视图和残余 VML 的限制记录在转换观察中。

```powershell
.venv/Scripts/python.exe -X utf8 tools/import_data_corpus.py
.venv/Scripts/python.exe -X utf8 tools/import_data_corpus.py --manifest-out artifacts/data-corpus/import.jsonl --db artifacts/data-corpus/corpus.sqlite --import-ready --snapshot-id data-official-20261013
```

默认命令只审计目录。派生数据库与快照仅在 `artifacts/` 创建；法规权威目录、
来源原件和转换全文必须留在 `data/`。本次已生成上述快照，8 个版本共 724 个
chunk，快照完整性校验通过。这是导入验收，不是问答准确率评分。
中间转换文件和重复 ZIP 保留本地，不随权威数据批次提交。
详情见 `../docs/data-catalog-import.md`。
