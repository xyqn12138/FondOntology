# Legal Markdown pilot — not an acceptance set

These three source-authored questions and draft references are frozen before
running retrieval or scoring. They are separate files: production receives only
questions; the evaluator merges references after execution. Do not tune these
references to match a system response or repeatedly select favorable judge runs.

The selection is `../corpora/legal-md-pilot.selection.json`. Its hashes pin two
local research Markdown files, not verified authoritative originals. Question
001 uses article 3 of the liquidity document; 002 uses article 16 of the operations
document; 003 uses article 23 of the operations document. Dates and source URLs
are declarations, not proof of present legal force. The retrieval `as_of` date
only filters stored metadata, with explicit unknown-issue-date research opt-in.

The source PDFs were downloaded for limited textual cross-checking into ignored
`artifacts/legal-source-check/`, not ingested as the corpus. Their SHA256 values:

- Liquidity: `813558004fa2d8d6c87050ef634b49d47a8e913d99c76590f281d711554ecf93`.
- Operations: `b8d078253e3048aebb2e057e953ee442ec41c864c4461c0008d4042f8a952511`.

The same coding team authored these references. They are **draft**, not an
independently reviewed business gold or a blind test. Three favorable source
questions cannot estimate general user success, legal validity, abstention,
multi-turn behavior or document-version conflict handling. The 10% boundary is
one business-shaped probe, not a complete boundary suite.

An extractive baseline concatenates retrieved passages, so high faithfulness
mainly checks the scoring plumbing and must not be advertised as answer quality.
Context precision/recall are model judgments against the short draft reference,
not deterministic article recall. Missing scores stay in the denominator.

Next acceptance data should be authored by domain reviewers from frozen sources,
split by document family/version rather than random questions, and include
missing evidence, exact threshold/exception, historical dates, conflicting
versions, source citation obligations, entity scope and user paraphrases.
