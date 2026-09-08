# CNFO 基金智能问数系统 — 设计文档（v0.6，锚点本体驱动化回填版）

版本：0.5（重构后回填：意图层改为语义视图注入的 LLM 语义解构、新增 OntologyContext、聚合/排名查询落地、enforce 批量导入生产路径、唯一性约束两层补齐、LLM 调用全流式化；v0.4 冻结稿的架构定论与证据合同不变，本版记录"代码逼设计暴露问题"后的实际形态）
日期：2026-09-07（v0.4：2026-09-03）
关联本体：CNFO v0.5.3（`ontology/modules/cnfo-domain.ttl` 入口；发布件 `artifacts/cnfo/cnfo-fund-tbox.ttl`）
数据：仿真 A-BOX（`artifacts/cnfo/abox/cnfo-sim-abox.ttl`；SQLite 镜像改为 `--sqlite` 可选产出）
状态：**v0.5 回填冻结**（架构讨论收敛；以下用代码和 benchmark 逼设计暴露问题）

---

## 0.5 三阶段语义生命周期（Ontology 的角色划分，用户定稿）

| 阶段 | Ontology 的角色 | 当前实现 | 状态 |
|---|---|---|---|
| ① **Semantic Modeling** | 定义"有哪些东西/什么类型/什么属性/哪些关系合法" | CNFO 0.5.3（143 类/204 属性/互斥组/4 属性链/代码表） | ✅ 完备 |
| ② **Semantic Enforcement** | 数据导入期的 **Schema/Mapping 目标**：类型约束、关系约束（domain/range）、属性约束、继承闭环、**唯一性约束** | `qa/enforce.py`（Raw Data → Entity Resolution → Ontology Mapping → Validation → 静态推理 → Semantic Graph）；**`import_records()` 批量导入生产路径**；fundCode=合并键 / fundName=全库唯一；SHACL 跨节点唯一性约束（SPARQL） | ✅ 落地（`tests/test_qa_enforce.py`；库内同名/批内重复导入被拒实测） |
| ③ **Semantic Querying** | LLM 的**世界模型**：概念/实体/关系/约束 → QueryPlan → SPARQL → 推理层 → 结果 | **`qa/semantics.py` OntologyContext**（语义视图注入 prompt + 白名单/domain-range 守门 + 关系路径发现）+ intent/query_planner/sparql_builder + 定向物化推理 + LLM 表达闸门 | ✅ 主体具备；**COUNT 聚合/Top-N 排名已落地**；SUM/AVG/时间序列/compare 待扩展 |

边界：②的"推理"是**数据侧的静态闭合**（类型继承、逆关系、属性链直连）；③的"推理"是**查询侧的按需利用**（DR 物化产物服务 SPARQL）。Ontology 从不为 LLM"代答"，它提供约束与被检索的语义模型。

---

## 0. 设计定论

**Ontology-Guided QA / Semantic Query System**：LLM 只负责"自然语言 → 受约束的结构化意图"与"基于证据的自然语言表达"；候选检索、白名单、语义校验、确定性推理、查询计划编译、SPARQL 生成、证据与引用校验全部由确定性组件完成。

```
                         USER
                          │
                          ▼
                 ┌────────────────────────┐
                 │ LLM 语义解构（intent.py）│  ① prompt 注入 OntologyContext 语义
                 │ NL → SemanticParse      │     视图（类层级/类间关系/数据属性）
                 └──────────┬─────────────┘     + 解析规则 + few-shot；流式调用
                            │
                 ┌──────────▼─────────────┐
                 │ 白名单守门              │  ② target/related/属性/关系路径必须
                 │ （OntologyContext）     │     存在于本体且过 domain/range 校验；
                 └──────────┬─────────────┘     不过/LLM 失败→确定性规则兜底
                            │
                 ┌──────────▼─────────────┐
                 │ 关系路径发现            │  ③ LLM 未给路径时沿本体关系图 BFS
                 │ （find_relation_path）  │     + 问题相关性选路（闭包感知）
                 └──────────┬─────────────┘
                            │
                 ┌──────────▼─────────────┐
                 │ Query Planner           │  ④ SemanticParse → QueryPlan；
                 │ （约束感知）            │     逐跳 domain/range 闭包校验，
                 └──────────┬─────────────┘     语义非法计划级拒绝（INVALID）
                            │
                 ┌──────────▼─────────────┐
                 │ SPARQL Builder          │  ⑤ 纯函数翻译，LLM 永不生成 SPARQL
                 └──────────┬─────────────┘     （含 GROUP BY/HAVING/Top-N）
                            │
                 ┌──────────▼─────────────┐
                 │ Graph (EXPLICIT+INFERRED)│ ⑥ TBOX/ABOX/闭包 分层（§3）
                 └──────────┬─────────────┘
                            │
                 ┌──────────▼─────────────┐
                 │ Evidence Builder        │  ⑦ 证据 + Claim-Evidence Map（§7）
                 └──────────┬─────────────┘
                            │
                 ┌──────────▼─────────────┐
                 │ Local Context (Slice)   │  ⑧ 带硬上限的局部本体（§11）
                 └──────────┬─────────────┘
                            │
                 ┌──────────▼─────────────┐
                 │ LLM Explain             │  ⑨ 只能引用 Claim-Evidence Map 中的
                 └────────────────────────┘     证据；后端 citation 校验兜底
```

**四层防错原则**：
1. LLM 不做本体推理、不生成 SPARQL、不自由选择证据；
2. LLM 直接语义解构（ SemanticParse ），但**输出必须过本体白名单 + domain/range 校验**才采纳，不过则回退确定性规则——"LLM 提议、本体裁决"；
3. 进入 LLM 的词汇是 OntologyContext 渲染的本体语义视图（当前全量 T-BOX ≈1.7 万字符；查询范围裁剪路线见 §14-6）；
4. 每个答案结论 = Claim，必须落在 Claim-Evidence Map 中（Unsupported Claim Rate → 0）。

---

## 1. 词汇四件套 + 语义视图：Index ≠ Resolver ≠ Validator ≠ OntologyContext（消除职责重复）

v0.2 的 `qa/vocabulary.py` 与 `tbox/resolver.py` 存在平行重复风险，本版改为**单向依赖的四件套**，代码层面就从四个文件起步：

```
┌────────────────────────────────────────────────────────┐
│ qa/index.py      Ontology Index（只做索引，无逻辑）        │
│   build_once(): 类/属性/代码值/实体的 IRI、label、prefLabel、│
│   altLabel、code、namespace、entity_type；名称归一化索引     │
└────────────────────────────────────────────────────────┘
            │ 只读查询（string → tokens → hits）
┌────────────────────────────────────────────────────────┐
│ qa/resolver.py   Vocabulary Resolver（检索职责）          │
│   resolve_concept(text) -> candidates（类/属性候选）       │
│   resolve_entity(text)  -> candidates（ABOX 个体候选）     │
│   resolve_code(text)    -> candidates（代码值候选）         │
│   （内部用 Index；不含任何“判断对错/解释语义”逻辑）           │
└────────────────────────────────────────────────────────┘
            │ candidates
┌────────────────────────────────────────────────────────┐
│ qa/validator.py  Whitelist Validator（判定职责）           │
│   validate(candidate) -> valid/invalid + reason          │
│   whitelist 集：CNFO 类 / CNFO 属性 / CNFC 代码 / ABOX 个体 │
│   规则：候选必须来自 Index 且类型匹配预期槽位                 │
└────────────────────────────────────────────────────────┘
            │ valid concept
┌────────────────────────────────────────────────────────┐
│ qa/semantics.py  OntologyContext（v0.5 新增：世界模型职责） │
│   从 T-BOX 提取类层级/类间关系图/数据属性 domain-range；     │
│   render_for_llm() 渲染语义视图注入 prompt；               │
│   check_property_domain / find_relation_path 供守门与选路  │
└────────────────────────────────────────────────────────┘
```

**v0.5 职责修订**：v0.4 设想的 `qa/compiler.py`（Compiler 只出 Semantic Specification）未单独落地——其"语义解释"职责由 **OntologyContext**（类闭包/合法属性/可走路径的查询接口）与 **Query Planner**（约束感知计划）分担；五层职责闭合相应变为：**Resolver**（有哪些候选）→ **Validator**（候选是否合法）→ **OntologyContext**（概念在语义上意味着什么/能走哪些路径）→ **Query Planner**（需要怎样查询）→ **SPARQL Builder**（怎么执行）。任何一层都不跨级生成 Query Plan。

**硬边界**：Index 不回答任何问题；Resolver 不判断对错；Validator 不解释语义；OntologyContext 不生成查询计划。任一层越权 → 代码评审拒绝合并。

**SemanticParse 协议 + resolution 三态（v0.5 重写，替代 v0.4 Candidate Selection 协议）**：
- LLM 不再"在候选里选"，而是**在注入完整本体语义视图后直接输出结构化语义解析**：

```json
{
  "operation": "find",
  "target": "FundManagerPerson",
  "select": "entities",
  "related": "Fund",
  "relation_path": [{"property": "hasFundManager", "inverse": true}],
  "aggregation": {"func": "count", "operator": ">=", "value": 2},
  "order_by": "agg", "order_direction": "desc", "limit": null,
  "entity_label": null,
  "filters": [{"property": "investmentFocus", "operator": "contains",
               "value": "医药", "on": "related"}],
  "verify_subject": null, "verify_object": null, "verify_relation": null
}
```

- **守门**：target/related/relation_path/filters 的每个 local 名必须存在于本体（白名单），属性过 domain 校验，路径过逐跳闭包校验；任一不过 → 该字段丢弃（记 notes）或整体回退确定性规则；LLM 未给 relation_path 时由 `OntologyContext.find_relation_path` 沿关系图发现并按问题相关性选路。
- **filters 的落点语义（v0.5 新增）**：属性属于谁就落在谁上——`"on": "related"` 表示过滤沿 relation_path 落在终点类（如 investmentFocus 属于 FundInvestmentStrategy，"医药基金"的过滤落在策略上而非基金上）；缺省落在 target。
- resolution 三态不变：

```
resolution_status
  RESOLVED     ← 语义解析成立（LLM 过守门 或 确定性规则命中）
  AMBIGUOUS    ← 多个解释均成立 → 用户澄清 / 二次 LLM 确认（绝不自动择优）
  UNRESOLVED   ← 没有解释成立 → 说明原因并终止
```

- **禁止** `score 最高 → 自动选` 的原则不变；confidence 仅用于候选展示；实测指标是 Semantic Accuracy。compare/对比类问题在 LLM 之前由关键词守卫直接拒答（Phase 2 边界）。

## 2. 模块树（v0.5 实际形态）

```
fondontology/
├── qa/
│   ├── index.py           # Ontology Index（索引仓库）
│   ├── resolver.py        # Vocabulary Resolver（string → candidates）
│   ├── validator.py       # Whitelist Validator（candidate → valid/invalid）
│   ├── semantics.py       # OntologyContext（v0.5 新增：query-time 世界模型）
│   ├── intent.py          # LLM 语义解构：NL → SemanticParse（语义视图注入 +
│   │                      #   白名单守门 + 确定性兜底：聚合/排名/锚点/verify 句型）
│   ├── query_planner.py   # SemanticParse → Query Plan（约束感知：逐跳 domain/range）
│   ├── sparql_builder.py  # Query Plan → SPARQL（纯函数；GROUP BY/HAVING/Top-N）
│   ├── graph.py           # TBOX/ABOX/闭包分层装载 + GraphSnapshot
│   ├── abox_query.py      # 实例检索 + 聚合度量 + 局部子图（explicit/inferred 区分）
│   ├── evidence.py        # Evidence Builder + Claim-Evidence Map + citation 校验
│   ├── context.py         # Ontology Slice Policy + 硬上限 + Local Context 组装
│   ├── explainer.py       # LLM 表达（只能引用批准的 claims；流式调用）
│   ├── enforce.py         # Stage ② 语义控制层 + import_records 批量导入生产路径
│   ├── lexicon.py         # NL 归一化（“国内”→CN，确定性）
│   └── templates.py       # 模板回退
├── tbox/
│   ├── taxonomy.py        # subClassOf 闭包（v0.5 修复 ancestors/descendants 互换 bug）
│   ├── constraints.py     # domain/range/restriction/disjoint 查询
│   └── inference.py       # 定向物化推理（property chain + 逆关系传播）
tools/
├── qa_bench.py            # 分阶段 benchmark 跑批（verify/find/e2e/intent/intent-real/citation）
├── qa_cli.py              # 单问 / REPL / --detail 溯源
└── gen_sim_abox.py        # 仿真数据生成（唯一性守卫；--sqlite 可选导出）
```

(v0.4 设想的 `qa/compiler.py` 未单独落地，职责由 semantics.py + query_planner 分担，见 §1；`tbox/paths.py` 的可走路径规划由 OntologyContext.find_relation_path 承担)

## 3. 图分层与 Phase 1 推理执行策略（不做"看似按需"的增量推理）

分层不变：`TBOX / TBOX_INFERRED / ABOX / ABOX_INFERRED`，三元组带来源标记 `tbox|tbox_inferred|abox|abox_inferred`，`GraphSnapshot` 记录本体与数据版本/hash、推理档位。

**Phase 1 明确不做增量/查询局部推理**（评审点六）：模拟数据量小，启动时一次性物化：

```
启动时（一次性）：
  TBOX_INFERRED = owlrl(TBOX, OWLRL_Semantics)                    # schema 闭包
  ABOX_INFERRED = owlrl(ABOX ∪ TBOX_INFERRED, OWLRL_Semantics)    # 实例闭包（含 property chain 物化）
  INFERRED_REGISTRY = {triple: rule_name}                          # 记录“哪条规则推出的”
```

- **推理产物可用性**：`inferred = closure − explicit`（集合差）天然给出"哪些是推出的"，Evidence Builder 据此标 `kind=inference` + `rule`；
- 代价可控（3.5 万净值记录级别的闭包在 rdflib 内存可完成，启动一次）；
- incremental reasoning / query-local inference / materialized views 全部延后到数据规模真正需要的阶段，不在 Phase 1 挖坑。

## 4. 推理边界：Inference Rule ≠ Query Path（评审点五）

- **Inference Rule（tbox/inference.py）**：`hasFundManagerRole ∘ rolePlayedBy → hasFundManager`——"能推出**新事实**"，产物落入 ABOX_INFERRED（v0.5 实际为**定向物化**：property chain + 逆关系传播，产物可经 `stack.inference_registry` 归因；全量 OWL-RL 闭包按 §3 仍延后）；
- **Query Path（qa/semantics.py + qa/query_planner.py）**：用户问"基金A的管理人是谁"，直接规划路径 `Fund →[hasFundManagerRole] Role →[rolePlayedBy] Person`，**不物化新事实**，边走边查询（v0.5：路径由 `OntologyContext.find_relation_path` 闭包感知发现，替代 v0.4 设想的 tbox/paths.py）；
- 两者**共享** `propertyChainAxiom` 信息但执行动作不同：前者把链写进推理闭包，后者把链展开成 Query Plan 的 `traversals`；
- 边界规则：Phase 1 的 find 默认走 **Query Path**（少物化、证据更直观）；verify/一致性类走 Inference 产物。二者在证据里分标 `kind: "query_path"` / `kind: "inference", rule: …`。

同时保留 v0.2 的四层边界：① Taxonomy（SPARQL 路径）② Schema（domain/range/restriction）③ Instance（owlrl）④ Consistency/validation（pyshacl，独立于问答热路径）。owlrl 管"能推出什么"，SHACL 管"数据违不违规"，互不混用。

## 5. verify：三态 + 请求状态（ENTAILED / CONTRADICTED / UNKNOWN / INVALID_REQUEST）

v0.2 的布尔 true/false 改为三态——"false" 可能意味着"本体没证明它为真"而非"本体证明它为假"，Ontology QA 最怕混淆这两者。

**补充（P1，评审点十七-③）**：再增加 **INVALID_REQUEST** —— 它不是 verify 的逻辑结果，而是**输入语义错误**（subject/object 不是本体中的合法 IRI/词、relation 不在白名单）。统计时 UNKNOWN（本体不知道）与 INVALID_REQUEST（请求本身非法）必须分开。

```json
// 请求（同 v0.3 通用谓词）
{ "operation": "verify", "subject": "…/ExchangeTradedFund",
  "relation": "subClassOf", "object": "…/OpenEndedFund" }
```

```json
// 响应（四状态；INVALID_REQUEST 时返回 reason，不产生逻辑结论）
{
  "answer": "ENTAILED",        // ENTAILED | CONTRADICTED | UNKNOWN | INVALID_REQUEST
  "basis": "taxonomy",         // taxonomy | constraints | instance
  "chain": [ {"subject": "…", "predicate": "rdfs:subClassOf", "object": "…"} ],
  "evidence_ids": ["E1", "E2"],
  "note": null,                 // 如 disjoint 场景附"一致性提示"
  "reason": null                // INVALID_REQUEST 的具体原因（不可解析/谓词非法/空参数）
}
```

- `subClassOf/subPropertyOf/equivalentClass` → taxonomy 判链：`ENTAILED`（正链）/ `CONTRADICTED`（存在互斥证据，如 subject 与 object 互为 disjoint 却问子类关系）/ `UNKNOWN`（无链）；
- `disjointWith` → 声明存在则 `ENTAILED`（声明成立）+ `note`（一致性提示：若 ABOX 出现共指实例需走 ④）；声明不存在但判出子类链 → `CONTRADICTED`；否则 `UNKNOWN`；
- `domainOf/rangeOf` → constraints 查询；
- subject/object 无法解析为合法本体 IRI、关系不在白名单 → **`INVALID_REQUEST`**，与"本体不知道"严格区分；
- 四状态从 M1 就实现，后续 compare/contrast 直接复用。

## 6. find：类型闭包 + 显式/隐式类型证据（同 v0.2，§6 保留）

- 标准查询：`?f rdf:type/rdfs:subClassOf* cnfo:ExchangeTradedFund .`
- 证据区分 declared / inference（规则名 + 源三元组），两种可信度展示。

## 7. 证据合同 v3：Claim-Evidence Map + 后端引用校验（评审点八、九）

**Claim 定义（正式）**：Claim = 一条**可被事实验证的陈述**（可对应对应证据 ID 的断言），不包括表达性语言成分（如"其中包括"）。

```json
{
  "meta": { "ontology": {"iri": "…", "version": "0.5.3", "hash": "sha256:…"},
            "abox": {"file": "cnfo-sim-abox.ttl", "hash": "sha256:…"},
            "reasoning": {"profile": "OWL-RL", "inference_enabled": true,
                          "query_graph": "TBOX_INFERRED + ABOX + ABOX_INFERRED"} },
  "intent": { … }, "query_plan": { … },
  "evidence": [
    {"id": "E1", "kind": "declared", "source": ["cnfo-a:F051143", "rdf:type", "cnfo:ExchangeTradedFund"]},
    {"id": "E2", "kind": "inference", "rule": "rdfs:subClassOf", "source": ["…IndexFund", "rdfs:subClassOf", "…Fund"]},
    {"id": "E3", "kind": "query", "sparql": "SELECT …", "row_count": 4, "rows": […]},
    {"id": "E4", "kind": "derived", "rule": "property_chain:hasFundManagerRole∘rolePlayedBy",
     "premises": ["E5", "E6"], "source": ["cnfo-a:F001113", "…/hasFundManager", "cnfo-a:Party9"]}
  ],
  "claims": [
    {"claim_id": "C1", "type": "count", "claim": "国内交易型开放式指数基金共有 4 只",
     "evidence": ["E3"]},
    {"claim_id": "C2", "type": "classification", "claim": "交易型开放式指数基金是开放式基金的子类",
     "evidence": ["E1", "E2"]}
  ],
  "subgraph": {…}, "unresolved": []
}
```

执行规则：
1. **Claim-Evidence Map 由 Evidence Builder 生成**（后端），不是 LLM；
2. **Evidence provenance chain（P1）**：证据不只标"是推出来的"，还记录**由什么推出**——`premises`（前提证据 ID 列表）与 `derived`（由本规则产出的证据 ID），使证据形成图结构 `Claim → Evidence → Derived Evidence → Premises → Ontology Rule`，而非扁平的 `Claim → E#`（这对"某个间接事实为什么成立"的复核至关重要）；
3. **Claim 增加类型槽位**：`type: fact | count | comparison | classification | inference | definition`，分别可验证，为 M7 的 compare/aggregate 铺路；
4. **citation validation（后端闸门）**：explainer 输出后逐条校验引用 ∈ claims 集合；引用不存在 → 拒绝输出并要求重写；
5. 自动化评测直接比对 `{claim, evidence}` 结构，不必解析自然语言里的 `[E#]` 符号。

## 8. Entity Resolver：结果契约与防碰撞（评审点十一）

Phase 1 解析顺序与结果契约：

```json
{ "candidate": "https://ontology.example.cn/cnfo/abox/F510050",
  "match_type": "normalized_name",     // exact | alias | label | code | normalized_name
  "matched_text": "华夏上证50ETF",
  "score": 0.91,
  "collision": false }
```

- **规范化防碰撞**：名称归一化只做**受控规则**（去"证券投资基金"尾缀、全角→半角、大小写），绝不随意截断；`A证券投资基金 / A证券投资基金C / A证券投资基金联接A / A证券投资基金ETF` 这类家族名，归一化后不得合并，候选逐个返回；
- `collision: true` 或多个高分候选 → **进入消歧协议**（回问用户/交 LLM 二次选择），**禁止 normalize 后强行取第一名**；
- Phase 2 才在 benchmark 证明 exact+alias+code 不足时引入 BM25，最后才考虑 embedding/Qdrant（见 §13 ③）。

## 9. Lexicon Resolver（同 v0.2 §9，保留）

"国内→CN""最新→max""R4 以上→≥R4"等 NL 归一化全部确定性规则化；结果过白名单才进计划。

## 10. Semantic Query IR（Query Plan 正式中间表示）——M3 末架构冻结（评审点四、十二）

```jsonc
// Query Plan v1.0（示例：找出基金 A 的基金经理管理的其他 ETF）
{
  "plan_version": "1.0",
  "kind": "find",                          // find | verify | aggregate | compare
  "target": {
    "concept": "…/ExchangeTradedFund",     // 语义目标（已过白名单与语义校验）
    "type_constraints": [{"closure": "rdfs:subClassOf*"}]
  },
  "source": {"entity": "…/abox/F001113"},  // 显式锚点实体（可能为空）
  "exclusions": [                          // P1：语义显式排除（“其他基金/除 A 外/不包括”）
    {"entity": "…/abox/F001113", "rationale": "提问中的“其他”"}
  ],
  "filters": [
    {"property": "…/jurisdictionCode", "operator": "eq", "value": "CN",
     "lexicon_source": "国内"}
  ],
  "traversals": [                          // 查询路径（§4 Query Path）
    {"from": {"type": "…/Fund"}, "property": "…/hasFundManagerRole",
     "to": {"type": "…/FundManagerRole"}, "inverse": false},
    {"from": {"type": "…/FundManagerRole"}, "property": "…/rolePlayedBy",
     "to": {"type": "…/FundParty"}, "inverse": false}
  ],
  "projections": ["fundCode", "fundName"],
  "aggregations": [                      // v0.5 已落地：COUNT + GROUP BY/HAVING
    {"func": "count", "over": "…/Fund",  // 沿 related_class + relation_path 聚合
     "having": {"operator": ">=", "value": 2}}
  ],
  "ordering": [{"by": "agg", "direction": "desc"}],   // Top-N 排名已落地
  "pagination": {"limit": 50, "offset": 0},
  "inference_policy": {"materialize": false, "path_based": true},
  "evidence_policy": {"include_sources": true, "include_query": true}
}
```

- **字段全集**：`target / source / exclusions / type_constraints / filters / traversals / projections / aggregations / ordering / pagination / inference_policy / evidence_policy`；
- **filters 落点（v0.5 新增）**：`filters[].on: "related"` 表示该过滤沿 relation_path 落在终点类上（"属性属于谁，过滤落谁上"），planner 的 domain 校验相应对准路径终点类；`operator: contains` 用于字符串包含匹配；
- **聚合（v0.5 已落地）**：`aggregations[].func: "count"` 已实现（"同时管理多个基金的基金经理"→ COUNT(基金)>=2；GROUP BY target、HAVING 阈值、按聚合值 ORDER BY + LIMIT 做 Top-N）；SUM/AVG/MAX/MIN 预留未实现（需先定度量属性建模）；
- **exclusions / 语义表达式（P1，评审点十七-⑤）**：`exclusions` 显式表达"其他/除外/不包括/除了"（详见上面的 `exclusions` 槽位），禁止这些语义偷偷落到 SPARQL Builder 的隐式 `FILTER (?x != …)`；更复杂的两侧比较（"A 与 B 的差异"）用 `filters[].expression` 两层结构扩展（`operator: neq/gt/lt/between/in` + `left/right ref`）；
- `traversals` 使"基金A的基金经理管理的其他ETF"这类多段链成为一等公民；
- **SPARQL Builder 契约**：`QueryPlan(JSON) → SPARQL` 纯函数；每个算子（type closure、filter、traversal、projection、aggregation、ordering、pagination）有独立单测；
- **冻结点**：M3 结束时冻结 Query Plan v1.0 schema（`artifacts/qa/query_plan.schema.json` + 版本号）。冻结后：LLM 可换、SPARQL 可换、后端可换，`Intent → QueryPlan` 契约不变。

## 11. Ontology Slice Policy：保留分级 + 硬上限（评审点十）

分级沿用 v0.2（L0–L4，语义闭合原则）。新增**硬上限**（默认值，config 可调）：

```
max_classes       = 32
max_properties    = 64
max_triples       = 2_000
max_context_tokens ≈ 6_000   （按模型估算）

Slice expansion overflow
   ↓
后端照常执行完整查询（Query Plan 不变）
   ↓
LLM context 只取 L2 截断切片 + 证据摘要
   ↓
上下文不足时：答案标注“简答”，前端展开后端证据查看
```

原则：**后端可以处理大图，LLM context 不应成为系统瓶颈**；L4 不无限扩大，溢出即截断并显式标记。

**P2 概念预留（评审点十七-⑥）**：截断不是"随便砍掉后面的"，而是**语义优先级选择**——按 `required concepts → required properties → required constraints → optional neighborhood` 的顺序做取舍（本质是一个带预算的切片优化问题）。本版不实现，切片器接口保留 `prioritize(plan, budget)` 槽位。

## 12. 里程碑（评审点十五修订：M1–M4 全部是确定性语义链，M4 才接入 LLM）

| 阶段 | 内容 | 验收/基准 |
|---|---|---|
| **M0** | v0.4 冻结 | 上述 6 点修订闭合 |
| **M1** | `tbox/`（taxonomy/constraints/inference）+ `qa/verify.py`（四状态）+ **verify benchmark**：只做 TBox 语义，不碰 ABox | 30–50 条 CQ（subClassOf/equivalentClass/disjointWith/subPropertyOf/domainOf/rangeOf + 非法请求），语义正确率 100% |
| **M2** | `graph.py` 分层装载 + `query_planner`（手写 Query Plan，无 LLM）+ `sparql_builder` + `abox_query` | **find benchmark**：手写 Query Plan → SPARQL → 正确结果；explicit/inferred 证据可区分 |
| **M3** | `evidence.py`（Claim-Evidence Map + provenance chain + citation 校验）+ `context.py`（切片+上限）；**确定性端到端**：手工 Intent → QueryPlan → SPARQL → Evidence → 模板回退，**无 LLM 也能完整工作** | 证据完整度 100%、SPARQL 全通过率 100%；**===== 架构冻结点：Query Plan v1.0 冻结 =====** |
| **M4** | `intent.py`（LLM Candidate Selection 协议 + resolution 三态）+ `resolver|validator|lexicon` | **intent benchmark**：Semantic Accuracy 主指标、resolution 分布（RESOLVED/AMBIGUOUS/UNRESOLVED） |
| **M5** | `explainer.py`（引用受校验的 claims） | **citation benchmark**：Unsupported Claim Rate=0；引用全部 ∈ claims |
| **M6** | Viewer 侧边 tab UI + `/api/qa/ask` | 端到端走查 + 全套回归 |
| **M7（Phase 2，按证据决定）** | 先 BM25（仅当 benchmark 证明 exact/alias/code 不足）→ 再评估 embedding/Qdrant；compare/aggregate | 消歧提升报告 |

**实验框架（评审点十六）**：本项目有一条清晰可测的学术/工程主线——在"无 LLM"下 M1–M3 是一个**完整的 Ontology Semantic Engine**；M4–M5 把 `Natural Language → Intent` 接上 LLM。最终分别 benchmark：LLM Intent Accuracy / Semantic Accuracy / Query Accuracy / Evidence Completeness / Unsupported Claim Rate。无 key 模式与有 key 模式共享同一套确定性引擎，差异只在 `NL → Intent` 一步。

**落地状态**：M1 ✅（verify 四状态，72 CQ 100%，三方独立交叉验证一致；`tests/test_qa_verify.py` + `tests/test_tbox_inference.py`）｜M2 ✅（分层图 + QueryPlan→SPARQL→ABOX 检索 + explicit/inferred 类型证据 + 局部子图，16 find CQ 100%；`tests/test_qa_find.py`；ABOX 物化闭包按 §3 延后）｜**M3 ✅**：Evidence Builder（Claim-Evidence Map + premises/derived provenance + 引用校验闸门）+ Ontology Slice（预算/截断）+ 确定性端到端引擎（手工 Intent→QueryPlan→SPARQL→证据→模板，12 条 e2e CQ 100%）；**架构冻结点已执行：`artifacts/qa/query_plan.schema.json`（v1.0）落盘**｜**M4 ✅（本版）**：Ontology Index / Vocabulary Resolver（含实体代码与受控归一化+碰撞标记）/ Whitelist Validator / Lexicon Resolver（"R4以上/国内"确定性归一化）/ LLM 意图解构（局部候选 schema + Candidate Selection + `resolution_status` 三态；无 key 确定性路径兜底，有 key 时 LLM 输出须过白名单）——intent benchmark 14 CQ 100%，Semantic Accuracy 10/10=100%，resolution 分布 RESOLVED 10/AMBIGUOUS 1/UNRESOLVED 3；核验：与独立最长标签实现三方比对 0 不一致，空问题→INVALID 修正；`tests/test_qa_intent.py`（14 用例）｜**M5 ✅（本版）**：`qa/explainer.py`（LLM 逐句 claim_id 结构化表达 + citation 闸门：越权→带反馈重试→模板回退，`violations_before_gate` 留指纹、终态 UCR=0）+ `engine.answer_question()`（NL 全链路入口，索引缓存）+ `tools/qa_cli.py`（单问/REPL/--detail 溯源）——citation benchmark 10 CQ 100%，经闸门后最大 UCR=0，引用全部 ∈ claims；gate 分布统计与闸前越权数在 LLM 配置时透明报告；`tests/test_qa_explainer.py`（9 用例，含闸门回退行为 mock 验证）｜**数据缺陷修复（基金经理锚点）**：排查确认仿真 A-BOX 中基金经自然人节点原为孤立节点（仅 type+label，40/40 零业务边）——根因是生成器未建 `playsFundRole` 边；现生成器为每位基金经理补边 `(person, playsFundRole, FundManagerRole)`（与 rolePlayedBy 互逆，不违反 hasFundManagerRole maxCount=1），系统锚点链注册表扩展 `FundManagerPerson → [playsFundRole, roleInFund]`，"魏辉的基金有什么？"现可答（磐石货币货币市场基金）；intent benchmark 16/16（I016 由 UNRESOLVED 改为 RESOLVED）、e2e 13/13（E013 source 锚点）、citation 11/11（C11）

**v0.5 重构落地（2026-09-04 ~ 09-07，"框架过度设计、核心没搭起来"专项重构）**：
- **意图层重写（M4'）**：`qa/semantics.py` OntologyContext 落地（类层级/类间关系图/数据属性 domain-range；`render_for_llm()` 语义视图注入 prompt ≈1.7 万字符；`find_relation_path` 闭包感知 BFS + 问题相关性选路）；intent.py 改为 SemanticParse 协议（§1），LLM 为主、白名单+domain/range 守门、确定性规则兜底（聚合"多个/最多/前N/多少"句型）；compare 守卫前移至 LLM 之前；
- **聚合/排名查询落地**：QueryPlan `aggregations` 由空壳变为真实实现（COUNT + GROUP BY/HAVING + ORDER BY agg + LIMIT），"同时管理多个基金的基金经理有什么？"端到端可答（10 位经理在管 ≥2 只）；filters 支持 `"on": "related"` 落点语义 + `contains` 算子（"医药基金"→ investmentFocus 沿 usesInvestmentStrategy 落在策略类）；
- **Stage ② 生产路径**：`enforce.import_records()` 批量导入 API；**唯一性约束两层补齐**——enforce ①b 检查（fundCode=合并键/fundName=全库唯一，批内重复经逐条合并天然拦截）+ SHACL 两条跨节点唯一性 SPARQL 约束（fundCode/fundName）；
- **LLM 调用全流式化**：共享入口 `_stream_chat_content`（intent/explainer 共用）——非流式下服务端生成完成前不下发字节，复杂问题长推理（实测 145s）必然读超时，流式首字节数秒即达；失败原因（超时/限流/HTTP）透传 notes，不再静默吞掉；
- **数据层修复**：仿真生成器唯一性守卫（基金名全库唯一，13 对重名清零）+ 货币基金池 1→3 + 一人多管（10 位经理各管 2 只，支撑聚合问法）+ 生物医药主题确定性覆盖（行业主题问法数据可达）；魏辉/005377 锚点稳定；
- **顺带修复**：`tbox/taxonomy.py` ancestors/descendants 实现互换 bug（导致本体切片一直显示子类而非祖先）；explainer 限流/超时击穿链路 → 优雅回退；6 个构建期脚手架归档 `archive/tools/`；`cnfo-sim.sqlite` 改 `--sqlite` 可选产出；
- **基准（全部 100%）**：verify 72/72、find 16/16、e2e 13/13、intent 16/16、**intent-real 10/10**（真实口语问法，R02/R03/R09 修复后全通）、citation 11/11（UCR=0）；`tests/test_qa_aggregate.py`（21 用例：确定性意图/规划约束/端到端/mock LLM 解析/related 过滤）。

**v0.6 锚点本体驱动化与延时治理（2026-09-07，"恒信货币基金经理"问法暴露的两个问题）**：
- **锚点解析本体驱动**：`_resolve_anchor_query()` 取代"实体类型→硬编码链"门禁——锚点类型的祖先闭包天然继承父类关系边（MoneyMarketFund ⊂ Fund 继承 hasFundManager），`find_relation_path` BFS 即可成链，**任何实体类型**（基金/公司/份额）都能作为锚点；**具体实体提及优先于类候选猜测**（实体标签/代码是精确命中，"恒信货币货币市场基金的基金经理是谁"中"货币市场基金"不再误中 MoneyMarketFund 类）；基金锚点两种新句型落地："X 的基金经理是谁"（target=FundManagerPerson，1 跳）、"他还管别的基金吗"（target=Fund，经 pivot 折返 2 跳 + `exclusions=[锚点]` 自排除）；
- **语义偏好链**：同一对端点多条合法路径时 BFS 不保证语义贴合（Investor→Fund 的"持仓 3 跳" vs "风险等级匹配 2 跳"），已知类型（Investor/FundManagerPerson）固定选 `_ANCHOR_PATHS` 偏好链，BFS 只服务未覆盖类型；
- **跳终点类约束**：traversals 新增 `to` 槽位（planner 解析校验、builder 渲染类型闭包 pattern、evidence 层过滤同步）——"他还管哪些"的 pivot 收窄到 FundManagerPerson，避免 hasFundManager 的 FundParty range 把管理公司混入；
- **pivot claim（证据合同扩展）**：多跳锚点链的中间节点（基金经理）不在结果集中，Evidence Builder 沿见证路径逐跳归因（物化边→inference 证据含 premises，显式边→declared 证据，按 fact 去重），并为 pivot 显式生成 claim——否则表达层（只消费 claims）拿不到"基金经理是谁"这半个答案；
- **锚点快路径（延时治理①）**：实体锚点确定性成链时跳过 LLM 意图调用（verify 标记/聚合触发词命中除外）——锚点识别本身是高精度信号（标签/代码精确子串命中），原路径每个锚点问题白付一次分钟级 LLM 调用；
- **LLM 关闭深度思考（延时治理②）**：`LLM_THINKING=false`（默认）→ 请求体并 `thinking={"type":"disabled"}`（Ark/DeepSeek；`LLM_THINKING_PARAM=qwen` 切 `enable_thinking=false`）——意图解析/表达是结构化任务，thinking 把秒级响应拖成分钟级；热路径 LLM 问答 2min+ → 7~9s；
- **查询图缓存（延时治理③）**：`query_graph(with_abox_inferred=True)` 的 50 万+ 三元组合并图按栈缓存（原每次查询重建 ~8s），`merge_into_stack` 同步失效；SPARQL 锚点模式跳链先于类型闭包 pattern（rdflib 无代价重排，模式顺序即求值顺序）——热路径确定性问答 19.5s → **0.3s**；
- **锚点识别精度**：同码多实体（基金与其份额代码相同）时偏好 rdf:type 含 Fund 的本体（"基金001113"指基金，不是它的 FundUnit）。

## 13. 指标：Unsupported Claim Rate 的形式化（评审点八）

- **Semantic Accuracy**：Intent.target_class 是否**确实是**问题对应的本体类（legal ≠ correct）；
- **Evidence Completeness**：`claims[]` 中每条 claim 都有非空 `evidence`，且全部 evidence id 存在于 `evidence[]`；
- **Unsupported Claim Rate**：`|LLM 输出中无对应 claim 的陈述| / |陈述总数|`，其中 **Claim = 可事实验证的陈述**（不含表达成分），评测对接 JSON 结构而非解析 `[E#]` 文本；目标 = 0；
- verify 准确率（三态对照）、find 非空率/top-k 精确率、解构成功率、Sparql builder 全通过率、人工抽检（每周走查）同 v0.2。

## 14. 待办与开放问题

1. **Qdrant 明确延后**（评审点十三）：Phase 1 的 Entity Resolver 用 exact/alias/label/code/受控归一化；只有 benchmark 证明不够再引入 BM25；embedding/Qdrant 最后评估——避免在 ontology/query planning 验证前堆 RAG 基建。
2. 一致性语义只出"声明 + 提示"，不做自动断言（HermiT 交叉认证另立任务）；
3. SHACL 校验独立于问答热路径（构建期报告，复用 `tools/gen_sim_abox.py` 内置校验）；**已知脆弱性**：shapes 文件所有 `sh:select` 的前缀解析依赖数据图命名空间绑定（生产 A-BOX 绑了 cnfo/cnfc 故正常），规范做法是为每条 SPARQL 约束加 `sh:prefixes` 声明，待加固；
4. `.env`：`OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL`（OpenAI 兼容）；`LLM_THINKING`（默认 false，关闭推理模型深度思考）/`LLM_THINKING_PARAM`（默认 auto=Ark 形态）；`QDRANT_URL/KEY` 预留但默认不读；
5. 无 key 模式：M1–M3 全可用；M4–M5 退化为模板回退，benchmark 照跑（指标=覆盖率）；
6. **语义视图规模化路线（v0.5 新增）**：当前 `render_for_llm()` 全量注入 T-BOX（143 类 ≈1.7 万字符），实例数据（A-BOX）永不进 prompt——瓶颈是**本体规模**而非数据规模。演进路径：① 查询范围裁剪（resolver 确定性粗选候选类 → 只渲染 k 跳邻域，失败回退全量重试；不做 LLM 多轮粗选——省 input token 但延迟/推理 token 翻倍、错误复合）；② 静态前缀缓存（视图按本体版本不变，prompt 静态段在前）；③ 本体到 FIBO 量级后评估 ontology-as-tools（function calling 按需查邻域）；
7. **Phase 2 查询能力**：compare/对比（现关键词守卫直接拒答）；SUM/AVG/MAX/MIN 聚合（需度量属性建模）；规模（AUM）时间序列与基金经理变更建模（R02 类问题当前数据层不可答——本体无规模时点记录、仿真数据无任期变更历史，另立任务）。

---

## 附：v0.4 → v0.5 差异索引（重构回填）

| # | 重构点 | v0.5 修订 |
|---|---|---|
| 1 | 意图层核心化 | §0/§1：LLM Candidate Selection → **SemanticParse 协议**（语义视图注入 + 白名单/domain-range 守门 + 确定性兜底）；新增 `qa/semantics.py` OntologyContext 承担 query-time 世界模型；v0.4 的 compiler.py 不单独落地 |
| 2 | 聚合/排名落地 | §10：`aggregations` 空壳 → COUNT+GROUP BY/HAVING/Top-N 真实实现；filters 新增 `"on": "related"` 落点语义与 `contains` 算子 |
| 3 | Stage ② 生产化 | §0.5：`enforce.import_records()` 批量导入路径；唯一性约束（fundCode 合并键 / fundName 全库唯一） |
| 4 | SHACL 跨节点唯一性 | §14-3：FundShape 新增 fundCode/fundName 全库唯一 SPARQL 约束（SHACL Core 无此原语）；前缀解析脆弱性记录在案 |
| 5 | LLM 调用流式化 | intent/explainer 共用 `_stream_chat_content`；复杂问题长推理（145s）不再读超时；失败原因透传 notes |
| 6 | 数据质量 | 生成器唯一性守卫（13 对重名清零）；一人多管；生物医药主题覆盖；taxonomy.py ancestors/descendants 互换 bug 修复 |
| 7 | 瘦身 | 6 个构建期脚手架归档 archive/tools/；cnfo-sim.sqlite 改 `--sqlite` 可选产出；qa/__init__ 惰性导入 |
| 8 | 规模化路线 | §14-6：语义视图查询范围裁剪（确定性粗选，非 LLM 多轮）→ 前缀缓存 → ontology-as-tools（FIBO 量级后） |

## 附：v0.3 → v0.4 差异索引（第三轮评审 6 点 + 补充）

| # | 优先级 | 评审点 | v0.4 修订 |
|---|---|---|---|
| 1 | P0 | Compiler/Query Planner 再切分 | §1 Compiler 只出 Semantic Specification（concept/type_closure/allowed_properties/constraints/available_paths）；Query Planner = Intent + Specification → QueryPlan；五层职责闭合 |
| 2 | P0 | Resolution 必须允许 AMBIGUOUS | §1 `resolution_status: RESOLVED/AMBIGUOUS/UNRESOLVED`；唯一解释成立才 RESOLVED；禁 score 择优（那是启发式猜测） |
| 3 | P1 | verify 增加 INVALID_REQUEST | §5 四状态 ENTAILED/CONTRADICTED/UNKNOWN/INVALID_REQUEST；UNKNOWN（本体不知道）与 INVALID（请求非法）分开统计 |
| 4 | P1 | Evidence provenance chain | §7 证据增加 `premises`（由什么推出）与 `derived`；证据成图结构 Claim→Evidence→Premises→Rule，而非扁平 Claim→E# |
| 5 | P1 | QueryPlan exclusion/语义表达式 | §10 增加 `exclusions` 槽位（"其他/除外/不包括"显式化）+ `filters[].expression` 两层结构（neq/gt/lt/between/in）；禁止语义偷跑到 Builder |
| 6 | P2 | Slice 语义优先级 | §11 截断 = 带预算的语义优先级选择（required concepts→properties→constraints→optional），接口预留 `prioritize(plan, budget)` |
| 7 | — | Claim 类型槽位 | §7 `claims[].type: fact|count|comparison|classification|inference|definition` |
| 8 | — | 里程碑重排 | §12 M1 只做 TBox verify；M2 手写 QueryPlan→SPARQL find；M3 证据/切片 + 确定性端到端（无 LLM 完整工作）；M4 才接 LLM；实验框架（无 key 也是完整 Semantic Engine）显式化 |

## 附：v0.2 → v0.3 差异索引

| # | 评审点 | v0.3 修订 |
|---|---|---|
| 1 | 二（Compiler 确定性） | §1 Candidate Selection 协议：Intent 带 target_concept + 候选集 + resolution；confidence 不参与判定；§10 ⑥ Semantic Validation |
| 2 | 三（Resolver 重复） | §1 词汇四件套 Index≠Resolver≠Validator≠Compiler，四个独立模块，越权拒绝合并 |
| 3 | 四（Query Plan IR） | §10 Semantic Query IR v1.0：字段全集 + traversals + aggregations 槽位；M3 末冻结 |
| 4 | 五（propertyChain 二分） | §4 Inference Rule（物化新事实）≠ Query Path（布路查询）；新增 tbox/paths.py |
| 5 | 六（按需推理风险） | §3 Phase 1 全量启动物化 + inferred=closure−explicit；增量/局部推理延后 |
| 6 | 七（verify 三态） | §5 ENTAILED/CONTRADICTED/UNKNOWN + basis + note |
| 7 | 八（Claim 定义） | §7/§13 Claim=可验证陈述；评测对接 JSON 结构 |
| 8 | 九（引用不可自造） | §7 Claim-Evidence Map 后端生成 + citation validation 闸门 |
| 9 | 十（L4 膨胀） | §11 硬上限（类/属性/三元组/token）+ overflow 截断策略 |
| 10 | 十一（归一化碰撞） | §8 Entity Resolver 结果契约（match_type/score/collision）+ 消歧协议，禁强取第一 |
| 11 | 十二（冻结点） | §12 M3 末冻结 Query Plan v1.0 |
| 12 | 十三（Qdrant 延后） | §14 ① BM25→embedding 按 benchmark 证据分步引入 |