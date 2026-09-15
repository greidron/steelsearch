# Core Performance Pain-Point Ledger

## Purpose and Status

This is the append-only decision record for recurring core performance risks.
It distinguishes a measured symptom from a demonstrated cause so a later
compatibility repair does not repeat an earlier expensive pattern by accident.
It covers the non-plugin core replacement profile only. It is not release
approval, a substitute for the fixed v0.6.0 gate, or evidence that a proposed
cause has been eliminated.

The latest completed, execution-verified gate for the currently retained
candidate is `target/v071-search-pool-full-gate-20260914/result.json`. Its
candidate executable SHA-256 is
`25f39d6a7e422e10c0679bd64f51ce1d929dd8123125d8f42b7095540326829e`. Its two
published-v0.6.0 comparisons have 27 and 25 of 44 measurements below `0.950x`;
the corresponding paired fresh-baseline comparisons have 21 and 14 failures.
The later deferred-replay experiment was rejected and removed; its gate is
retained only as rejection evidence. Neither result permits acceptance: the
fixed published v0.6.0 budget remains the release-blocking criterion.

## Required Use for Every Core Change

Before declaring a change to core write, refresh, replay, query, collector,
response materialization, or fallback code complete:

1. Classify it with one or more tags: `write-conversion`, `refresh`, `replay`,
   `native-query`, `collector`, `response`, `fallback`, `allocation`, or
   `measurement`.
2. Search this document by those tags and read every matching entry. Record the
   entry IDs in a new Change Review row below. If there is no match, record
   `no-match` and the search terms; a missing record is not a no-match.
3. State the product invariant, the native Tantivy 0.21.1 API/source review,
   the hot-path admission condition, and why any retained fallback is necessary.
4. Keep attribution honest: mark a claim `demonstrated` only with a minimal
   reproduction or focused telemetry. Use `measured symptom` or `hypothesis`
   otherwise.
5. Run focused functional coverage and the preserved full non-plugin HTTP
   fixture after a functional repair. Once functionality is green, run the full
   isolated v0.6.0 performance gate with no concurrent build, test, or
   diagnostic activity. Record the evidence path and whether every individual
   throughput/mean/p95/p99 requirement passes.

The full gate is still required when a change resembles no existing pattern.
No comparison in this ledger permits changing workload settings, ignoring a
scenario, or trading an over-5% regression in one metric for improvement in
another.

## Evidence Levels

| Level | Meaning | Permitted conclusion |
| --- | --- | --- |
| `demonstrated` | Minimal reproduction or component telemetry isolates the cause. | Apply a narrow mitigation rule. |
| `measured symptom` | A repeated full-gate or component delta exists, but multiple causes remain. | Prioritize investigation only. |
| `hypothesis` | Plausible explanation without isolation. | Do not optimize or relax behavior on this basis alone. |
| `rejected` | Measurement or source review disproves the proposed cause. | Preserve the rejection to prevent rediscovery. |

## Pattern Entries

### PP-001: Source Re-evaluation on a Native-Capable Path

- Tags: `fallback`, `native-query`, `collector`, `allocation`.
- Level: `demonstrated architectural risk`; not attributed to the current gate.
- Pattern: implement OpenSearch compatibility by scanning or re-scoring source
  documents before confirming whether Tantivy 0.21.1 already provides a query,
  scorer, collector, fast-field, or extension point.
- Cost mechanism: source traversal and hit materialization scale with candidate
  documents and can bypass Tantivy postings, collectors, or statistics.
- Required prevention: inspect the pinned Tantivy source/API first, write a
  minimal semantic comparison, and record why a native composition or narrow
  extension cannot meet the contract before adding a fallback.
- Related records: `native-ranking-audit-2026-09-10.md`,
  `native-aggregation-collector-investigation-2026-09-11.md`, and the
  Native-First rules in `AGENTS.md`.

### PP-002: Broad Batch Preconversion for a Narrow Failure Invariant

- Tags: `write-conversion`, `refresh`, `allocation`.
- Level: `demonstrated` for the broad admission condition; contribution to the
  total gate regression remains to be measured after the narrowing change.
- Product invariant: a fallible conversion must not leave a partially queued
  Tantivy writer batch. Multi-field conversion can reject an object value, and
  positioned text arrays can fail on position overflow.
- Historical broad guard: `TantivySearchState::write_documents` prepared every
  document into `Vec<TantivyDocument>` whenever any indexed field had either a
  multi-field source or a text position gap. All normal `text` mappings have
  the default gap `100`, so a batch containing only direct string values paid
  the allocation and conversion pass.
- Evidence: the completed gate above reports three-node cumulative
  `document_add` of about `0.416s` for the candidate versus about `0.290s` for
  v0.6.0, while commit time is comparable (`12.3-12.9s` versus `12.8s`). This
  identifies native document conversion/add as the first measured bottleneck;
  it does not quantify the preconversion branch's exact share.
- Narrow mitigation: prebuild a batch only when a document has a multi-field or
  a text field whose extracted values are neither absent nor exactly one string.
  Direct-string text uses Tantivy `add_text`, which is infallible in this path.
  Arrays and non-string values retain the prebuild boundary.
- Required regression coverage: normal direct-string admission, array admission,
  and a multi-field conversion failure that proves no partial writer batch is
  queued.
- Follow-up measurement: `target/plain-text-preparation-full-gate-20260914/`
  (result SHA-256
  `6284af322273e1520e20a8e99e650d622f724844abdff776f9f9d96d2820e369`) is
  execution-verified but still fails the fixed gate, with 22 of 44 conservative
  values below `0.950x`. Three-node `document_add` is `0.458-0.478s` for the
  candidate and `0.319-0.332s` for the same-run v0.6.0 baseline. The narrowed
  admission condition is therefore a correctness-preserving cleanup, not a
  demonstrated performance improvement. Do not claim it removes the measured
  write bottleneck; investigate a native writer transaction/rollback boundary
  before adding more source-shape prechecks.
- Current mitigation under measurement: Tantivy 0.21.1
  `IndexWriter::rollback()` cancels all updates after the last commit and
  reinitializes the writer. Build and enqueue each document once; on either
  failure, call this native rollback before returning the error. This removes
  both the broad `Vec<TantivyDocument>` preparation and the extra source-shape
  traversal while retaining batch atomicity. Focused rollback and late-replay
  tests pass, as does the preserved `1180/1180` HTTP fixture at
  `target/native-writer-rollback-full-20260914/report.json` (SHA-256
  `199a0c130e81b2f080e2c55c94bceb3894c5ed978fc0eb278d7b9dd1f109bda1`).
  The first gate attempt is invalid because its second OpenSearch run failed to
  clear cluster blocks; it is preserved at
  `target/native-writer-rollback-full-gate-20260914/` and is not performance
  evidence. The full rerun at
  `target/native-writer-rollback-full-gate-rerun-20260914/` is
  execution-verified (result SHA-256
  `fed0758abc14128c53bdb26eb093afa6661fa24f6b40f7e9caa1ed4216957466`) but
  fails with 24 of 44 lower ratios below `0.950x`. Candidate `document_add`
  is directionally lower than the prebuild candidate in separate runs (single
  `686-723ms` versus `771-818ms`, three-node `399-447ms` versus `458-478ms`),
  but baseline variance prevents treating that comparison as gate acceptance.

### PP-003: Correctness Replay Scope Accidentally Replaced by Incremental Refresh

- Tags: `replay`, `refresh`, `write-conversion`.
- Level: `demonstrated correctness constraint`; its steady-state performance
  cost is not isolated.
- Pattern: a late replay whose sequence number is already behind the published
  watermark cannot use the normal append/replacement refresh plan without
  risking loss of older visible documents.
- Required prevention: preserve a shard-scoped `Full` refresh for that case and
  retain the direct late-replay regression test. Do not broaden it to ordinary
  append writes without a separate measurement.
- Related source: `StoredShard::documents_after_until` and
  `documents_changed_since_refresh_through` in `crates/os-engine-tantivy/src/lib.rs`.

### PP-004: Incomparable or Semantically Incorrect Measurements

- Tags: `measurement`.
- Level: `demonstrated` process risk.
- Pattern: compare execution-dependent response metadata as functional output,
  reset the cumulative baseline, use an executable identity inferred from a
  filename, or improve a result by changing runtime durability/shared-state
  settings.
- Required prevention: preserve raw responses, validate `took` only for shape
  and range in compatibility fixtures, and use it only as a latency measurement
  in the fixed benchmark workload. Record actual executable SHA-256, separate
  build directories, and runtime settings. Compare each scenario and topology
  with the immutable v0.6.0 baseline.

### PP-005: Native Collector Setup on a High-Segment Search Path

- Tags: `collector`, `allocation`, `native-query`.
- Level: `measured symptom`; the removed setup overhead is real by source
  inspection, but its share of full request latency is not isolated.
- Pattern: a native multi-sort collector creates per-segment boxed closures
  for fast-field reads and duplicates `SortSpec` values into each child
  collector. Write/refresh-heavy workloads create many small visible segments,
  magnifying setup cost before a collector sees its first matching document.
- Native review: Tantivy 0.21.1 supplies `TopDocs::order_by_fast_field` for a
  single field only. Its public `fast_fields().u64_lenient` API supplies typed
  native columns, so multi-key ordering must remain a narrow collector
  extension instead of falling back to source ordering.
- Required prevention: retain exact key encoding, missing-value ordering,
  segment/doc-address tie breaks and bounded per-segment windows; use typed
  `Column<u64>` values and share immutable sort specifications where possible.
  Do not infer a gate improvement from fewer allocations alone.
- Follow-up: child collectors were already bounded to `from + size`, but their
  fruits were flattened and fully sorted before global pagination. Retain only
  that same global prefix while merging sorted child fruits. This is an exact
  collector operation, not a source ordering fallback. Its latest full-gate
  measurement is directional only: the conservative fixed-baseline sort ratio
  moved from `0.924x` to `0.933x` single-node and from `0.889x` to `0.903x`
  three-node across separate candidates, while both remain below the required
  `0.950x`. Do not call it accepted until every fixed-baseline metric passes.

### PP-006: Native Authority Guard Performs Per-Shard Term-Dictionary Reads

- Tags: `native-query`, `fallback`, `ranking`.
- Level: `demonstrated` semantic overconstraint; performance contribution remains
  to be measured by the next isolated full gate.
- Pattern: a compatibility guard requires every selected shard to contain a
  query token before allowing Tantivy phrase scores. This causes repeated
  `Searcher::doc_freq` calls and rejects a native scorer merely because other
  refreshed shards correctly have no matching documents.
- Native review: Tantivy 0.21.1's phrase query and scorer operate per shard.
  The required admission conditions are a refreshed shard, no pending deletes,
  compatible native text metadata, and the indexed field's presence; a query
  term is not required in every shard.
- Evidence: a three-shard live OpenSearch 3.7.0-SNAPSHOT comparison placed
  `alpha beta` only on routing shard 2, with nonmatching documents on shards 0
  and 1. OpenSearch and SteelSearch returned the same IDs and exact emitted
  scores (`0.20836751`, `0.19191743`).
- Required prevention: do not reintroduce term-dictionary scans as a score
  authority condition without a minimal OpenSearch case proving a score
  difference. Retain the shard-distribution unit and HTTP fixtures.

### PP-007: Treat a Mixed-Workload Regression as an Attribution Problem

- Tags: `measurement`, `write-conversion`, `refresh`, `native-query`.
- Level: `measured symptom`; a write-only isolation rejected the hypothesis that
  the current single-document PUT path alone explains the full-gate write loss.
- Evidence: the execution-verified full gate reports three-node write ratios as
  low as `0.849x` versus v0.6.0. In the separate 45-second, write-only,
  three-node diagnostics using the identical corpus, clients, shard count and
  durability flags, v0.6.0 measured `3.421ms` mean / `5.235ms` p95 /
  `6.256ms` p99 while the current candidate measured `3.477ms` / `5.349ms` /
  `6.447ms` (`1.6%`, `2.2%`, and `3.1%` slower respectively). Candidate RSS
  was `1.184GB` versus `1.162GB` (`2.2%` higher). The artifacts are
  `target/v060-write-cpu-20260914/` and
  `target/native-phrase-shard-authority-write-cpu-20260914/`.
- Consequence: do not claim that Tantivy commit/reload, native replay, or a
  single PUT-route check is the demonstrated source of the full-gate write
  regression. The benchmark sets `STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH=1`
  for `refresh=false` writes, and the native refresh counters stay zero in the
  isolated write run.
- Required prevention: reproduce a suspected cost under a single operation and
  under the affected mixed workload before changing a correctness path. For the
  current gate, investigate refresh/search interference, runtime lock waits,
  and cross-node state activity with diagnostics that preserve the fixed
  workload; retain the full gate as the only release decision.

### PP-008: Native API Presence Is Not Score-Compatibility Evidence

- Tags: `native-query`, `ranking`, `fallback`, `measurement`.
- Level: `demonstrated` compatibility constraint and `measured symptom` for the
  current three-node ranking regression.
- Pattern: replace a narrow exact native extension with a public Tantivy query
  merely because the API exposes the same operation name. Pinned Tantivy 0.21.1
  has `PhraseQuery::new_with_offset_and_slop`, but its own sloppy phrase scorer
  documents an incorrect-count case for expanded positions. The local audit
  additionally proves a two-term, slop-1 repeated-position case with the same
  hit set but different scores and ordering from the exact phrase scorer.
- Product invariant: exact phrase membership, frequency-derived `_score`, and
  unequal-score ranking remain compatibility contracts. A faster native query
  that changes either score or ordering is not an optimization.
- Evidence: `tantivy_two_term_sloppy_phrase_score_diverges_from_the_exact_native_phrase_scorer`
  compares normalized pinned `PhraseQuery` with `NativePhraseQuery` over the
  preserved phrase-frequency corpus. It verifies equal document-address sets
  and requires at least one score divergence. The exact scorer is independently
  checked against the OpenSearch phrase-frequency reference.
- Required prevention: first compare membership, score bits and ranking against
  the narrow exact path and OpenSearch fixtures. Retain `NativePhraseQuery` as
  a postings/scorer extension, not a source fallback. Optimize its candidate
  admission, seek/reuse, or shard scheduling only after an isolated latency
  measurement; never replace it with the vendor scorer under the current pin.

### PP-009: Nested Timing Spans Include Their Child Logging Cost

- Tags: `measurement`, `native-query`, `response`.
- Level: `demonstrated` instrumentation risk.
- Pattern: a sampled outer span writes after sampled inner spans, while each
  span synchronously emits to stderr. The outer duration then includes child
  diagnostic I/O and cannot be interpreted as product execution time minus the
  child durations.
- Evidence: with the ranking-only, three-node, one-client diagnostic at
  `target/v070-bm25-generation-clients1-diagnostic-20260914/`, the same sampled
  `NormalizedBm25Query::weight` call reported 44.88us p50 while the explicitly
  timed generation comparison, field-statistics lookup, and inner Tantivy
  weight were 2.08us, 0.28us, and 3.04us. The missing time is the nested
  sample writes, not a demonstrated BM25 cost. The focused measurement also
  establishes the generation comparison itself is not a hot-path bottleneck.
- Required prevention: use leaf spans for attribution, or collect samples in
  memory and flush after the request. Never optimize an outer timing span until
  child instrumentation cost is excluded. Preserve raw diagnostic logs and
  distinguish them from acceptance benchmarks.

### PP-010: Request Admission Limit Can Underutilize Native Search

- Tags: `response`, `native-query`, `measurement`.
- Level: `measured symptom`; this is not an attribution for the remaining
  fixed-gate regression.
- Pattern: cap REST search admission at the logical CPU count even when each
  admitted request fan-outs into bounded native shard work. Under a small
  multi-client workload, the cap can add queueing delay while server CPU is not
  saturated.
- Evidence: identical 45-second, 5,000-document, three-node ranking-only
  diagnostics using v0.7.0 executable SHA-256
  `40830af495aadde1b922acd01ec2cb19a6ce0a9584c30b868a43e0982e807454`
  measured 1,031.48 ops/s and 3.866ms mean with pool size 3, versus 1,067.21
  ops/s and 3.737ms with size 6. Size 12 reached only 1,063.95 ops/s and
  worsened p95/p99 relative to size 6. The artifacts are
  `target/v070-ranking-cpu-compare-20260914-r1/matrix/`,
  `target/v070-ranking-pool6-diagnostic-20260914-r1/`, and
  `target/v070-ranking-pool12-diagnostic-20260914-r1/`.
- Required prevention: keep `STEELSEARCH_SEARCH_THREAD_POOL_SIZE` as an
  explicit override, bound the default to a measured small multiple of logical
  CPUs, and verify non-overridden behavior with focused and full workload
  evidence. This request-admission policy is outside Tantivy; no Tantivy API or
  source fallback is involved. Do not infer that higher concurrency improves
  every topology or operation from this one ranking diagnostic. The full gate
  still has 27 and 25 published-baseline failures in its two repetitions, so it
  does not establish release acceptance.

### PP-011: Same-Host Multi-Node CPU Competition Is Not a Product Improvement

- Tags: `measurement`, `native-query`, `response`.
- Level: `measured symptom`; not a candidate implementation or a benchmark
  configuration change.
- Pattern: a local three-node topology runs multiple Steelsearch processes on
  the same small host. Rayon defaults independently in each process, so a
  process-local native query worker configuration can compete for the same
  CPUs even when each request's outer shard reduction is sequential.
- Evidence: the isolated 45-second, four-client, three-node ranking diagnostic
  at `target/v071-rayon-one-ranking-diagnostic-20260914-r1/` used the changed
  executable SHA-256 `25f39d6a7e422e10c0679bd64f51ce1d929dd8123125d8f42b7095540326829e`
  with `RAYON_NUM_THREADS=1` and measured 1,085.24 ops/s, 3.675ms mean,
  6.174ms p95, and 7.587ms p99. The otherwise matching pool-size-6 diagnostic
  measured 1,067.21 ops/s, 3.737ms mean, 6.311ms p95, and 7.801ms p99. The
  small improvement establishes host-level contention as a contributor, not a
  dominant cause.
- Required prevention: do not change the published-baseline resource settings,
  runtime environment, or Rayon worker count to make a candidate appear to
  pass. A benchmark topology that colocates multiple nodes is valid for
  regression diagnosis, but it cannot establish a production default. Any
  product-level worker policy must be independently justified for both
  colocated and one-node-per-host deployments, then measured against the same
  fixed v0.6.0 settings.

### PP-012: Semantically Divergent Benchmark Responses Distort End-to-End Attribution

- Tags: `measurement`, `response`, `ranking`, `compatibility`.
- Level: `demonstrated measurement constraint`; it does not waive the fixed
  v0.6.0 gate or justify omitting any latency measurement.
- Pattern: a baseline can return a materially smaller HTTP response because it
  misses documents that the compatibility-correct implementation returns. An
  end-to-end benchmark then includes real client read/decode work for the
  candidate that the baseline never performs. Treating the whole difference as
  native scorer, collector, or response-body generation cost is unsound.
- Evidence: the preserved response-shape diagnostic in
  `docs/rust-port/write-interference-investigation-2026-09-11.md` found that
  the same ranking requests returned 0 hits and 160-byte average responses on
  the v0.6.0 baseline, versus 230 hits and 10,637.75-byte average responses on
  the compatibility-correct candidate. Its ABBA HTTP phase measurement found
  candidate ranking client JSON decode at about 0.234ms per request versus
  0.017ms for the baseline, while the candidate's `urlopen` phase was slightly
  lower. The response-body build counter in the later native ranking diagnostic
  was only about 4.8us per request.
- Required prevention: before attributing a benchmark regression to a server
  path, inspect returned hit counts, response bytes, and the client phases for
  the exact workload. Keep fixed-baseline metrics reported and investigate
  them, but separately report semantic-output differences. Never suppress hits,
  alter a correct response, or weaken fixture contracts merely to match a
  smaller historical response.

## Change Reviews

| Date | Change | Tags | Pattern comparison | Evidence and outcome |
| --- | --- | --- | --- | --- |
| 2026-09-14 | Raise sharded native page reduction's Rayon threshold from 2,048 to 10,000 documents. | `native-query`, `collector`, `measurement` | PP-008; no prior scheduling-specific entry. | Rejected. The 5,000-document, three-node, one-client ranking isolation at `target/sharded-page-sequential-ranking-clients1-20260914/summary.json` measured 1.236 ms mean, 1.957 ms p95, and 2.284 ms p99 over 24,076 requests. The preserved b38 candidate measured 1.224 ms, 1.938 ms, and 2.173 ms over 24,328 requests at `target/native-phrase-shard-authority-ranking-clients1-20260914/summary.json`. The sequential policy was 1.0% slower in mean latency, so it was reverted. The candidate passed the full non-plugin HTTP fixture 1,180/1,180 at `target/sharded-page-sequential-20260914/full-fixture-live/report.json`; this is functional evidence only, not a performance acceptance. |
| 2026-09-14 | Narrow refresh-batch Tantivy document preparation for plain text documents. | `write-conversion`, `refresh`, `allocation` | Matched `PP-002`; no other matching pattern. Tantivy 0.21.1 source/API was reviewed: direct `TantivyDocument::add_text` is the native path, while positioned array conversion and multi-field keyword conversion remain fallible. | Focused tests: `plain_text_documents_skip_preparation_but_arrays_keep_it` and `multi_field_append_conversion_failure_does_not_queue_partial_documents` passed. Preserved OpenSearch HTTP projection passed `1180/1180`, report `target/plain-text-preparation-full-20260914/report.json`, SHA-256 `652b337b318e4b6735474d585a977dc30223ae28ab4b439a003ef0821a537b9a`. Full v0.6.0 gate completed but failed: `22/44` lower ratios below `0.950x`; three-node `document_add` remained `0.458-0.478s` versus baseline `0.319-0.332s`. No improvement is claimed. |
| 2026-09-14 | Replace refresh-batch prebuild with native writer rollback on conversion/enqueue failure. | `write-conversion`, `refresh`, `allocation` | Matched `PP-002`; native Tantivy 0.21.1 `IndexWriter::rollback` source and upstream reuse-after-rollback test were reviewed. It resets to the previous commit, so it covers both deletes and documents queued by the failed refresh batch. | `multi_field_append_conversion_failure_rolls_back_partial_writer_batch` and `late_replay_is_not_lost_behind_the_refresh_watermark` passed. Preserved OpenSearch HTTP projection passed `1180/1180`, report `target/native-writer-rollback-full-20260914/report.json`, SHA-256 `199a0c130e81b2f080e2c55c94bceb3894c5ed978fc0eb278d7b9dd1f109bda1`. Candidate binary SHA-256 `0844e7315357c4bdca8194da46dfcf9ec940d4cb442957b967bb5b2c0dc818e6`. The valid full rerun is `24/44` below `0.950x`, so this change is not accepted. Component telemetry is directionally better than the prior prebuild candidate but does not establish a fixed-gate improvement. |
| 2026-09-14 | Replace boxed multi-sort field accessors and child `SortSpec` copies with typed Tantivy fast-field columns and shared specifications. | `collector`, `allocation`, `native-query` | Matched `PP-001` and new `PP-005`. Tantivy 0.21.1 `TopDocs` supports only one fast field; `fast_fields().u64_lenient` is the native extension point used for the existing exact multi-key collector. No source ordering or score fallback was added. | Exhaustive collector windows/missing-value/tie tests plus native multi-sort and page-offset tests passed. Preserved OpenSearch HTTP projection passed `1180/1180`, report `target/native-multisort-columns-full-20260914/report.json`. Valid gate `target/native-multisort-columns-full-gate-rerun2-20260914/result.json`, SHA-256 `4bf27b2895ed5613d88cbc15ace0fc1980babb0af01529a53165f1f6d77d69ef`, has 24/44 conservative published-baseline failures and 13 same-run failures. This is not an accepted performance improvement; continue with measured write/ranking/sort investigation. |
| 2026-09-14 | Keep only the requested global prefix while merging bounded native multi-sort collector fruits. | `collector`, `allocation`, `native-query` | Matched `PP-005`; no source fallback was admitted. Tantivy 0.21.1 provides child collector execution and typed fast-field columns but no public multi-key `TopDocs` collector, so this remains a narrow native collector extension. | Exhaustive collector, native tuple-order, and offset-window tests passed. Preserved OpenSearch HTTP projection passed `1180/1180`, report `target/native-multisort-merge-prefix-full-20260914/report.json`. Execution-verified gate `target/native-multisort-merge-prefix-full-gate-rerun-20260914/result.json`, SHA-256 `48e6539282c9fadc7869d8c4fe93db5de6985945bb36c24390a803a4eb63cf79`, candidate SHA-256 `c53dbbcdc601d4b743c42b00979302eb507b3c6c0c42fd16c8235bb37a5a42d7`, still has 24/44 conservative published-baseline failures. The sort ratios are directionally better than the preceding valid candidate, but this is not accepted performance evidence and the release remains blocked. |
| 2026-09-14 | Avoid allocating a path-walk `Vec<&Value>` when a native document field is a direct top-level source member. | `write-conversion`, `allocation` | Matched `PP-002`; `no-match` for `native-query`, `collector`, and `fallback`. Tantivy requires the values in the native document, but a direct top-level JSON object lookup has the same scalar/array semantics as the existing generic dotted-path walker. Dotted paths retain the walker. | Focused top-level/nested/missing-path and multi-field source tests passed. Preserved OpenSearch HTTP projection passed `1180/1180`, report `target/native-top-level-source-values-full-20260914/report.json`. Execution-verified gate `target/native-top-level-source-values-full-gate-20260914/result.json`, SHA-256 `dd16c850b82cb5c18a7df62b8036c434065008e57daf72c73245c15cabd6752f`, candidate SHA-256 `03dd5e9e4138e4f9f4d8e767b294cda46da660805a63ce75781ca9583adaf9b2`, remains 24/44 below the fixed threshold. Write ratios improved directionally versus the immediately preceding candidate but stay below `0.950x`; this is not accepted performance completion. |
| 2026-09-14 | Remove the phrase-score authority requirement that every selected shard contain a query token. | `native-query`, `fallback`, `ranking` | Matched `PP-001`; added `PP-006`. Tantivy 0.21.1 phrase scoring is shard-local. The old `doc_freq` condition was introduced without a minimal semantic proof and made a missing term on an otherwise healthy shard force source score correction. | Focused `native_phrase_scores_remain_authoritative_when_other_shards_lack_query_terms` and `native_exact_phrase_pages_preserve_native_scores_and_boosts` passed. `tools/fixtures/search-native-phrase-shard-distribution-compat.json` live OpenSearch comparison passed `1/1`, with exact IDs and scores. Preserved non-plugin HTTP projection passed `1180/1180`, report `target/native-phrase-shard-authority-release-20260914/full-fixture-search-rerun/report.json`; executable SHA-256 `b38f4c5d10bf1c4917b24957f38afc113f1e4f836e1ec96dd31687692cb25d9a`. Valid fixed gate `target/native-phrase-shard-authority-full-gate-rerun-20260914/result.json`, SHA-256 `607c18c3c166a6cb4034beae27a948bcfbf94efac2d0a0dc27654b4f336c5172`, is `26/44` below the fixed threshold. Single-node ranking is `1.027x`, but three-node ranking is `0.847x`; no acceptance or net performance claim is made. |
| 2026-09-14 | Isolate three-node write latency before modifying the write path. | `measurement`, `write-conversion`, `refresh` | Added `PP-007`. The full-gate write failure matched `PP-002` only superficially, but the benchmark defers native writes until refresh. | Current and v0.6.0 write-only diagnostics completed with verified executable identities. Candidate mean/p95/p99 were only `1.6%` / `2.2%` / `3.1%` slower, so no PUT or Tantivy change was made. Continue with mixed-workload, refresh and ranking interference diagnosis. |
| 2026-09-14 | Assess whether pinned Tantivy sloppy `PhraseQuery` can replace the exact phrase scorer on the ranking hot path. | `native-query`, `ranking`, `fallback`, `measurement` | Added `PP-008`; matched `PP-001`. Tantivy 0.21.1 source was reviewed before a replacement attempt. | The focused audit proves equal membership but at least one score/ranking divergence for a two-term slop-1 repeated-position case. No production replacement was made. The candidate's isolated three-node ranking mean is `1.224ms` at one client versus v0.6.0 `0.856ms`, and `3.687ms` versus `2.429ms` at four clients; these diagnostics guide further native optimization but do not replace the fixed full gate. |
| 2026-09-14 | Evaluate a native required-clause candidate pass before exact full-query scoring. | `native-query`, `ranking`, `collector`, `measurement` | Matched `PP-001` and `PP-008`. The candidate was a narrow native composition: collect `must`/`filter`/`must_not` addresses, then seek the exact full scorer at those addresses. | Rejected after the preserved OpenSearch HTTP fixture passed `1180/1180` at `target/native-required-candidate-ranking-release-20260914/full-fixture-live/report.json`, but an isolated 30-second, one-client, three-node ranking run measured `1.352ms` mean / `2.104ms` p95 / `2.444ms` p99, worse than the preceding candidate's `1.224ms` mean and v0.6.0's `0.856ms` mean. The additional candidate collection and scorer seek pass cost more than it saved for this workload. Revert the path; do not retry it without evidence that the required candidate set is substantially smaller. |
| 2026-09-14 | Use Tantivy 0.21.1 `MinimumShouldMatchQuery` for native bool `minimum_should_match=1`, instead of a nested all-`Should` `BooleanQuery`. | `native-query`, `ranking`, `collector`, `measurement` | Matched PP-001 and PP-008. The pinned implementation is a native threshold union that admits documents with at least one matching child and sums each matching child once. Existing focused overlap, filter, score, and 1/3-shard audits exercise the benchmark query shape. | Focused `native_ranking_audit_tests` passed for the candidate path, including `native_minimum_one_preserves_matches_and_scores_across_overlapping_shoulds`, `native_minimum_should_match_overlap_audit`, and `native_compound_authority_covers_benchmark_ranking_shape`. Live OpenSearch HTTP comparison with executable SHA-256 `797f28b8131382785ab83674036567a3d035061d50480e12668f897bacba4f6c` passed every non-plugin case: `1180/1180`; report `target/native-msm-one-candidate-20260914/full-fixture-live/report.json`. The report's sole failure is `bad_knn_vector_dimension`, whose reference lacks the k-NN plugin and is outside the agreed plugin-excluded scope. No performance claim or gate result is made: the follow-up benchmark is blocked until disk capacity is restored (92MB free after candidate build and report generation). |
| 2026-09-14 | Replace the exact phrase scorer's duplicate `TermQuery` candidate setup with an intersection of cloned native position postings. | `native-query`, `ranking`, `allocation`, `measurement` | Matched PP-008. Tantivy 0.21.1 `PhraseScorer` was reviewed: it intersects position postings directly. Steelsearch retains `NativePhraseQuery` and its exact frequency matcher; only its candidate enumeration now follows that native postings composition. | Focused native phrase tests and the vendor-divergence audit passed, followed by the preserved OpenSearch HTTP fixture `1180/1180` at `target/native-phrase-postings-candidate-20260914/full-fixture-live/report.json`; executable SHA-256 `d505badf514306733bce9e09c693831a2bb267177b6d1eb528505f748b697b97`. Two 30-second, one-client, three-node ranking samples averaged 1.212ms mean and 818.9 ops/s versus b38's 1.221ms and 813.2 ops/s, but p95 was effectively unchanged and p99 was 0.5% slower. Keep the correctness-preserving native cleanup, but do not claim it addresses the fixed gate or run a full acceptance gate on this signal alone. |
| 2026-09-14 | Record the v0.7.0 candidate's repeated fixed-v0.6.0 gate before beginning the next optimization unit. | `measurement`, `write-conversion`, `refresh`, `native-query`, `ranking`, `collector` | Matched PP-002, PP-005, PP-007, and PP-008. No product path was changed from this result alone. | The execution-verified six-run gate at `target/v070-core-gate-20260914/result.json` used candidate SHA-256 `40830af495aadde1b922acd01ec2cb19a6ce0a9584c30b868a43e0982e807454` and reports 26/44 conservative fixed-baseline values below 0.950x. Three-node throughput is 0.882x; worst write, lexical, ranking, sort, nested, and refresh latency ratios are 0.822x, 0.846x, 0.791x, 0.858x, 0.820x, and 0.698x. OpenSearch remains faster only in the inverse comparison: SteelSearch is 2.727x single-node and 7.156x three-node throughput relative to OpenSearch. This establishes symptoms, not cause attribution; next work must isolate mixed refresh/search interference before modifying an exact scorer or fallback. |
| 2026-09-14 | Raise the default REST search admission size from one logical CPU slot to two slots per logical CPU. | `response`, `native-query`, `measurement` | Added PP-010; no Tantivy API applies because this is REST request admission. Existing `STEELSEARCH_SEARCH_THREAD_POOL_SIZE` remains an override. | The focused pure-policy test `default_search_thread_pool_size_allows_two_requests_per_cpu` passed. Under the preserved v0.7.0 ranking-only diagnostic, pool size 6 was the local optimum: 1,067.21 ops/s, 3.737ms mean, 6.311ms p95, 7.801ms p99, versus 1,031.48 ops/s, 3.866ms, 6.599ms, 8.225ms at the former default 3. Pool 12 gave no further throughput gain. The changed executable SHA-256 `25f39d6a7e422e10c0679bd64f51ce1d929dd8123125d8f42b7095540326829e` passed the isolated preserved non-plugin HTTP fixture `1180/1180` at `target/v071-search-pool-candidate-20260914/full-fixture-isolated/search-compat-report.json`. The fixed v0.6.0 gate `target/v071-search-pool-full-gate-20260914/result.json` remains blocked: its two published-baseline repetitions have 27 and 25 failures, while the paired fresh-baseline comparisons have 21 and 14. Three-node throughput is 0.932x and ranking mean/p95/p99 are 0.829x/0.841x/0.796x in the first published comparison. Retain the bounded default as a demonstrated local improvement, not release acceptance; investigate distributed coordination and mixed-operation interference next. |
| 2026-09-14 | Diagnose the Rayon worker count under colocated three-node ranking load. | `measurement`, `native-query`, `response` | Added PP-011. No source, workload, or release runtime setting changed. | `RAYON_NUM_THREADS=1` improved the isolated ranking diagnostic modestly, from 1,067.21 to 1,085.24 ops/s and from 3.737ms to 3.675ms mean. This does not qualify for the fixed gate because it changes the historical resource setting; it is evidence of host-level CPU competition only. |
| 2026-09-14 | Replay consecutive deferred index writes under one engine store write lock before refresh. | `replay`, `refresh`, `allocation`, `measurement` | Matched PP-002, PP-007, PP-010, and PP-011. Tantivy 0.21.1 writer source was reviewed: native documents are still batched and committed only by the existing refresh path. This change does not introduce a source fallback, query scorer, or separate writer batch; it preserves seq_no order while avoiding per-document engine lock reacquisition. | Rejected. Focused engine replay ordering/metadata test and node admission test passed. Candidate SHA-256 `694ed25252064ba637fc101d1ead440a06d750308d52a497acac3323cb7afad1` passed the isolated core HTTP fixture `1180/1180`, failed `0`, skipped `0`, at `target/v071-deferred-replay-batch-fixture-20260914/search-compat-report.json`. The execution-verified full gate `target/v071-deferred-replay-batch-full-gate-20260914/result.json` finished all six runs with matching executable identities, but published v0.6.0 comparison failed 23 and 25 metrics in its two candidate repetitions. The same-run paired comparison still failed 9 and 16 metrics, concentrated in write and three-node ranking. It does not demonstrate a refresh bottleneck improvement; remove this implementation rather than retain unproven lock batching. |
| 2026-09-14 | Recheck sequential sharded-page reduction under the actual four-client, colocated three-node ranking condition. | `native-query`, `collector`, `measurement` | Matched PP-008, PP-010, and PP-011, plus the earlier rejected sharded-page threshold change. No scorer, result, or fallback behavior changed; only the 2,048-document Rayon threshold was raised to 10,000 for the candidate. | Rejected. Candidate SHA-256 `f1c9be0682174377f7209877ff311c8177ea3783e0508217e1388167d157a2ad` completed the identical 45-second, 5,000-document, four-client, three-node ranking diagnostic with 0 errors at `target/v071-sharded-sequential-ranking-diagnostic-20260914/summary.json`: 1,068.17 ops/s, 3.733ms mean, 6.252ms p95, 7.765ms p99. This is within measurement noise of the retained parallel policy's 1,067.21 ops/s, 3.737ms, 6.311ms, and 7.801ms. Do not retain or retry this threshold change without a workload with materially different shard count, corpus size, or verified CPU allocation. |
| 2026-09-14 | Permit search admission while a refresh is active, but continue to yield to queued maintenance work. | `response`, `refresh`, `native-query`, `measurement` | Matched PP-007, PP-010, and PP-011. Pinned engine source was reviewed before changing admission: `TantivyEngine::refresh` captures a plan under the store lock, performs the expensive native work on cloned search state, then publishes it; search takes an immutable snapshot under a read lock. This is a scheduling change only, not a visibility, scorer, or fallback change. | Focused policy and existing maintenance-priority tests passed. The isolated OpenSearch HTTP fixture passed `1180/1180`, failed `0`, skipped `0`, at `target/v0711-refresh-admission-fixture-isolated-20260914/search-compat-report.json`; the earlier non-isolated `1177/3/1` report is preserved at `target/v0711-refresh-admission-fixture-20260914/search-compat-report.json` and is attributed to its document-write prelude changing root-count fixture state, not suppressed. The execution-verified full gate used the preserved initial v0.6.0 SHA-256 `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57` and candidate SHA-256 `d662d6af0f76a057a08a0538a38bbe5b2bc74c961c7b8f65ba9e8b3756df59e8`; result `target/v0711-refresh-admission-full-gate-20260914/result.json` remains rejected. The conservative fixed-baseline table has `21/44` values below `0.950x`: three-node throughput `0.909x`; three-node ranking worst latency `0.834x`; refresh worst latency `0.711x` single-node and `0.771x` three-node. Steelsearch remains faster than OpenSearch in every table row, but that does not offset the fixed v0.6.0 gate. Retain this narrow policy because it preserves correctness and improves the observed gate relative to the prior request-pool candidate; do not call it accepted or use it to reset the baseline. |
| 2026-09-14 | Release the runtime document map before native deferred-write replay after validating the captured document identity. | `write-conversion`, `refresh`, `allocation`, `native-query`, `measurement` | Matched PP-002 and PP-007; distinct from the rejected per-batch engine store lock experiment. The pending replay already owns an immutable document `Arc` and establishes its refresh generation by pointer identity. Tantivy conversion, writer replay, and store locking do not require holding the runtime document map. | Focused refresh-generation boundary tests (3) and deferred replay tests (5) passed. The isolated OpenSearch HTTP fixture passed `1180/1180`, failed `0`, skipped `0`, at `target/v0711-runtime-lock-fixture-isolated-20260914/search-compat-report.json`. Execution-verified full gate `target/v0711-runtime-lock-full-gate-20260914/result.json` used candidate SHA-256 `faf6886691b8dc2dec445461de9ab6f19f0e1eeb9f9ede99264e3b669a0a7d46` and remains rejected, but the conservative fixed-baseline count improved from `21/44` to `20/44` below `0.950x`. Three-node throughput improved `0.909x -> 0.919x`; three-node write `0.835x -> 0.849x`; three-node refresh `0.771x -> 0.854x`. Three-node ranking slightly regressed `0.834x -> 0.830x`, so this is not an accepted solution or evidence that replay dominates ranking. Retain the critical-section reduction because it preserves the captured-generation contract and improves the overall fixed-gate count; continue with ranking and mixed-workload investigation. |
| 2026-09-14 | Re-measure ranking-only after runtime document lock reduction before changing the native query path. | `measurement`, `native-query`, `response` | Matched PP-008, PP-010, and PP-011. The candidate does not alter the read-only ranking path, so a ranking-only measurement must not be used as evidence that the write/refresh lock change improved its scorer or fan-out. | Diagnostic only, not a gate: `target/v0711-runtime-lock-ranking-diagnostic-20260914/summary.json` used candidate SHA-256 `faf6886691b8dc2dec445461de9ab6f19f0e1eeb9f9ede99264e3b669a0a7d46`, 5,000 documents, three colocated nodes, four clients, 45 seconds, and `ranking=100`. It completed 48,044 requests with no errors: 1,067.55 ops/s, 3.733ms mean, 6.247ms p95, and 7.654ms p99. This is within noise of the retained pool-size-6 ranking diagnostic (1,067.21 ops/s, 3.737ms, 6.311ms, 7.801ms). The active node's response-body build counter was 231,691,239ns total, about 4.8us per successful request, so response JSON materialization is not the demonstrated main cost. Do not retry runtime document-lock or response-body changes for ranking without new mixed-workload evidence; inspect the native compound scorer and colocated shard scheduling next. |
| 2026-09-14 | Compare a two-distinct-term direct sloppy-frequency formula with the retained Lucene-adapted matcher. | `native-query`, `ranking`, `measurement` | Matched PP-008. Tantivy 0.21.1 `PhraseScorer` source was reviewed, but its known sloppy-count limitation prevents it from replacing the exact scorer. The proposed fast path retained native postings and was restricted to two different terms with small slop, yet still required equivalence with the exact local matcher. | Rejected before production adoption. The exhaustive small-position-set test found `first=[0]`, `second=[0,1]`, offsets `(0,1)`, slop `1`: direct pair summation returned `1.5`, while the Lucene-adapted matcher returned `1.0`. A term position cannot be treated as independently reusable across every apparent sloppy alignment even when the query terms differ. The code was removed with no retained product diff, fixture run, or performance claim. Do not replace the matcher with pair-window summation unless a complete traversal-equivalence proof covers the matcher’s advancement and collision semantics. |
| 2026-09-14 | Reduce the explicit REST search admission pool from six to three slots during mixed three-node load. | `response`, `refresh`, `measurement` | Matched PP-010 and PP-011. This was a diagnostic-only environment override, not a source or default-policy change. | Rejected. The identical 45-second, 5,000-document, four-client, three-node mixed workload completed without errors at `target/v0711-runtime-lock-mixed-pool3-diagnostic-20260914/summary.json`, using retained candidate SHA-256 `faf6886691b8dc2dec445461de9ab6f19f0e1eeb9f9ede99264e3b669a0a7d46`. Pool three produced 874.42 ops/s, 3.348ms write mean, 8.987ms ranking p95, and 18.828ms refresh p95. The matching default-pool-six diagnostic at `target/v0711-runtime-lock-mixed-default-diagnostic-20260914/summary.json` produced 875.08 ops/s, 3.344ms write mean, 9.015ms ranking p95, and 18.232ms refresh p95. The small ranking p95 difference is noise while throughput and refresh do not improve. Do not globally shrink the default pool or build a maintenance-specific cap from this evidence; diagnose native refresh commit and mixed-operation scheduling instead. |
| 2026-09-14 | Audit whether Tantivy indexing-worker fan-out causes colocated refresh CPU contention. | `refresh`, `native-query`, `measurement` | Matched PP-011. Tantivy 0.21.1 source was inspected before introducing an explicit writer-thread setting. | No change required. Steelsearch creates its writer with `TANTIVY_WRITER_HEAP_BYTES = 16 MiB`. Pinned Tantivy's `Index::writer` divides that budget by the CPU-derived worker count, then falls back to `max(1, total_budget / MEMORY_BUDGET_NUM_BYTES_MIN)` when the per-worker budget is under the 15,000,000-byte minimum. Therefore this production writer already has exactly one indexing worker, independent of host CPU count. Sources: `vendor/tantivy/src/core/index.rs:582-588` and `vendor/tantivy/src/indexer/index_writer.rs:28-35`. Do not add a redundant `writer_with_num_threads(1, ...)` call or attribute the remaining commit latency to writer-worker oversubscription. |
| 2026-09-14 | Restore the declared Rust 1.76 MSRV in the refreshed-document comparison. | `build`, `refresh`, `compatibility` | No performance-ledger pattern applies. This is a toolchain contract repair required before any new candidate can be compiled or tested. | `Cargo.toml` declares `rust-version = "1.76"`, but `StoredShard::documents_changed_since_refresh_through` used `Option::is_none_or`, which is unavailable in Rust 1.76. Replaced it with equivalent `map_or(true, ...)`. A fresh Rust 1.76 release diagnostic build succeeded at `target/v0711-sort-timing-build-20260914/release/steelsearch`; its standalone non-plugin search fixture passed `1180/1180`, failed `0`, skipped `0` at `target/v0711-msrv-compat-fixture-isolated-20260914/search-compat-report.json`. The preceding non-isolated `1178/4/16` report is preserved and classified separately: three root-count failures were caused by the runner's document-write prelude changing `.tasks` state, and the remaining KNN case is within the agreed plugin exclusion. Never treat the non-isolated report as a product regression or silently discard it. |
| 2026-09-14 | Isolate current and fixed-v0.6.0 native multi-sort performance before revising the collector. | `collector`, `native-query`, `measurement` | Matched PP-005, PP-007, PP-010, and PP-011. The native collector had already been optimized twice; this run distinguishes a collector regression from mixed write/refresh interference. | No collector change. Identical 45-second, 5,000-document, four-client, three-node, `sort_filter=100` diagnostics completed without errors. Fixed v0.6.0 SHA-256 `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57` at `target/v060-sort-filter-diagnostic-20260914/summary.json` measured 1,412.37 ops/s, 2.822ms mean, 4.897ms p95, and 6.088ms p99. The current diagnostic feature binary at `target/v0711-sort-timing-diagnostic-20260914/summary.json` measured 1,413.24 ops/s, 2.820ms mean, 4.862ms p95, and 6.032ms p99. Sparse native samples show sharded page mean 0.181ms, fan-out 0.138ms, Tantivy search 0.028ms per shard, and HTTP total 0.543ms; the external mean includes scheduling/queueing. Do not optimize the multi-sort collector without a new workload proving an isolated loss. |
| 2026-09-14 | Add diagnostic-only refresh phase spans and test a two-worker native writer. | `refresh`, `write-conversion`, `measurement` | Matched PP-007 and PP-011. The spans compile only with `diagnostic-search-timing`; normal release builds do not include them. Pinned Tantivy source confirms 16 MiB total writer memory selects one worker because each worker needs 15 MB. | Rejected and reverted. In the current 1-worker mixed diagnostic at `target/v0711-refresh-phase-diagnostic-20260914/`, sampled means were 0.004ms for native-text compatibility, 0.022ms for document build, 0.159ms for writer enqueue, and 5.669ms for Tantivy commit. Raising the native writer heap to 30 MiB creates two workers, but the matching diagnostic at `target/v0711-writer-two-workers-diagnostic-20260914/summary.json` dropped throughput from 869.20 to 840.57 ops/s and worsened refresh p95 from 19.448ms to 22.541ms. The extra worker increases colocated CPU/merge contention; retain the 16 MiB/one-worker production setting and do not retry this writer-thread change under the fixed topology. |
| 2026-09-14 | Add an ASCII-only fast path to the required custom OpenSearch standard tokenizer. | `write-conversion`, `allocation`, `measurement` | Matched PP-002 and PP-007. The custom tokenizer remains necessary for demonstrated OpenSearch Unicode semantics; this candidate did not replace it with Tantivy's built-in tokenizer. The ASCII scanner was compared exhaustively against the existing tokenizer over all inputs through length five from `aZ1 '-_`, plus the 255 UTF-16-unit boundary. | Rejected and reverted. The candidate passed the isolated non-plugin OpenSearch HTTP fixture `1180/1180` at `target/v0711-ascii-tokenizer-fixture-isolated-20260914/search-compat-report.json`, executable SHA-256 `ca1a6340d4585811051313130b19b8f90e692e4a04cb83360ce0d7689139cb9e`. Its identical 45-second mixed three-node diagnostics measured 863.21 and 870.19 ops/s at `target/v0711-ascii-tokenizer-mixed-diagnostic-20260914/summary.json` and `target/v0711-ascii-tokenizer-mixed-diagnostic-repeat-20260914/summary.json`, averaging 866.70 ops/s versus the retained current diagnostic's 875.08 ops/s. Avoid allocating character indices only when profiling proves it matters; this implementation did not improve the mixed workload and must not be retained. |
| 2026-09-14 | Attribute the benchmark ranking query's exact slop phrase scorer before changing it. | `native-query`, `ranking`, `measurement` | Matched PP-008 and PP-012. The workload contains `multi_match(best_fields)` plus `match_phrase` with `slop=1`; the pinned Tantivy scorer remains score-incompatible for this proven case, so the exact `NativePhraseQuery` is required. | No source change. Diagnostic executable SHA-256 `ca1a6340d4585811051313130b19b8f90e692e4a04cb83360ce0d7689139cb9e` completed the 45-second, 5,000-document, four-client, three-node `ranking=100` run at `target/v0711-native-phrase-ranking-diagnostic-20260914/summary.json`: 1,076.72 ops/s, 3.704ms mean, 6.258ms p95, 7.690ms p99. Sparse spans show native phrase scorer mean 6.976us and find-match mean 2.458us, while per-shard Tantivy search is 104.388us and engine search is 581.376us. The exact phrase path is not the demonstrated ranking bottleneck; do not replace or micro-optimize it without a workload where its fraction is material. |
| 2026-09-14 | Attribute mixed-workload refresh latency with diagnostic-only runtime phase spans. | `refresh`, `replay`, `measurement`, `native-query` | Matched PP-007 and PP-011. The spans compile only with `diagnostic-search-timing`; normal release builds do not include them. | No production path changed. The diagnostic binary SHA-256 `7be1098b8ceba2e949f7a8376f0454bb2d8728583b7090f4271e219c030104c6` completed the mixed three-node run at `target/v0711-refresh-native-timing-diagnostic-20260914/`. Sampled refresh route time was 41.620ms: native engine refresh was 36.667ms, deferred replay 4.241ms, visibility capture 0.172ms, dirty-shard marking 0.224ms, visibility publish 0.198ms, persistence 0.004ms, and admission 0.003ms. This rules out queue admission, replay capture/sort selection, visibility publication, and persistence as the dominant contribution. The next investigation is inside the native engine refresh path; no configuration or replay change is justified by this evidence, and the fixed v0.6.0 gate remains unmet. |
| 2026-09-15 | Measure mixed-workload refresh owner, plan, publish, and search-snapshot lock contention before changing lock scope. | `refresh`, `measurement`, `native-query` | Matched PP-007 and PP-011. Existing `diagnostic-lock-timing` was enabled only in the diagnostic executable; no lock behavior changed. | No production path changed. The three-node, 45-second mixed run at `target/v0711-refresh-lock-timing-diagnostic-20260915/` used SHA-256 `7e93f7ee083bf4c0f6de678a5672b32f5258529f9ea32c6471be8b87bc2e9a1c`. `refresh_owner` wait was 0.000068ms mean and 0.000240ms max across 30 samples; plan, publish, and search-snapshot waits were also below 0.001ms. The owner lock was held for 27.162ms mean, but it protects the already-measured native refresh work rather than blocking concurrent owners. The diagnostic writes a sample to stderr every 64 lock acquisitions and reduced observed throughput to 686.40 ops/s, so its latency/throughput is diagnostic-only and not comparable to the normal binary. Do not weaken refresh ownership or reader/write locking; next attribution must isolate native refresh and replay execution below this lock. |

### Correction: PP-012 Tokenizer Measurement

- The earlier PP-012 Change Review incorrectly compared a
  `diagnostic-search-timing` executable against a non-instrumented executable.
  That comparison is not performance evidence and must not be used to infer a
  regression.
- A follow-up used only non-instrumented executables in an ABAB sequence. The
  retained control SHA-256 `faf6886691b8dc2dec445461de9ab6f19f0e1eeb9f9ede99264e3b669a0a7d46`
  measured 864.91 and 868.03 ops/s; the ASCII candidate SHA-256
  `c35fe5fad9fbcd7cf77ef6956e776e4544d7bfdd1db263addc6424167972ca6d`
  measured 865.50 and 875.73 ops/s. The candidate's mean throughput was 0.48%
  higher, inside observed run-to-run variation, while mean refresh latency was
  9.67ms versus the control's 9.33ms. Both use the same 45-second,
  5,000-document, four-client, three-node mixed workload. Evidence:
  `target/v0711-ascii-tokenizer-{control,normal}-mixed*-20260914/summary.json`.
- The candidate passed the non-plugin fixture 1,180/1,180 with the normal
  executable at
  `target/v0711-ascii-tokenizer-normal-fixture-isolated-20260914/search-compat-report.json`.
  It remains rejected and reverted because it does not produce a reproducible
  fixed-gate improvement. Future candidates must compare executable feature
  sets identically before interpreting throughput or latency differences.

## Review Queries

Use these exact searches before beginning a change, then add the result to a
Change Review row:

```sh
rg -n 'write-conversion|refresh|replay|native-query|collector|response|fallback|allocation|measurement' \
  docs/rust-port/performance-pain-point-ledger-2026-09-14.md
rg -n 'Tantivy API or feature under consideration' \
  vendor/tantivy crates/os-engine-tantivy/src
```

The second search is an investigation step, not proof of a library limitation.
