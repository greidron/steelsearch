# Fetch Projection Ordering

Status: isolated implementation, not accepted. Parent binary4086ba72 and its failed
initial-v0.6.0 cumulative performance gate remain the latest measured product evidence.

## Proven Gap and Scope

The new native-aggregation date contracts show missing fields when _source:false is
combined with docvalue_fields. standalone_native_search_request_with_alias_filters applies
source projection in the engine before apply_native_search_fetch_fields reads hit._source.
The current exception retains source only for stored_fields plus disabled source.
Includes/excludes can similarly hide values needed by independently requested fields.

Pinned Tantivy has typed fast-field column readers, including date and multivalues.
The engine SearchRequest currently has no docvalue_fields member; REST build_search_hit_fields
is source-backed. This is an adapter gap, not a library limitation. This unit repairs
ordering of that EXISTING adapter without adding a source scan, evaluator or formatter.
It does not claim native doc-values support or resolve date parsing, array formatting,
mapping-derived histogram formatting or aggregation collector compatibility.

## Implementation Unit

1. Snapshot4086ba72 source into native-fetch-projection-candidate with a separate build
   directory. Defer source projection only for requests handled by the existing REST
   stored_fields/docvalue_fields/fields extraction pass. Ordinary search requests retain
   their existing engine projection. Keep the original request body for response visibility.
2. Extract fields from the hit source, then apply the existing source projection
   helper, including explicit false, object fetch:false, includes/excludes and stored-field
   suppression. Do not expose retained source or change authorization/routing/generations.
3. Add focused request/response tests and live fixture cases for independent field fetch
   and source visibility. Exercise normal/PIT/scroll call sites and the unchanged no-fetch
   path. Preserve known date/array failures rather than change their expected responses.
4. Before completion run full engine/node tests, the expanded non-plugin HTTP fixtures
   including both new aggregation fixtures and new projection cases, and the full six-run/
   twelve-topology benchmark. Record source/binary/tool/fixture identities, actual settings,
   all scenario mean/p95/p99 and topology throughput. No concurrent work during timed runs.
5. Enforce fixed initialv0.6.0 throughput>=95% and each latency<=105% cumulatively, with
   prescribed repeated measurements, no averaging or baseline reset. A failure remains
   incomplete; investigate/optimize and apply the main plan's attributable unresolved
   single-unit exclusion rule. Any retained exception needs explicit approval.

Release remains held. Neither focused tests nor this document authorizes publication.

## Initial Implementation Evidence

The isolated source differs from4086ba72 only in standalone_runtime.rs and the new
native_fetch_projection_tests.rs. Terra supplied four tests; the parent added explicit
boolean/object-hidden source checks and direct ordinary/PIT/scroll native entry-point
assertions. This avoids assuming the REST test necessarily exercised a native path.
The original scroll implementation collects its stored result set before pagination;
this unit does not claim to optimize that behavior or fetch only a single scroll page.

Source manifest SHA-256:
c7a957552e4bd13d56bbad4821e891300ad3c73db188dd4cc163b6262fde121e.
All entries verify; full tree comparison finds no engine/vendor/Cargo changes.
Full engine tests passed966 (946+7+4+9), no ignored/filtered tests, exit0;
build2m24s. Full node tests also passed1141 (682+459), including all five new tests,
no ignored/filtered tests, exit0; build2m09s and test groups4.10/12.27s. Luna's independent
read-only review found no concrete regression in request envelopes, visibility or scroll
storage; it is additional evidence, not a substitute for HTTP/performance verification.
The implementation is not accepted. Release artifact build is in progress.

| Artifact | SHA-256 |
| --- | --- |
| Engine test log | 7ddbdd9be672f5b773bd6747c428a813575b1c0b275a9f64155a7d8d0ceca9aa |
| Node test log | 170735d94dc87094b55c74194112760560824a3116a0972fa07d443b6aafa934 |
| Parent live execution.json | 293ed69248abd4d814459610fa6b42d51999033224c48e359dd9e9ed5a4c1d14 |
| Parent new-fixture report | af5a8d2391f8b019ad400e4476e2b0a2998fd2b8d0dd94b84e8b62ef6553f54c |

The parent4086ba72 live run uses search-native-fetch-projection-contract.json plus
the existing1500 core cases. All1500 pass; new10 cases have2 passes/8 failures;
no setup failures or skips, count probe passed, executable/fixtures unchanged.
Preserve this raw evidence under native-fetch-projection-parent-live.

Not all eight failures have the same cause. Four directly show missing/incorrect fields
when hidden/included source removes a separately requested numeric docvalue/fetch/stored
field. Remaining controls expose pre-existing differences: object fetch:false and body
_source_excludes are rejected by OpenSearch but accepted by this product; fields:[] is
accepted by OpenSearch but rejected by the product; ordinary _source projection emits
unrequested fields on the product. Do not count those differences as repaired by ordering
alone, remove their tests, or infer native-library limitations from them.

The expanded candidate HTTP invocation must include all40 fixtures/2659 cases and
compare raw _source visibility in the projection fixture in addition to search_fields
extraction. Existing date/array failures remain expected diagnostic failures, not waivers.

## First Artifact and Visibility Failure

The first artifact completed release build in7m58s, exit0:
d8fd7ce603ac78ecc9d2d7c4a558fe508bcb38caafc710a3e01c5727d4f4b544.
Build log SHA030e519531878bc2cfbc99fc25e573cb29b4ce68f9a290616d6c354e6a685460.
Its full40-fixture/2659-case HTTP run terminated exit1 with2367 passed/292 failed/skip0,
no setup failures, count probe passed and binary/fixtures unchanged. The reference is
functional OpenSearch3.7 build f991609d190dfd91c8a09902053a7bbfe0c27b3e.
Four projection cases changed fail->pass; all remaining extracted case statuses match
the matching4086ba72 reports. This is not raw-response equality or complete acceptance.

Raw _source audit found a pre-existing visibility failure even in a search_fields-pass
case: stored_fields:[rank] without an explicit source request returns full source in both
4086ba72 and d8fd7ce6, whereas OpenSearch omits it. The original comparator checked only
fields. Do not count that case as full fetch-contract acceptance or ignore the discrepancy.
The planned timed gate for d8fd7ce6 was NOT started: this draft needs a correctness revision
within the same incomplete unit. Its source, binary, tests, HTTP failures and audit remain.

| Artifact | SHA-256 |
| --- | --- |
| d8fd7ce6 HTTP execution.json | b5d088f025edb8bb3755bef7e9f8b4a2490b9eee5a78b89a639d8b3c03f34da3 |
| HTTP/source audit | 5d37443687ae00c605a782d6aa6e4ad05700f7cd8168d62d07f4b9a15b06d107 |

## Visibility Revision

New isolated source: target/core-replacement-c06/native-fetch-visibility-candidate/source.
Initial revision manifest SHA2c3c07bea1fae696f61274a515116583fe8650a125b1e089f11ef746bd7e4e27.
Full engine/node tests and a separately identified release artifact are required again.

The local OpenSearch FetchPhase.java createStoredFieldsVisitor method distinguishes absent
stored_fields from a selection. An explicit stored field named _source enables source fetch,
even overriding a disabled fetch context, while preserving source includes/excludes. This
is not a Tantivy limitation. The revised existing visibility helper suppresses implicit
source for ordinary stored selections and honors that explicit _source selection. No new
source evaluator, formatter, native reader generation or authorization rule is introduced.

Luna added search_fetch_projection extraction, and the parent reused the existing
search_fields extractor rather than duplicating it. The new comparator additionally checks
each hit's source presence and value: absent source, source:null and a projected object are
distinct. All19 search_compat unit tests pass, including legacy search_fields shape checks.
The original10-case fixture remains unchanged. Additional12-case
search-native-fetch-visibility-contract.json uses the stronger extractor and tests string/
array stored selections, implicit/explicit/disabled source, explicit stored _source,
source filters and numeric arrays. Parent live control uses the actual d8fd7ce6 binary.

Before this unit can complete, run full engine/node, ALL41 HTTP fixtures/2671 cases, and
the full six-run/twelve-topology non-plugin benchmark with fixed initialv0.6.0 cumulative
5% limits. Neither intermediate draft nor an extractor-only pass bypasses that gate.

## Cache Preservation

Visibility revision full engine tests passed966. The first node run terminated101:
682 passed/1 failed in the library suite; the binary suite did not run. The old
search_routes_surface_pagination_track_total_hits_and_target_expansion_semantics
test expected implicit source with stored_fields:"tenant". This contradicts the
reference FetchPhase and the parent live string/array stored-selection responses.
Only that source-presence assertion was corrected to require absence; the fields
assertion is retained. The original node-tests.log is preserved and the entire node
suite must rerun to a new log. This test edit supersedes the initial source manifest.

The complete node rerun subsequently passed1142 tests (683 library +459 binary),
exit0; compile52.97s, test4.08s/12.00s. Log:
native-fetch-visibility-candidate/node-tests-visibility-expectation.log,
SHA87ef2120594a615a7ef3eb51c59a8e5fee84ba08fb1fa1091dba61c1284e7a87.
No further implementation changed in this rerun. Release build, refreshed source
manifest, expanded live HTTP and full benchmark remain pending; test success does
not establish that the292 HTTP failures have decreased.

The subsequent release-build inputs freeze2908 source files in artifacts/source.sha256,
SHA d9454f532236a5070f1b66ffd3cf1f849c1111a7a2b43b4b9184280b73c48cc3.
The original pre-expectation manifest is retained separately. The actual full engine
log SHA is7e07b7b750e9bd01b6ca6cd1d51f4b84b80bfb0469edde951b0f9a0553216654.
The planned HTTP invocation preserves all prior40 fixtures and adds the12-case
visibility fixture:41 fixtures/2671 cases. It records the current root comparator
hash separately from the frozen source tree's comparator.

Visibility release build completed7m50s/exit0, source unchanged:
binary SHA7d83e363a6e2537fedbe4c029d98b894909b62be765212ed08def3dabf409994;
build log SHAdfb791dabee161fc419fcc5402192000c3e9c8285047adfbc8a2f9894907a2e4.
Build provenance and the executable were preserved under artifacts before scoped Cargo
clean removed3943 cache files/2.1GiB. Binary hash was verified again after cleanup.
Full HTTP was then invoked from artifacts/http-invocation.json with all41 fixtures,
actual comparator hashes and the new binary identity. Completion remains pending.

The full41-fixture HTTP run subsequently completed exit1 with2379 passed/292 failed,
zero skipped, no setup failures, count probe passed, and binary/fixtures unchanged.
Functional reference remains3.7.0-SNAPSHOT buildf991609d190dfd91c8a09902053a7bbfe0c27b3e.
All report hashes were verified. Against matching d8fd7ce6 reports plus its12-case
visibility control, exactly three cases improved and no case status regressed:
stored-default, stored-string-default, stored-source-overrides-disabled. All12 visibility
cases now pass; raw ordered IDs/source presence/source values/fields also match the
reference, not just extracted pass statuses. The original292 failures remain unchanged.

| Artifact | SHA-256 |
| --- | --- |
| native-fetch-visibility-release-live/execution.json | 03ee2d6eb41c1b97da6199e89a0c795f487f5e7fa2a8bd8d73e7b75ce9ea4449 |
| native-fetch-visibility-candidate/artifacts/http-audit.json | 7bb7745d805dd2f9577b5d710dcf31a756261e5f4f94d243ee986466740251ed |

Full six-run/twelve-topology performance remains pending for7d83e363. Do not mark the
unit complete or start the next implementation unit without that required measurement.
Latest measured performance is still4086ba72 FAIL; no new performance claim or release.

## Performance Preflight

Recorded runtime settings were additionally compared after the timed run: both single/
three-node baseline and candidate repeats have identical captured workloads, selected
environment/CLI, affinity, limits and visible cgroup settings across all nodes before/
after load. Actual process hashes match each report executable. The audit is
artifacts/runtime-settings-audit.json, SHA
702ca1e65eb825d507f085a8e762c6a1232dd5190a36373a0db4cb4c8aa6395c.
This does not prove effective durability/security parity or production acceptance;
the recorded cgroup coverage/missing-file limitations remain in the evidence.

## Completed Performance Measurement

Actual run directory: target/core-replacement-c06/native-fetch-visibility-repeated-full.
All six runs/twelve topologies completed; every subprocess exited0,84 operation groups
reported zero errors, and input verification passed. The gate itself exited1 because
numeric_budget_passed=false; acceptance remains false. Both candidate runs used7d83e363.

| Metric versus initial published v0.6.0 | Repeat1 | Repeat2 |
| --- | ---: | ---: |
| Single-node throughput change | -1.8473% | +2.7006% |
| Three-node throughput change | -5.4686% | -5.9706% |
| Single-node write mean increase | +12.7356% | +8.0665% |
| Single-node write p95 increase | +16.9763% | +11.1348% |
| Single-node write p99 increase | +17.7832% | +12.4313% |
| Three-node write mean increase | +9.8756% | +9.9748% |
| Three-node write p95 increase | +11.6751% | +11.2219% |
| Three-node write p99 increase | +7.5214% | +12.0670% |
| Fixed-baseline failed metrics /44 | 11 | 15 |
| Paired-baseline failed metrics /44 | 11 | 10 |
| Fresh-baseline drift failures /44 | 6 | 3 |
| Single-node throughput / pinned OpenSearch | 2.5784x | 2.6658x |
| Three-node throughput / pinned OpenSearch | 7.8180x | 7.6683x |

All44 fixed-baseline metric values and verdicts, not only this summary, are preserved
in artifacts/performance-audit.json. Full failed lists including lexical/ranking/sort/
nested/refresh are in result.json; they are not waived or offset by faster metrics.
Report hashes were reverified. OpenSearch ratios describe this measured mixed workload,
not all functionality or every latency percentile. No averaging or repeat selection.

| Evidence | SHA-256 |
| --- | --- |
| result.json | 236780df497c7e7d6c8fc324a2fa5e9d8a9b2a0312457835b1fdd9af35d51876 |
| plan.json | eb642583d9c6f0267c7777e20cd5171cd21056a21b252495e26db6de7366b17b |
| artifacts/performance-audit.json | fb568757ed0af01ccca0ef3303c1e7ade9834f00038d9748de8393af69df163c |

This satisfies execution of the full measurement, not the performance acceptance gate.
The pre-existing4086ba72 gate also failed. This run alone does not attribute the cumulative
regression to fetch visibility or justify excluding a correctness fix. Keep the unit
unaccepted and release held. Follow functional-first ordering for the remaining292 cases,
with full measurement after each unit and cumulative recovery required for acceptance.

### Historical Preflight

The baseline executable db244133, published current.json d2fdabfa, candidate7d83e363,
gate runner ce077298 and matrix046630f1 were rehashed and match their recorded identities.
`native-fetch-visibility-predeclared/plan.json` was generated with `--prepare-only`:
six runs/twelve topologies are declared, but NO timed load ran. Execute the gate in a
fresh directory, not this prepare-only directory, and recheck environment headroom first.

Disk free space initially15414489088 bytes was below the default OpenSearch low-watermark
headroom. No watermark, workload, durability or safety setting was changed. Three inactive
C06 cache directories (fallback-pipeline-candidate, native-bucket-pipeline-candidate,
fst-isolated-candidate) contained binaries identical to their preserved artifacts. Every
cache file was archived and verified after decompression before scoped Cargo clean;
each clean exited0 and all artifact binaries remain. Archive SHA:
4a53314136798d0e6719f18fb860aea87c7ccc59ba5b35391612b0dfd0f3f741.
Preservation ledger artifacts/pre-gate-duplicate-cache.json SHA:
0b3e27318a9da8880baf2129956c7bcebb3de4a3c0bdd3f8fe47f2ea7d96d729.

The inactive field-cache-debug-candidate/steelsearch was compressed separately, with
no matching live executable in /proc and decompressed SHA verified before removing
the uncompressed copy. Restore from steelsearch.gz when using old diagnostic paths.
Original SHA fbf849b2174d9849fae75c9caaf71c2aaf35ece8e92563272194f04ad9e18be3;
gzip SHA d82d843e30d3f133b7507ef9fc72c5bc46625ca5558dc0726b2af45207a8ed5c.
The full record is artifacts/debug-binary-compression.json. Final observed disk free
space15550988288 bytes is improved but still tight; it is not a guarantee of sufficient
headroom throughout all runs. All benchmark evidence, candidate/source, baseline and
unrelated services were preserved. This preflight does not complete the performance gate.

The parent visibility control completed1509 pass/3 fail, with9/12 new cases passing.
Report SHA2da8fc0a45885a0e2f37e6c3b1e459db37a612a8456513002512b1ef474d86a1
records source absence in OpenSearch for both default stored-field forms. These are
functional mismatches, not performance failures; the revised candidate is not yet
validated by live HTTP or the full performance gate.

Current diagnostic/build caches were cleaned only after preserving inputs, logs and the
release artifact. Older inactive C05 build caches were archived with every regular file's
SHA verified against decompressed archive content before scoped cargo clean. Preservation
ledgers and archives are under native-fetch-projection-candidate/artifacts:

- pre-gate-cache-preservation.json: archive SHA
  ccb3a1528f49e4faf3dee9aaf98e8eb64b816fce423de47eb45a2bdeb8a23616;1980 files verified.
- pre-gate-fst-cache-preservation.json: archive SHA
  3ba30915415872a849283def3b64daa69e63639ff2157d7f8f340bc207016689;1495 files verified.
  Cargo refused the outer Miri directory without CACHEDIR.TAG; that refusal is preserved.
  Cleanup then targeted its actual nested miri directory with the existing valid cache tag.
  No cache tag was fabricated, no refusal was bypassed, and no source/result file was removed.

Original publishedv0.6.0 evidence and its db244133 binary remain unchanged. No Docker
watermarks, benchmark settings or safety controls were relaxed to obtain disk headroom.
