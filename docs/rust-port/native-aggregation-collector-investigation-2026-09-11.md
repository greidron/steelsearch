# Native Aggregation Collector Investigation

## Current Evidence

Latest measured candidate is4086ba72; its full fixed-v0.6.0 gate failed. This investigation
does not reset the baseline or declare C06 complete. See
[the latest complete gate](native-response-mapping-investigation-2026-09-11.md).

The parent reviewed response conversion and Terra reviewed hit materialization:

- SearchResponse/SearchHit::into_opensearch_body already move owned source and optional
  values. The requested-page sharded reducer borrows documents until global pagination.
  The generation-matched ID lookup avoids normal per-hit stored-document decompression.
  Removing its defensive fallback is not a justified hot-path optimization.
- In the latest single-node repetitions, native_response_body_build_nanos is532796343
  and538334165. Dividing by all34243/34558 completed search operations gives15.56/15.58us.
  These are normalized recorded wall-time totals, not per-native-call timings, CPU time,
  JSON serialization cost, or proof of the cause of write latency. The counter may cover
  only native response paths; three-node endpoint counters are not cluster totals.
- Source-score correction is guarded by native authority predicates. Its presence in
  code or an old investigation is not proof that current benchmark requests execute it.
  The known v0.6.0 ranking omission will not be restored.

The next concrete opportunity is different: collect_aggregations_native in the frozen
engine obtains matched documents using Tantivy, then calls collect_aggregations_from_documents.
It does not use Tantivy's aggregation collector. The preserved a5b38b49 CPU profile
native-buffered-write-search-cpu-abba/01-candidate/server-relative-self-report.txt includes
collect_simple_bucket_aggregations_from_documents_with_budget and its memcmp work.
That older profile is directional evidence, not a current4086ba72 CPU attribution.

## Pinned API and Boundaries

Read directly in frozen vendor/tantivy0.21.1:

- aggregation/mod.rs lists fast-field terms, range, histogram/date histogram and metric
  collectors. AggregationCollector::from_aggs and DistributedAggregationCollector::from_aggs
  accept Aggregations plus AggregationLimits. IntermediateAggregationResults supports
  merge_fruits and into_final_result for multiple indexes/shards.
- The current engine schema already makes keyword fields fast. Numeric/date fields are
  fast only when the mapping says so; an adapter must verify actual schema and refreshed
  reader availability, not assume every source field has usable fast values.
- date_histogram validate rejects calendar_interval and format; fixed_interval is supported.
  The benchmark asks for calendar_interval day. A fixed1d capability probe is not proof of
  general calendar equivalence. Time zones, DST, offsets, negative timestamps, bounds,
  empty buckets and output formatting require explicit validation before any translation.
- Native TermsAggregation has order: Option<CustomOrder>. The old plan note about
  parse_terms_aggregation rejecting order describes the product adapter, not proof that
  upstream Tantivy lacks ordering. Do not repeat that mistaken library limitation.
- AggregationLimits controls shared estimated memory and returned buckets. Its default
  limits are not automatically equivalent to the product's cumulative bucket/error contract.
  Resource errors must not silently retry through an unlimited source path.
  In particular, current BucketAllocationBudget counts cumulative allocations in a serial
  collector tree (default65535), while Tantivy's bucket limit checks returned buckets
  (default65000). Passing the same integer is not sufficient to preserve that contract.
  Integration needs proven allocation bounds or a narrow native accounting extension;
  otherwise it must remain ineligible rather than weaken allocation protection.
- Historical rejected unordered document collectors and fused source collectors are not
  a rejection of Tantivy's fast-field AggregationCollector. Do not repeat those rewrites.

## Implementation Plan and Gates

1. Diagnostic-only capability probe against the pinned frozen library: mixed terms/range/
   fixed-day date buckets, duplicate keyword values, distributed merge equality, explicit
   calendar rejection and bucket-limit failure. Preserve source/lock/log identities.
   This is not product implementation, performance measurement or acceptance.
2. Define a native eligibility/translation adapter from actual aggregation and query
   semantics. Include all benchmark facet branches, not only an easier subset as success.
   Validate UTC calendar-day translation before enabling it; retain existing semantics
   for unsupported calendars/options until a native extension is proven. Do not claim
   those paths are native. Preserve nested/source-only fields, post-filter requirements,
   routing and shard scope; never omit requested aggregations.
3. Integrate the proven collector using the same published reader generation and native
   query. Merge intermediate results before finalization. Check exact low-cardinality
   terms, numeric boundary ordering, missing/multivalued data, zero buckets, date output,
   shard truncation/error bounds and cumulative limits. No unapproved accuracy relaxation,
   hand-written replacement bucket engine, or loss of safety/error propagation.
4. Every product implementation unit, including adapter/integration or later extension,
   requires focused tests PLUS full engine/node tests, the full expanded HTTP suite,
   and the full non-plugin six-run/twelve-topology benchmark before completion. Use
   independently identified candidate binaries/build directories and fresh output paths.
   No builds/tests/agents during timed measurement. Record failures rather than dropping them.
5. Fixed initial v0.6.0 remains the cumulative gate: each topology throughput >=95%,
   each scenario mean/p95/p99 <=105%, both prescribed repetitions, no averaging/offsetting,
   favorable selection or baseline reset. Preserve published evidence; retain separate
   previous-published and pinned OpenSearch comparisons. Baseline drift grants no waiver.
6. Over-budget units remain incomplete and must be investigated/optimized. Apply the main
   plan's attributable unresolved single-unit exclusion rule, without removing correctness
   or safety or counting excluded functionality as implemented. Retention exceptions need
   explicit approval. Release remains held and follows the existing release tooling/policy.

Acceptance0/40 and TV1 incomplete remain unchanged. The probe and proposed integration
do not establish performance improvement or overall OpenSearch replacement readiness.

## Executed Capability Probe

Directory: target/core-replacement-c06/native-aggregation-capability-probe.
Terra wrote only its Cargo.toml/src/lib.rs. The parent pinned dependency versions exactly,
matched product date precision to milliseconds, selected a single indexing thread, reviewed
the tests, and executed them. No production or frozen candidate source was modified.

- Dependencies use the frozen4086ba72 Tantivy0.21.1/FST/columnar paths. The copied parent
  lockfile was resolved offline for the standalone workspace: the only added package is
  native-aggregation-capability-probe; retained dependency versions/sources/checksums
  exactly match the parent. Initial invocation omitted --locked only to add that package;
  subsequent runs used --locked --offline. No dependency upgrade was performed.
- Initial four tests:3 passed/1 failed, exit101, build51.79s. The locked repeat reproduced
  the same failure with3 passed/1 failed. Both show two documents containing service=api
  counted as3 when one document stores api twice. Expected doc_count=2 was not relaxed.
- A fifth scalar control changes only that duplicate value to a single api. It matches
  the complete expected mixed aggregation JSON. Final run:4 passed/1 failed, exit101,
  build1.84s/tests0.04s, no ignored/filtered cases. The original failing expectation remains.
- Distributed intermediate merging matches the combined index, but both share the duplicate
  overcount: this passing test proves merge consistency on the fixture, not correct document
  counts for multivalued inputs. Calendar day rejection and native returned-bucket-limit1
  errors pass their explicit negative expectations. Fixed-day results and terms.order work
  on the small scalar fixture; this is not broad calendar/high-cardinality certification.
- All runs use cargo+nightly test, -j2, an independent build directory, dev/test debug0,
  CARGO_INCREMENTAL=0. All sessions and agents are terminal. The diagnostic has no timed
  benchmark and does not replace an implementation unit's full performance gate.

Preserved evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Initial input manifest | 1dd48d386c9ea61fb44e88b0acf25729866c05e2c528c1238a7413641da9cecc |
| Scalar-control input manifest | 4838715ce51ec2dfa3fd8a180a5dbcd3584871d7916c6dc402dae3d83aec0b6d |
| Initial test log | 9d77be171ae829cbb7e8a48ce62d6bd3dec6a81ec4ba027b09c9e192010dbdf8 |
| Locked repeat log | b7354d6f1b3413d4da4f3bf4f9ba4e626b04caad69c4fc2e33db858c3e50427b |
| Scalar-control test log | 39e491aff4d3f31db65fc18262614d487c632b07ebd074737e14a7e16f29b057 |

The pre-control source is retained as artifacts/probe-before-scalar.rs; initial manifests
and both failed logs are not overwritten. The latest input manifest and frozen candidate
source manifest must be checked after execution.

Next implementation constraints are now concrete:

1. Validate product/reference document-count semantics with repeated and distinct multivalues
   before integration. Verify numeric range/date multivalues too; do not extrapolate the
   keyword observation to every collector. Test the actual facet query shape, not only AllQuery.
2. Derive native eligibility from the same reader generation's actual field/column state.
   Scalar fast fields are a demonstrated candidate, not yet a production fast path. Unsupported
   multivalues must retain existing semantics until a narrow native correction is verified;
   do not silently overcount or report those requests as natively supported.
3. Prove UTC day translation, output formatting and cumulative allocation protection before
   enabling the whole facet request. The source-allocation/native-returned-bucket distinction
   remains unresolved. Merely using AggregationLimits defaults is not acceptable.
4. Only after these contracts are proven, implement the adapter/collector unit and execute
   its full engine/node/HTTP/non-plugin benchmark gate as specified above. Current performance
   evidence remains the failed4086ba72 gate; no new performance improvement is claimed.

## Multivalue and Eligibility Follow-up

Terra added numeric/date multivalue tests, then reader-cardinality, negative UTC boundary
and native BooleanQuery controls. The parent reviewed and ran each frozen input set with
the same locked/offline command and isolated build directory. No product/vendor changes.

| Run | Passed | Failed | Exit | Scope |
| --- | ---: | ---: | ---: | --- |
| Multivalue extension | 5 | 3 | 101 | Eight native-library tests |
| Eligibility extension | 8 | 3 | 101 | Eleven native-library tests |

The three failures retain their original correct-document-count expectations:
keyword api count2 is3; one numeric document with [50,50,60] has range count3 instead
of1; one date document with [0,0,1000] has fixed-day count3 instead of1. Values spanning
two numeric ranges correctly contribute once to each range. This is not approximate
distributed terms error and has no approved tolerance waiver.

New passing controls establish only the tested boundaries:

- Actual reader-backed keyword ords(), numeric and date columns expose Full versus
  Multivalued cardinality without scanning stored source. Optional/empty columns,
  deleted documents, multiple segments and refresh transitions still require tests.
- Scalar timestamps -1,0,86399999,86400000 produce UTC keys -86400000,0,86400000 with
  counts1,2,1. This does not certify all representable dates or time-zone/calendar options.
- Native BooleanQuery intersection of service=api/category=auth restricts the whole mixed
  collector to one document. It is not the benchmark's text-match/tenant query compilation
  or proof of product routing/postfilter eligibility.

Preserved pre-edit sources are artifacts/probe-before-multivalue.rs and
artifacts/probe-before-eligibility.rs. All four input manifests verify against their
matching preserved/current source. Frozen4086ba72 source.sha256 also verifies unchanged.

| Artifact | SHA-256 |
| --- | --- |
| Multivalue input manifest | 1c640c41fbea89460029817ebbd95a28399db1d45eb7f783d90ac73b716a790d |
| Multivalue test log | 7b266d8b75c1bfec8a6fccc580829cb3f1ec73ae4a6710142e17098fca9611cb |
| Eligibility input manifest | 24b1ca9ff604b6a0493e966e8c6bf50dbf1bbf851fd76b58872743584a11ccb9 |
| Eligibility test log | 0042deaaf00b226fa0ada01bbe3c5db9e8e8c04ec13f7eeafb4dba6c9ea4b7b8 |

## Live Reference Contracts

Two diagnostic HTTP runs used the unchanged4086ba72 executable and actual OpenSearch
3.7.0-SNAPSHOT build f991609d190dfd91c8a09902053a7bbfe0c27b3e, Lucene10.4.0.
This is the functional reference, not the pinned2.19.0 performance reference.
Both runs terminated with exit1, passed count probes, recorded binary/fixtures unchanged,
and have verified report hashes. Their repeated1500 core cases must not be added together
as3000 distinct tests or represented as the full expanded HTTP acceptance suite.

| Output under target/core-replacement-c06 | New fixture | New pass/fail | Entire run pass/fail |
| --- | --- | --- | --- |
| native-aggregation-contract-reference | search-native-aggregation-collector-contract.json | 8/6 | 1508/6 |
| native-aggregation-date-parsing-reference | search-native-aggregation-date-parsing-contract.json | 0/10 | 1500/10 |

No skipped cases or setup failures. The first run records actual1/3 shard settings and
search-shard state for both targets. All original fixtures and failures are preserved.
The second fixture adds explicit epoch_millis and scalar1000 controls; its min_doc_count1
cases reveal nonempty buckets without triggering zero-fill across centuries. They are
additional diagnostics, not replacements for the original default-min_doc_count failures.

Raw responses establish separate contracts:

1. OpenSearch counts duplicate keyword/numeric terms and same-range multivalues once per
   document. With explicit epoch_millis it also counts repeated dates once per UTC bucket.
   Pinned Tantivy's three duplicate-count failures therefore block unguarded integration.
2. Under default date mapping, numeric1000 is parsed as year1000 for BOTH scalar and array
   input: docvalue_fields(format=epoch_millis) returns -30610224000000. Explicit epoch_millis
   mapping returns1000. The original354287-bucket errors result from the large date span;
   they are not evidence of an OpenSearch multivalue collector defect. Do not emulate the
   error blindly or weaken the bucket limit to hide it. SteelSearch interprets1000 as1s.
3. Explicit epoch_millis mapping also controls the default histogram key_as_string:
   OpenSearch returns "0"/"86400000" while SteelSearch returns ISO strings. Numeric keys
   and counts match for these controls, but the response contract still fails.
4. Both docvalue_fields controls request _source:false and format=epoch_millis. OpenSearch
   returns fields.event_time; SteelSearch omits fields entirely. This is a product fetch
   contract gap, not proof that Tantivy cannot read date fast fields.
5. The original filtered mixed request with explicit terms.order also has product low-range
   count0/day buckets[] where the new plain-terms request yields the expected numeric counts.
   The two request shapes are not interchangeable. Isolate this dispatch difference before
   claiming multivalue fallback correctness; retain both fixtures and their raw responses.

| Artifact | SHA-256 |
| --- | --- |
| First execution.json | 5814d6ac5676a66f1030d21d932f5921d75ef27c9dcbbe78643bee951f070158 |
| First new-fixture report | ca5d8b223cbef62e821c7d5dc629ca696179104da2d3a9cc27fb94b98d637cc0 |
| Date-parsing execution.json | 060ca297f73b4c5e4cf47d341675c30c70090f6a91585143380e0c5cac0d5b82 |
| Date-parsing new-fixture report | 7da957d7b84755b53d5e97abc1c59e9b71a47aeff21579d1da68e738476ade91 |

## Next Integration Decisions

- C02 date ingestion and C05 fetch/C06 formatting failures above are open product work,
  not accepted exclusions. Check native date representation/formatter and existing adapter
  ownership before changes; do not add a per-query source evaluator to repair ingestion.
- Initially consider only flat, verified single-valued native columns and a query with no
  required source postfilter, all from the same published reader generation. Reject unsupported
  eligibility before execution, rather than catch resource errors and silently retry.
- For exact low-cardinality terms, use actual reader dictionary cardinality to bound all
  shard/segment candidates before truncation. A small requested size alone is not a bound.
  Prove integer/date precision and UTC-day translation, including mapping-derived output.
- Cumulative allocation accounting remains unproven. A prospective conservative preflight
  can use dictionary cardinalities, range counts and checked date-span bounds across all
  segments/shards and merge stages. It must cover intermediate/empty buckets, not only final
  output. An overestimate can make the request ineligible; it must not introduce a false
  TooManyBuckets response where the existing correct path succeeds. Do not enable native
  collection until that bound or a narrow native accounting extension is tested.
- Each resulting product implementation unit must run full engine/node tests, the expanded
  HTTP suite including BOTH new fixtures (previous37 plus2,2649 total cases), and the full
  six-run/twelve-topology non-plugin benchmark before completion. Preserve all failures,
  use separately identified builds, and enforce the initialv0.6.0 cumulative5% gate.

No product unit was completed in this diagnostic follow-up. Acceptance0/40, TV1 incomplete,
the latest failed4086ba72 performance evidence and release hold remain unchanged.
