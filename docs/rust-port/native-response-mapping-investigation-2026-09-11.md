# Native response mapping clone investigation

## Scope and Evidence

This is an incomplete optimization unit, not implementation acceptance or a release.
Parent candidate: native-http-encode-candidate, executable SHA-256
`231c65f67360b27f2cd37625540a427adc01fcc5d4aeb23891cf7bec33ae4bf3`.
Its complete repeated gate failed; see
[HTTP encode evidence](native-http-encode-investigation-2026-09-11.md).

The isolated source is `target/core-replacement-c06/native-response-mapping-candidate/source`.
It was copied from the measured parent's frozen source. Root product code and measured
parent source/binaries remain unchanged.

- PUT holds documents_state for OCC, mapping updates, insertion, and refresh tracking.
  apply_dynamic_mappings_for_source takes metadata_manifest_state under that lock.
  Removing these consistency protections is not an optimization option.
- Normal, PIT, and scroll native response wrappers unconditionally call index_mappings_for,
  cloning mappings under metadata_manifest_state after the engine returns.
- native_search_response_to_rest_response uses that mapping argument only for
  render_existing_search_hit_sort_values_with_mappings. No parsed sort means an early
  return; an empty sort has no fields to render. Thus no mapping is consumed in either case.
  Explicit sort still needs the mapping, notably date/date_nanos string rendering.
- The earlier mapping snapshot for validation and the separate fetch-field mapping
  path remain necessary and are not removed. This is not a claim that all metadata
  locks disappear or that this lock accounts for the measured latency regression.
- The pinned local Tantivy is 0.21.1. This unit changes only the OpenSearch REST response
  adapter, not Tantivy queries, scoring, collectors, native serialization, or visibility.
  It does not add a source-evaluation fallback or substitute custom domain logic.
- Terra traced the mapping consumers; the parent checked the actual renderer. The
  known v0.6.0 ranking omission is not a new finding and will not be reintroduced.

## Implementation Unit and Gate

1. Add one helper that returns a mapping snapshot only for a parsed, nonempty sort.
   Use it at all three native response call sites, passing Option::as_ref to the
   existing response renderer. Keep explicit sort, request validation, PIT/scroll
   state, fetch formatting, security, durability, source, and returned hits unchanged.
2. Test absent/null/empty sorts without acquiring metadata; retain snapshots for
   explicit numeric/date/date_nanos sorts. Compare no-sort response bodies with the
   original mapping-present path, including hits and aggregations. Check actual
   sorted date formatting, not only whether a snapshot exists.
3. Review the diff against the frozen parent and record source manifests. Run focused
   tests, then full engine and full node lib/bin tests with standalone-runtime in a
   separate candidate build directory. No shared parent build-cache identity claims.
4. Build the release artifact, record toolchain/log/binary identity, and run all37
   expanded HTTP fixtures (2625 cases at the parent revision). Preserve all failures
   and compare named case statuses; do not call matching failure counts compatibility.
5. Before marking this unit complete, run the full non-plugin benchmark suite: six
   ordered runs across12 topologies under identical actual workload, resources,
   durability and security. No concurrent build/test/agent activity during timing.
   Preserve prior failed runs and use a fresh output directory.
6. Keep initial published v0.6.0 as the fixed cumulative baseline. Each topology
   throughput must be >=95%; every scenario mean/p95/p99 must be <=105%. Use both
   prescribed repetitions without averaging, favorable selection, baseline reset,
   or compensation across metrics. Baseline drift does not waive candidate failures.
   Preserve previous-published and pinned OpenSearch comparisons independently.
7. An over-budget result remains incomplete: investigate and optimize. Apply the
   exclusion ledger only to proven attributable unresolved single-unit degradation
   under the main plan's rules, never by removing correctness/safety or silently
   treating an excluded feature as implemented. Exceptions require explicit approval.

The performance benefit is unproven. This unit removes a provably unused snapshot,
not a proven explanation of all write/ranking cost. Acceptance remains0/40, TV1
incomplete, release held. Follow the main plan and release tooling for any later release.

## Implementation and Source Tests

- Terra implemented the helper, all three call sites, an empty-sort renderer early
  return, and three tests in native_response_mapping_tests.rs. The parent reviewed
  the diff, added empty-object/boolean sort cases, and formatted only the test file.
  A full tree diff against the measured parent shows only standalone_runtime.rs
  changed and the new test module added. No engine, vendor, Cargo manifest, or lockfile change.
- Source manifest SHA-256:
  `df27bffe3f02502e34bb5d5f8a46d6fb6cf854715712ecd643671b85fa0f8d86`.
  All manifest entries verified after both test runs. Engine/vendor source was also
  compared directly with the frozen parent before testing. Engine compilation began
  while the disjoint node-only patch was finishing; no engine inputs were edited.
- Engine command: `cargo +nightly test --locked --offline -j2 -p os-engine-tantivy`.
  Exit0;946+7+4+9=966 passed, no failures/ignored/filtered tests; doc tests0.
  Build2m19s; test groups14.40/8.44/2.11/0.18s. Log SHA-256:
  `93408b5c1f1b099aceec6ca3c16aaaf9c4d3b0a5d443fa03de5cd33dca25e4a8`.
- Node command: `cargo +nightly test --locked --offline -j2 -p os-node
  --features standalone-runtime --lib --bin steelsearch`.
  Exit0;677+459=1136 passed, no failures/ignored/filtered tests. All three new tests
  passed. Build2m08s; test groups4.22/12.04s. Log SHA-256:
  `65af3b03b360a3c3e2e489d7b2946b59d82fc8da6e3aa98193bf56ae2d8ab18b`.
- Both commands used the isolated candidate/build target directory, dev/test debug0,
  and CARGO_INCREMENTAL=0. All test sessions and agents are terminal.
- Release binary build, expanded HTTP and full performance gate have NOT run for
  this candidate. Do not reuse231c65f6 performance or HTTP results as this candidate's
  evidence. Next step is building and identifying its own release artifact, followed
  by the mandatory HTTP and complete repeated benchmark sequence above.

## Release Artifact and Expanded HTTP

- Release build completed with exit0 in7m52s using
  `cargo +nightly build --release --locked --offline -j2 -p os-node
  --features standalone-runtime --bin steelsearch`, CARGO_INCREMENTAL=0, and the
  candidate's separate build directory. Toolchain: rustc1.97.0-nightly,
  commit ad3a598ca4bc7c68bcbbce3e0d3be9a7618df190, aarch64-unknown-linux-gnu,
  LLVM22.1.4. Source manifest verification passed after the build.
- Preserved artifact: native-response-mapping-candidate/artifacts/steelsearch,
  SHA-256 `4086ba72cd923c0757584af7cf58a5980ceae838084ebabb30c4b68b4d69fcc3`.
  Build log SHA-256:
  `37c6c46ae23f502ad797a8b545d1609f3d732030850e1e4246d82995b39a29da`.
- After preserving the artifact, cargo clean removed only this candidate's build
  cache (3943 files,2.1GiB reported). The binary, source, manifests, and test/build
  logs remain. Available disk space was15630938112/102888095744bytes before HTTP.
- Luna verified37 fixture hashes; the parent independently rechecked them. Actual
  argv is in artifacts/http-invocation.json, derived from the preceding invocation
  by changing only the candidate/output arguments and recording the new binary hash.
  The old output was neither cleared nor reused.
- native-response-mapping-release-live completed37 fixtures/2625 cases:
  2353 passed,272 failed,0 skipped, count probe=true, exit1. Every report SHA was
  checked and all2625 unique (report filename,case name) statuses equal the measured
  parent231c65f6. This does not claim raw-response byte equality or full compatibility.
  Candidate/fixtures unchanged=true. Functional reference identity is
  OpenSearch3.7.0-SNAPSHOT, build f991609d190dfd91c8a09902053a7bbfe0c27b3e,
  Lucene10.4.0. Execution SHA-256:
  `8126105a8109a2fb3598e5c7f8386f35073c4b0d0fec33177c179115311bf798`.

## Complete Repeated Performance Gate: FAIL

- Fresh directory: target/core-replacement-c06/native-response-mapping-repeated-full.
  All6 runs/12 topologies completed, each runner exit0; parent gate exit1.
  Every topology has0 request errors. execution_inputs_verified=true,
  numeric_budget_passed=false, acceptance_established=false.
  The user interrupted observation during the final baseline run; the original
  session remained live and was resumed, not restarted or replaced.
- Baseline remains initial published v0.6.0/db244133. Performance reference remains
  pinned OpenSearch2.19.0/fd9a9d90, not the functional3.7 reference above.
  No concurrent builds/tests/diagnostics/agents ran during timed measurements.
- Plan SHA-256 `2c3484d81686b6e3b6e3f457ad1585836128e745c0f54ad7c28ceef2d8ea211b`;
  result SHA-256 `e7ed17321f7c9e36f26b254808e1de1fa6e2059dc3b38ef28f6d598e2278c203`.
  After completion, source/binary hashes and execution fingerprint/plan verified.
  Recomputing assess from the six source reports reproduced every recorded field.

Throughput (ops/s), with repetitions kept separate:

| Run | Identity | Single-node | Three-node |
| --- | --- | ---: | ---: |
| 00 | v0.6.0 db244133 | 735.283 | 910.558 |
| 01 | candidate4086ba72 | 748.909 | 882.737 |
| 02 | OpenSearch2.19 fd9a9d90 | 279.044 | 114.756 |
| 03 | OpenSearch2.19 fd9a9d90 | 274.027 | 114.109 |
| 04 | candidate4086ba72 | 755.700 | 883.923 |
| 05 | v0.6.0 db244133 | 736.925 | 905.115 |

| Numeric check | Repeat1 | Repeat2 |
| --- | ---: | ---: |
| Failed metrics vs fixed published v0.6.0, out of44 | 13 | 11 |
| Failed metrics vs paired v0.6.0, out of44 | 6 | 8 |
| Baseline drift failed metrics, out of44 | 7 | 9 |
| Single throughput vs fixed v0.6.0 | +0.79% | +1.71% |
| Three throughput vs fixed v0.6.0 | -5.22% | -5.09% |
| Single write mean vs fixed v0.6.0 | +10.60% | +8.52% |
| Three write mean vs fixed v0.6.0 | +8.70% | +8.54% |
| Single throughput / paired OpenSearch | 2.684x | 2.758x |
| Three throughput / paired OpenSearch | 7.692x | 7.746x |

Luna independently verified all6 report hashes,12/12 topology summaries with zero
errors and84/84 operation error counts of zero, and the paired OpenSearch throughput
ratios above. The audit agent was started only after measurement completion and is closed.

- Both repetitions fail fixed-budget three-node throughput, single/three write
  mean/p95/p99, and three-node ranking mean/p95/p99. Repeat1 additionally fails
  single sort_filter mean, three facet p99 and sort_filter p95. Repeat2 additionally
  fails three refresh p99. All44 individual numeric rows, values, limits and pass/fail
  decisions for each comparison are preserved in result.json; no failed metric is omitted
  from the underlying evidence. Baseline drift does not waive candidate failures.
- Paired write mean still regresses: single+7.04%/+8.04%, three+8.15%/+7.27%.
  Paired three-node ranking mean regresses+10.41%/+9.92%.
- Removing the unused snapshot has not resolved the performance gate. Differences
  from separately timed earlier candidates are not causal proof of this one change's
  improvement or degradation. Do not reset the baseline, pool favorable repetitions,
  or restore the known ranking omission to manufacture a pass.
- The unit remains incomplete, unpromoted, acceptance0/40, TV1 incomplete, HTTP272
  failures and release hold retained. No tag/release was created. A cumulative failure
  is not automatically attributable to this single optimization for exclusion-ledger use.
