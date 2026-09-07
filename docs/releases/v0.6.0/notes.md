# SteelSearch v0.6.0

## Changes

- Repair all 27 originally failing core suite entries (16 distinct cases), excluding two unsupported plugin entries rather than counting them as passes.
- Correct integer missing-sort values and search-after boundaries, source-filter conflict errors, ingest timestamps, date-histogram empty buckets, extended-stats fields and geo-centroid quantization.
- Preserve arbitrary JSON document sources, including internal-looking keys, and improve combined-fields parser error locations without adding parsing work to normal requests.
- Reduce document-record copying, borrow aggregation/nested keys and reuse unchanged segment document-ID snapshots. Unsuccessful optimization trials are not included.
- Require generated scenario performance tables against the previous published release and pinned OpenSearch, with checked raw evidence attached to every future release.

## Compatibility

The supported release profile is **core-no-plugins**. OpenSearch plugin APIs,
including k-NN and ML Commons, are unsupported. Plugin exclusions are not passes.
The performance workload contains no vector or hybrid queries.

Behavioral corrections include OpenSearch-style 400 errors for conflicting
source filters, signed integer extrema for missing sort values, and default
date-histogram min_doc_count=0. Clients relying on the previous behavior should
check these changes before upgrading.

This release is not a claim of complete OpenSearch API/scoring equivalence,
production replacement readiness, or supported mixed-cluster membership.
The release tag is v0.6.0; internal Cargo crate versions and OpenSearch protocol
compatibility version fields are separate identifiers, not the release tag.

## Validation

The final source build was freshly live-compared on 2026-09-07 against separate
OpenSearch 3.7.0-SNAPSHOT instances: core search 1180, strict search 922,
semantic search 79 and document write 78 passes, with zero failures/skips across
all 2259 comparisons. The original-failure audit again confirms 27 repaired
core entries and two excluded plugin entries. The speed reference below is
separately pinned OpenSearch 2.19.0.

A clean rebuild of all local workspace release crates exactly reproduced the
measured db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57
executable. Therefore the 2026-09-06 performance reports identify the final
release source build, not a relabelled different executable. An initial build
using the previous-release comparison cache failed four aggregation cases;
that discarded build is not release evidence. Final source/build provenance
and both the failed attempt and successful revalidation are attached.

Release policy and benchmark-tool tests pass 24 and 30 tests respectively.
Current source library tests pass 825 engine, 585 node and 133 query DSL tests.
The daemon suite passes all 457 tests with one test thread; its initial parallel
run failed one plugin-cache test that passed in isolation. That parallel failure
is preserved in the evidence and is not a claim of plugin support.
Source/build identity, unit-test logs, original-failure closure and detailed
comparison evidence are supplied in the supplementary validation asset.
The mandatory performance-evidence.zip contains the exact validated notes,
metadata and all three raw benchmark matrices. The immutable v0.6.0 Git tag
identifies the release source; build provenance identifies its source commit.

Publication was explicitly requested by the user on 2026-09-07. That approval
does not change the unresolved performance-preservation goal or certify the
broader production readiness gates.

## Known Limitations

- Remote-backed restore options and restored backing-index attachment are rejected as unsupported. Broader restore-option combinations and exact partial/corrupt-shard restore and clone failure parity still need live-reference coverage.
- Search fixtures cover bounded cases, not every parameter combination or exact Lucene/OpenSearch scoring and term-statistics behavior.
- Mixed-cluster peer membership, write replication and external interop remain bounded. Durability, security, rolling-upgrade and aggregate cutover readiness are not certified by the core search/write passes.
- This is a source release with performance and validation evidence, not a certified multi-platform binary/container distribution.
- The original intermediate development control is not v0.5.0. Against that control, three-node long mixed runs show sort mean latency +0.82%; interleaved sort-only runs show +0.18%, with some individual p95 increases. Higher overall throughput does not waive these observations. Strict no-regression acceptance remains unproven.
- These short same-workload comparisons do not establish statistical significance. SteelSearch development durability differs from OpenSearch default durability, so the OpenSearch ratios must not be presented as production-equivalent speedups.

See docs/rust-port/release-diagnostic-2026-09-06.md and the API gap ledger in
the tagged source for detailed evidence and remaining work. Do not use this
release announcement alone as approval for a production cutover.

<!-- release-performance:start -->
## Performance

- Current: `v0.6.0`; previous published release: `v0.5.0`.
- Reference: OpenSearch `2.19.0`; support: `core-no-plugins`.
- Environment: Same Ubuntu 24.04.3 LTS ARM64 host, 3 Neoverse-N1 CPUs and 17 GiB RAM; native SteelSearch processes versus Docker OpenSearch with 512 MiB JVM heap per node and no Docker CPU/memory quota; unrelated host services remained running
- Runtime and durability settings: Both SteelSearch versions used PERSIST_SHARED_RUNTIME_STATE_PER_WRITE=0, SYNC_SHARED_RUNTIME_STATE_PER_REQUEST=0, DEFER_DEVELOPMENT_SHARD_PERSIST_PER_WRITE=1 and DEFER_NATIVE_WRITE_UNTIL_REFRESH=1 (all STEELSEARCH_ prefixed); OpenSearch used default durability, disabled security/demo setup, explicit refresh workload and image digest sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb
- Limits: Measured 2026-09-06, one 60-second run per system/topology; previous reference is a local locked-dependency rebuild of published v0.5.0 commit 2acaea6313cf7da3d7c657af3860bef1ab0ee221, not an official downloaded binary; unequal durability/deployment means no production-equivalent speed claim; fixed-duration writes grow corpora differently; separate development-control sort latency increases remain unresolved
- Workload: 5000 documents, 4 clients, 60.0 seconds per topology, 3 shards; replicas: 0 on one node, 1 on three nodes; seed 13.
- Operation weights: write=15, lexical=15, ranking=15, facet=15, sort_filter=10, nested=10, refresh=5.
- Synthetic source embedding array: 384 numbers per document; no k-NN index or requests.
- Current binary SHA-256: `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
- Previous binary SHA-256: `5633bca06bad3cc447c02be6963bb52f9f9f5965106f24d616c10c7292b1bf8a`.
- Raw reports and release metadata: attached `performance-evidence.zip`.

### Throughput

Higher is better. Change = (current / previous - 1) * 100; ratio = current / OpenSearch.

| Topology | Previous ops/s | Current ops/s | Change | OpenSearch ops/s | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| single-node | 663.42 | 743.01 | +12.00% | 283.11 | 2.62x |
| three-node | 846.55 | 931.37 | +10.02% | 115.11 | 8.09x |

### Scenario Latency

Mean milliseconds, lower is better. Positive change is a regression; speedup = OpenSearch / current. Throughput is not per-operation latency.

| Topology | Scenario | Previous ms | Current ms | Change | OpenSearch ms | Speedup | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-node | write | 2.93 | 2.87 | -2.05% | 13.28 | 4.62x | 5.28 |
| single-node | lexical | 4.45 | 4.10 | -7.91% | 9.72 | 2.37x | 8.95 |
| single-node | ranking | 7.22 | 6.41 | -11.13% | 12.49 | 1.95x | 12.41 |
| single-node | facet | 8.17 | 7.34 | -10.19% | 11.80 | 1.61x | 15.16 |
| single-node | sort_filter | 5.00 | 4.57 | -8.51% | 12.21 | 2.67x | 9.30 |
| single-node | nested | 7.43 | 6.35 | -14.62% | 10.60 | 1.67x | 12.15 |
| single-node | refresh | 9.26 | 7.39 | -20.22% | 52.26 | 7.07x | 14.88 |
| three-node | write | 3.03 | 2.97 | -1.98% | 29.82 | 10.04x | 5.48 |
| three-node | lexical | 3.67 | 3.52 | -4.16% | 25.10 | 7.13x | 6.75 |
| three-node | ranking | 4.92 | 4.48 | -8.89% | 31.56 | 7.04x | 8.04 |
| three-node | facet | 5.46 | 4.93 | -9.59% | 30.82 | 6.25x | 9.45 |
| three-node | sort_filter | 4.13 | 3.97 | -3.80% | 36.73 | 9.25x | 7.19 |
| three-node | nested | 4.79 | 4.35 | -9.09% | 25.95 | 5.97x | 7.92 |
| three-node | refresh | 11.01 | 8.39 | -23.81% | 118.51 | 14.13x | 17.26 |

<!-- release-performance:end -->
