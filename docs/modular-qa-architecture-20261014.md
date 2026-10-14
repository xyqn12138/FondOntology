# QA模块边界与接口审查（2026-10-14）

## 审查结论

原架构不是没有模块，而是缺少明确的应用入口与可组合执行边界：

1. 图谱问数返回`QaAnswer`，文档RAG返回字典，直接消费时容易混淆“执行成功”和“断言为真”。
2. 文档召回、父子切分、向量缓存、RRF与rerank集中在一个执行函数内，难以单独替换或测试。
3. 直接加入rewrite/HyDE会产生新的查询身份；只改请求不改溯源，会使缓存身份和审计失配。
4. 历史图谱解释链与新文档检索链用途不同，不能把仍被消费的旧模块一删了之。

本轮解决入口、算子拆分及转换审计；不新建服务或数据库，也不宣称两条运行路径已完全合并。
与本地`E:/LX/bkn-foundry`参考路线保持定义/数据、执行、溯源分离，
借鉴Retrieval与Ranker边界，而不是照搬其基础设施。

## 显式应用接口

入口：`fondontology/qa/service.py`。

| 接口 | 输入 | 输出与边界 |
| --- | --- | --- |
| `KnowledgeGraphService.answer` | `KnowledgeGraphRequest`、显式图栈 | `route=knowledge_graph`；保留图证据、schema trace、verdict与解释报告 |
| `DocumentService.answer` | `DocumentRequest`、`RetrievalPlan` | `route=document_rag`；显式数据库、快照、日期、预算、范围、生成与网络开关 |
| `AnswerService` | 类型化请求协议 | 可注入实现，不把业务调用绑定到CLI或具体模型厂商 |
| `QaResponse` | 两种路由共同外层 | `route/status/text/evidence/trace/payload`；原始payload保留兼容 |

- 图谱`ok`映射为`answered`，并不把`CONTRADICTED/UNKNOWN`改成真；`ambiguous`映射为`clarification`。
- 文档保留`retrieved/answered/unresolved/error`，检索有结果不代表问题已回答。
- 两类evidence内部格式依然不同；用route区分，不冒充同一种引用合同。
- `doc_ids/version_ids=None`表示不额外限缩；空tuple表示禁止全部，不能被默认全库替代。
- 请求验证非空问题、严格日期、正整数预算、布尔开关和支持的组合；不接受gold/reference/oracle。
- 用户指定范围可以传入，但自然问题基准必须只传`id/question/as_of`，不能根据金标准预选文档。
- 配置/请求错误显式抛异常；模型执行错误保留原因和轨迹，不自动改策略产出伪成功。
- 两个CLI均已接入应用接口。Web UI需要会话和流式回调，仍保留原图谱引擎入口，不在本轮破坏兼容。

## 执行模块

```text
DocumentRequest + RetrievalPlan
  → store：加载显式快照与日期可用正文
  → document_scope：仅从原始问题/显式条件决定范围
  → query_transforms：identity / rewrite / hyde
  → document_retrieval：选择已验证的执行组合
      → retrieval_stages：词项召回 / 父子召回 / 向量召回 / rerank / 缓存
      → ranking：纯RRF及rerank分数校验
  → document_pipeline：预算裁剪、源证据序列化、状态与结果组装
  → generation：原问题 + 实际源证据，生成带引用的回答（可选）
  → artifact_audit：读取实际输出和只读数据库，独立检查一致性
```

| 模块 | 不应承担的职责 |
| --- | --- |
| `document_scope.py` | 不访问参考答案，不用模型生成的标题/条号再次限缩 |
| `query_transforms.py` | 不查询数据库、不改日期/权限/文档白名单，不产生证据 |
| `retrieval_stages.py` | 不决定业务路由，不加载金标准，不调用生成器 |
| `ranking.py` | 不读环境配置、不发网络请求，只处理候选排序 |
| `document_providers.py` | 模型协议与传输适配，不决定范围、金标准或成功条件 |
| `generation.py` | 不接收HyDE假想文本作为引用；引用ID校验不等于语义忠实性评估 |
| `service.py` | 不重新实现检索，不把图谱问题悄悄变成全文问答 |

`RetrievalResources`注入embedding/rerank回调及元数据，`QueryTransformResource`注入查询转换。
生产factory惰性构建且本身不发请求；单元测试用合成资源，无须密钥。
模型配置读取既有项目配置，不增加一套环境变量或复制密钥。

## 已支持的组合，不是任意堆叠

| strategy | identity | rewrite | hyde |
| --- | --- | --- | --- |
| bm25 | 默认 | 可选 | 拒绝 |
| parent_child | 可选 | 可选 | 拒绝 |
| hybrid_rrf | 可选 | 可选 | 可选，仅改变dense查询 |
| bm25_rerank | 可选 | 可选 | 拒绝 |

Rewrite作用于词项与dense查询，HyDE保留原词项查询，仅改变dense输入。
Rerank和生成始终接收原问题。已解析的条文直达与无可用范围直接绕过转换，不浪费模型调用。
父子策略以细粒度子片段召回，返回完整父条文并保存子片段原文坐标，避免丢失例外条件。
纯BM25保留全部正向词项候选的历史行为；其他策略按`candidate_k`截断，不能声称候选预算完全相同。

当前不支持任意DAG、HyDE→BM25、hybrid→rerank或父子dense等组合。
后续先复用stage函数增加一个显式preset，同时补齐独立审计和测试，不在CLI中散落新分支。
新策略需要同步`STRATEGIES`、配置验证、code identity与独立审计规则；不能把未知组合当默认策略。

### CLI示例

以下仅展示调用方式，本轮没有执行实际题库检索或调用付费模型：

```powershell
.venv/Scripts/python.exe -X utf8 tools/document_rag.py --db artifacts/data-corpus/corpus.sqlite --snapshot data-reviewed-20261013 --as-of 2026-10-13 --question "一只公募换了基金经理，最晚什么时候要披露？" --retrieval-strategy bm25 --query-transform identity --top-k 5 --candidate-k 40 --output artifacts/experiments/bm25.json
```

将策略改为`parent_child`可做离线对照；改为`hybrid_rrf`并添加`--allow-retrieval-network`可显式使用配置的embedding。
Rewrite需要`--query-transform rewrite --allow-retrieval-network`；
HyDE必须同时选择`--retrieval-strategy hybrid_rrf --query-transform hyde --allow-retrieval-network`。
`--generate`另行启用回答模型，不等同仅开放检索网络。每次实验使用不同输出路径，避免覆盖基线。

## 执行溯源和失败管理

- 保存原问题、范围推导、候选通道、排序、父子坐标、源文档/版本/chunk与原文哈希。
- 转换轨迹保存mode、输入/输出、输入/输出SHA256、provider/model、prompt版本、耗时、失败原因。
- 模型事件只记录请求/响应哈希、耗时、token统计及错误类型，不记录鉴权或HTTP响应正文。
- 向量cache key绑定快照、模型配置、阶段和实际embedding文本；HyDE/rewrite不会错误命中原问题向量。
- 默认查询转换最多一次HTTP请求，输入上限16000字符、输出4000字符、生成上限1536 tokens。
- HTTP timeout为30秒且不重试；这是传输超时，不是整条管线的硬性总时限。自定义回调也不自动获得硬超时保证。
- 未开放网络、配置缺失、非法输出或调用失败时返回error、无证据、不降级；范围绕过单独记录。
- 审计拒绝缺失转换轨迹、篡改模式/输入/哈希、越权网络、失败后仍有检索结果，以及不绑定转换文本的cache key。
- 独立审计只证明本地记录一致性，不证明远程服务真的执行、模型分数正确或法规现行有效。

## 保留的技术债与后续门槛

1. 图谱解释兼容链仍有自己的召回策略；只有显式文档路由具有本轮组合与审计契约。不要把两路成绩混报。
2. Web UI高级会话/流式参数尚未迁移到新facade；旧入口仍可用。后续先补这些请求契约，再替换UI适配器。
3. 生成模块仍复用旧LLM流式传输函数，引用校验只校验ID；后续需独立生成传输接口和语义忠实性评估。
4. 默认不切换到Rewrite/HyDE。保持43源、44题、统一预算与as_of，按单变量实验决定保留哪些方案。
5. 指标用新题库协议：必要原文范围覆盖率、跨文档完整性、错误分母、答案要点/无支持断言、澄清/拒答、Ragas、延迟与调用成本。
6. 本次只做结构性合成fixture回归，未跑44题实际结果，未改gold迎合算法，也不声称检索或Ragas成绩提高。

新测试覆盖接口路由、参数验证、空范围保护、查询转换闸门、失败不降级、原问题保留、
假想文本不入证据、缓存身份，以及CLI输出经过独立审计和篡改拒绝。
子代理任务转发在本轮返回空消息，未产生修改或独立审核；本轮实现和复核由主代理完成。

## 本轮验证结果

- 相关74项单元/集成测试全部通过，其中新增22项测试；合成资料不属于业务QA金标准。
- 全量发现并执行649项：首次627通过、19失败、3跳过。19项失败均因本轮测试隔离器
  连Windows事件循环使用的本机socketpair及本机HTTP服务也一起禁止，并非产品断言回归。
  在继续禁止外网、仅允许回环地址后，19项全部补跑通过；合并结果646通过、3跳过。
- 3项跳过分别涉及缺失的旧HTML集成fixture和2项可选兼容Ragas安装检查，不虚报为通过。
- 初次完整日志：`artifacts/workspace-maintenance-20261014/regression.log`；
  补跑日志：`artifacts/workspace-maintenance-20261014/network-isolation-retest.log`。
- `git diff --check`通过；冻结来源与44题发布校验通过，真实评测与模型调用未执行。
