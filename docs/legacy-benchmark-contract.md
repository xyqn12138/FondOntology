# Legacy Benchmark Contract

`tools/qa_bench.py` keeps the historical benchmark suites runnable, but a
legacy green result is only a regression signal. It is not a claim of business
accuracy or user-facing end-to-end coverage.

Use `--acceptance` explicitly when a suite has reviewed gold that covers every
required business slot. Acceptance mode rejects count-only find gold,
unreviewed or incomplete intent contracts, unknown expected fields, duplicate
cases, malformed values, and successful answers without a non-empty
claim/evidence report.

The `e2e` stage enters through a manually constructed Intent and is therefore
reported as deterministic integration, not natural-language user E2E.
`citation` and `explain` are projection/evidence contracts; they are not
factual-support approval. Online stages require all LLM settings (API key,
base URL, and model) and fail when configuration is absent or execution falls
back to deterministic/template output. Deterministic stages do not invoke
paid model endpoints.

Gold files remain the source of expected entities and semantic conditions.
The runner never fills missing gold from executor output. A fixed eligible case
set is scored case by case; malformed cases and per-case exceptions are
failures, and a zero-case set is invalid.
