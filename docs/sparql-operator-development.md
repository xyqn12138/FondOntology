# CNFO SPARQL 算子开发文档

版本：v1.2
日期：2026-09-28
状态：P1-P3 开发完成，进入回归审核

## 1. 目标

SPARQL 层不按自然语言问法堆叠模板，而采用：

```text
SemanticParse -> QueryPlan -> GraphQueryIR -> SPARQL
```

LLM 只产生受约束的语义结构，不生成 SPARQL。完整 T-BOX 负责
domain/range、类层级和属性白名单校验；SPARQL 编译器只接收合法的
QueryPlan/GraphQueryIR。

目标是用有限的通用算子组合覆盖基金问数中的绝大多数场景：

- 按类查询、子类闭包查询；
- 属性过滤和多条件过滤；
- 实体锚点、正向/反向多跳关系；
- 关联对象过滤；
- 计数、分组、HAVING、排名、Top-N；
- 排序、分页、排除；
- EXISTS/NOT EXISTS、时间窗口、最新记录和更复杂聚合的扩展。

## 2. 分层职责

### 2.1 QueryPlan

QueryPlan 是语义层协议，描述用户要查什么。它必须经过 planner
的本体约束校验，不能直接交给字符串模板。

### 2.2 GraphQueryIR

GraphQueryIR 是执行层协议，不表达中文语义，只表达图查询算子：

```text
TypeScan
PathJoin
ValuePattern
Optional
Filter
Aggregate
GroupBy
Having
Order
Slice
Project
```

IR 的好处是算子可以单独测试，同一个 QueryPlan 可以编译成实体列表、
数量统计或聚合查询；变量命名、字面量转义和 DISTINCT 语义集中处理。

### 2.3 SPARQL Compiler

Compiler 只负责把 IR 渲染为合法 SPARQL，并保持变量、类型约束、过滤、
聚合和排序的语义不变。Compiler 不负责猜测属性、选择关系路径或修复
非法计划。

## 3. 第一阶段算子

### 3.1 TypeScan

```sparql
?entity rdf:type/rdfs:subClassOf* <.../Fund> .
```

所有实体类型查询默认使用子类闭包。

### 3.2 PathJoin

正向：

```sparql
?fund <.../usesInvestmentStrategy> ?strategy .
```

反向：

```sparql
?manager ^<.../hasFundManager> ?fund .
```

每一步必须在 planner 阶段通过 domain/range 闭包校验。

### 3.3 Filter 和 ValuePattern

IRI 值使用三元组模式；字符串、数字和列表使用安全过滤：

```sparql
?fund <.../hasFundRiskLevel> <.../FundRiskLevelR4> .
FILTER(?value = 'ETF')
FILTER(CONTAINS(STR(?value), '医药'))
FILTER(?value >= 100)
FILTER(?value IN ('R4', 'R5'))
```

禁止直接使用 Python `repr()` 作为 SPARQL 字面量编码。

### 3.4 Optional

属性投影或排序需要绑定但不应限制结果时使用：

```sparql
OPTIONAL {
  ?entity <.../fundName> ?p0 .
}
```

### 3.5 Aggregate

COUNT + GROUP BY + HAVING 用于关系数量聚合：

```sparql
SELECT ?entity (COUNT(DISTINCT ?fund) AS ?agg)
WHERE { ... }
GROUP BY ?entity
HAVING (COUNT(DISTINCT ?fund) >= 2)
ORDER BY DESC(?agg)
```

数值度量聚合使用 `measure_property`，只允许本体声明为数值类型的数据属性：

```json
{
  "related": "NetAssetValueRecord",
  "relation_path": [{"property": "hasNetAssetValueRecord"}],
  "aggregation": {
    "func": "avg",
    "measure_property": "fundUnitNetAssetValue"
  }
}
```

已支持 `SUM / AVG / MAX / MIN`。`COUNT` 默认对关系终点
`COUNT(DISTINCT ...)`，数值聚合默认保留每条度量值，避免把不同记录
错误去重。聚合函数、度量属性 domain/range 和数值类型均在 planner
阶段校验。

### 3.6 Order 和 Slice

排序属性没有出现在 projection 中时，compiler 自动添加 OPTIONAL 绑定。
实体列表默认使用稳定的结果变量排序。

## 4. 查询模式

### 4.1 Entity Select

```sparql
SELECT DISTINCT ?entity WHERE { ... }
```

### 4.2 Count Select

```sparql
SELECT (COUNT(DISTINCT ?entity) AS ?count) WHERE { ... }
```

### 4.3 Group Aggregate

```sparql
SELECT ?entity (COUNT(DISTINCT ?a1) AS ?agg)
WHERE { ... }
GROUP BY ?entity
HAVING (...)
ORDER BY DESC(?agg)
```

### 4.4 Ask / Verify

T-BOX 的 subclass、equivalent、disjoint 判断继续走现有 verify 实现；
实例级 EXISTS/NOT EXISTS 由 P2 的 `where` 条件树编译。

## 5. 变量和 DISTINCT 规则

```text
?entity       主结果变量
?h1, ?h2      锚点/遍历变量
?a1, ?a2      关联路径变量
?v0, ?v0r     过滤值变量
?p0            projection/order 变量
?agg           聚合别名
```

- 实体列表：`SELECT DISTINCT`；
- 关系聚合：默认 `COUNT(DISTINCT ...)`；
- 明细记录：未来通过 `select=rows` 明确关闭实体去重；
- 排序字段不得改变主结果集合；
- 多跳关系造成的重复必须在查询模式或聚合层显式处理。

## 6. Phase 2：表达式和存在性

P2 使用 `QueryPlan.where` 表达条件树，使用 `QueryPlan.optional` 表达
不会限制主结果的可选路径。

```json
{
  "op": "and",
  "args": [
    {
      "op": "filter",
      "property": "fundTypeCode",
      "operator": "eq",
      "value": "ETF"
    },
    {
      "op": "not_exists",
      "path": [{"property": "hasFundManagerRole"}],
      "target": "FundManagerRole"
    }
  ]
}
```

支持的表达式：

```text
and / or / not
filter
exists / not_exists
```

属性过滤会编译为局部 `EXISTS` 子模式，因此：

```text
A OR B
```

不会因为两个属性三元组被放在主 WHERE 中而错误地变成：

```text
A AND B
```

`optional` 示例：

```json
{
  "optional": [
    {
      "path": [{"property": "fundName"}]
    }
  ]
}
```

P2 条件仍须经过 planner 的属性白名单和 domain/range 校验；非法条件在
计划阶段返回 INVALID，不交给 SPARQL 执行。

### 6.1 Phase 3：时间和高级聚合

#### DateRange

`date_ranges` 对 target 或 relation_path 终点做闭区间过滤：

```json
{
  "date_ranges": [{
    "property": "valuationDate",
    "on": "related",
    "from": "2025-04-01",
    "to": "2025-04-30"
  }]
}
```

日期属性必须是本体声明的 `xsd:date` 或 `xsd:dateTime`，日期值必须是
ISO-8601 格式，并渲染为 typed literal。

#### LatestPerEntity / Subquery

`latest` 当前用于 relation_path 终点记录，按每个 target 实体计算日期
属性的 `MAX`，再回连到该日期的记录：

```json
{
  "latest": {
    "on": "related",
    "date_property": "valuationDate"
  }
}
```

编译结果是分组子查询，不是全局 `ORDER BY ... LIMIT 1`，因此不会把
所有基金错误地压成一条全局最新记录。并列最新日期会保留并列记录。

## 7. 安全和失败策略

- 变量、属性和类不能来自未经 planner 校验的自由文本；
- IRI 统一使用尖括号渲染；
- 字面量统一转义；
- 不支持的操作符返回计划级错误，不静默降级为等值过滤；
- 聚合缺少 relation_path 或度量属性时返回 INVALID；
- 空结果不能自动替换为语义不等价的关系路径。

## 8. 测试矩阵

P1-P3 必须覆盖：

1. TypeScan + 子类闭包；
2. 正向 PathJoin；
3. 反向 PathJoin；
4. IRI、字符串、数值和列表过滤；
5. 中文引号和反斜杠转义；
6. related path 终点过滤；
7. COUNT + GROUP BY + HAVING；
8. 聚合排序和 Top-N；
9. count select；
10. 属性排序自动绑定；
11. 排除和分页；
12. 非法计划拒绝；
13. 现有 find/e2e/citation 全链路回归。
14. SUM/AVG/MAX/MIN 度量属性及数值类型拒绝；
15. 日期范围 typed literal、非法日期拒绝；
16. 每实体 MAX 日期子查询；
17. P2 条件树与 P3 时间条件组合。

## 9. 开发顺序

### Phase 1：IR 基础和兼容迁移

- 新增 `qa/query_ir.py`；
- 现有 plain/aggregate builder 改为 `QueryPlan -> IR -> SPARQL`；
- 增加安全 literal renderer；
- 支持 count select 和排序自动绑定；
- 现有 benchmark 结果保持不变。

### Phase 2：表达式和存在性

- AND/OR/NOT；
- EXISTS/NOT EXISTS；
- OPTIONAL 和 VALUES；
- 复杂过滤的 planner 校验。

### Phase 3：时间和高级聚合（已完成）

- 日期范围；
- 最新记录子查询；
- SUM/AVG/MAX/MIN；
- 每实体最新值和时间窗口聚合。

### Phase 4：意图覆盖与性能优化

- 将稳定的时间/度量问法映射为 `date_ranges`、`latest` 和
  `measure_property`；
- 对大 ABOX 增加查询图裁剪、索引或后端 SPARQL endpoint；
- 增加真实业务问句的计划准确率与执行耗时基准。

每个阶段都必须先更新本文档和 IR 协议，再实现代码和测试。
