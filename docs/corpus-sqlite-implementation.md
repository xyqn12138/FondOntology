# Corpus SQLite Implementation

This P1 layer stores document evidence separately from TBOX and ABOX data. It
does not import RDF facts, edit ontology files, or make a document authoritative
by itself.

## Data flow

1. Create a database: `python tools/corpus_cli.py --db corpus.sqlite init`
2. Prepare a UTF-8 JSONL manifest. Each entry points to a local `.txt`,
   Markdown, or PDF original and must include its SHA-256, provenance,
   authority, status, and locator metadata. PDF entries additionally reference
   a hashed canonical extraction JSON; the original hash always identifies
   PDF bytes, not Markdown.
3. Import atomically:
   `python tools/corpus_cli.py --db corpus.sqlite import manifest.jsonl`
4. Publish an immutable membership set:
   `python tools/corpus_cli.py --db corpus.sqlite publish regression-v1 VERSION_ID --kind regression`
5. Verify after restart:
   `python tools/corpus_cli.py --db corpus.sqlite verify regression-v1`

`trusted` snapshots accept only `authoritative_original` entries marked
`verified` with an issued date. `research` snapshots accept non-quarantined
`research_note` entries. `regression` snapshots accept only explicitly
`synthetic` and non-quarantined entries. Synthetic fixtures are test assets,
not evidence of regulatory or business truth.

## Repository contract

`CorpusRepository.open_existing(path)` never creates a missing database or
initializes an empty one; it is not a database permission sandbox.
`get_chunks(snapshot_id, as_of=...)` returns only
the selected immutable versions and never silently falls back to another
snapshot or older version. Returned chunks include `chunk_id`, `doc_id`,
`version_id`, `doc_type`, `section`, `text`, `locator`, `fund_code`, `period`,
`entity_links`, `authority`, `status`, and `provenance`.

Version IDs include canonical metadata, source URI, source hash, provenance,
extractor/chunker versions, and chunk configuration. Chunk IDs additionally
include version, section, character offsets, and chunk configuration; equal
text from different versions therefore remains distinguishable.

Imported original bytes are retained in SQLite for exact recovery through
`get_original(version_id)`, even if the external local path later disappears.
Failed imports roll back all document changes and record a failed ingestion run.

## Dates and Publication

`issued_date` is the disclosure/publication date. `effective_from` is optional
and must not be invented from the issue date; when present it further restricts
eligibility. `withdrawn_date` is an exclusive upper boundary. `period` is an
opaque report-period label, not an effective date. An `as_of` query requires a
known issue date, excludes future issue/effective dates, and excludes withdrawn
versions. Undated records require no `as_of` filter or the explicit
`include_undated=True` research-only opt-in with an explicit `as_of`.
The latter never bypasses known effective/withdrawal dates and does not
establish historical availability.

The importer does not independently verify legal effectiveness, publishers,
licenses, or truth. `status=verified` is an explicit upstream review decision,
not a result of a checksum or `verify` command. Data owners must not label
unknown effective dates as known. For regulation questions, the runtime must
distinguish issue-date availability from an independently established effective
interval. `verify_snapshot` checks SQLite integrity, foreign keys, membership,
stored original hashes, and exact chunk spans; it does not prove authority.

## Manifest Contract

Required fields are `doc_id`, `title`, `doc_type`, `source_uri`, `path`, `sha256`,
`authority`, `status`, nonempty `provenance`, and nonempty `locator`. Optional
fields are `publisher`, `fund_code`, `period`, `issued_date`, `effective_from`,
`withdrawn_date`, `supersedes`, `license`, `chunker_config`, `entity_links`, and
`extraction` (PDF only, with `path` and `sha256`).
Unknown top-level fields are rejected. Dates use `YYYY-MM-DD`. `supersedes`
must identify an already imported version of the same stable document.
`chunker_config` has integer `max_chars` and `overlap`; the default is 800/0.
Entity links contain `entity_id`, `method`, `confidence` in [0, 1], and
`review_status`. These are explicit manifest assertions; this importer does
not perform ontology entity resolution.

The fixture template under `tests/fixtures/corpus` is intentionally synthetic
and not an import-ready real manifest: tests replace the SHA placeholder with
the exact source-byte hash in a temporary directory. File paths resolve
relative to the manifest. Text inputs must be valid UTF-8. PDF originals are
validated using the optional `pdf` dependency group (`uv pip install -e '.[pdf]'`).
The importer consumes existing MinerU v1 extraction JSON and performs no
network requests, HTML scraping, or OCR itself.

## Migration and RAG Boundary

- Schema migrations cover initial creation and transactional version 1 to 2
  using `PRAGMA user_version`. Version 2 adds immutable `document_extractions`
  with extraction bytes/hash, normalized text, and original page count. Existing
  text version identities are unchanged. There is no
  migration from the simulation generator's SQLite mirror.
- Stable document identity is the manifest's `doc_id`; title, document type,
  publisher, fund code, and period belong to the immutable version. Metadata
  corrections append a new version and do not edit previously published data.
- Original source bytes are also stored as a BLOB in each immutable version.
  This provides atomic, exact recovery for the small initial corpus; large
  documents need a separately designed content-addressed file-store contract.
- `get_extraction(version_id)` restores the exact PDF extraction JSON bytes.
  PDF spans refer to normalized MinerU v1 block text, not PDF bytes or Markdown
  offsets. `discarded` blocks remain in the raw artifact but are not indexed;
  all PDF locators are unreviewed starting pages, not single-page proof.
  `verify_snapshot` checks both original and extraction hashes and rederives
  block/chunk spans. It does not measure OCR accuracy.
- Snapshots contain one explicitly selected version per stable document.
  There is no implicit latest-version or global active-snapshot pointer.
  Switching snapshots means passing a different ID to the runtime.
- This layer exposes chunks for a RAG adapter; it does not replace the existing
  BM25 tokenizer, implement Chinese FTS5, or configure a vector index.
  `index_version` records the caller's intended index contract, not a built
  persisted index. Cache keys must include database identity, snapshot,
  index/tokenizer configuration, and `as_of`.
- Do not promote the SQLite corpus to the TBOX/ABOX fact source. Do not claim
  a real-data QA acceptance result from these synthetic fixture tests.

Validation: `python -m unittest discover -s tests -p test_corpus_store.py -v`
passes 10 offline tests covering restart, original recovery, duplicate import,
metadata revisions, dates, failed-batch rollback, atomic publication,
classification gates, input validation, chunk identity, immutability, and the
CLI init/import/publish/list/verify workflow.
