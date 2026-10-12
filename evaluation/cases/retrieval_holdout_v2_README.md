# Retrieval Holdout V2

## Authorship

Independent source-authored draft, not derived from production outputs. The author read only four official HTML originals, the official sources registry, the author's prior questions, and the approved official HTML/article extraction functions. No retrieval implementation, actual answers, traces, generated answers, scores, or RAGAS results were read; the tested system was not invoked.

This is author separation within the same AI team, not independent human legal review or certified blind testing. The oracle and all references are `draft`. Human domain review remains required. The author has not audited current validity: each ordinary question explicitly asks about its corpus version, not current law.

## Contents

- `retrieval_holdout_v2_questions.json`: input-only questions with no gold labels.
- `retrieval_holdout_v2_oracle.json`: source-authored document/article targets, AND-of-OR evidence requirements, categories, and source notes.
- `retrieval_holdout_v2_references.json`: independent reference answers and concise scope/time explanations for controls.
- `retrieval_holdout_v2_freeze.json`: external hashes of these three JSON files and this README, source hashes, UTC freeze time, and structural validation counts. The manifest does not hash itself.

There are 16 ordinary questions, four per law, all `test`, plus two separately reported `challenge` controls. Ordinary categories are primarily `business` and `user`, with one explicit article locator for `system`. Seventeen of 18 questions give no article number. Nine ordinary questions require two complete articles, expressed as separate required singleton groups; all groups must be satisfied. Other questions require one complete article. Source notes identify official chapters and numbered article headings, not invented descriptive legal headings.

All 25 distinct ordinary target articles are new relative to the prior frozen 32-question official-laws-v1 set. New coverage includes initial redemption restrictions, different day bases, mergers and resolution filing, initial allocation versus passive deviation, written sales agreements, fee disclosure, branch geography, private settlement cross-references, technology-service boundaries, issuance versus listing disclosure, liquidation, multilingual precedence, holder-convened meetings, rumor response, related trades, audit recipients, ongoing information, reporting confidentiality, and cross-border roles.

## Scope And Time

Natural questions explicitly name the law and version. Only the direct article request and controls have caller-provided `doc_ids`; the unknown-version control also includes `version_ids`. These constraints are authored request scopes, not automatically inferred from gold. Ordinary `as_of` is 2026-10-12.

Challenge 1 restricts the caller to an unregistered version ID and forbids fallback. Challenge 2 requests already-effective sales rules as of 2020-09-30: the corpus sales version was issued 2020-08-28 but commences 2020-10-01. This distinguishes published from effective; it does not deny the existence of the published text. Neither challenge depends on an arbitrary substantive no-answer question or claims knowledge of law outside this snapshot.

The disclosure text is the 2020-03-20 revision, with `effective_from: null` in the source registry. Its original 2019 commencement date is not used to backdate the revision. No source is described as currently valid.

## Locked Evaluation Protocol

Freeze the questions, oracle, references, and this README after validation, before the tested runner sees the new inputs. Validate IDs, uniqueness, input-only fields, official source SHA-256 and complete article counts, chapter/heading references, target existence, required group completeness, fixed splits, family/category counts, and new target status versus the author's prior frozen set.

The runner must lock its candidate strategy and dev parameters before a single holdout evaluation. Report ordinary `test` and `challenge` separately. Do not tune parameters or silently alter targets or references after seeing holdout outputs. A later source or human-review correction needs a documented new freeze, not adjustment to match retrieval behavior. No test execution is performed by this author.
