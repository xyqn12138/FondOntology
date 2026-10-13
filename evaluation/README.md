# External QA evaluation, version 1

This is a usable P0 protocol/scorer baseline, **not independent business
acceptance**. All checked-in examples are hand-authored `synthetic_contract`
fixtures. They do not prove real-document correctness or user E2E success.
No production output was used to generate gold.

## Source of truth and contract

Versioned JSON arrays or JSONL files referenced by a manifest are the only gold
source. SQLite contains `eval_runs` and `case_results` only; it is not a gold
editor or an alternate expected-answer source. Cases contain provenance,
split/scenario grouping, a dataset snapshot, capabilities, status and explicit
assertions. Manifests explicitly lock `scope` and `allowed_modes`; unsupported
execution modes fail before cases execute. Reviewers must independently ensure the oracle covers every
required question condition. Schema validation alone cannot establish that
business annotations are complete or independent.

`fondontology/evaluation/contracts.py` is the executable standard-library
validator. The portable schema is structural-only: `schemas/*.schema.json`
encode shapes and key if/then constraints, not full validation equivalence.
The CLI and Python API always apply the stronger executable validators; an
external schema check alone is not an execution authorization.
Additional cross-field checks are enforced in Python: unique case/matcher/slot
identities, matching suite/snapshot, at least one eligible case, mandatory
status, result plus evidence for answered cases, explicit empty sets for empty
answers, and separate intent/answer protocols. Unknown fields and matcher
names, duplicate JSON keys, blank questions, nonfinite numbers, malformed dates,
empty gold files and duplicate IDs fail before execution.

Relative `case_files` resolve inside the manifest directory by default, after
symlink resolution. Parent traversal or a symlink escaping that directory is
rejected before reading the case file. A manifest needing an intentionally
external relative file must declare `allow_external_case_files: true`; this
does not permit absolute or drive-rooted paths. The checked-in fixtures use
this explicit opt-in to reference the sibling `cases` directory. This directory
isolation is not a filesystem sandbox; load only trusted manifests, especially
when the external-files opt-in is enabled.

## Matchers

- `status`: exact answer status; answered, empty, clarification, insufficient,
  refused and invalid are distinct. `intent_only` never denotes a business answer.
- `intent_status`: RESOLVED, AMBIGUOUS, UNRESOLVED or INVALID, intent cases only.
- `entity_set`: exact IDs, order-insensitive; duplicate IDs are invalid even
  if they would preserve the apparent count.
- `slots`: exact typed values at explicit object/list paths below `actual.slots`;
  dates use YYYY-MM-DD; units are explicit strings; ordered IDs preserve order;
  numbers never coerce strings/booleans. JSON objects compare their complete
  shape, so list-valued filters can be checked in full rather than by keywords.
  Extra paths outside the declared slots are not scored. Passing slots is not
  complete semantic accuracy: independent reviewers must annotate all required
  constraints. No numeric tolerances or text inference are supported in v1.
- `evidence_groups`: OR over alternatives, AND within each required group;
  each reference matches exact `source_version` and `locator`. Extra references
  are permitted. Chunk IDs are not required.

**Evidence identity is not entailment.** A locator/version match checks only the
independently annotated reference obligation. It does not read the source,
check expiry or determine that the passage semantically supports a claim.
Unsupported-claim/source validity checks require a future reviewed oracle and
document adapter. No UCR or semantic-support metric is reported here.

## Controlled offline commands

Run from the repository root with the project Python environment:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_evaluation_contract.py -v
.venv\Scripts\python.exe tools/evaluate_qa.py --mode replay --manifest evaluation/manifests/synthetic_contract.json --actuals evaluation/examples/synthetic_actuals.json
.venv\Scripts\python.exe tools/evaluate_qa.py --mode rules_intent --manifest evaluation/manifests/synthetic_intent.json --source ontology/modules/cnfo-domain.ttl
```

`replay` only re-scores recorded structured actuals; it never calls the tested
system and is explicitly saved as replay. Actual IDs must exactly match the
manifest. Replay does not verify who generated the recording, whether its
`used_llm` claim is true, or whether a model/system actually executed; summary
labels its origin `recorded_unverified`. Model/prompt metadata `none` describes
this replay invocation, not the recording's historical origin.
A replay actual may report `used_llm=true` or `false`; neither value proves
that a model did or did not execute during the original recording.
`rules_intent` genuinely executes
`build_intent(question, index, use_llm=False)` in a per-case subprocess.
It checks `used_llm=False`, sends only the question (never oracle/gold), records
the actual TBOX graph and optional ABOX hashes, and enforces subprocess timeout.
Only `kind=intent` with `allowed_capabilities=["intent"]` is supported.
`as_of`, turns, real answer/query/evidence execution, and online models are not
supported and cannot be silently ignored. Nothing is extracted from answer text.
An optional `--abox` supplies actual entity data; this remains intent-only.

Run output contains per-case assertions/actual/errors, mode, fixed eligible
denominator, and every pass/fail/error/timeout/skip/not_run count.
`--max-cases` and `--stop-on-error` leave remaining eligible cases as not_run;
unavailable/skipped cases remain in the eligible denominator. Zero eligible
cases are invalid. Exit 0 requires all eligible cases pass, exit 1 means any
nonpass case, and exit 2 means setup/contract unavailable.

`--database` defaults to ignored `artifacts/evaluation/evaluation.sqlite`.
Run metadata includes manifest/case-set/case hashes, corpus/ontology declarations,
actual rules graph/ABOX hashes, commit plus dirty-workspace SHA256, model/prompt
(`none`), mode, retry/cache/budget execution settings where applicable.
The manifest's corpus/snapshot/ontology labels are declarations, not a verified
binding to the supplied TBOX/ABOX. Actual graph/ABOX content hashes are recorded
separately, but v1 does not establish manifest-to-artifact snapshot consistency.
No corpus locking claim is made by these synthetic fixtures.
The generic Python runner checks elapsed time after an adapter returns and does
not enforce a hard deadline for arbitrary callables. Hard cancellation of an
arbitrary callable is unsupported, including a callable that never returns;
custom adapters must enforce their own deadline. Saved execution config records
`timeout_enforcement` as `hard deadline not enforced; elapsed check only`.
The included rules adapter separately kills timed-out
subprocesses. No timeout or exception is counted as success.

Business gold and blind sets must be supplied and reviewed independently from
the tested system, with corpus snapshots locked separately. The current
fixtures do not convert historical regressions into an independent baseline.

## Separate document RAG and optional Ragas diagnostics

`tools/document_rag.py` actually executes snapshot-backed BM25 retrieval. Its
default response is an **extractive baseline**, not a generated user answer.
It does not call the ontology intent router. `--generate` is optional and its
citation-ID guard is not a semantic entailment validator; the existing streaming
generator does not yet enforce a total deadline/output budget. Do not use it as
a bounded production generation SLA.

The input contract is a JSON object with `schema_version: "1.0"` and `cases`;
each case has `id`, `question`, optional `as_of`, `entity_iri`, `doc_ids` and
`version_ids`. Omitted/null scope means no caller filter; an empty list forbids
all documents/versions. Gold fields are
not passed to the pipeline. The checked-in three-question legal MD pilot keeps
all references in a separate file and labels them `draft`; it is source-authored
by the implementing team, not an independent blind business set.

Actuals are JSON envelopes with `schema_version`, `provenance`, and `rows`, or
JSONL rows repeating the same schema/provenance. Rows contain `id`, `user_input`,
`response`, and `retrieved_contexts`. The CLI separately writes JSONL traces with
answer mode/status, evidence versions/locators, warnings and timing. Provenance
records actual corpus membership and selected implementation hashes, not just
Git HEAD. A declared trace path/hash alone does **not** authenticate execution.

`tools/evaluate_ragas.py` is separate from the deterministic contract scorer:

- Default is offline validation; `--execute` is the explicit network switch.
- Install optional `ragas==0.4.3` and `langchain-community==0.3.31`. The latter
  pin avoids an observed missing `chat_models.vertexai` import with 0.4.2.
- Configure `RAGAS_JUDGE_API_KEY`, `RAGAS_JUDGE_MODEL`, and optional
  `RAGAS_JUDGE_BASE_URL`. Project model configuration is **not** silently reused.
- Requested metrics: `faithfulness`, `context_precision`, `context_recall`,
  `response_relevancy`. The last uses `AnswerRelevancy` and additionally needs
  explicit `RAGAS_EMBEDDING_MODEL/API_KEY/BASE_URL`; there is no implicit key reuse.
- External `--references` is `{ "schema_version": "1.0", "rows": [...] }`,
  keyed by actual row IDs, with `reference`, optional `reference_contexts` and
  `review_status` (`draft` or `reviewed`). It cannot overwrite actual gold fields.
  Context precision/recall currently use `reference`, not `reference_contexts`.
- Every requested metric retains the full row denominator. A failure, timeout,
  missing dependency/reference/embedding or nonfinite result is not a pass. A
  metric's aggregate mean is null unless all rows have valid results.
- JSON and SQLite (`ragas_runs`, `ragas_results`) retain per-item outcomes,
  model and dependency versions, call/token/time budgets, actual call count and
  input/row hashes. Telemetry is disabled. Error details are redacted.

Example validation-only invocation, using the isolated environment:

```powershell
artifacts/ragas-venv/Scripts/python.exe -X utf8 tools/evaluate_ragas.py --input artifacts/legal-md-pilot/extractive.actual.json --references evaluation/cases/legal_md_pilot_references.json --metrics faithfulness,context_precision,context_recall --max-rows 3 --max-judge-calls 18 --output artifacts/legal-md-pilot/ragas-dry-run.json
```

Add `--execute` only after configuring/authorizing the judge. A high faithfulness
score for copied extracts says little about answer relevance or synthesis.
These metrics do not check legal currency, source completeness, authentic
citation locators, scope permissions or independently reviewed business success.

## Official legal corpus and retrieval gate

`corpora/official-laws-v1.sources.json` locks four official HTML originals and
226 full articles. It records official origin, not current legal validity.
The acquisition and reproduction guide is `docs/official-law-corpus-20261012.md`.

`cases/official_laws_v1_questions.json` contains only caller inputs. Oracle,
references, and freeze hashes are separate files. The 32-case set comprises
14 dev, 14 test, and 4 challenge cases; splits were fixed by document family.
It was source-authored without actuals by another agent in the same team, not
independently reviewed by a human domain expert. All gold remains draft. Once
test failures have been inspected, this release is a regression baseline, not
an untouched blind set for subsequent tuning.

`tools/evaluate_legal_retrieval.py --verify-trace` first checks the artifact
against read-only SQLite using a separate HTML parser, then scores exact
document/article addresses, AND-of-OR evidence groups, status, and scope.
The audit validates local consistency, not signed execution authenticity,
BM25 replay, the completeness of declared candidates, current law, or prose
correctness. An explicit article budget flag is not an oracle completeness flag.

The original overall denominator includes all 32 cases. Zero-target challenge
rows contribute zero to recall/MRR, not a fabricated perfect recall. Separate
`by_split` and `by_expected_status` summaries retain every declared case,
including errors. Every summary reports `pass_count`, `nonpass_count`, and
`expected_status_match_rate`; empty groups have null rates. None of these is
business acceptance. CLI exit 1 means a retrieval gate failed; exit 2 means
input/audit/setup failure. The top-3 and top-5 baselines each have one missing
target case; expected-unresolved controls must not be removed from the report.

For Ragas, `--max-rows` is a safety ceiling, **not a sampling selector**. Select
and record diagnostic IDs explicitly, create a separate question/reference
subset, execute that subset to produce its own actual/trace, then use
`--verify-trace --corpus-db ... --execute`. Do not truncate actual contexts or
reuse the full-run trace hash for a fabricated subset. Retain failures in each
metric's denominator and report diagnostic selection bias. A ContextPrecision
score near one is not a literal fraction of relevant contexts or proof that
every necessary article was retrieved. The official small-sample run and the
older Markdown run use different corpora/questions and are not comparable A/B
results.

## Retrieval V2 Ablation

`experiments/legal_retrieval_v2.json` registers four separate strategies and fixed
budgets. `legal_retrieval_v2_selection.json` records the chosen `bm25_rerank`
candidate before the frozen `retrieval_holdout_v2_*` set was executed or opened.
That set has 16 ordinary cases and two controls, authored without system outputs
by a separate agent in the same team; it is still draft, not human-reviewed.
After this run both released sets are exposed and cannot be reused as unseen
holdouts. Never modify their oracle to fit retrieval results.

`tools/compare_document_retrieval.py --run NAME=ACTUAL ...` independently audits
each input and rejects comparisons with different code, corpus, scopes, dates,
or candidate/output budgets. Its exit zero means the diagnostic report exists,
not that every gate passed. It separates target-only precision, fixed-denominator
coverage, evidence characters, transport versus response-validation errors, and
cold/mixed/warm cache timing. Per-query timing excludes CLI corpus/index startup.

`--retrieval-strategy` selects `bm25`, `parent_child`, `hybrid_rrf`, or
`bm25_rerank`; only explicit `--allow-retrieval-network` authorizes provider calls.
The default stays BM25. All strategies return full parent articles. Model errors
are explicit and do not silently fall back. Dense/rerank scores are recorded,
not independently recomputed by the auditor; RRF arithmetic and child offsets are.

Ragas supports explicit process-local `--reuse-project-model --judge-model
deepseek-v4.1-flash`. `--judge-thinking disabled --judge-thinking-param
enable_thinking` selects the provider parameter verified for the current endpoint;
it is never inherited from production configuration. Alternative protocol
`--judge-thinking-param thinking` is explicit, not auto-detected. The report records
requested parameters, returned model, response finish reasons and token usage,
without recording judge prompt/response content or credentials. Execution retains
the three-row, 90-second-per-metric and 18-call ceilings. Preserve failed runs.

Results and reproduction: `docs/rag-retrieval-ablation-20261012.md`. Old-set
coverage gains did not repeat as an additional gain on the new holdout, so rerank
remains opt-in. The paired three-row Ragas diagnostic is not business acceptance.

## Source-review corrections, R1

Use `cases/official_laws_v1_r1_*` and `cases/retrieval_holdout_v2_r1_*` for the
corrected public regression inputs, oracle and references. Their original frozen
parents and historical scores remain unchanged. The external
`cases/official_laws_revision_r1.json` records four source-based P1 corrections,
field differences and parent/content hashes; each new freeze binds its revision.
Case IDs, requested scopes/dates, expected statuses, article targets and required
groups do not change. Questions still contain no gold.

The reviewer is GPT-6 Astra with high reasoning and the implementing author is
GPT-6.1-sol with high reasoning. This is AI collaboration, not independent human
domain certification. Oracle authorship and all references remain `draft`, with
`independent_human_review=false`; both revised releases are exposed regression
sets. A corrected wording or a new hash does not restore blind-test status.

Review evidence: `docs/domain-draft-review-20261012.md` and
`docs/domain-draft-r1-acceptance-20261012.md`. Validation, remaining limits and
the next evaluation route: `docs/domain-draft-iteration-20261012.md`. Run the R1
inputs into new artifact paths; preserve original actuals and failed judge runs.

## Natural-input baseline correction, 2026-10-13

The old official/R1 and holdout/R1 sets contain source cues. Their recorded
ordinary queries search one document each, not the full corpus. Preserve their
frozen bytes and scores as source-cued regression diagnostics; those results do
not establish natural-question retrieval quality.

`cases/natural_facts_v1_*` is a new 16-case, source-authored draft development set,
created by GPT-6.1-sol high and reviewed by GPT-6 Astra high before freezing and
first execution. Its only runtime case fields are `id`, `question`, and a common
`as_of`; document identity, article targets, business strata and references stay
in evaluation files. The oracle permits all four corpus documents. Gold targets
are never query authorization filters. This is same-team AI work, not independent
human review or representative user traffic; the released set is now exposed.

`tools/audit_search_scope.py --questions QUESTIONS --output REPORT` reports source
cues without rejecting legitimate explicit-source queries. Add
`--require-unscoped` for the strict natural-input benchmark contract. Add both
`--actual ACTUAL --corpus-db DB` to bind questions through the independent artifact
auditor and compare the recorded eligible set with the complete date-available
body set rebuilt from read-only SQLite. Outputs distinguish full source article
counts from searchable complete articles and detect title/direct-address bypasses.
Exit 0/1/2 means diagnostic pass, contract-policy violation, or setup/audit error.
No-cue heuristics do not certify naturalness; eligible-set equality does not
certify actual execution over the full index or current legal validity.

The preregistered protocol is `experiments/natural_facts_v1_protocol.json`; results
and artifact hashes are in `experiments/natural_facts_v1_results.json`. Offline
BM25 Top-5 and Top-3 each pass 11/16 complete-evidence gates, including only 3/8
multi-article and 0/2 cross-document cases. All 16 recorded scopes match four
documents and 226 articles. Top-3 additionally cannot hold the four necessary
articles of one case; its failure stays in the denominator. Lexical top-20 cannot
contain complete gold for three cases even with perfect reranking. These are
candidate-coverage findings, not executed model-reranking results.

No Ragas judge or answer-generation score is claimed here. Corpus size remains a
small fixed-source experiment, and all source validity fields remain unchecked
for current law. Reproduction, exact missing ranks and the revised BKN-aligned
evaluation route: `docs/natural-fact-evaluation-20261013.md`.
