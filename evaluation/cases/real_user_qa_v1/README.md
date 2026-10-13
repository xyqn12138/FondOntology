# 真实用户式QA v1（draft）

检索源固定为 `fund-rag-source-v1-20261013` 的43份正文。
44题包含投资者13题、业务人员18题、系统人员13题；
36题有正向依据，4题需要澄清，4题缺少实时或个人事实。
正向证据覆盖24/43份文档、12题需要跨文档证据；
这不是43份文档全部覆盖测试，也不是实际用户流量统计。
部分估值题是同一知识点的不同角色视角，44题不代表44个独立知识能力样本。

## 输入与评测文件

- `questions.json`：唯一运行输入，每题只有 `id/question/as_of`。
- `oracle.json`：评测专用，参考答案、必要要点、禁止断言、原文范围及源哈希。
- `references.json`：输出产生后按ID合并给Ragas，不进入检索或生成。
- `sources.json`：完整43文档范围注册表，不是单题目标文档白名单。
- `protocol.json`：统一预算、指标、范围和分组协议。
- `domain-review.json`：独立模型逐题审核记录，**不是人工签核**。
- `freeze.json`：绑定源版本、文件哈希及命题输入哈希；修改须另发修订。

## 提问设计

问题模拟任务而不指定法规名称、版本、条号或文档ID，例如：

- “我们一只公募今天换基金经理了，市场部想等下一次季报一起说，免得单独发公告。这样安排可以吗，最晚什么时候要披露？”
- “我那只境内公募的三季度刚结束，现在还没看到季报。一般多久要出来、在哪能看到？如果这只基金成立还不到两个月，是不是可以不出这一期？”
- “我这只基金现在想赎回，最晚几天钱能到账？”

第三题刻意不给产品和订单条件，应澄清而非猜测一个固定期限。
技术题可以提供自然接口场景和字段名，不能用文件版本替系统预选来源。
统一 `as_of=2026-10-13` 是运行日期约束，不证明各文件现行有效。

## 审核与量化

业务/技术命题由 GPT-6.1-sol high 完成，边界控制题由主代理编写，
全部题目由 GPT-6 Astra high 独立模型复核。
所有参考仍是AI草案：`draft`、`independent_human_review=false`。
命题和复核未使用实际RAG输出；开发/挑战分组不是盲测分组。
发布时只进行离线验证，不声称已有新题库的RAG或Ragas成绩。

检索量化以36道可回答题的完整必要证据范围覆盖率为主；
失败保留分母，分别报告用户/业务/系统与跨源表现。
8道控制题单独核验澄清或数据边界行为，不能以检索为空判定成功。
答案要点、无支持断言和Ragas辅助指标独立于检索命中率。
源、问题和预算保持不变后，再比较切片、混合召回或rerank，不能改金标准迎合输出。

```powershell
.venv/Scripts/python.exe -X utf8 tools/build_natural_qa_release.py --validate
.venv/Scripts/python.exe -X utf8 tools/audit_search_scope.py --questions evaluation/cases/real_user_qa_v1/questions.json --registry evaluation/cases/real_user_qa_v1/sources.json --require-unscoped --output artifacts/qa-redesign/input-scope.json
```

后续运行及限制见 `docs/real-user-qa-design-20261013.md`。
旧题库、冻结及历史评分不变；不要把旧指定来源的小范围成绩当作本题库基线。
