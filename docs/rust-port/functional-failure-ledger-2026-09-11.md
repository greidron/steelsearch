# Functional Failure Ledger

Latest candidate d1407ff6 retains2466 passed/205 failed in the identical41-fixture
HTTP suite. Deferred-write realtime term-vector reads now return the correct document,
version and tokens in two existing failures; field statistics still differ, so neither
case is counted as passing. Evidence: native-termvectors-deferred-replay-live/audit.json.
Additional daemon integration coverage found one pre-existing lifecycle failure
(shutdown after recovery failure returns503 where the test expects200), independently
reproduced on preserved11d91339. Three poison-induced follow-on failures are not three
additional product defects. This integration finding is outside the2671 HTTP case set
and remains open; do not claim complete node-suite success or exclude recovery safety.

Latest per-field-analyzer candidate37998881 also has2466 passed/205 failed, with no
status transitions or regressions. Stored/generated keyword overrides now reproduce
OpenSearch terms, positions and offsets; the two original override cases remain failed
only because shared native field totals are12 where OpenSearch reports14. This is a
real corpus-statistics failure, not a score tolerance or metadata normalization case.
The dedicated OpenSearch probe adds4/4 passing analyzer cases outside the fixed2671
ledger and covers arrays, implicit selection, unknown fallback and native analyzer
selection. Custom analyzer configurations remain unsupported.
Engine975, node library695, node binary459, daemon53 and OpenAPI1 functional tests
pass for this candidate. No benchmarks ran.

Latest directive2026-09-11 overrides all older per-unit benchmark instructions in this
ledger and linked plans: finish functional compatibility first, then benchmark and
optimize while preserving passing functional tests. Benchmarks are stopped throughout
functional repair. Fixed initialv0.6.0 cumulative limits and release conditions remain.
Current verified11d91339 functional dev binary:2466 passed/205 failed/skip0 of2671
cases after correcting elapsed-time comparison. The same binary first passed2458 with
213 failures under unchanged fixtures;75 cases improved against132d8d6f with no new
regressions. A subsequent comparator-only correction resolved8 timing false failures,
not8 additional product implementations. The original292-case inventory below is
retained;87 of those cases now pass, including4 earlier fetch fixes and8 comparator
corrections. This unoptimized binary is not performance evidence.
Partial interrupted benchmark results are not an acceptance.

## Latest Functional Verification

Latest evidence: target/core-replacement-c06/native-termvectors-metadata-contract-live.
Same11d91339 executable and reference build;41 fixtures/2671 identical case keys.
Only the80 positions cases changed extractor from source_body to the already-existing
term_vectors contract. Request bodies, expected statuses and all other fixture values
are unchanged. The old fixture is preserved in candidate/artifacts/
array-positions-before-timing-normalization.json. Top-level took validates as a
nonnegative integer; document fields, IDs, versions, positions, offsets and statistics
remain exact. Fields or terms NAMED took inside document data are not stripped.
User explicitly clarified execution-dependent metadata must be distinguished from
document/search semantics. This is now a persistent AGENTS.md rule, not a performance
latency exemption. All21 search comparator tests pass, including fixture wiring and
nested took preservation regressions.

Full rerun:2466 passed/205 failed/skip0, setup failures0, count probe passed, new case
regressions0. Exactly8 old failures changed status; no binary change was involved.
Execution SHA119217e09a19f5466e532046a9f6d6754ede0f206ddd911cb1ad1025893d9f22.
Candidate artifacts/http-metadata-audit.json SHA:
328fca0c02637040cf2d3a6fc34af39efd93ecebc3eb018b167c51ab0c4e930f.
The before-normalization execution/audit below is preserved as historical evidence.

Evidence: target/core-replacement-c06/native-termvectors-functional-live.
Binary SHA:11d9133988f2c67923dba19a208b53cf7e02db6b47039c75a011022365c6320c.
Execution SHA:02bd82f6dbc3f827b1547daf67b689962f55c58368f251a8be998c7c1d3e0ad3.
Audit: native-termvectors-candidate/artifacts/http-functional-audit.json under the same
c06 directory; SHA732fd73a31659595240b0580f855aaea90c43f78e924649f0429b12e9cd4bb2a.
All41 fixtures completed, setup failures0, count probe passed. Report hashes verified.
Reference remains OpenSearch3.7.0-SNAPSHOT/f991609d190dfd91c8a09902053a7bbfe0c27b3e.

Array-position family:72 newly passing cases;8 remaining comparisons differ ONLY in
top-level took. Their full extracted responses are equal after removing that field.
Do not make the product fabricate equal timing values. These remain counted as failed
until the fixture's elapsed-time contract is explicitly corrected and revalidated;
the existing term_vectors extractor validates nonnegative integer timing while keeping
all other response fields exact. No comparator or fixture was changed in this run.
Array ranking's55 failures remain unchanged.

Termvector contract:3 newly passing cases,19 failures remain. Preserved raw reference
proves the standard tokenizer includes emoji terms which current SimpleTokenizer drops;
that also changes corpus field totals for non-emoji target documents. Native Unicode
tokenizer parity, artificial/analyzer/multi-request contracts and other discovered
gaps remain in scope. Current engine975/node1145 tests passing do not prove these gaps
resolved. The full implementation and release remain incomplete; no benchmark ran.

This is a case inventory, not a count of independent bugs or missing features.
Functional repair precedes performance-only optimization. Native capabilities must
be checked before adding replacement logic. Plugins remain outside this scope.

## Fixed Inventory

Measured executable SHA-256:
`d8fd7ce603ac78ecc9d2d7c4a558fe508bcb38caafc710a3e01c5727d4f4b544`.
Evidence directory: `target/core-replacement-c06/native-fetch-projection-release-live`.
Execution SHA-256:
`b5d088f025edb8bb3755bef7e9f8b4a2490b9eee5a78b89a639d8b3c03f34da3`.
All report names below are relative to that directory. Actual report cases were
recounted: 2367 passed, 292 failed, zero skipped across 2659 cases/40 fixtures.

| Report | Failed | Initial investigation, not proven root cause |
| --- | ---: | --- |
| search-bm25-routing-scope-compat-report.json | 17 | Routing/alias statistics and scoring |
| reference-fixture-report.json | 10 | Text ranking and field statistics |
| stable-reference-fixture-report.json | 8 | Phrase scores/ranking |
| search-native-phrase-explain-compat-report.json | 14 | Phrase scoring, explain and numeric comparison |
| search-native-exact-phrase-scores-compat-report.json | 3 | Score rounding/precision comparison |
| search-native-compound-ranking-compat-report.json | 22 | Compound scores and equal-score ordering |
| search-native-array-positions-compat-report.json | 135 | 80 positions-family cases, 55 ranking-family cases |
| search-native-phrase-frequency-compat-report.json | 41 | Phrase frequency, scores and ordering |
| search-native-termvectors-contract-report.json | 22 | Term vector contract, positions/offsets/statistics |
| search-native-aggregation-collector-contract-report.json | 6 | Date parsing, bucket limits and mixed aggregation |
| search-native-aggregation-date-parsing-contract-report.json | 10 | Date mapping interpretation and rendering |
| search-native-fetch-projection-contract-report.json | 4 | Invalid options, empty fields and unrequested fields |
| Total | 292 | Shared causes must be established, not inferred from counts |

Some observed score comparisons differ only at the sixth decimal place (for example
0.131499 versus0.131500). Some compound failures differ in equal-score ordering.
These are not proof of missing search functionality. Inspect the request's ordering
contract and numeric comparator before changing the scorer. Do not globally loosen
equality or add a tolerance without an explicit, scoped agreement. Conversely, routing
examples include materially different scores, so not all ranking failures are rounding.

A diagnostic recount of the292 failures found51 search_scores cases with identical
status/total/ordered IDs and maximum absolute difference at most0.0000011 on the
already six-decimal-rounded scores. Another18 have identical IDs but larger score
differences,101 differ in IDs or order, and122 use other extractors. This is NOT an
approved tolerance, raw-score accuracy bound, or51 repaired cases. Raw float values,
relative error near zero, tie behavior and query contracts still need inspection.
The machine-readable audit is
`target/core-replacement-c06/native-fetch-visibility-candidate/artifacts/parent-score-difference-audit.json`.
No comparator or fixture was changed by this diagnostic.

## 2026-09-12 Scoped Relevance Comparison Decision

The user approved a scoped numeric comparison contract after inspection of the raw
OpenSearch and Steelsearch scores. For default relevance-only searches with no
`sort`, `min_score`, `search_after`, PIT, or scroll control, score values compare with
`abs(a-b) <= max(1e-6, 1e-6 * max(abs(a), abs(b)))`. This reflects bounded
cross-engine floating-point variation; it is not a general score-accuracy waiver.

Within that same scope, documents with exactly equal emitted scores have no required
cross-engine relative order. Steelsearch must still be deterministic for identical
index state and request. The dedicated extractor canonicalizes only those tied groups;
its 20-request repeat check produced one `took`-excluded response SHA. Membership,
totals, page boundaries, non-tied ranking, explicit sort values, `min_score`,
`search_after`, PIT, and scroll remain exact. The persistent agent rule is in
`AGENTS.md`; extractor and fixture-scope regression tests enforce this decision.
The fixed OpenSearch `3.7.0-SNAPSHOT` reference (build
`f991609d190dfd91c8a09902053a7bbfe0c27b3e`) then passed all120 phrase-frequency
cases against the current candidate; report:
`target/core-replacement-c06/phrase-frequency-live-v6/search-native-phrase-frequency-compat-report.json`.
This removes41 cases from the prior205 functional failures alongside the separately
verified10 date-histogram repairs, for a projected154 remaining failures pending the
required full fixture rerun. It is not a new product scoring implementation.

## 2026-09-12 Native Array Phrase Ranking Repair

The 55 array phrase-ranking failures were a product routing defect, not a score
tolerance case. Array positions, field norms, and postings were already native, but a
field-wide compatibility guard rejected ASCII numeric/boolean values and non-default
valid position gaps. That forced all phrase scoring on the field through the
source-BM25 fallback. The repair admits only values indexed equivalently by the native
path: ASCII strings, numbers, booleans, nulls, and nested arrays thereof; objects and
non-ASCII strings remain excluded. It also accepts only parseable `u32` numeric or
string position gaps while retaining analyzer, norms, index-option, and similarity
guards.

The isolated working source is
`target/core-replacement-c06/native-termvectors-source`. Its functional debug
executable SHA-256 is
`cf6969c0c86b0a7d7c7510e12691f81283855b959ad7322a8c13595cb966a7e8`.
Against the pinned OpenSearch `3.7.0-SNAPSHOT`
`f991609d190dfd91c8a09902053a7bbfe0c27b3e`, the unchanged array fixture passed
135/135: ranking 55/55 and term-vector/position 80/80. Evidence:
`target/core-replacement-c06/native-array-ranking-guard-live-20260912/report.json`.
Focused eligibility and native array-position tests passed before live comparison.
This moves the projected remainder from154 to99 (`205 - 41 - 10 - 55`), pending the
required full 41-fixture rerun. No benchmark was run under the functional-first
directive, and this unit is not marked complete.

## 2026-09-12 Full Functional Rerun After Array Repair

The full isolated-candidate HTTP rerun completed all41 preserved fixtures with
2616 passed /55 failed /0 skipped (2671 cases). It used the executable identified in
the preceding array-ranking entry and the pinned OpenSearch reference. Relative to the
preserved 2466 passed /205 failed result,150 named cases changed from failed to passed
and no previously passing case regressed. Reports are in
`target/core-replacement-c06/full-functional-rerun-20260912/`.

The JSON snapshot cat fixture initially exposed stale filesystem repository state in
the reference: snapshot creation permits400, so a reference node can list a prior
snapshot while a fresh Steelsearch data directory has no row. A dedicated JSON snapshot
extractor now permits an empty result but verifies the exact selected alias-column set
on every returned row. It applies only to that state-dependent fixture; no general cat
or response-field comparison was relaxed. The extractor has regression coverage.

The remaining55 cases are: BM25 routing17, native term-vector contract19, stable
phrase ranking8, compound ranking7, explicit field-sorted exact phrase scores2, and
native aggregation collector2. The field-sorted cases remain exact by policy despite
their small score deltas. No performance benchmark ran; functional repair continues.

Aggregation reference503 responses must be interpreted using the raw error, not copied
as arbitrary product failures. Earlier date diagnostics establish a large generated
bucket span caused by the default mapping interpreting1000 as a year; preserve the
mapping, resource-limit and explicit epoch_millis control cases.

## Newly Detected Failures

The stronger source-visibility comparator adds12 cases, beyond the292 inventory.
Parent control: `target/core-replacement-c06/native-fetch-visibility-parent-live`.
Three fail: stored-default, stored-string-default, stored-source-overrides-disabled
(all with the `native-fetch-visibility-` prefix). The other nine pass. Original fields
comparisons did not detect implicit source exposure. Preserve both old and new evidence;
do not claim the original292 was an exhaustive contract audit.

## Execution And Acceptance

The subsequent read-only native audit groups22 termvector-contract and80 array-position
cases around the existing REST termvector path (not102 independent defects). Parent
inspection confirms that build_term_vectors reads only Value::as_str, makes the entire
string a single term, uses byte length for the end offset, and hard-codes statistics
to1. Field selection, capability metadata, flags and realtime reader semantics require
separate verification. The55 ranking-family array cases are not automatically repaired
by replacing this response builder. Existing native indexing tests do not prove the
public termvector endpoint correct.

Pinned Tantivy exposes segment readers, inverted indexes, term dictionaries and
WithFreqsAndPositions postings. Current persisted product state is not a persisted
termvector/offset store: the native search state uses a refresh-built directory, and
postings do not expose start/end offsets. Native analyzer reanalysis of the selected
document is a possible bounded offset path, not proof of stored-offset support.
Do not substitute a source-wide analyzer/scorer or claim a missing product API means
Tantivy has no native capability. Refreshed/native snapshot resolution, UTF-16 offsets,
arrays/gaps, generated/artificial fields, analyzer overrides, realtime pending writes,
deletions and statistics remain in the overall target scope. Incremental implementation
must not silently exclude these harder cases or count a narrow stored-only path as full
termvector completion. No product edits or tests resulted from this read-only audit.

Luna's read-only fetch audit locates the next four fixes in the REST boundary:
reject `_source` object key `fetch`; reject body-level `_source_include(s)` and
`_source_exclude(s)` BEFORE merging valid URL source parameters; accept `fields:[]`;
and prevent source-only projection from emitting unrequested `fields`. The current
visibility binary is frozen, so these are not implemented in it. Preserve valid URL
parameters, explicit source selection and source filters in regression tests. Inspect
engine-internal projection contracts separately instead of assuming the REST parser's
rejection rules should redefine internal SearchRequest semantics.

1. Finish the in-flight fetch visibility unit, including corrected legacy source
   expectation backed by raw OpenSearch responses. Keep its first failed node log.
2. Investigate the large native positions/phrase/statistics groups and term vectors
   using existing native audit evidence and pinned APIs. Separate cosmetic comparator
   differences from result-set, statistics, offset and actual scoring defects.
3. Repair date/aggregation and remaining request/response contracts, retaining controls
   for arrays, explicit mappings, invalid requests and protective resource limits.
4. After EACH implementation unit run full engine/node tests, expanded HTTP without
   dropping scenarios, and the full non-plugin six-run/twelve-topology benchmark.
   Focused tests are diagnostics only. Use separately built, identified executables
   and identical actual workload, durability, security and resource settings.
5. Keep functional repair and acceptance separate. Fixed initialv0.6.0 throughput must
   remain at least95% per topology and each scenario mean/p95/p99 at most105% cumulatively.
   Do not offset failures with improvements, reset the baseline, waive safety, or claim
   normal completion/release for an over-budget candidate. Apply the main plan's repeated
   measurement and exclusion/explicit-exception rules. Preserve original release evidence.

No new functional unit, TV1, release or whole-plan acceptance is established by this
inventory. Current fetch visibility still needs complete tests, live HTTP and performance.

## 2026-09-13 Native Descending Missing Sort Repair

The native multi-sort collector encoded a missing descending fast-field value ahead of
present values. This was exposed by the first page of
`search_after_multi_sort_search`: with `size: 1`, Steelsearch returned the document
without `age`, while OpenSearch returned the document with `age: 24`. The later
`search_after` request then received the wrong cursor and returned no document.

Tantivy's fast-field column remains the execution source. The repair changes only the
collector key encoding: present descending values use rank `0` and their inverted
fast-field encoding; missing values use rank `1`, matching OpenSearch's default
`missing: _last` behavior. It does not add source-level scoring or re-evaluation.
The focused engine test
`native_tantivy_page_sort_keeps_missing_values_last_in_both_directions` covers
ascending/descending tuple sorting and, critically, a descending `size: 1` window.
It passed with `cargo +nightly test --locked --offline -p os-engine-tantivy
native_tantivy_page_sort_keeps_missing_values_last_in_both_directions --lib --quiet`.

The exact HTTP fixture `search_after_multi_sort_search` subsequently passed against
the pinned OpenSearch reference. Report:
`target/core-replacement-c06/unicode-scanner-functional-live/search-after-multi-sort-final-report.json`
(SHA-256 `b44865279758dc72da5dfc62c4279e080297a45f509f08ffe026f9a3ffa9b77c`).

Per the functional-first gate, the full preserved 41-fixture driver was started before
beginning another repair. It fails closed because these seven preserved fixture inputs
are absent from the workspace:

- `target/core-replacement-c05/bool-minimum-compat.json`
- `target/core-replacement-c05/nested-bool-canonical-compat.json`
- `target/core-replacement-c05/nested-bool-final-compat.json`
- `target/core-replacement-c06/pipeline-selection-compat.json`
- `target/core-replacement-c06/native-ranking-audit/reference-fixture.json`
- `target/core-replacement-c06/native-minimum-one/single-hit-reference-fixture.json`
- `target/core-replacement-c06/native-minimum-one/stable-reference-fixture.json`

The same immutable inventory was then run sequentially in explicitly marked
available-only mode: 34 present fixtures, 2,094 passed / 15 failed / 0 skipped across
2,109 cases. This is provisional evidence only, not a 41-fixture confirmation. The
previous available-only run was 2,093 passed / 16 failed, so this repair resolves the
one `search_after_multi_sort_search` failure with no new available-fixture regression.
Execution record:
`target/core-replacement-c06/unicode-scanner-functional-live/post-sort-available-preserved-reports/execution.json`
(SHA-256 `2757f2f80e5a48f5a70d0ff4972e1f06160e9b86d17b556b62995afc047d36e4`).

The provisional remaining 15 failures are eight routed BM25 cases, six exact/sloppy
phrase ranking cases, and one field-sorted exact phrase score case. No performance
benchmark ran, no performance optimization was performed, and no release conclusion
is established by this repair.

## 2026-09-13 Retained Reader BM25 Score Repair

The eight routed BM25 failures were not routing-selection failures: document IDs,
membership and totals matched. Repeating fixture cases rewrites the same routed IDs.
OpenSearch's later `explain` response retained deleted reader statistics (for the
affected shard, `N = 54` and `n = 54`), whereas SteelSearch marked a native Tantivy
compound text score authoritative and emitted the current reader's `N = 3` score.
The pinned Tantivy scorer has no OpenSearch reader-lifecycle aggregate itself; this
is a demonstrated integration gap, not evidence that Tantivy cannot collect the
candidate set natively.

The repair keeps Tantivy query composition, shard selection and candidate collection.
Only when (1) a query has BM25 text scoring and (2) one of its selected shards has a
retained deleted reader does it reject the native score as authoritative and use the
existing retained-reader BM25 statistics for the materialized native hits. Term-only
and numeric native scores remain authoritative. The regression test
`bm25_statistics_keep_every_replaced_routed_reader_generation` replays 18 full routed
generations, populates the cache after each generation, asserts `N = n = 54`, and
asserts that a boosted `bool.must.match` is not native-score-authoritative in that
scope. It passed with `cargo +nightly test --locked --offline -p os-engine-tantivy
bm25_statistics_keep_every_replaced_routed_reader_generation --lib --quiet`.

The focused live fixture `search-bm25-routing-scope-compat.json` passed all 18 cases
against the pinned OpenSearch reference. Report:
`target/core-replacement-c06/unicode-scanner-functional-live/bm25-routing-scope-native-stats-fixed-report.json`.

The required sequential preserved run then completed in explicit available-only mode:
34 present fixtures, 2,102 passed / 7 failed / 0 skipped across 2,109 cases. This is
provisional because the same seven preserved inputs listed above are absent; strict
41-fixture confirmation remains fail-closed. Compared with the preceding available
run (2,094 passed / 15 failed), all eight routed BM25 cases passed and no available
fixture regressed. Execution record:
`target/core-replacement-c06/unicode-scanner-functional-live/post-bm25-native-stats-available-preserved-reports/execution.json`.
The remaining provisional failures are six compound exact/sloppy phrase ranking cases
and one field-sorted exact phrase score case. No performance benchmark ran and this
does not establish a release conclusion.

## 2026-09-13 Native Phrase Score Authority Repair

The direct field-sorted phrase response and two compound phrase responses exposed a
one-bit score difference between the pinned Tantivy phrase scorer and Lucene.  The
candidate set, document order and sort values already matched.  OpenSearch `explain`
showed that Lucene applies a phrase clause boost after calculating the BM25 phrase
score, while the retained-statistics implementation had applied the boost to IDF
before scoring.  The repair preserves Tantivy candidate collection and changes the
retained-statistics scorer to apply that boost after BM25.  For a field-sorted exact
phrase response, where the emitted score is an exact response contract, native score
authority is disabled and the existing retained-statistics score is used for the
materialized native candidates.  This is a documented narrow fallback for a proven
one-bit scorer difference; it does not re-evaluate membership, sorting or candidate
collection from source.

The focused `search-native-exact-phrase-scores-compat.json` fixture passed all 8
cases.  The compound fixture improved from 54 passed / 6 failed to 56 passed / 4
failed; its remaining failures are all sloppy-phrase field-sort scores for the same
`sparse` document.  The required sequential preserved run completed in explicit
available-only mode with 34 present fixtures: 2,105 passed / 4 failed / 0 skipped
across 2,109 cases, versus 2,102 passed / 7 failed previously.  No available fixture
regressed.  This remains provisional because the same seven preserved fixture inputs
listed above are absent.  Execution record:
`target/core-replacement-c06/unicode-scanner-functional-live/post-phrase-native-fallback-available-preserved-reports/execution.json`.

No performance benchmark ran and this repair does not establish release acceptance.

## 2026-09-13 Sloppy Phrase Page Score Repair

The four remaining compound phrase failures all used a field sort with a sloppy
phrase in a `bool` query.  Their memberships, sort order and all but one displayed
score per response matched.  The affected `sparse` document also had an exact phrase
match.  The direct native page-collection path was still emitting Tantivy's one-bit
score for that materialized document, while the non-page paths already selected the
retained-statistics scorer for the same condition.  A broad fallback for every
sloppy-phrase candidate was rejected: it changed the genuinely sloppy `gap` document
by a material amount.  The accepted repair instead applies the existing exact-source
match predicate to the native page materialization path only.  Tantivy remains
responsible for query composition, candidate collection and field sorting; only the
emitted score of an exact phrase match in this narrow field-sort scope is recomputed.

The focused `search-native-compound-ranking-compat.json` fixture passed all 60 cases.
The required sequential preserved available-only run then passed all 2,109 cases in
the 34 present fixtures (0 failed / 0 skipped), improving from 2,105 passed / 4
failed.  The strict 41-fixture result remains unavailable, not passed: the seven
preserved source fixtures listed above are still absent and the driver continues to
fail closed for them.  Execution record:
`target/core-replacement-c06/unicode-scanner-functional-live/post-sloppy-phrase-page-available-preserved-reports/execution.json`.

No performance benchmark ran, no performance optimization was attempted, and this
functional result alone is not release acceptance.
