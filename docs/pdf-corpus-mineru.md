# PDF 教材接入与验收边界

## 授权与分类

本轮仅获授权上传 `data/国内基金教材` 的三份 PDF，共 264 页：股权投资基金
91 页、基金法律法规 79 页、证券投资基金基础知识 94 页。其他 Markdown 与 EPUB
不在上传范围。使用本项目 `.env` 的 `MINERU_KEY`，不复制参考项目密钥。

用户确认的是 PDF 原件经核验；教材不是法规或披露原件。清单登记
`status=verified`、`authority=research_note`、`doc_type=educational_reference`，
provenance 记录用户核验。OCR 保持 `extraction_quality=unreviewed`。
发布日期、生效日未知保持 null，不能从文件创建时间推断。

## 使用

```powershell
uv pip install -e '.[pdf]'
.venv\Scripts\python.exe tools\pdf_to_md.py --data-dir data/国内基金教材 --output-dir artifacts/mineru --dry-run
.venv\Scripts\python.exe tools\pdf_to_md.py --data-dir data/国内基金教材 --output-dir artifacts/mineru --execute --source-verified --deadline 1800 --http-timeout 120
```

默认仅干跑，不联网、不写状态。只有 `--execute` 调用 MinerU。
只有原件已有核验授权时才传 `--source-verified`；不传时清单登记 `unverified`，
不会把解析成功自动升级成用户核验。本轮三份 PDF 已获该授权。
再次执行原命令会校验原件、配置和产物哈希；已完整上传的批次复用 batch ID，
已下载 ZIP 可本地重新适配，不必重新上传。上传未完成的批次会重新申请，
因此不能承诺任意中断场景都不会产生额外服务端任务。
提交批次的 POST 遇网络错误也可能重试；未实现服务端幂等键，可能重复申请任务，
故不宣称远程 exactly-once 或零额外费用保证。

结果保留在 `artifacts/mineru/files/<data_id>/`：`full.md`、v1/v2 原始内容列表、
图片、结果 ZIP、canonical `extraction.json` 及自动统计 `quality.json`。下载后立即保存
`artifacts/mineru/raw/<data_id>.zip`，即使结构校验失败也不删除。
全部文件转换成功后才写 `corpus.jsonl`，失败不能按成功文件缩小分母。
`state.json` 不保存密钥或预签名 URL。

已有离线结果可用 `--results-dir DIRECTORY`，无需密钥；子目录须按 `data_id`
或 PDF 相对路径去掉扩展名映射。不能与 `--execute` 混用。

```powershell
.venv\Scripts\python.exe tools\corpus_cli.py --db artifacts/corpus/research.sqlite init
.venv\Scripts\python.exe tools\corpus_cli.py --db artifacts/corpus/research.sqlite import artifacts/mineru/corpus.jsonl
.venv\Scripts\python.exe tools\corpus_cli.py --db artifacts/corpus/research.sqlite publish textbooks-v1 VERSION_ID_1 VERSION_ID_2 VERSION_ID_3 --kind research
.venv\Scripts\python.exe tools\corpus_cli.py --db artifacts/corpus/research.sqlite verify textbooks-v1
```

`VERSION_ID_*` 使用 import 返回值，不能自行拼接。原件与派生 JSON 进入 SQLite
各自保存 bytes/SHA-256；图片及原 ZIP 保留本地，不宣称全包已存入数据库。
资料产物被 Git 忽略，迁移或备份时须同时保护数据库和 MinerU 产物目录。

## 运行时与引用

研究快照须 `--allow-nontrusted`；未知发布日期另须 `--include-undated-research`，
仍传入显式 `--as-of`。该选项不绕过已知发布日期、生效日和撤回日，且不适用于
trusted/regression 快照；回答标明不证明历史可用性或现行法律效力。

当前只接入 SQLite → BM25，不改变 TTL 的本体/业务事实真源，不自动生成实体链接，
不把教材段落登记成现行监管规则。意图路由不支持的问题仍可 unresolved；
直接 BM25 命中或手工 describe 意图只能作为检索/集成 smoke，不能称用户 E2E 成功。

定位中的 `page` 为 MinerU 的 0 基 `page_idx` 加一；字符偏移基于规范化 block 文本，
不是 PDF 字节或 `full.md` 偏移。页眉页脚与页码
`discarded/header/footer/page_number` 只留原件，不入检索。
所有正文/表格块定位带 `page_scope=mineru_reported_start_page_unreviewed`：
报告起始页不能证明块内所有内容来自该单页。真实结果已发现跨页表及正文合并，
块边界不能当作物理页边界；跨页表、脚注与数字/单位必须另行抽检。

明确空字符串的正文/表体、无文本图表和无题注图片保留原 artifact，派生
`unindexed_blocks` 明细说明没有进入文本索引。缺表体仅在图片路径为空、题注和脚注
明确为空列表的已识别占位结构中允许，并记录 `missing_table_body_placeholder`；
其他缺字段、null、未知类型及非法结构仍拒绝，不补写或修饰原始提取结果。
不能用“覆盖所有页”掩盖未索引块，也不能把纯图片图表计作理解成功。

## 量化与审批

分四层报告，禁止混合成一个“通过率”：

| 层 | 分母与指标 | 不能推出的结论 |
| --- | --- | --- |
| 摄取 | 授权文件 3、原件页 264；成功数、失败数、内容覆盖页数 | 覆盖率高不代表 OCR 准确 |
| 完整性 | 原件/派生哈希、重启恢复、定位偏移、幂等导入 | 哈希正确不代表教材现行有效 |
| 抽取质量 | 独立抽样正文/表格/公式；字段正确率、关键数字错误数 | 无人工 gold 不报 OCR 准确率 |
| 业务验收 | 外置题库、独立证据标注、固定快照；召回@k、引用正确率、拒答与日期隔离 | 合成单测不算真实业务验收 |

路线继续对齐本地 BKN 参考项目的职责分离原则：先做好可追溯数据接入、版本化
证据与执行边界，再做语义检索/裁剪和独立业务评测；不因文件已经入 SQLite 就
引入额外图数据库/向量库，也不继续用旧 44 题通过率替代新资料验收。

真实运行结果见 `pdf-corpus-validation-20261012.md`；没有成功导入与重启校验前
不得批准数据链路。
