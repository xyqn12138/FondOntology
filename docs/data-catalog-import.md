# Data Source Catalog Import

`data/` is the authoritative source directory for the restored official full texts.
`data/source_catalog.json` is the sole explicit import whitelist. Directory globbing,
the previous official-law acquisition registry, and evaluation manifests are not
fallbacks. SQLite and generated JSONL manifests are derived artifacts, not source
records, and this entry point permits their creation only under `artifacts/`.

## Catalog Contract

The envelope is `{"schema_version": 1, "documents": [...]}`. Document IDs must be
unique. File paths are relative to the data root, without a `data/` prefix; absolute
paths, traversal, and links resolving outside that root are rejected. Every
non-null raw or Markdown path must exist and match its lowercase byte SHA-256,
including entries not selected for import. A legacy path is provenance only.
An unresolved source may have `origin_kind=null` when no original has been
identified; acquired and converted entries require an explicit origin category.

Only `status=ready`, `origin_kind=issuer_original|official_republication`, a present
raw source and Markdown, an explicit issue date, and
`verification.identity=verified`, `verification.completeness=complete` with
nonempty `verification.evidence` qualify for authoritative ingestion. Secondary
copies never qualify. These review declarations record a source decision; local
hash checks alone do not authenticate that decision or establish current legal
validity. All imported provenance keeps `legal_validity=not_checked_current`.

Ready entries must also bind actual acquisition and conversion records inside
data. `verification.acquisition` contains exactly `receipt_path` and
`receipt_sha256`; `verification.conversion` contains exactly `record_path` and
`record_sha256`. These reference hashes must match the JSON bytes. The acquisition
receipt's requested and final URLs must both equal the catalog `download_url`
after component-wise normalization of UTF-8 percent-encoded Unicode and ASCII
unreserved characters. Reserved escapes retain their encoded boundaries:
`%2F` cannot match `/`, and encoded query delimiters cannot create parameters.
Scheme, authority, path, query, and fragment must still agree; this does not
authorize a redirect to another host or resource.
The receipt's source hash and byte count must match the raw source, and its HTTP status must
be 200. Existing aliases `actual_url`, `sha256`, `byte_count`, and `http_status`
are accepted alongside `requested_url`, `raw_sha256`, `bytes`, and `status_code`;
conflicting aliases fail; requested URL aliases use the same URL comparison.
Receipt fields do not independently prove authenticity.

Conversion JSON contains exactly `schema_version=1`, `raw_path`,
`source_sha256`, `markdown_path`, `markdown_sha256`, nonempty `method` and
`version`, `observations`, and `identity_review`. Its source and Markdown paths
and hashes must equal the catalog entries. `identity_review` contains exactly
`scope=machine_conversion_and_structure_only` and `human_reviewed=false`.
`observations` must include `original_format`, `page_count`, `page_coverage`,
`article_count`, `missing_images`, and `unsupported`. Format and counts match
the catalog verification; complete page coverage is the actual ordered list
`[1,...,N]`, or `[]` with null page count for sources without pages. Ready PDF
requires an explicit page count. Missing images or unsupported content prohibit
ready status. Extra observations may record extraction details. Conversion
records preserve bounded machine observations, not a claim of human review or
proof of exact legal equivalence; the recorded page coverage must come from
actual conversion verification.

Legal texts declare `expected_articles` and matching `verification.article_count`.
Their Markdown article sequence must be complete and consecutive. Title and source
headers before the first article are retained as bytes but never become chunks.
The new `data-catalog-body-v1` chunker supports Markdown article headings without
changing the frozen `legal-article-v1` behavior; each complete legal article stays
one chunk even if it exceeds the soft character target.
Substantive gaps and trailing appendices receive independent
`supplementary_body` sections and never borrow a legal article number. Article
count validation counts article sections only; structural chapter headings alone
may be excluded. Snapshot verification rechecks these body ranges and chunks.

Non-article technical standards use `expected_articles=null` and require an
explicit 1-based `verification.body_start_line`. This boundary must point past
source/title headers into the verified full body. Subsequent body headings are
sections, split into deterministic character windows. No article count is
invented for protocols, tables, numbered technical clauses or appendices.
Article validation uses the explicit recovered `expected_articles`; article-like
examples in technical specifications never select legal article chunking.

Entries with `unresolved`, `downloaded`, or `converted_unverified` are reported and
excluded. Explicitly selecting one of those entries is an error. An empty ready
set is auditable but cannot be imported; missing catalog or failed checks cannot
silently revive historical cached sources.

## Commands

Materialize the recovered offline inputs before auditing the catalog:

```powershell
.venv/Scripts/python.exe -X utf8 tools/materialize_data_catalog.py
.venv/Scripts/python.exe -X utf8 tools/materialize_data_catalog.py --write
```

The default materializer previews the four explicit recovery manifests
`data/_recovery/l0-l3-sources.json`, `l1-sources.json`, `l2-sources.json`, and
`l1-stock-connect-2022-sources.json`. The 2022 attachment has a separate stable
ID from the preserved 2016 original; recovery never transfers newer dates onto
the old bytes.
`--source-manifest` and `--mineru-state` are repeatable explicit replacements
for the respective defaults. No directory discovery or network retrieval occurs.
`--write` creates immutable derivatives under `data/_fulltext/` and validates a
staged catalog before replacing `data/source_catalog.json`. Existing source
bytes and legacy summaries remain intact. Generated paths bind source and
Markdown hashes; conflicting bytes at an existing generated path fail.
Conversion JSON records live under `conversions/<record_sha256>.json` beside
the Markdown. Updated observations for unchanged Markdown create a new record
and preserve the previous bytes.

The explicit default MinerU states are `_converted/L1/state.json`,
`_converted/L2/state.json`, and `_converted/L3/state.json`, relative to data.
A listed missing state is an error; the materializer does not discover other
state files.

HTML extraction uses each manifest's explicit body selector; optional
`title_selector` must select exactly one title in the same original HTML.
Only that selected title and body participate in identity verification.
Comments, declarations, doctypes, processing instructions, and executable
elements are excluded, including Word conditional comments inside tables.
Full-title or base-title prefix lines are removed after identity verification.
Official structured
JSON preserves active articles and their nested operative paragraphs. Substantive
decrees, transitions, and appendices remain body content. Exact title-only
prefix lines are removed from these generated body derivatives. A missing
separator after a complete line-start `第…条` heading receives one space,
and an isolated article heading joins its following substantive paragraph.
Both transformations are recorded in conversion observations; source bytes
remain unchanged. Tables and
unreviewed images prevent ready status. PDF conversion uses only completed,
source-bound MinerU state, verifies extraction and Markdown hashes against that
state, and records actual reported page indices. Word conversion binds the
explicit conversion manifest, Markdown hash, and referenced image asset hashes.
Referenced local assets are copied beside their generated Markdown.
All PDF and Word derivatives remain `converted_unverified` until independent
full-text fidelity verification; page coverage and structural checks alone do
not certify OCR formulas, rendered layout, revision semantics, or legal identity.

```powershell
.venv/Scripts/python.exe -X utf8 tools/import_data_corpus.py
.venv/Scripts/python.exe -X utf8 tools/import_data_corpus.py --manifest-out artifacts/data-corpus/import.jsonl --db artifacts/data-corpus/corpus.sqlite --import-ready --snapshot-id data-official-v1
```

The default action is a read-only catalog audit. `--document-id` can be repeated
to select an explicit ready subset. Without that option, all ready catalog
entries are selected. Acquisition, conversion, catalog edits and source review
are separate tasks; this command has no network behavior and never modifies data.
Every ready catalog entry passes the full ready gate even when an explicit ID
selection does not include it. Selection cannot conceal an invalid ready record.
Historical versions whose usable time range remains unresolved must remain
`converted_unverified`. The 2018 registration notice is explicitly recorded as
repealed on **2023-05-01**, with the 2023 registration rules' Article 83 identified
in verification evidence; it cannot become ready. This restoration does not introduce current-law validity
or historical cutoff inference.

## Historical Boundaries

`tools/import_legal_markdown.py`, `tools/fetch_official_laws.py`, and the generic
`tools/corpus_cli.py import` remain low-level legacy interfaces for historical
experiments and frozen benchmarks. Their historical selection/registry contracts
and existing snapshots are deliberately unchanged. They are not entry points for
the restored data source catalog. A trusted snapshot means fixed verified source
provenance, not a certification that a rule remains in force.
