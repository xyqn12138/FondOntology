# Official Laws V1 R1 Exposed Regression Revision

This is the explicit `official_laws_v1_r1` source-review correction of `official_laws_v1` on the same `official-laws-v1` snapshot. The 32 ordered IDs, dates, explicit scopes, statuses, gold article targets, evidence groups, categories, scenarios and splits are unchanged. The four parent content files, parent freeze and original results remain unchanged.

The revision was AI-reviewed by `{"model": "gpt-6-astra", "effort": "high"}`; `independent_human_review=false` and `exposed_regression=true`. Every reference and oracle authorship remains `draft`. This revision is exposed regression data, not a new untouched blind set or independent human legal review.

Only `P1-private-07-responsible-party` changes domain content: the question, reference and source notes clarify the same responsible party's insufficient property, without treating independent fund property as a manager's penalty property. Article 60 remains the sole gold target; article 4 is review context only. The machine-readable `official_laws_revision_r1.json` records before/after fields, issue and source article IDs, parent SHA-256 values, necessity and unchanged gold declarations.

The revision author read parent data, the registry and official extraction, and received source-based AI review. No actual answers, traces, RAGAS scores or tested-system output were read to write these corrections; no model or tested-system request was made by the revision author. Any old/new evaluation is an exposed regression comparison. Preserve original scores and hashes without retrospectively relabeling them.

The current content files are `official_laws_v1_r1_questions.json`, `official_laws_v1_r1_oracle.json`, `official_laws_v1_r1_references.json` and this README. `official_laws_v1_r1_freeze.json` hashes those four files and the external revision record only after the AI reviewer approves the draft. After freeze, any correction requires another explicit revision and freeze.

The following parent documentation is retained as historical authorship and contract context. Its original pre-evaluation separation and blind-test protocol do not turn this R1 revision back into an untouched test.

## Authorship And Review

This is a source-authored evaluation set, independently authored from system output. The author read only the four official HTML originals under `data/official-laws-v1`, their source metadata in `evaluation/corpora/official-laws-v1.sources.json`, and the extraction functions `extract_official_html` and `legal_article_sections` in `fondontology/corpus/legal_text.py`.

The author did not read retrieval or document-pipeline implementation, prior business gold, actual answers, traces, RAGAS results, or other tested-system output, and did not call the tested RAG system. Targets and reference answers derive from the official originals, not from observed system behavior.

This separation is within the same AI team. It is not independent human legal review, a certified blind test, or a claim that the references are production legal advice. Oracle authorship and every reference remain `draft`. A human domain reviewer must review the questions, legal interpretations, target completeness, references, and version applicability before a reviewed benchmark release.

## Files And Contract

- `official_laws_v1_questions.json`: caller inputs only; no target articles, expected statuses, categories, or other gold fields.
- `official_laws_v1_oracle.json`: expected retrieval status, target article sets, required evidence groups, allowed documents, scenario, category, split, and source notes.
- `official_laws_v1_references.json`: independently source-authored concise reference answers. Negative controls describe scope expectations without fabricated substantive law.

`required_groups` is an AND of groups; a group is an OR of acceptable complete articles. In this release every ordinary question uses singleton groups; all such groups must be satisfied. Multi-article questions intentionally require every necessary article, not one convenient answer-bearing sentence. `target_articles` includes every required article. An `unresolved` control has no target or required group.

Article identification uses the complete ordered official article sequence, not snippets from a search result. Chapter and article headings are recorded in each oracle `source_notes`; the official text generally has numbered articles rather than descriptive article titles. Any short scenario name is an author label, not a purported official article heading.

## Fixed Split And Coverage

There are 32 cases: 28 ordinary answerable cases and 4 scope/time negative controls.

| Document family | Ordinary cases | Split | Official articles |
| --- | ---: | --- | ---: |
| `csrc-operations-2014` | 7 | dev | 59 |
| `csrc-sales-2020` | 7 | dev | 63 |
| `csrc-disclosure-2020` | 7 | test | 42 |
| `state-council-private-funds-2023` | 7 | test | 62 |
| Explicit scope and time controls | 4 | challenge | Not applicable |

The document-family split is fixed before running the tested system: operations and sales belong to dev, disclosure and private-funds to test. Challenge is reported separately and is not a substitute for the ordinary held-out test. No question family is moved between splits based on retrieval success.

All three categories (`system`, `business`, `user`) occur across the set. There are 3 positive direct-article locator cases and 1 direct-article scope-conflict control; 28 of 32 questions (87.5%) do not give an article number. Natural questions explicitly name the requested source version. Coverage includes synonym-style operational language, exact numerical thresholds, strict versus inclusive inequalities, exceptions, different start dates, post-contract versus fundraising expenses, and seven multi-article AND combinations.

Natural questions usually omit `doc_ids` so explicit law names are part of the input resolution task. Only direct locator requests and explicit scope controls carry caller-provided `doc_ids`; those fields are not generated from gold to make retrieval easier. `doc_ids: []` means an intentionally empty authorized document scope, not an omitted filter. A conflicting caller scope must not be expanded merely because a different law is named in the question.

## Version And Time Boundaries

The sources' current legal validity has not been comprehensively audited. Questions refer to the version in the corpus and do not characterize it as current law.

| Corpus version | Issued | Effective from in metadata |
| --- | --- | --- |
| Operations 2014 | 2014-07-07 | 2014-08-08 |
| Disclosure revision 2020 | 2020-03-20 | null |
| Sales 2020 | 2020-08-28 | 2020-10-01 |
| Private-funds ordinance 2023 | 2023-07-03 | 2023-09-01 |

Ordinary requests use `as_of: 2026-10-12`. The disclosure source is the text revised on 2020-03-20. Its final article's 2019-09-01 commencement belongs to the original measure and does not establish that the 2020 revision existed or applied before its revision issue date. No independent commencement verification for the revision is claimed. The prior-date challenge uses `as_of: 2019-10-01` and expects unresolved for that specifically requested revision.

Negative controls are limited to resolvable contract constraints: explicitly unknown source title, deliberately empty document scope, incompatible named source and authorized document scope, and revision requested before issue. Arbitrary substantive questions with no obvious answer are not assigned unresolved merely to convert an extractive retriever into a generative refusal policy.

## Freeze Procedure

Before handing the set to the system runner, validate JSON ID equality, uniqueness, article existence against official HTML extraction, source chapter/article references, category counts, fixed family splits, multi-article group completeness, and the absence of oracle fields in questions. Record the local UTC freeze time and SHA-256 of these four files in the handoff. Hashes are external to these files to avoid self-referential changes.

Once handed off as frozen, do not change targets or references in response to actual retrieval or generated answers. Any later correction must be a documented source or reviewer correction with a new version and freeze record, not a silent adjustment to match system behavior.
