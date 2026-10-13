# 真实文档资料接入契约

> 2026-10-13 数据恢复入口：`data/` 是正式全文与来源记录的唯一权威目录。
> 新数据仅通过 `data/source_catalog.json` 的显式 ready 白名单与
> `tools/import_data_corpus.py` 导入；SQLite/生成清单只允许位于 `artifacts/`。
> 细则见 `docs/data-catalog-import.md`。下文通用 manifest 分层保留用于历史实验复现，
> 不能替代来源 catalog，也不能从旧 registry 或目录 glob 静默回退。

本目录约定是文档证据库的**输入规范**，不是官方资料仓库。没有经过授权、来源核验和
版本登记的文件不得直接复制到发布快照。

## 建议分层

- `incoming/official/`：法律、行政法规、部门规章、监管规定和正式公告；
- `incoming/disclosure/`：基金合同、招募说明书、定期报告、临时公告和产品资料；
- `incoming/research/`：经授权的研究或内部分析，仅用于 `research` 快照；
- `manifests/`：与原件一一对应的 JSONL 清单；清单本身进入版本控制，原件按权限管理。

## 最小登记字段

每行对应一个不可变文档版本，至少包含：

```json
{
  "doc_id": "stable-document-id",
  "title": "原件标题",
  "doc_type": "regulation_article|periodic_report|disclosure|research_note|educational_reference",
  "path": "../incoming/official/example.txt",
  "source_uri": "https://authoritative.example/document",
  "sha256": "原件字节 SHA-256",
  "authority": "authoritative_original|research_note|synthetic",
  "status": "verified|unverified|quarantined",
  "issued_date": "YYYY-MM-DD",
  "effective_from": null,
  "withdrawn_date": null,
  "provenance": {"acquired_at": "YYYY-MM-DD", "reviewer": "审校编号"},
  "locator": {"page": 1},
  "entity_links": []
}
```

`path` 相对于 manifest 所在目录解析。`effective_from` 只有在原件明确给出时才填写；
不能用发布日期或抓取日期代填。法规适用范围、条文/页码定位和实体链接必须由人工或
可审计规则核验。`sha256` 必须对应原始 bytes，不能对应清洗后的文本。

当前 SQLite 契约只接受上面列出的 authority/status 枚举。后续若引入“已抓取/已解析”
等摄取生命周期，应新增版本化状态契约，不能在 manifest 中私自扩展字符串。

## 导入与发布

```powershell
.venv\Scripts\python.exe tools\corpus_cli.py --db evidence.sqlite init
.venv\Scripts\python.exe tools\corpus_cli.py --db evidence.sqlite import data\corpus\manifests\official.jsonl
.venv\Scripts\python.exe tools\corpus_cli.py --db evidence.sqlite publish official-v1 VERSION_ID --kind trusted
.venv\Scripts\python.exe tools\corpus_cli.py --db evidence.sqlite verify official-v1
```

只有 `authority=authoritative_original`、`status=verified` 且有 `issued_date` 的版本
才能进入 `trusted` 快照。研究、回归和合成资料必须显式使用对应快照类型；RAG CLI
消费非 trusted 快照时必须传 `--allow-nontrusted`，答案会带非权威提示。

当前仓库没有随代码提交真实法规或披露原件；合成 fixture 仅用于验证导入、重启、日期
隔离、范围过滤和原件引用闭环。

## PDF 教材通道

用户已核验的教材登记为 `research_note` / `educational_reference`，不是
`authoritative_original`。原件核验与 OCR 审校分开，不能用 PDF 创建日期代替发布日期。
PDF manifest 增加 `extraction: {"path": "派生JSON路径", "sha256": "派生JSON哈希"}`；
原有 `path` / `sha256` 始终对应 PDF 原件。派生 JSON、原 PDF 都保存在 SQLite，
Markdown、原始内容列表、图片及结果 ZIP 留作本地产物。使用与限制见
`docs/pdf-corpus-mineru.md`。
