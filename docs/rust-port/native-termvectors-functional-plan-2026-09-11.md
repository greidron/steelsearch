# Native Termvector Functional Repair

Latest directive: NO benchmarks during functional repair. Complete functionality
first; later optimize with benchmarks while preserving all functional tests. The
initialv0.6.0 cumulative budget remains a later acceptance/release condition.

Parent:132d8d6f, full2671-case HTTP2383 pass/288 fail/skip0. Working source:
target/core-replacement-c06/native-termvectors-source. Preserve the measured parent.
The interrupted parent benchmark is not resumed and is not a completed measurement.

## Required End State

Replace the REST whole-string/constant-statistics termvector response with native
analysis and index-backed terms, frequencies, positions and statistics. Cover stored,
generated/artificial, routed, realtime/non-realtime, scalar/array and multi-termvector
requests; honor field selection, flags, mapping capability, analyzer overrides,
Unicode UTF-16 offsets, pending updates/deletes and snapshot visibility. The22 contract
and80 positions failures are a root-cause group, not proof that one change fixes102
cases. Array ranking55 cases remain a separate scorer investigation. No exclusions,
hard-coded expected responses, comparator relaxation or source-wide search evaluator.

## Native Contracts

- Pinned Tantivy supplies tokenizer_for_field, pre-tokenized strings, term dictionaries,
  postings with frequencies/positions, alive bitsets and immutable searcher snapshots.
- The existing add_positioned_text_values path already handles array position gaps.
  Reuse its native analysis; do not create a second tokenizer or gap algorithm.
- Native offsets are byte offsets. Convert to the public UTF-16 contract explicitly
  and test accented/astral characters; do not call analyzed offsets persisted offsets.
- Resolve a routed document and native reader under a consistent engine snapshot.
  Realtime handling must not expose pending writes through ordinary non-realtime
  search or mutate published visibility as a side effect. Inspect local OpenSearch
  realtime reader behavior before choosing the native read/update mechanism.
- Use requested document terms to probe native dictionaries/postings. Do not turn
  diagnostic full-vocabulary/postings enumeration into an unconditional per-request
  algorithm. Field-statistic collection must match reader generation and deletion
  semantics; retain native caches/providers where their contract matches.

## Implementation Sequence

1. Preserve term_vector mapping metadata across parse/serialization/reload. Extract
   reusable positioned-text native analysis without changing indexing behavior.
   Full engine regression tests include the existing reference positions/statistics
   fixtures, not only new metadata tests. This is infrastructure, not endpoint repair.
2. Add typed native termvector request/result APIs and snapshot-bound document/term
   reads. Add engine tests for stored/generated modes, flags, Unicode, arrays, routing,
   realtime updates/deletes and missing documents. Use native analysis for selected
   target documents and native indexes for statistics; retain pending semantic gaps
   explicitly until resolved, not as silent supported-subset exclusions.
3. Wire single and multi REST endpoints to the engine API, retaining validation,
   security, error handling, routing and visibility. Remove placeholder response
   construction once all its callers are migrated. Keep invalid mapping/request
   validation in scope; metadata preservation alone is not validation support.
4. After each functional change run focused regression tests and relevant full
   engine/node suites; run expanded full HTTP before declaring functional completion.
   Preserve failures and report exact executable/fixture identities. Add uncovered
   cases without dropping existing ones. NO performance or microbenchmark runs.
5. Continue the remaining288-case functional repair work. Only after functional
   compatibility is established run full non-plugin performance measurement and
   optimization, rerunning functional tests and repairing any optimization regression.
   Maintain fixed initialv0.6.0 throughput95%/each mean,p95,p99 105% cumulative limits.

No functional case reduction, performance improvement, package acceptance or release
is established by this plan or the initial metadata/token-analysis extraction.

## Initial Implementation Evidence

TantivyTextOptions now retains optional term_vector metadata through existing mapping
deserialization. The native array indexing analysis was extracted to
analyze_positioned_texts and reused by the original indexing path; tokenizer, checked
position limits, gap rules, token byte offsets and single-value fast path are unchanged.
Terra added three metadata tests covering default/explicit modes, nested and multi-field
serialization and legacy snapshots. The test file initially landed at repository root;
parent moved only that newly created file into the isolated source before compilation.

Frozen2909-file source manifest SHA:
3a9bc79bea5c44f83c0451cd25f479b939564d18c1e872493565fa035108688c.
Full engine tests passed969 (949+7+4+9), exit0; compile2m20s, test14.30s/8.09s/2.10s/0.19s.
This includes existing native array positions/offset/reference-statistics tests.
Log SHA3f18311b9ed6e07cf3dea3b6e7f6a49d468496d1bc4d57b48b6ae1266a9c5e5a.
Source manifest was verified unchanged afterward. No benchmark ran. Node/HTTP endpoint
verification and typed native termvector API/REST wiring remain pending;288 failures
remain the last verified count. This is not termvector feature completion.

## Refreshed Native Reader API

Implemented NativeTermVectorOptions/NativeTermVectorResponse and
TantivyEngine::get_native_refreshed_termvectors in src/native_termvectors.rs. A routed
published document and native reader are resolved under the same engine read lock;
native _id TermQuery resolves the document address. Existing positioned native analysis
selects document terms, and postings supply frequencies/positions. Stored capability
and positions/offsets/statistics flags control output; native byte offsets convert to
UTF-16 code units. Text collection reuses the existing indexing helper.

Field totals are computed from native dictionaries/postings on first demand and cached
by exact searcher generation. This is not a source scan or per-request unconditional
full-vocabulary traversal. Term-statistics requests read the requested terms' native
postings. Offset reanalysis is bounded to the selected document and is NOT persisted
offset storage. Keyword/generated/artificial, wildcard selection, analyzer overrides,
realtime pending state and unsupported index record options still require completion;
this API has not been wired to REST and is not a full termvector compatibility claim.

Terra added3 engine tests: scalar/array Unicode offsets and statistics, disabled token/
statistics flags, and routing/published update visibility. Parent review corrected the
array-position expectation to101 and required an actually distinct routed shard.
The first full build failed because DocSetCollector was imported only under cfg(test)
in the parent module. Its log is preserved. Adding the import to the new module fixed
the build without weakening any expected values.

Full engine rerun:972 passed (952+7+4+9), zero failures, exit0; compile1m24s,
tests14.06s/7.81s/2.12s/0.18s. Rerun log SHA:
3aba1c789a50a7e7d12fd40fb023164a490c74e2a99b35db0ddd60e4364fea8d.
Post-test2911-file manifest artifacts/source-native-reader-verified.sha256 SHA:
751df119073a5b8935411558e29630b57232f85b487b1823c9b18ebf1ad0ce11.
The initial pre-import-fix manifest remains separately preserved. No benchmarks ran;
node/HTTP tests and public endpoint repair remain pending. Failure count remains288.

## Refreshed REST Wiring And Field Selection

The isolated source now routes realtime=false single and multi termvector requests
through the native reader API. Single requests forward positions, offsets and statistics
flags, including URL precedence. Default realtime, artificial documents and multi-request
flag propagation remain unfinished; this is not full endpoint completion.

The first node run failed one external-version snapshot test (684 passed/1 failed).
That test requested generated vectors without selecting fields in its multi request.
OpenSearch TermVectorsService only adds generated vectors for selected fields. Making
the request explicit exposed an actual REST defect: handle_mtermvectors_route discarded
per-document fields. The intermediate run retained this failure (685 passed/1 failed).
The route now forwards document-level selections. Version, found and published term
assertions remain intact. Added exact-response regressions check generated field omission,
wildcard selection, multi/single equivalence and empty multi-document field selection.
The subsequent complete node run passed1145 tests (686 library+459 binary), exit0.

Source review of OpenSearch FieldTypeLookup and Regex.simpleMatch established that only
'*' is special in field selection. The general product wildcard helper also accepts '?',
so the termvector path uses escaped, anchored patterns in the existing regex library,
compiled once per request. A literal-question-mark negative test was added afterward;
final node verification is recorded below. Full HTTP comparison has
not been rerun:288 remains authoritative. No performance measurements ran.

Next realtime implementation must preserve internal versus externally published readers.
Local OpenSearch TermVectorsService constructs Engine.Get(realtime,false,...), so the
InternalEngine.get translog shortcut is disabled for this API. Pending versions trigger
refreshIfNeeded and INTERNAL searcher scope; realtime=false uses EXTERNAL scope. Do not
publish ordinary search visibility merely to satisfy a realtime termvector request or
replace matching shard statistics with a single-document synthetic index. Other pending
contracts include keyword fields, analyzer overrides, index record options, malformed
multi-document field input, shared multi parameters and single empty-field selection.

The literal-question-mark rerun passed686 library tests but failed the binary suite
(269 passed/190 failed). The first failure was cleanup_repository_transport_route;
subsequent failures reported the poisoned dev transport PIT test lock. Inspection found
four tests changing shared transport bindings without that lock: clear_cache, knn_warmup,
recovery_phase_predicates and multi_term_vectors_transport. The first two replace the
shared metadata manifest, permitting interference with the cleanup repository assertion.
Applied the existing test lock to those four tests only; no product safety checks or
assertions were removed. A fresh full node run passed686+459=1145, exit0 (session65360).
This fixes an identified synchronization defect; one passing rerun is not exhaustive
proof against all possible test-order dependencies. Engine-wide rerun and full HTTP on
these latest edits remain pending. Benchmarks remain stopped.

Latest verified source file SHA-256 identities (isolated native-termvectors-source):
- crates/os-engine-tantivy/src/native_termvectors.rs:
  d29325474a0e28d3b923588ae25856edb0f57d204f8f6b4ccebeee3a50221313
- crates/os-node/src/standalone_runtime.rs:
  866f1193be2c3da2881e295a8a7c1cdca7840d6cb563a21fa1eb4783985b6f65
- crates/os-node/src/native_termvector_rest_tests.rs:
  b023f07500b375f6fa93c461a587ee63a13812e2c0555dd0885b8ee854611d71
- crates/os-node/src/main.rs:
  59de6de561be9debd7b0697bd7c2ce21f053ecae20032b17a79f312e38a41dba

## Native Realtime Reader

Added get_native_termvectors(..., realtime) and a shard-local internal reader cache.
Published reads retain get_native_refreshed_termvectors. Realtime resolves the routed
current document while holding the index refresh owner and engine read lock. It never
calls the public refresh operation or mutates the externally published searcher.
Cache identity includes schema hash, index sequence boundary and shard mutation/
persistence generations. Subsequent writes apply native delete/add deltas; unchanged
documents are not reanalyzed. Failed updates discard the private cache for reconstruction.

Luna verified pinned RamDirectory::deep_clone and lock semantics. RefreshDirectory now
retains a native handle in TantivySearchState, clones its independent file map under
META_LOCK, and removes copied writer/meta lock markers only from the fork. Managed file
metadata and native deletion files remain intact. The fork opens a separate native
writer/manual reader. A background merge can yield a newer native segment generation
with the same committed document boundary; this is NOT an exact clone of the external
Searcher's segment IDs. The product refresh owner excludes pending public commits during
capture. New indexes or incompatible schemas use normal native indexing to establish
the first internal index; this is not a per-request source-wide scoring fallback.
Performance and retained-reader memory costs are unmeasured; no performance acceptance.

Terra added pending routed lifecycle tests with exact UTF-16 offsets/statistics, repeated
reads, update version boundaries and deletion visibility. Parent added a separate test
that first publishes documents, then forks native segments for an update and verifies
the external writer remains usable. A compile failure (DeleteError lacks implicit
conversion to TantivyError) was corrected with explicit IO error conversion.
Full engine rerun session94865 passed974 (954+7+4+9), exit0.

Single and multi REST requests now use the native realtime API by default, not the old
whole-string/constant-statistics document response. Single requests distinguish omitted
fields from explicit empty fields. Removed the unused document-map lock from multi
requests. An added REST check confirms a pending termvector read returns native tokens
while ordinary search still returns zero documents before public refresh.
Initial full node run session9415 passed684/failed2: both legacy tests expected generated
vectors without field selection. Requests that inspect generated terms now explicitly
select message; omitted-field controls assert an exact empty term_vectors object.
Full node rerun session88167 passed1145 (686 library+459 binary), exit0. The engine and
node functional suites pass for this source; full HTTP and remaining contracts below
still prevent termvector feature acceptance.

Remaining endpoint work: keyword/non-positioned index options, artificial documents,
per-field analyzers, multi-request flags/common parameters and malformed input, filter/
payload semantics, and live OpenSearch validation of realtime statistics and deletion/
merge behavior. No whole-feature completion, HTTP failure reduction or release is claimed.
The latest full HTTP result remains2383 passed/288 failed/skip0; benchmarks remain stopped.

Source identities for this implementation (before final node result):
- engine lib.rs: dcaa2df46677ae7213140867628e60b6572d1a2cdbabf5c6a9ad18893ec6fe76
- native_termvectors.rs: c3536b2c0beccf1a8b14deb1e279da7529b3b19211de5613afa4453d07e68618
- refresh_directory.rs: a5bc6d00ca6ac74899715a118e6beddeaa8280abf0d8be7e70d4586f6ef66399
- reader tests: 7868cf3bccc64d51245dbfcd4cd95b90094443c7a244110a2bfacbc1393664ad
- standalone_runtime.rs: f8fe2d7f539f34bf607414d5adabb4d39eabd5af279e30e086fb00bcadd302e3
- REST tests: 545e21fe67b04d374053713ef07b78fa023b93ba90c3b6f025ed7cd9f7dc7b98

## Generated Keyword And Text Vectors

Generated vectors now take term frequency and positions from the selected document's
native analyzer tokens, independently of search-posting capabilities. Actual index
postings still supply requested corpus statistics; stored-capability vectors retain
their existing native-posting path. Added keyword field selection with the native raw
tokenizer and zero position gap. This is not a claim that all keyword normalizers,
multi-field generation, source-disabled mappings or index_options search semantics
are compatible.

Terra added a regression for repeated raw keyword values with astral UTF-16 offsets,
text index_options=docs, realtime/refreshed paths and omitted-field defaults. Parent
corrected two BTreeMap-versus-JSON comparisons without changing expected data. Full
engine rerun passed975 (955+7+4+9), exit0; log engine-generated-keyword-tests.log.
The corresponding REST keyword response is checked exactly. Full node tests passed
1145 (686+459), exit0; log node-generated-keyword-tests.log. Logs are under the isolated
native-termvectors-candidate directory.

Important newly confirmed gap: preserved OpenSearch HTTP responses for both stored and
generated astral cases contain an emoji term at position1 and beta at position2. Our
current native SimpleTokenizer drops that emoji. Earlier engine tests prove current
native token/offset behavior, NOT OpenSearch Unicode tokenization equivalence. Do not
weaken HTTP comparisons or count those cases repaired. Native tokenizer/library options
are being audited before implementing a tokenizer extension.

Functional-only dev build completed in41.08s, exit0, with --locked --offline,
standalone-runtime, CARGO_PROFILE_DEV_DEBUG=0 and CARGO_INCREMENTAL=0. Preserved executable:
native-termvectors-candidate/artifacts/steelsearch-functional-debug, SHA-256
11d9133988f2c67923dba19a208b53cf7e02db6b47039c75a011022365c6320c.
This unoptimized executable is NOT a performance or release comparison candidate.
Full41-fixture HTTP run is in progress in native-termvectors-functional-live using the
unchanged c05 runner and count probe. No workload benchmark is run by this invocation;
cluster-start helpers are reused only for functional HTTP requests. Failure count stays
288 until the completed reports are audited. No release or feature completion.

The full HTTP run completed, exit1 for remaining functional comparisons (not startup
or setup failures). Verified41 fixtures/2671 identical case keys:2458 passed/213 failed,
skip0. Compared with132d8d6f,75 failed-to-passed and zero passed-to-failed transitions.
Array positions improved72, termvector contract improved3. All other status groups are
unchanged. The8 remaining array position failures differ only in top-level took; all
other extracted fields are identical. This run did not alter their source_body extractor
or reclassify them. Retain the full19 remaining termvector contract failures as well.
Reference version/build matches the previous run exactly, binary and fixtures unchanged,
count probe passed and setup failures0. Report hashes verified by the generated audit.

Execution SHA02bd82f6dbc3f827b1547daf67b689962f55c58368f251a8be998c7c1d3e0ad3.
Audit artifacts/http-functional-audit.json SHA:
732fd73a31659595240b0580f855aaea90c43f78e924649f0429b12e9cd4bb2a.
Engine test log SHA5887bc068e22a59f45dd755e0ebda76de3c9d2695adb7364051bc0a671a0634f.
Node test log SHAb36f41976c10f334a3ab24940b7764900a9a5e9555be087d5c893e8da4b31451.
Build log SHAff9324154e09c42d502a84ba9fd70c07f18878705f6ca13419cc5339249a1a82.

Luna's native-tokenizer audit found no already-pinned UAX29 word-break implementation.
Tantivy0.21.1 supports custom native Tokenizer/TokenStream registration; SimpleTokenizer
is alphanumeric-only. Parent corrected an audit statement: WhitespaceTokenizer DOES
emit the three space-separated tokens in 'Alpha [emoji] beta', but cannot substitute
for standard punctuation/UAX29 behavior. A proven Unicode word-break dependency and
Lucene-reference cases are needed before adoption; no ad-hoc emoji regex was installed.
Remaining functional failures are213, not a performance gate result or release approval.

## Execution Metadata Comparison Correction

User clarified that elapsed/auxiliary execution metadata must not be conflated with
document/search semantics. Corrected the array positions fixture's80 extractors from
source_body to the existing term_vectors extractor. A structured comparison verified
no other JSON values changed. Preserved the original fixture separately. No binary or
product behavior was changed. Added tests ensuring the fixture keeps that contract and
document fields/terms named took remain strictly compared. All21 comparator tests pass.
The rule is recorded in root and isolated-source AGENTS.md: validate volatile values'
contracts, preserve semantically important metadata, never blanket-strip document data,
and do not exempt actual benchmark latency from its separate performance gate.

The identical executable reran all41 fixtures/2671 cases in
native-termvectors-metadata-contract-live. Result2466 passed/205 failed/skip0; exactly8
comparator corrections, zero new regressions, setup failures0, count probe passed.
All80 array-position cases now pass;55 array ranking failures remain unchanged. The
19 termvector-contract failures and other failure groups remain. This is not8 additional
feature implementations, a Unicode-parity claim, or release/performance acceptance.
Execution SHA119217e09a19f5466e532046a9f6d6754ede0f206ddd911cb1ad1025893d9f22.
Candidate artifacts/http-metadata-audit.json SHA:
328fca0c02637040cf2d3a6fc34af39efd93ecebc3eb018b167c51ab0c4e930f.

## Unicode Library Evaluation And Remaining Failure Separation

Functional probe completed against the actual local Lucene10.4.0 StandardAnalyzer
and an isolated unicode-segmentation1.6.0 executable. Evidence and reproducible
sources: target/core-replacement-c06/unicode-native-evaluation/{comparison.json,
compare.py,src/main.rs,LuceneTokens.java,Cargo.lock}. No product dependency changed.
The report records source, native executable, Cargo.lock and Lucene jar identities.
This is28 functional samples, not a performance benchmark or production acceptance.

Seven samples have Lucene token spans absent from library word boundaries:
presentation selectors, Thai, Lao, Khmer, Myanmar, long ASCII and long astral text.
Seven samples also contain Lucene tokens which unicode_words would discard:
emoji, adjacent emoji, ZWJ families, skin tones, regional flags, keycaps and
presentation symbols. These groups overlap. Boundary coverage alone is not token
stream equivalence. Four evaluator regression tests verify that distinction.
The additional lowercase stream is explicitly a Python str.lower diagnostic model,
not evidence of native Rust lowercase parity. Lucene emits a single i for U+0130;
the evaluator model expands it. Do not adopt a generic word-break replacement as
standard-analyzer compatibility without resolving these demonstrated differences.

Structured inspection of the preserved HTTP failures is reproducible using
unicode-native-evaluation/classify_http.py; output is http-differences.json.
Source report SHA cf06e08c4e04417bbb6cf0f9b93a7f4b8f62a0d8c9203da322ee5306c6234b02.
The19 termvector failures separate into disjoint observed categories:

| Observed difference | Cases | Next implementation boundary |
| --- | ---: | --- |
| Field statistics only | 9 | Native indexed token/corpus parity; keep statistics exact |
| Emoji/combining terms or positions plus field statistics | 6 | Proven native analyzer extension/library integration |
| Ignored keyword analyzer override plus field statistics | 2 | Request options into native RawTokenizer, not source splitting |
| realtime=true reports missing document | 2 | Deferred runtime writes into native internal reader |

The last category is NOT a Unicode tokenizer failure. The current runtime checks
STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH and skips native replay until refresh;
the live runner's cluster-start helper enables that setting. The termvector path
reads the native engine directly. Existing private reader tests without deferred
runtime writes therefore do not establish HTTP realtime compatibility in this mode.
No existing case is reclassified as passing by this diagnostic inventory.

Next repair priority is the runtime-to-native deferred-write boundary. Reuse native
replay/internal readers without publishing an ordinary search refresh. Audit pending
index/delete identity and replay-error propagation before reusing the existing
refresh replay helper: its index branch currently discards replay errors. Cover
deferred inserts, replacements, deletes, routing, single/multi vectors, error paths
and unchanged realtime=false/search visibility. Then run engine/node functional
regressions and all41 HTTP fixtures under the same actual deferred-write settings.
Do not mark the unit complete from focused tests. Benchmarks remain stopped until
functional repairs are established, after which the full non-plugin suite and fixed
v0.6.0 cumulative throughput/latency gates in AGENTS.md apply.

Current verified product counts remain2466 passed/205 failed; this probe did not
change the product binary or complete an implementation unit. No release acceptance.

## Deferred Runtime Writes: Implemented And HTTP Verified

The isolated candidate now replays pending native mutations before realtime single
and multi term-vector reads, without invoking a public refresh or clearing runtime
unrefreshed visibility. realtime=false continues to use the published reader.
Pending index replay now checks the captured document Arc identity under the runtime
document lock, like the existing delete replay path. Removed/replaced snapshots are
skipped; invalid metadata and native replay errors propagate instead of being ignored.
No source-level term-vector fallback was added.

New helper tests cover current/stale/removed snapshots, missing native index, and
negative version/primary term. A routed three-shard REST test covers insert, replacement,
single/multi realtime vectors, pending deletion, unchanged published vectors/search,
and final refresh. Run that REST module both normally and with
STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH=1; the latter also verifies that the initial
write is actually absent from native storage before the realtime read.

Functional executable: native-termvectors-candidate/artifacts/
steelsearch-deferred-replay-functional-debug, SHA
d1407ff6e78bd937d5db07021f70a7cd06a753dc5ef238b5b9ef176a49b8ee38.
Dev/unoptimized build succeeded in31.72s, not performance evidence. The previous
11d91339 executable and all raw reports remain preserved.

Full HTTP evidence: native-termvectors-deferred-replay-live, unchanged41 fixtures and
2671 case keys,2466 passed/205 failed/skip0, setup failures0, count probe passed.
No pass/fail transitions. Both previously missing realtime documents now have found,
version and complete term/token results identical to OpenSearch. Their field statistics
still differ, so both cases correctly remain FAILED. This is a component repair, not
two newly passing cases. Unicode/corpus parity and analyzer override work remain.
Execution SHA ee2b869246ac03b9035d0fe522859ecb56b3935d3298ad498c81e0916200a64f.
Audit SHA1586d0069e7aa139535edc677e7215d6228ed852646a33a291514490e8d651c5;
reproduce with unicode-native-evaluation/audit_deferred_http.py.

Node library692 and binary459 tests passed; deferred-mode REST tests3 passed.
The initial new stale-delete test failed in setup before calling replay because a
default DELETE leaves native deletion pending; corrected setup to refresh=true and
retained separate pending-delete coverage. Both test logs are preserved.

Expanded cargo test additionally ran53 daemon integration tests, not included in the
older1145 library/binary count. A lifecycle test expects HTTP200 from the development
shutdown endpoint after explicitly marking recovery failed; actual status503. Three
following tests failed only because the serial-test mutex was poisoned. The same
primary failure reproduces using the preserved11d91339 pre-change executable via
CARGO_BIN_EXE_steelsearch and the identical daemon test executable. This is an existing
unresolved integration failure, not evidence that the complete node suite is green.
Do not bypass recovery safety or hide this failure as a plugin exclusion. Separate
daemon-lifecycle-before.log preserves that reproduction. The other daemon tests are
reran independently of the poisoned mutex:52 passed/1 explicitly filtered; this diagnostic exclusion does NOT
make the full integration suite pass or remove the primary failure from the ledger.

Engine regression suite completed975 passed (955+7+4+9), exit0. Node library/binary
total1151 and deferred-mode REST3 remain green. Logs are engine-deferred-replay-tests.log,
node-deferred-replay-tests-final.log, node-deferred-mode-tests.log and
daemon-other-tests.log under native-termvectors-candidate. The full node command's
exit101 remains recorded because the known lifecycle integration failure is unresolved.

Benchmarks remain stopped. No implementation/performance acceptance or release.

## Lifecycle Integration Contract Correction

The daemon lifecycle failure was traced to an obsolete test expectation, not a
permission to bypass recovery protection. handle_rest_request deliberately rejects
all REST requests after shared-runtime recovery failure. The integration test invoked
the development shutdown probe after setting that failure and expected200. Keep the
503/unavailable_shards_exception guard unchanged, including development probe routes.
Actual process shutdown invokes lifecycle hooks internally, not through REST.

Added a direct regression proving recovery-failed REST lifecycle probes cannot append
hook executions or set the shutdown flag, while the internal shutdown hook still runs
and preserves the recovery-failure flag and REST rejection. All3 recovery_failure_
tests pass, including preservation of corrupt recovery files. Terra is updating the
daemon scenario to exercise recovery-first and shutdown-first in independent clusters,
retaining normal shutdown transcripts and explicitly asserting blocked post-failure
requests. Full node-suite verification is still required before closing this test issue.
This is a test-contract correction, not an additional implemented OpenSearch feature.

### Analyzer Override Reference For The Next Repair

Inspected the actual local OpenSearch reference source, commit
f991609d190dfd91c8a09902053a7bbfe0c27b3e (same as the HTTP reference build):
server/src/main/java/org/opensearch/index/termvectors/TermVectorsService.java,
SHA586a5c0fd034b5bc5a769d477a8d5ddd14c7d20de3ff5cca76385649b49cd8c5.
addGeneratedTermVectors regenerates selected fields even when stored vectors exist
if that field has an analyzer override. getAnalyzerAtField resolves the named index
analyzer and falls back to the default index analyzer when lookup returns null;
do not invent an unknown-analyzer error without contrary HTTP evidence. Generated
tokens use Lucene MemoryIndex with analyzer-specific multi-value gaps, so overriding
to keyword must not blindly inherit the text mapping's100-position gap. Missing
selected-fields behavior must also preserve the distinction between stored-vector
selection and requested generation. Native Tantivy RawTokenizer is the intended
keyword implementation, not manual whole-source token construction. Verify field
selection, arrays, offsets, flags and statistics with reference probes before wiring.

## Per-Field Analyzer Override: Implemented, Bounded Native Support

Implemented request-local per-field analyzer support without changing Tantivy or
introducing source-level token splitting. `keyword` selects the pinned native `raw`
tokenizer and forces source-derived vector rendering even when the mapping stores
term vectors. Both accepted request spellings (`per_field_analyzer` and
`perFieldAnalyzer`) are parsed as field-to-string maps. Empty maps retain normal
stored/generated behavior. Invalid non-object or non-string values return400 parse
errors. Single and multi term-vector requests carry the same options; multi now also
honors document-level positions, offsets, field_statistics and term_statistics flags
instead of silently using defaults.

The generated override path preserves the native text value loop: array values are
analyzed separately, have a100 position gap and one UTF-16 offset separator. Actual
OpenSearch reference probe confirms keyword array terms `first two` at0/0..9 and
`second three` at101/10..22. That probe also proves an unavailable named analyzer
falls back to the current default analyzer in this fixture. Current native mappings
have no configurable analyzer catalog/default setting, so custom analyzer execution
is explicitly unsupported; neither stored analyzer metadata nor an unknown override
is misrepresented as custom-analysis support.

Evidence source: per-field-analyzer-reference-probe.json SHA
397bb9562dad3b451726a83566d5a9a7e54559bf80ecd3e5359654e8d7328ef2.
Reference run uses OpenSearch3.7.0-SNAPSHOT build f991609d190dfd91c8a09902053a7bbfe0c27b3e.
Before implementation its4 cases had3 failures; current functional probe is4/4 passed.
Candidate functional debug binary SHA
37998881c209f82be445b95a64ce1c48f43d9786996b0175f9818e93746c4966.
Focused node tests2/2 pass, covering stored/generated mappings, array offsets and
positions, implicit default behavior, camelCase fallback, multi-doc forwarding and
malformed input. No benchmark ran.

Post-implementation full regression is green: engine975 passed (955+7+4+9), node
library695 passed, node binary459 passed, daemon integration53 passed and OpenAPI
integration1 passed. This replaces the earlier daemon lifecycle test-contract failure:
the test now validates recovery-first and shutdown-first in independent3-node clusters
without weakening the recovery REST guard. Logs: engine-per-field-analyzer-tests.log
and node-per-field-analyzer-full-tests.log under native-termvectors-candidate.

The full identical41-fixture/2671-case HTTP rerun passed2466/failed205/skipped0;
fixtures, count probe and executable identity verified; setup failures0 and no status
transitions from deferred-replay evidence. The two prior keyword override failures
now differ only in `field_statistics` (OpenSearch14/14 versus native12/12), while
their term maps are exact. Therefore neither is counted as a passed case. Execution
SHA5048a4f963c9bb0b7c9a1cfd37e93c82cec29f2d9b09dd23b804039439c58078;
termvector report SHAeaa86603b6eb571f6828bb8a8cdc434ffb0e6423b3a851216a859fa2953f1bf8.
Next work remains native Unicode/corpus field-statistics parity, rather than further
override plumbing. Custom analyzer definitions, char filters, synonyms, payloads,
source-disabled vectors and artificial documents remain unimplemented and must not
be counted as supported.

## Lucene Standard Analyzer Parity: Native Scanner Plan

The remaining Unicode termvector failures cannot be repaired by changing response
comparison, source-level splitting, or a generic Unicode-word dependency. The
preserved functional evaluation demonstrates that those approaches disagree with
the actual OpenSearch/Lucene stream for emoji sequences, presentation selectors,
complex-context scripts and Lucene's UTF-16 token-length boundary. Tantivy0.21.1
does provide its supported `Tokenizer`/`TokenStream`, `TextAnalyzer` and
`TokenizerManager` extension API, but does not ship an equivalent standard
tokenizer. The implementation boundary is therefore a native tokenizer extension,
not a Tantivy fork and not a regex fallback.

The behavioral reference is Lucene10.4.0 `StandardTokenizerImpl.jflex`, matching
the local OpenSearch reference build at commit
f991609d190dfd91c8a09902053a7bbfe0c27b3e. Before product code is changed, retain
the exact upstream source revision/hash and generate frozen token-stream vectors
from the local `lucene-core-10.4.0` jar. Each vector records normalized term text,
position increment, UTF-16 start/end offsets, and input identity. It must cover
ASCII and supplementary-plane 255 UTF-16-unit limits, combining marks, UAX29
letters/numbers, Han/Hiragana individual terms, Katakana/Hangul runs, Thai/Lao/
Khmer/Myanmar complex-context runs, emoji ZWJ/modifier/flag/keycap/presentation
sequences, apostrophes, punctuation and U+0130 lowercase behavior. The existing
28-sample evaluator is a seed, not sufficient proof of implementation parity.

Implementation units are deliberately separated:

1. Expand and freeze the Lucene reference vectors and add Rust tests that consume
   them. The test oracle must be the generated reference artifact, never an
   independently hand-written approximation. Verify the generator against the
   recorded jar hash and ensure offsets stay UTF-16 at the public boundary.
2. Implement a bounded port of the pinned Lucene scanner tables/logic as a native
   Tantivy `Tokenizer`/`TokenStream`. Keep tables immutable and stream buffers
   reusable; preserve Lucene token classes, surrogate-safe maximum token length,
   original byte-to-UTF-16 offset conversion, and Lucene-compatible lowercase
   behavior. Add only the scanner code and vector tests in this unit. Do not add a
   generic `unicode-segmentation`, ICU, source regex or per-query source scan as a
   fallback.
3. Register the tokenizer in the native `TextAnalyzer` construction used by both
   indexed text fields and generated termvectors. Retain `raw` for keyword
   overrides. Prove matching arrays still receive the existing native position and
   offset gaps. Add an explicit analyzer implementation identity to the persisted
   native schema/manifest compatibility boundary so recovery reconstructs postings
   with the same analyzer; legacy state must rebuild from retained documents rather
   than silently mixing old SimpleTokenizer postings with new query analysis.
4. Verify native postings-derived field statistics, stored/generated termvectors,
   realtime replay, search/phrase behavior and the full 41-fixture HTTP comparator.
   A case passes only when document semantics and stable response metadata match;
   `took` remains presence/type validated rather than value-equal.

The current user-directed functional-first phase prohibits performance benchmarks
until the outstanding functional repair work is complete. Consequently, each unit
above requires its focused tests plus the relevant full functional suites before it
is marked complete; no benchmark result may be used to close it. Once all
functionality is complete, run the full non-plugin benchmark suite and enforce the
fixed v0.6.0 cumulative gate in AGENTS.md: every topology throughput must be at
least95% of v0.6.0 and every scenario mean/p95/p99 latency at most105%, using the
same actual workload and separately recorded executable identities. A later unit
may not reset that baseline or offset one failing scenario with another improvement.

Custom analyzer definitions, char filters, synonyms, payloads, source-disabled
vectors and artificial documents remain separate unsupported capability boundaries.
They are not implied by this scanner work and must remain outside completion counts.
