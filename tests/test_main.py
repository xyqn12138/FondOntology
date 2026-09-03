from fondontology.qa.graph import build_stack
from fondontology.qa.engine import answer_question
stack = build_stack("ontology/modules/cnfo-domain.ttl", "artifacts/cnfo/abox/cnfo-sim-abox.ttl")
ans = answer_question("魏辉管理的基金有什么？", stack)
print(ans.text)                 # 答案（带 [E#]）
print(ans.explanation)          # {'gate', 'used_llm', 'ucr', 'claims_used'}
print(ans.report)               # 证据合同（meta/evidence/claims/subgraph）