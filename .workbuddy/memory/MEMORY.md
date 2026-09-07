# FondOntology 项目长期记忆

## 架构共识
- CNFO 独立演进，不 import FIBO；FIBO 仅作对标参考。
- 三阶段本体生命周期：Stage 1 Semantic Modeling（T-BOX）→ Stage 2 Semantic
  Enforcement（enforce.import_records 批量导入生产路径）→ Stage 3 Semantic
  Querying（intent → query_planner → sparql_builder → evidence → explainer）。
- 问数链路：LLM 语义解析为主（prompt 注入 OntologyContext 语义视图），
  本体白名单 + domain/range 校验守门，确定性规则兜底（无 key/失败/限流回退）。
- Phase 2 边界：compare/对比拒答；SUM/AVG/MAX/MIN 预留未实现；
  规模（AUM）时间序列与经理变更建模未做（R02 类问题数据层不可答，另立任务）。

## 关键工程教训
- **LLM 调用必须流式**：非流式下服务端生成完成前不下发字节，复杂问题长推理
  （实测 145s）必然读超时；流式首字节数秒即达。共享入口
  `qa/intent.py::_stream_chat_content`（intent 与 explainer 共用）。
- **属性属于谁，过滤落谁上**：如 investmentFocus 属于 FundInvestmentStrategy，
  "医药基金"的过滤须沿 usesInvestmentStrategy 落在关系路径终点
  （filters 带 `"on": "related"`），而非被 target domain 校验拒绝。
- 记录/指标类（FundPerformanceRecord、NetAssetValueRecord）永远不作查询 target。
- 仿真数据改动铁律：fund_code 由 rng 块生成与风格无关（安全）；基金名由
  公司+风格派生（改风格池会连锁改名）；魏辉/005377 是基准锚点。
- 测试约定：用户要求不跑全量、不跑批量——验证时跑一两条示例即可。
