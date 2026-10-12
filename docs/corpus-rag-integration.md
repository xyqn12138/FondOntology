# Corpus Snapshot RAG Integration

`load_corpus_store(db, snapshot, as_of=...)` opens an existing CorpusRepository
and builds a read-only BM25 store from that snapshot's selected versions.
`answer_question(..., rag_store=store)` injects it into describe, regulation,
code, and entity comparison. Default QA calls keep their legacy data source.

CLI usage:

```text
python tools/qa_cli.py --no-llm --corpus-db evidence.sqlite --corpus-snapshot approved-v1 --as-of 2026-10-10 "question"
```

All three corpus arguments are required together. `as_of` filters issued and
effective dates and withdrawal dates within the selected snapshot; it does not
select an older or newer version outside that snapshot. Missing databases,
unknown snapshots, malformed dates and non-trusted snapshots fail closed.
Research/regression use requires `--allow-nontrusted` and answers display
their non-authoritative scope.

Undated educational PDFs require both `--allow-nontrusted` and
`--include-undated-research`. This opt-in is accepted only for `research`
snapshots, still requires `as_of`, and does not bypass known issue/effective or
withdrawal dates. Both CLI and library answers warn that unknown issue dates
cannot establish historical availability or current legal effectiveness.

SQLite retrieval is BM25-only: it cannot consult the legacy vector index,
embedding endpoint, or reranker. Regulation and code evidence uses repository
entity links, never fixed simulation-report TTL files. Missing anchor scope,
missing scoped documents, or no lexical match returns unresolved rather than
relaxing to the whole corpus or taking arbitrary first documents.

Evidence carries document/version IDs, original SHA256, source/locator,
authority/status and provenance; report metadata records snapshot membership
hash, index version and date scope. JSONL stores no longer share a process-wide
singleton across paths.

PDF evidence additionally carries extraction SHA-256, reported page and block,
normalized-text offsets, available bounding boxes, and `extraction_quality`.
`unreviewed` OCR is not independently verified even when the source PDF is
user-verified. All PDF block locators carry
`page_scope=mineru_reported_start_page_unreviewed`; a reported starting page is
not proof that all text or table cells came from that single page. The live
pipeline output includes merged paragraphs as well as merged tables.

Integration fixtures are synthetic contract documents, not verified regulations.
Passing these tests demonstrates runtime consumption and isolation, not real
legal or financial answer accuracy. Semantic entity links and original content
still require independent review.
