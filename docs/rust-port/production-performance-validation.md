# Steelsearch Production Performance Validation

This document defines the performance, load, and operations validation required
before Steelsearch can be approved as a standalone OpenSearch replacement.

The goal is not to prove that every OpenSearch feature is implemented. The goal
is to prove that supported Steelsearch replacement workloads meet explicit
latency, throughput, error-rate, resource, recovery, and operations gates, while
unsupported workloads remain visible blockers.

## Scope

Validation applies to Steelsearch-owned clusters and migrated OpenSearch data
that enter Steelsearch through supported APIs and migration tooling. It covers:

- single-node development replacement;
- multi-node standalone Steelsearch clusters;
- supported HTTP write, search, k-NN, hybrid, bulk, refresh, snapshot, restore,
  migration, and cluster-operation paths;
- Steelsearch-vs-OpenSearch comparison for workloads where both systems expose
  compatible APIs.

Validation does not approve direct OpenSearch shard-store reuse, direct
OpenSearch snapshot-byte restore into Steelsearch shard stores, unsupported
plugins, or OpenSearch APIs that remain outside the compatibility matrix.

## Workload Profiles

Each profile must produce a JSON or JSONL report under `target/` and record the
cluster topology, node count, shard count, replica count, corpus size, vector
dimension, duration, client count, query mix, and seed.

| Profile | Required mix | Required evidence |
| --- | --- | --- |
| Write-heavy | At least 70 percent write or bulk operations, periodic refresh, configured shards and replicas. | Throughput, p50/p95/p99 write latency, refresh latency, error rate, operation-log growth, memory growth, disk IO. |
| Search-heavy | At least 80 percent warmed lexical search made up of basic term/match queries, ranking-oriented queries, filtered/sorted queries, and facet or aggregation requests. | p50/p95/p99 search latency, throughput, cache pressure, CPU, memory, error rate. |
| Vector-heavy | At least 70 percent k-NN vector queries with production-representative dimensions. | p50/p95/p99 vector latency, vector cache memory, native memory, throughput, error rate. |
| Hybrid | Mixed writes, lexical queries, vector queries, hybrid bool+k-NN queries, and refresh. | Per-operation latency, throughput, memory growth, cache pressure, error rate. |
| Snapshot/restore | Snapshot while the target cluster is serving read traffic, then restore into an isolated cluster. | Snapshot duration, restore duration, restored shard count, restored document checksums, error rate. |
| Migration | Scroll or PIT export from OpenSearch, retry-safe Steelsearch `_bulk` import, metadata translation, checksum validation. | Source/target counts, checksums, checkpoints, retry counts, migration duration, unsupported metadata gaps. |
| Mixed cluster operations | Concurrent write/search/vector load with rolling restarts, shard relocation, node join/leave, and cluster-state publication. | Recovery duration, relocation duration, publication latency, readiness blockers, client-visible error rate. |

## Tooling

Use the existing tools as the validation entry points:

- `tools/run-http-load-baseline.py` for Steelsearch-only or OpenSearch-only
  sustained HTTP load. It supports configurable client count, expected node
  count, shard count, replica count, corpus size, vector dimension, duration,
  query mix, process RSS sampling, operation-log growth sampling, and optional
  metrics sampling.
- `tools/run-http-load-comparison.py` for Steelsearch-vs-OpenSearch load
  comparison on the same fixture and query mix.
- `tools/run-multinode-rehearsal.sh` for local multi-node cluster formation
  evidence before multi-node load tests are trusted.
- `tools/run-development-replacement-rehearsal.sh` and
  `tools/run-opensearch-compare.sh` for development replacement and compatibility
  rehearsal evidence.
- `tools/attach-release-readiness-evidence.py` for attaching benchmark, load,
  comparison, chaos, packaging, and rolling-upgrade reports to
  `/_steelsearch/readiness` output and writing the artifact-backed
  `release-readiness.json` manifest consumed by production startup preflight.
- `tools/check-release-readiness-evidence.py --require-passed` for verifying
  that the generated production startup manifest contains every required
  release-readiness item, every item passed, no blockers remain, and every
  referenced evidence artifact exists before setting
  `STEELSEARCH_RELEASE_READINESS_FILE`.

Current HTTP load reports include p50, p90, p95, p99, mean, min, and max
latencies per operation, total throughput, error rate, memory RSS delta,
operation-log byte delta, and vector cache byte delta when available.

Current Steelsearch lexical validation also distinguishes between:

- native Tantivy-backed lexical execution for refreshed `match_all`, top-level
  `term`/`terms`, `match`, `bool`, and numeric `range` query paths; and
- compatibility fallback execution for query families that have not yet been
  migrated without changing OpenSearch-facing semantics.

Validation notes must state which execution path was exercised whenever a run is
used as release evidence.

## Metrics

Every replacement-grade run must capture these metrics:

- latency: p50, p95, p99, max, and mean per operation;
- throughput: successful operations per second and total operation count;
- errors: total error count, per-operation error count, examples, and error
  rate;
- resources: process RSS, memory growth, CPU utilization, disk IO, operation-log
  growth, vector/native cache pressure;
- cluster operations: node count, shard count, replica count, cluster-state
  publication latency, relocation duration, recovery duration, readiness
  blockers;
- migration and snapshot: export/import duration, retry count, checkpoint
  progress, snapshot duration, restore duration, checksum and count results.

If a metric cannot be collected by the current harness, the report must include
an explicit unsupported or missing-metric blocker. Missing metrics are not
silently treated as passing.

## Readiness Gates

Development replacement gate:

- single-node load baseline completes with zero load errors;
- comparison dry-run or completed comparison report is attached when OpenSearch
  is available;
- p99 latency and throughput are recorded for write, lexical, vector, hybrid,
  and refresh operations;
- readiness still reports production blockers for missing production-only gates.

Staging replacement gate:

- multi-node rehearsal passes before load begins;
- multi-node load baseline uses the intended node count, shard count, replica
  count, corpus size, vector dimension, and duration;
- Steelsearch-vs-OpenSearch comparison is completed for supported workloads;
- unsupported workload gaps are listed in the comparison report;
- p95 and p99 latency regressions, throughput regressions, memory growth, error
  rate, recovery duration, relocation duration, and publication lag are reviewed
  against the previous accepted staging run.

Production replacement gate:

- all development and staging gates pass on production-like hardware or an
  explicitly approved capacity model;
- mixed cluster-operation soak runs through rolling restarts and shard
  relocation while writes, lexical search, vector search, and hybrid search
  continue;
- error rate is zero for control-plane operations and within the approved SLO
  for client traffic;
- p99 latency, throughput, memory growth, recovery time, relocation time, and
  publication lag are at or better than the approved production SLO;
- benchmark, load, load-comparison, chaos, migration, snapshot, restore, and
  readiness reports are archived in the release record.

## CI And Nightly Plan

Gated CI must run fast deterministic benchmarks and dry-run validation for the
load and comparison harnesses. Nightly jobs must run actual load:

- single-node HTTP baseline against a fresh Steelsearch daemon;
- multi-node HTTP baseline after `tools/run-multinode-rehearsal.sh`;
- Steelsearch-vs-OpenSearch comparison when OpenSearch is available;
- migration rehearsal and checksum validation;
- readiness evidence attachment with freshness checks.

For the current Tantivy-native engine work, benchmark jobs must launch
Steelsearch with:

- `STEELSEARCH_BUILD_PROFILE=release`
- `STEELSEARCH_RUSTUP_TOOLCHAIN=nightly`

until the workspace-wide Rust/Cargo baseline is raised beyond `1.76`.

Soak jobs must run outside normal CI because they are intentionally long-running.
They must combine writes, lexical queries, vector queries, hybrid queries,
refresh, rolling restarts, shard relocation, snapshot, restore, and readiness
polling. A soak report is passing only when the final readiness report has no
unaccepted blocker for the target replacement level.

## Regression Rules

Treat any of these as a release blocker until explicitly accepted:

- load report error count is non-zero;
- comparison target returns non-zero;
- p95 or p99 latency regresses beyond the target replacement SLO;
- throughput regresses beyond the target replacement SLO;
- memory growth, cache pressure, operation-log growth, or disk IO exceeds the
  accepted envelope;
- recovery, relocation, or publication latency exceeds the accepted envelope;
- any required report is missing, stale, unparsable, or not attached to the
  readiness record;
- an unsupported OpenSearch workload is required for the intended cutover.

## Evidence Archive

Archive these files for every replacement decision:

- deterministic benchmark JSONL;
- HTTP load baseline JSON;
- Steelsearch-vs-OpenSearch comparison JSON;
- multi-node rehearsal logs and manifest;
- migration validation report;
- snapshot and restore reports;
- chaos or soak report;
- `/_steelsearch/readiness` report after evidence attachment.

Current benchmark evidence produced by the Tantivy-native transition includes:

- `target/tantivy-native-benchmarks/deterministic_baselines.jsonl`
- `target/search-benchmark-matrix-tantivy-native-rerun/summary.json`
- `target/search-benchmark-matrix-tantivy-native-rerun/report.md`

The release owner must review the archive before approving a replacement gate.
Missing archive evidence blocks production cutover even if the live cluster
currently appears healthy.

## Current E2E Parity Audit Notes

The broad OpenSearch E2E harness is `tools/run-unified-opensearch-e2e.py`.
It aggregates route, semantic, durability, security, and distributed parity
reports across the compatibility fixtures. The report must not treat
`failed=0` as full fixture coverage by itself: a stale or partial report can
have zero failed cases while missing fixture cases that were added later.

As of the current audit command:

```bash
python3 tools/run-unified-opensearch-e2e.py \
  --output-dir target/unified-opensearch-e2e-audit \
  --allow-missing
python3 tools/check-unified-opensearch-e2e-report.py \
  target/unified-opensearch-e2e-audit/unified-opensearch-e2e-report.json
```

the checker fails closed without `--allow-missing` when required suite evidence
does not cover every fixture case. The current collected required-suite reports
show zero failed and zero missing cases. The search semantic suite now reports
49 passed, 0 failed, and 0 skipped cases, including root and targeted
`_validate/query` range-query parity, native root multi-index shard accounting
for term, search-template, sorted, thresholded, ignored-unavailable, and
`_msearch` sub-response status queries, plus OpenSearch-matched error-shape
parity for `_count?q`, malformed `_count`, malformed `exists`, missing search
templates, malformed stored search-template sources, malformed `_msearch` NDJSON
bodies, malformed inline `_render/template` sources, malformed
`_validate/query` payloads, `_validate/query?rewrite=true`, range `_count`,
range `_explain`, OpenSearch-compatible `_msearch` dangling-header parsing,
rescore score-mode, highlight encoder, term suggest size, and missing
`_explain` targets. k-NN query and hybrid-query option parity is covered by the
dedicated `vector-search` suite, which runs against the OpenSearch k-NN plugin
profile and currently reports 10 passed, 0 failed, and 0 skipped cases.

This means OpenSearch feature E2E comparison is broad and currently has no
observed failing compared cases in the collected required-suite reports. The
remaining replacement work is concentrated in explicitly skipped known gaps and
optional blocked suites, not in missing required evidence.

The generated JSON and Markdown reports include `case_gaps` for each suite so
the next run can target the exact missing, skipped, failed, or extra case names
instead of working from aggregate counts only. Each suite also includes
`rerun.unified_command` and `rerun.direct_command` entries so the next evidence
capture can rerun the affected suite without reconstructing command-line
arguments from the fixture table. When missing case names are known, these
commands include repeated `--case` filters and the underlying compatibility
runners fail closed if a requested case name is not present in the fixture.
When `tools/run-unified-opensearch-e2e.py --run --case ...` is used, the
partial case report is merged into the best existing suite report by case name
before the unified audit is regenerated, so targeted reruns can fill missing
evidence without discarding previously passing cases from the same fixture.

`tools/report-rest-api-coverage.py` adds a source-inventory view on top of the
suite/case report. It compares
`docs/rust-port/generated/source-rest-routes.tsv` against compatibility fixture
HTTP methods and paths, then optionally narrows the view to the fixtures from
`ok` required suites in a unified E2E report. The current 0.2.0 audit results
are:

- source REST inventory: 389 total rows, 373 in scope, with 365 `planned`, 6
  `stubbed`, 2 `implemented`, and 16 `out-of-scope` rows;
- all repo compatibility fixtures touch 289 of the 373 in-scope source route
  rows and leave 84 in-scope rows without fixture coverage;
- the green required live audit for `search-semantic` and `vector-search`
  touches 15 of the 373 in-scope source route rows and leaves 358 in-scope rows
  outside that green live subset;
- the broader collected unified report touches 86 of the 373 in-scope source
  route rows, but that report is `blocked` because retained `search-compat` and
  `search-strict` suite evidence still has failed, missing, or skipped cases.

This means current required E2E evidence is clean for its supported fixtures,
but it must not be read as full OpenSearch REST API coverage. The next API
compatibility workstream should promote blocked route-parity suites into the
green required audit one suite at a time, starting from the existing
`case_gaps` lists and preserving the source-inventory coverage report as the
coverage counter.
