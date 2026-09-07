# Release Diagnostic - 2026-09-06

Production release decision: NO-GO. The full OpenSearch replacement objective
remains incomplete. This diagnostic does not authorize a tag or release.

Publication update (2026-09-07): the user explicitly requested the v0.6.0
release. Its release notes disclose the unresolved performance and production
readiness limits. Publication approval is separate from the NO-GO decision
for a production replacement claim below; historical no-approval statements
describe the earlier audit, not the subsequent user instruction.

## Latest Evidence-Policy Audit

### Current Completion Audit

| Requirement | Current evidence | Decision |
| --- | --- | --- |
| Exclude unsupported plugins | Original-failure closure records two excluded plugin entries, not passes; core exclusion manifest remains in use | Satisfied within original failure scope |
| Repair remaining original failures | 27/27 original core entries, 16 distinct cases; existing reports have 1180 core, 922 strict, 79 semantic and 78 write passes, zero failures/skips | Functionally verified for the retained candidate; this audit is not a new HTTP run |
| Preserve performance | Current-candidate long mixed runs: single throughput +6.66%, three-node pooled throughput +3.54%; three-node sort mean +0.82% and some per-run tail increases remain | Unproven, not waived by faster total throughput or A/A variation |
| Require future release comparison tables | Documented format, validator, publisher and CI; 24 policy tests pass, including count integrity and validated-snapshot publication | Implemented supported path; remote permission enforcement is not configured |
| Compare against the previous published release and pinned OpenSearch | Fresh same-workload reports cover the pinned `v0.5.0` source rebuild, retained candidate and OpenSearch 2.19.0 below; `606854e7...` remains a separate development control | Measurements available with deployment/durability limitations; an approved release tag and complete new release bundle remain outstanding |
| Publish only after confirmation | No release approval or write operation performed | Remains deferred |

The retained executable hash was rechecked as `db244133...`; the restored engine
suite log records 825 passing tests. Existing live-comparison reports and both
long mixed comparisons were inspected directly, not inferred from the prose
summary. No runtime code changed and no benchmark/compile session was left live.
This audit does not prove overall completion or production replacement readiness.

### Published Reference Discovery

Read-only GitHub API discovery on 2026-09-06 found the latest non-draft published
release (including prereleases in the selection) to be `v0.5.0`, published at
`2026-08-30T02:26:29Z`. Its release has zero uploaded assets, so there is no
attached published executable available through that release's asset list.
This does not claim that no binary exists anywhere else.

The remote annotated tag object is
`2f53d7ff2d3ba8284c4145fe4d62a63fe0935655`, pointing to commit
`2acaea6313cf7da3d7c657af3860bef1ab0ee221`. Both the local tag object and peeled
commit match the remote objects. The release tag is not the current working
HEAD (`af7cdd2bd214d78560a4a7f22837b8a0a2f8e051`). Its `Cargo.lock` SHA-256 is
`9be7646434ae0668a194d6107b0fb84542236a9a06f677ac7a9210da1cee501f`, different from
the current workspace's `16e54ba05ff10f64fd71b87bc923444577a1569879d7f0726edccbd721648087`.
A controlled published-source baseline build must therefore use that exact
commit and its own locked dependencies in an isolated source directory; the
current workspace or an existing development executable cannot be relabelled
as the previous release. The subsequent pinned-source build and comparison are
recorded below; the discovery records alone are not build or benchmark evidence.

Discovery evidence is saved in `target/release-published-list-20260906.json`,
`target/release-v0.5.0-identity.json`, `target/release-v0.5.0-tag-reference.json`
and `target/release-v0.5.0-tag-object.json`. These are identity/provenance records,
not performance evidence. The publisher must still recheck the newest published
release at actual publication time. Only read-only API calls were made; no tag,
release, asset, branch or remote permission was modified.

The original-failure audit was rerun against `shared-put-record/`: 29 original
failed entries, two plugin exclusions and all 27 core entries (16 distinct
cases) passing. This audits existing live-comparison artifacts; it is not a
new live OpenSearch run. The retained executable remains
`db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
No engine/runtime code or performance criterion changed in this audit.

Release-policy inspection found that inconsistent per-operation/sample counts
could pass validation, and the publisher could reread workspace notes/reports
after validating them. Regression tests reproduced both issues. A further test
reproduced a misleading replica label when requested replicas exceeded the
three-node runner's cap. The initial regression run had seven failing assertions
across the new cases; it made no real GitHub calls.

The release validator now requires exactly seven core operation results,
positive integer success/total/latency counts, matching latency and success
counts per operation, and matching operation/scenario totals. Replica labels
reflect the executed cap. Publication snapshots all five evidence-bundle files,
validates that snapshot before GitHub lookup, and uses it for both notes and
the evidence archive. A mocked lookup mutates the original notes/report during
the test to verify that the validated bytes, not those replacements, are used.
Invalid-count publication is also tested to fail before any GitHub contact.

Release-policy tests passed 24/24 and benchmark-tool tests passed 30/30; logs
are `target/release-policy-audit-{before,after,benchmark-tests}.log` (the before
log is the intentional failing regression run). `git diff --check` passed.
The format policy still rejects diagnostic-only reports and still requires both
previous-published-release and pinned OpenSearch comparisons. No release bundle
or published-release performance numbers were fabricated. No push, tag, release
or remote permission change was performed. This hardening is not resolution of
the outstanding performance acceptance question or production-readiness gates.

## Published-Source Benchmark

The verified `v0.5.0` commit `2acaea6313cf7da3d7c657af3860bef1ab0ee221` was checked
out in the detached worktree `target/release-baseline-v0.5.0/source`. Its tracked
source stayed clean and its lock-file hash stayed `9be76464...` before and after
building. The command was `cargo +nightly build --locked --release -p os-node
--features standalone-runtime --bin steelsearch`, with `RUSTFLAGS=-Awarnings`
and the existing build cache. No current fixes or allocator dependencies were
backported. The tag lacks the current workspace's mimalloc dependencies; that
source-version difference was retained, not normalized by altering the tag.

Build completed in 4m09s using rustc 1.97.0-nightly (`ad3a598ca`, 2026-05-03),
cargo 1.97.0-nightly (`4f9b52075`, 2026-05-01), LLVM 22.1.4, on
`aarch64-unknown-linux-gnu`. The baseline executable is
`target/release-baseline-v0.5.0/steelsearch`, SHA-256
`5633bca06bad3cc447c02be6963bb52f9f9f5965106f24d616c10c7292b1bf8a`.
`build-provenance.json` in that directory records the source/tag/lock identity,
toolchain, command and result; `build.log` records the build. This is a locally
rebuilt published-source reference, not a downloaded official executable or a
claim to reproduce an undocumented historical build environment.

The retained candidate was restored at `target/release/steelsearch` and verified
as `db244133...` before measurement. Fresh baseline-then-candidate matrices used
60 seconds per topology, four clients, 5,000 seeded documents, three shards,
zero/one replicas and the seven-operation core mix with 384-value source arrays.
Actual hashes and equal top-level/executed configurations were verified; all
four executions had zero request errors. The release source supports the
development persistence/deferred-write controls used by the runner. No compiler,
reference server, profiler or second load generator competed with a measurement.

| Topology | v0.5.0 source rebuild ops/s | Retained candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 663.42 | 743.01 | +12.00% |
| Three nodes | 846.55 | 931.37 | +10.02% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | -2.05% | -1.74% | -1.98% | -5.05% |
| lexical | -7.91% | -17.39% | -4.16% | -4.48% |
| ranking | -11.13% | -15.84% | -8.89% | -10.83% |
| facet | -10.19% | -14.11% | -9.59% | -10.87% |
| sort_filter | -8.51% | -19.71% | -3.80% | -7.15% |
| nested | -14.62% | -19.41% | -9.09% | -11.15% |
| refresh | -20.22% | -18.75% | -23.81% | -21.48% |

All 14 means and 14 per-run p95 values decreased in this pair. That does not
establish statistical significance from one short pair, remove increases seen
against the separate intermediate `606854e7...` control, or establish the full
performance-preservation goal. These comparisons are not pooled with any prior
development, fixed-work, sort-only or OpenSearch measurements. Development
durability settings are disclosed, not claimed equivalent to production.

Sources under `target/release-baseline-v0.5.0/` are
`performance-before-1/summary.json`, `performance-after-1/summary.json` and the
canonical `published-source-comparison.json`, which attaches build provenance
and explicitly labels the source rebuild. `comparison-check.json` is the
intermediate numeric/configuration check from the development comparison helper;
its generic scope label is not the release-reference identity. No measured
numbers were changed when adding the source-build identity to the canonical
report. The subsequent same-workload OpenSearch report is recorded below; a
complete release bundle is still required. No new release tag was chosen or
published. All temporary benchmark
processes stopped, the detached source remains clean, and the active executable
remains `db244133...`.

## Three-Way Core Comparison

OpenSearch 2.19.0 was measured with the same matrix arguments and workload as
the published-source pair above: 60 seconds per topology, 5,000 initial
documents, four clients, three shards, zero/one replicas, seed 13, and 384-value
source arrays. Weights were write/lexical/ranking/facet 15 each,
sort_filter/nested 10 each and refresh 5; vector/hybrid/fallback weights were
zero. This is core search/write performance, not a vector benchmark despite
the runner's `minilm-knn` profile name.

| Topology | v0.5.0 source ops/s | Current ops/s | Change vs v0.5.0 | OpenSearch ops/s | Current / OpenSearch |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single node | 663.42 | 743.01 | +12.00% | 283.11 | 2.62x |
| Three nodes | 846.55 | 931.37 | +10.02% | 115.11 | 8.09x |

The following are per-operation mean latencies in milliseconds. Negative
previous-release changes mean lower latency; OpenSearch/current ratios above
one mean lower current latency. Current p95 values are individual-run
percentiles, not averages or pooled percentiles.

| Topology | Operation | v0.5.0 mean ms | Current mean ms | Change vs v0.5.0 | OpenSearch mean ms | OpenSearch / current | Current p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Single | write | 2.93 | 2.87 | -2.05% | 13.28 | 4.62x | 5.28 |
| Single | lexical | 4.45 | 4.10 | -7.91% | 9.72 | 2.37x | 8.95 |
| Single | ranking | 7.22 | 6.41 | -11.13% | 12.49 | 1.95x | 12.41 |
| Single | facet | 8.17 | 7.34 | -10.19% | 11.80 | 1.61x | 15.16 |
| Single | sort_filter | 5.00 | 4.57 | -8.51% | 12.21 | 2.67x | 9.30 |
| Single | nested | 7.43 | 6.35 | -14.62% | 10.60 | 1.67x | 12.15 |
| Single | refresh | 9.26 | 7.39 | -20.22% | 52.26 | 7.07x | 14.88 |
| Three | write | 3.03 | 2.97 | -1.98% | 29.82 | 10.04x | 5.48 |
| Three | lexical | 3.67 | 3.52 | -4.16% | 25.10 | 7.13x | 6.75 |
| Three | ranking | 4.92 | 4.48 | -8.89% | 31.56 | 7.04x | 8.04 |
| Three | facet | 5.46 | 4.93 | -9.59% | 30.82 | 6.25x | 9.45 |
| Three | sort_filter | 4.13 | 3.97 | -3.80% | 36.73 | 9.25x | 7.19 |
| Three | nested | 4.79 | 4.35 | -9.09% | 25.95 | 5.97x | 7.92 |
| Three | refresh | 11.01 | 8.39 | -23.81% | 118.51 | 14.13x | 17.26 |

OpenSearch's actual root responses identify version 2.19.0. The Linux ARM64
Docker image was pinned by digest
`sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb`.
Each JVM used `-Xms512m -Xmx512m`; security and demo configuration were disabled.
Captured container limits show no Docker memory or CPU quota. SteelSearch ran
as native processes. Both SteelSearch versions used these development settings:

- `STEELSEARCH_PERSIST_SHARED_RUNTIME_STATE_PER_WRITE=0`
- `STEELSEARCH_SYNC_SHARED_RUNTIME_STATE_PER_REQUEST=0`
- `STEELSEARCH_DEFER_DEVELOPMENT_SHARD_PERSIST_PER_WRITE=1`
- `STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH=1`

OpenSearch retained its default durability behavior. Therefore equal workload
does not mean equal durability, heap/allocation policy or deployment overhead;
these ratios are not a production-equivalent performance claim. Preexisting
unrelated host services remained running. No compiler, profiler or competing
benchmark was run during these measurements. The fixed-duration closed-loop
load also lets faster implementations append more documents, so corpus growth
is not held identical. One run per system/topology is not statistical evidence
of a stable ratio and does not waive regressions against the development control.
Functional parity uses a separate OpenSearch 3.7.0-SNAPSHOT reference, not this
2.19.0 speed reference.

All six scenario reports had zero errors. Validation checked equal top-level
and executed workload configurations (excluding URLs/index names), actual
SteelSearch hashes, actual OpenSearch version, identical operation sets,
matching success/total/sample counts, and operation totals. OpenSearch completed
16,989 single-node and 6,910 three-node requests. Evidence under
`target/release-baseline-v0.5.0/` includes:

- `three-way-comparison.json`: checked three-way numbers and identities.
- `opensearch-2.19-1/summary.json`: raw matrix results and runtime identities.
- `opensearch-image-identity.json`: pinned local image metadata.
- `opensearch-single-runtime.json` and `opensearch-three-runtime.json`: live container limits and selected environment.

The benchmark-owned containers and network were removed after completion;
preexisting services/networks were not removed. No release bundle, tag, commit,
push or publication was performed. These local evidence paths must be packaged
with the validated release bundle once a release is approved; this diagnostic
is not that bundle or approval.

## Latest Shared PUT-Record Candidate

Candidate SHA-256: `db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
The release build completed in 3m59s. `handle_put_doc_route` now shares its
stored record through `Arc` instead of deep-cloning it for insertion. The
native engine's source copy is made only inside the existing native-write
branch, so deferred writes no longer allocate a discarded copy. The local
record owner is released before refresh/persistence. Routing, sequence/version
checks, mapping updates, refresh and persistence policy, and response fields
are unchanged. No dynamic-mapping algorithm change was made.

Node library tests passed 585/585, node executable tests 457/457 and engine
tests 823/823. The new test verifies source versions, held record snapshots,
routing, array tracking, refresh visibility and rejected stale writes. It also
passed alone with `STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH=1`, in a separate
test process. Fresh isolated OpenSearch 3.7.0-SNAPSHOT comparisons passed 1180
core, 922 strict, 79 semantic and 78 document-write cases: 2259 total, zero
failures/skips. The original 27 core failure entries (16 distinct cases) remain
passing comparisons; two original plugin failures remain excluded, not passed.
The raw-value source-preservation regression case remains passing.

Reports, reference identities and `original-failure-closure.json` are under
`target/core-sort-parser-fixes-20260906/shared-put-record/`. Test/build logs in
the parent use the `shared-put-record-` prefix. The immediate previous binary
is archived as `steelsearch-before-shared-put-record` with SHA-256
`ef45bec167dcb445f1d9b9c071a42dba36aecca1fceedb48196590cdc9fe3697`.
Release-note tests passed 20/20, benchmark tool tests 30/30 and fixed-work
diagnostic tests 12/12. Functional success alone does not authorize adoption
as performance-preserving or release publication.

### Immediate Write-Only Diagnostic

An adjacent candidate-then-control diagnostic used 4,000 writes per client,
four clients, 5,000 seeded documents and no measured search/refresh requests.
Every client completed its budget (16,000 requests per topology), with matching
actual request digests/counts and zero errors. The control is the immediately
preceding `ef45bec1...` candidate, NOT the original development baseline,
previous published release or OpenSearch.

| Topology | Control ops/s | Candidate ops/s | Throughput change | Write mean change | Write p95 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single node | 1043.06 | 1049.87 | +0.65% | -0.29% | -0.60% |
| Three nodes | 1029.37 | 1032.63 | +0.32% | -0.03% | -0.47% |

Sources in the shared-put-record directory are `write-before-1/summary.json`,
`write-after-1/summary.json` and `write-comparison-1.json`. These explicitly
diagnostic-only results include client hashing overhead in wall throughput,
not request latency. Cross-client ordering can differ. Small differences from
one pair are not statistical proof or release acceptance evidence.

### Fresh 60-Second Mixed Pair

Fresh candidate-then-baseline runs used the same seven-operation core mix,
5,000 seeded documents, four clients and 60 seconds per topology. Here the
baseline is the original `606854e7...` development executable, NOT `ef45bec1...`,
a previous published release or OpenSearch. Both executable hashes and equal
top-level/executed workload configurations were checked. Development persistence
settings remain unchanged; production durability parity is not claimed.

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 707.41 | 750.57 | +6.10% |
| Three nodes | 906.81 | 930.55 | +2.62% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | -1.34% | -1.33% | -1.62% | -2.98% |
| lexical | -2.97% | -5.59% | +0.98% | +0.18% |
| ranking | -6.27% | -6.49% | -2.97% | -3.73% |
| facet | -8.79% | -10.74% | -5.91% | -7.07% |
| sort_filter | -1.03% | -2.55% | -0.90% | -3.61% |
| nested | -8.38% | -10.37% | -1.92% | -3.12% |
| refresh | -6.69% | -5.44% | -3.47% | +1.09% |

All four scenarios completed with zero errors. Sources in the same directory
are `core-performance-before-1/summary.json`, `core-performance-after-1/summary.json`
and `core-performance-comparison.json`. All single-node metrics decreased;
13 of 14 means decreased. Three-node lexical mean/p95 and refresh p95 increased.
P95 comparisons are per-run, not pooled percentiles. No tolerance or significance
conclusion is assumed. The user has been asked for a repeated-measurement
tolerance; no answer or default-selection consent has been assumed.

The PUT ownership change is retained on functional and measured write-path
evidence, but full performance preservation remains unverified. The repeated
180-second measurements of this actual binary below supersede the earlier
absence of long-run evidence, but retain a sort/filter latency increase.
The older `ef45bec1...` 180-second reports do not verify `db244133...`.
The active goal is not complete and release publication remains
unapproved. No compiler, reference server or profiler competed with timed
measurement; all temporary servers and measurement sessions stopped afterwards.
No commit, push, tag, release or remote permission change was performed.

### Equal-Request Mixed Diagnostic for the Retained Candidate

A new diagnostic used the retained `db244133...` candidate followed by the
original `606854e7...` development baseline, each on one and three nodes. Four
clients each completed 12,000 operations: exactly 48,000 per topology and
executable. It retained the seven-operation mix, 5,000 seeded documents, three
shards, zero/one replicas and 384-value source arrays. The 600-second duration
argument was an incomplete-work watchdog, not a fixed measurement duration.

The dedicated comparator verified distinct actual executable identities, equal
top-level/executed configurations, complete per-client budgets, equal operation
counts and identical per-client hashes of actual HTTP methods, paths and bodies.
All four executions completed with zero request errors. No compiler, reference
server, profiler or other benchmark competed with measurement.

| Topology | Baseline diagnostic ops/s | Candidate diagnostic ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 686.82 | 722.11 | +5.14% |
| Three nodes | 873.59 | 898.12 | +2.81% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | +0.33% | +0.67% | -2.34% | -2.68% |
| lexical | +0.27% | -0.54% | -1.59% | +1.22% |
| ranking | -5.87% | -6.03% | -3.85% | -1.52% |
| facet | -10.36% | -12.85% | -5.79% | -7.57% |
| sort_filter | +0.07% | +2.13% | -1.18% | -0.47% |
| nested | -6.28% | -6.36% | -3.51% | -5.21% |
| refresh | -5.66% | -0.69% | -1.67% | -4.62% |

All seven three-node means decreased under equal per-client work, including
sort/filter, but this does not prove the earlier timed-load increase was caused
solely by different document counts. Single-node write/lexical/sort means,
single-node write/sort p95 and three-node lexical p95 increased here. These
increases are retained, not waived. The pattern differs from the timed runs and
does not establish a code-level cause or full performance preservation.

Both source reports and the comparison are explicitly `diagnostic_only`.
Request hashing is outside individual request latency timers but inside wall
throughput; its CPU cost can affect request pacing. Cross-client ordering and
refresh batching can differ even when each client's request digest matches.
Consequently this is supplementary attribution evidence, not a replacement
acceptance workload. It is not pooled with timed runs, published-release data,
OpenSearch results, or fixed-work results from older candidates. P95 remains
per-run, with no synthetic pooled percentile.

Sources under `shared-put-record/` are `fixed-core-before-1/summary.json`,
`fixed-core-after-1/summary.json` and `fixed-core-comparison.json`. Development
persistence/deferred-write flags remain in effect; production durability parity
is not claimed. Runtime code and the executable were unchanged. All temporary
measurement processes stopped. The user has been asked which performance
metrics and variation tolerance should govern acceptance; no answer, tolerance
or release approval has been assumed.

### Fresh 180-Second Single-Node Mixed Comparison

A fresh baseline-then-candidate pair measured `606854e7...` against the retained
`db244133...` executable for 180 seconds each on one node. It used the same
seven-operation core mix, 5,000 seeded documents, four clients, three shards,
zero replicas and 384-value source arrays. Both actual executable hashes and
equal top-level/executed workload configurations were checked. Both executions
completed with zero request errors. No compiler, reference server, profiler or
second load generator competed with the measurements.

| Topology | Development baseline ops/s | Retained candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node, 180 seconds | 565.70 | 603.38 | +6.66% |

| Operation | Mean latency change | p95 change |
| --- | ---: | ---: |
| write | -1.46% | -1.53% |
| lexical | -2.40% | -4.14% |
| ranking | -4.47% | -5.79% |
| facet | -9.75% | -11.48% |
| sort_filter | -2.56% | -6.11% |
| nested | -9.84% | -13.04% |
| refresh | -5.70% | -5.19% |

All seven means and all seven per-run p95 values decreased in this pair. This
fills the previous absence of current-candidate single-node long-run evidence;
it does not waive the remaining three-node observations, establish statistical
significance from one pair, or prove full performance preservation. The run
does not replace the three-node repeated comparisons or the fixed-corpus sort
diagnostics. No different durations/topologies are pooled and p95 is not pooled.

Sources under `shared-put-record/` are `long-single-before-1/summary.json`,
`long-single-after-1/summary.json` and `long-single-comparison-1.json`. These are
development-binary comparisons, NOT previous published release or OpenSearch
comparisons. Development persistence/deferred-write flags remain in effect;
equivalent production durability is not claimed. Faster closed-loop execution
can append more documents, a workload limitation retained for this pair too.
Runtime code and the executable were unchanged; all temporary processes stopped.
No tag, push, release or remote permission change was performed.

### Repeated 180-Second Three-Node Comparison

Two fresh pairs measured this same `db244133...` candidate against the original
`606854e7...` development baseline. Pair 1 ran baseline then candidate; pair 2
ran candidate then baseline. Each execution used 180 seconds, the same seven
operations, 5,000 seeded documents, four clients, three shards and one replica.
Actual executable hashes, top-level configurations and executed configurations
were checked for both pairs; all four executions had zero request errors.
No build, reference server or profiler ran alongside measurement. Runtime code
was unchanged throughout the four runs, and the temporary servers stopped.

| Pair | Baseline ops/s | Candidate ops/s | Throughput change |
| --- | ---: | ---: | ---: |
| 1: baseline first | 776.55 | 804.19 | +3.56% |
| 2: candidate first | 778.57 | 805.95 | +3.52% |
| Pooled successes / elapsed time | 777.56 | 805.07 | +3.54% |

| Operation | Pair 1 mean change | Pair 2 mean change | Weighted mean change | Pair 1 p95 change | Pair 2 p95 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| write | -1.51% | -0.69% | -1.10% | -1.72% | +0.50% |
| lexical | -0.61% | -0.51% | -0.56% | +0.08% | +0.05% |
| ranking | -2.32% | -2.47% | -2.39% | -3.99% | -3.01% |
| facet | -7.56% | -7.46% | -7.51% | -11.01% | -9.77% |
| sort_filter | +0.88% | +0.75% | +0.82% | +1.45% | +0.03% |
| nested | -4.27% | -5.18% | -4.73% | -6.95% | -5.03% |
| refresh | -4.20% | -3.37% | -3.78% | -2.57% | -1.09% |

Means are weighted by each operation's sample count; p95 values are compared
within each pair, not pooled or averaged into a synthetic percentile. These
180-second results are not pooled with the 60-second measurements. The earlier
lexical mean and refresh p95 increases did not recur, but sort/filter mean
increased in both pairs. Small lexical p95 increases also remained, and write
p95 increased in pair 2. No increase is waived and no statistical significance
or full performance-preservation conclusion is inferred from two pairs.

Sources under `shared-put-record/` are `long-three-before-{1,2}/summary.json`,
`long-three-after-{1,2}/summary.json`, `long-three-comparison-{1,2}.json` and
`long-three-comparison-pooled.json`. These compare development binaries, NOT
the previous published release or OpenSearch. Development persistence flags
remain in effect. A faster closed-loop run executes more writes and therefore
can have a larger final corpus; this is a limitation, not a reason to discard
the measured increases. The separate single-node long pair above subsequently
filled the missing long-run evidence for that topology.

The attribution target is the repeatable sort/filter mean increase. The
workload combines tenant/category filters and a price range with a message
match, sorting by latency ascending and price descending. Source inspection
found per-document key allocation in `NativeMultiSortSegmentCollector`. The
profile and rejected trial below do not establish it as the regression cause.

### Fixed-Corpus Original-Baseline Sort Diagnostic

A fresh unprofiled baseline-then-candidate pair compared `606854e7...` with the
retained `db244133...` executable using 30,000 seeded documents, four clients,
three nodes, three shards, one replica and 60 seconds of sort/filter requests
only. Both sides had identical top-level/executed workload configurations and
verified actual executable hashes. Both completed with zero request errors.

| Metric | Original development baseline | Retained candidate | Change |
| --- | ---: | ---: | ---: |
| Throughput ops/s | 1389.69 | 1378.01 | -0.84% |
| Sort/filter mean ms | 2.8684 | 2.8927 | +0.84% |
| Sort/filter p95 ms | 5.1638 | 5.2036 | +0.77% |

Sources under `shared-put-record/` are
`static-sort-original-before-1/summary.json`,
`static-sort-original-after-1/summary.json` and
`static-sort-original-comparison.json`. There were no measured writes, so the
latency increase in this pair is not explained by a faster candidate appending
more documents during measurement. This single pair does not prove statistical
significance or isolate a code-level cause. It does not waive the mixed-workload
increases or replace mixed-workload acceptance. It is NOT a previous published
release or OpenSearch comparison, and development persistence settings remain.

### Identical-Binary Sort Repeatability Diagnostic

Before another runtime optimization, three sequential executions used the same
retained `db244133...` binary without any intervening build or source change.
Each used a fresh three-node cluster with the same ports, seed, 30,000-document
corpus, four clients, three shards, one replica and 60-second sort-only load.
All actual executable hashes matched. Top-level and executed configurations
were identical; all requests were sort/filter operations and all three runs
had zero errors. No compiler, profiler or reference server competed with them.

| Identical-binary execution | Throughput ops/s | Mean ms | p95 ms |
| --- | ---: | ---: | ---: |
| 1 | 1375.87 | 2.8969 | 5.2121 |
| 2 | 1379.36 | 2.8898 | 5.2082 |
| 3 | 1369.21 | 2.9111 | 5.2322 |

The observed maximum/minimum minus one was 0.74% for throughput, 0.74% for mean
latency and 0.46% for p95. These are descriptive spreads across three runs, NOT
confidence intervals, established noise limits, significance tests, or accepted
regression tolerances. P95 values remain individual-run percentiles.

The observed mean spread is of similar magnitude to the previous +0.84%
fixed-corpus comparison, so that single pair does not establish a code-level
cause. Conversely, these three identical-binary runs do not demonstrate that
the earlier increase was only noise or that performance was preserved. The
mixed-workload increases remain reported and neither rejected optimization is
reinstated. Further code-change claims require stronger interleaved repeated
baseline/candidate evidence, not just one favorable pair or reduced allocations.
Source review also confirmed integer missing-sort sentinels are constructed
through `unwrap_or_else` only when a source sort value is absent; no eager
sentinel-allocation fix was warranted from that inspection.

Sources under `shared-put-record/` are `sort-aa-{1,2,3}/summary.json` and
`sort-aa-summary.json`. The latter is explicitly `diagnostic_only`, records the
three source paths and identical executable/configurations, and does not label
identical-binary measurements as a code before/after comparison. This is not a
previous published release or OpenSearch comparison and does not alter release
acceptance. The executable and runtime code remain unchanged; all temporary
measurement processes stopped.

### Interleaved Original-Baseline Sort Comparison

A fresh four-run block used the order original baseline, retained candidate,
retained candidate, original baseline (A-B-B-A). The two adjacent pairs thus
reverse execution order. Each run used a fresh three-node cluster with 30,000
seeded documents, four clients, three shards, one replica and 60 seconds of
sort/filter requests only. Actual hashes were `606854e7...` for both baseline
runs and `db244133...` for both candidate runs. Top-level and executed workload
configurations were equal across all four runs (excluding base URLs for the
two port ranges), and all four completed with zero request errors. No runtime
source or executable changed during the block; no build, profiler, reference
server or second load generator competed with an execution.

| Pair | Baseline ops/s | Candidate ops/s | Throughput change | Mean latency change | p95 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1: baseline first | 1371.43 | 1369.95 | -0.11% | +0.10% | +0.15% |
| 2: candidate first | 1376.22 | 1372.68 | -0.26% | +0.26% | -0.43% |

Across these two pairs only, pooled successes divided by elapsed time were
1373.83 baseline versus 1371.32 candidate ops/s (-0.18%). Sample-count-weighted
mean latency was 2.9017 versus 2.9069ms (+0.18%). P95 remains per-run: baseline
5.2189/5.2428ms and candidate 5.2266/5.2200ms. No synthetic pooled p95 is computed.

The mean increase appeared in both orders but was smaller than the previous
single-pair +0.84%; the p95 direction was not consistent. Two pairs do not
establish statistical significance or a stable regression magnitude. The prior
identical-binary spread is not an acceptance allowance and does not waive this
increase. No code-level cause, performance-preservation completion or release
approval is inferred. These sort-only runs do not replace the seven-operation
mixed-workload results, including the separate current-candidate single-node
long pair above.

Sources under `shared-put-record/` are `sort-abba-before-{1,2}/summary.json`,
`sort-abba-after-{1,2}/summary.json`, `sort-abba-comparison-{1,2}.json` and
`sort-abba-comparison-pooled.json`. They compare development executables, NOT
the previous published release or OpenSearch. They are not pooled with earlier
sort-only, identical-binary, mixed-load or rejected-candidate measurements.
All temporary measurement processes stopped; the retained executable remains
`db244133...` and no production-code change was made in this verification.

### Original-Baseline Sort CPU Attribution

A missing original-development-baseline profile was collected using the
existing libprofiler-only wrapper at 99 Hz. All three live process hashes were
`606854e7a59628ab3c7cb1bccd1a01970aba3f29793eaeb8993b94b0e4043486`.
The load used 30,000 seeded documents, four clients, three shards, one replica,
384-value source arrays and 30 seconds of sort_filter=100. Profiling began only
after index setup and seeding. The 41,047 measured requests all succeeded.
The report explicitly has `diagnostic_only: true`; its throughput is not
unprofiled performance or release acceptance evidence.

Executed workload settings match the existing retained-candidate sort profile
after excluding base URLs and index names. Both use the same development
persistence flags and profiler library without replacing mimalloc. This new
baseline profile and the earlier candidate profile are not an interleaved
timing pair. No compiler, other benchmark or OpenSearch reference competed
with this collection; preexisting unrelated services remained running.

| Node-1 cumulative CPU samples | Original baseline | Retained candidate |
| --- | ---: | ---: |
| Total samples | 1305 | 1354 |
| search_tantivy_count_and_top_docs_with_scores | 311 (23.8%) | 325 (24.0%) |
| Generic segment collect symbol | 72 (5.5%) | 71 (5.2%) |
| compare_hits_by_sort | 12 (0.9%) | 19 (1.4%) |

These cumulative samples overlap and must not be added. The baseline pprof
demangler abbreviates some generic names to `::collect`; that symbol alone
does not distinguish all collector instantiations. Source inspection ties the
explicit multi-field sort branch to NativeMultiSortCollector, but the profile
does not prove this collector caused the small end-to-end increase. Likewise,
the difference of seven samples in compare_hits_by_sort is too small and
indirect to establish a regression cause. The broad native-search wrapper is
a substantial path in both binaries, not a newly discovered candidate-only
cost. No new runtime optimization is justified by this sample alone.

Evidence lives under `shared-put-record/cpu-profile-sort-original/`:
`diagnostic-load.json`, `profile-metadata.json`, per-node `cluster/node-*/cpu.prof.0`,
`node-1-symbolized.txt`, and portable `node-1-symbolized.profile`. Symbols were
resolved against the actual original baseline, not the current executable.
An initial command was rejected by the load-test opt-in guard before issuing
requests; the completed invocation set `RUN_HTTP_LOAD_TESTS=1`. All owned
servers were then stopped. The retained production source and `db244133...`
executable were not changed. Existing unprofiled increases and the unresolved
performance-preservation decision remain in force.

### Unadopted Full-Window Bound Trial

A separate trial added a boundary comparison before the native multi-sort
collector's binary search. Only when the window was full and its last retained
key/address compared strictly before the incoming candidate would collection
return early. Key allocation, sort-spec storage, encoding, comparisons and
merge rules otherwise stayed unchanged. It did not restore either prior rejected
optimization. The 224-combination full-sort oracle passed, and a new test checks
every prefix of an equal-key input stream with duplicate addresses, better and
worse arrivals, ascending/descending sorts and window sizes 1, 3 and 10.

All 825 engine tests passed. A 4m02s release build produced SHA-256
`d23e37a58242f448029e6033fe36a5c99e361556724048c1bb070f8dc2f2e395`.
Two adjacent sort-only pairs compared it with the immediate retained
`db244133...` candidate, with order trial/control then control/trial. Each fresh
three-node cluster used 30,000 seeded documents, four clients, three shards,
one replica and 60 seconds of sort/filter operations. Actual hashes and equal
top-level/executed configurations were checked across all four executions;
every run had zero request errors. No code/build, competing load, reference
server or profiler intervened during measurement.

| Pair | Retained candidate ops/s | Trial ops/s | Throughput change | Mean latency change | p95 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1: trial first | 1374.23 | 1363.41 | -0.79% | +0.80% | -0.33% |
| 2: control first | 1376.06 | 1381.87 | +0.42% | -0.42% | -1.36% |

Across those two pairs only, pooled successes/elapsed time were 1375.15 retained
versus 1372.64 trial ops/s (-0.18%). Weighted means were 2.8986 versus 2.9039ms
(+0.18%). P95 values remain per-run and are not pooled. Although both p95 values
improved, mean/throughput direction changed with the pair, and the pooled result
did not demonstrate an overall gain. This is not proof of a stable regression
or statistical significance; it is insufficient evidence to adopt the change
as performance-preserving. No A/A spread or arbitrary tolerance is used to
waive the unfavorable results.

The boundary-check runtime change was removed. The general prefix-window test
was retained alongside the full-sort oracle. `target/release/steelsearch` was
restored from `steelsearch-before-sort-key-reuse` to the `db244133...` executable;
the trial executable is archived at `sort-window-bound/steelsearch-rejected`.
No mixed-load or fresh live OpenSearch comparison was run for the unadopted
trial. Its unit-test results are not substituted for the retained candidate's
separate functional evidence.

Sources under `sort-window-bound/` are `static-sort-{before,after}-{1,2}/summary.json`,
`static-sort-comparison.json`, `static-sort-comparison-2.json` and
`static-sort-comparison-pooled.json`. Parent logs use `sort-window-bound-`.
After restoration, all 825 engine tests passed with no failures or ignored
tests (`sort-window-bound-restored-engine-tests.log`, 18.58s test execution).
Formatting and `git diff --check` passed. The retained executable hash was
rechecked as `db244133...`, and all temporary measurement processes stopped.
These compare development candidates, NOT the original `606854e7...` baseline,
a previous published release or OpenSearch. The full performance-preservation
goal remains unverified, and no publication approval is inferred.

### Rejected Sort-Orders-Only Trial

Inspection found `NativeMultiSortSegmentCollector` deep-cloning a complete
`SortSpec` vector per segment despite using only each spec's direction during
collection. A separate trial retained only `Vec<SortOrder>` in the child
collector. Field lookup and unmapped-type validation stayed in `for_segment`;
encoding, key allocation, comparison, windows and merge behavior were unchanged.
The previously rejected scratch-buffer implementation was not reintroduced.
The 224-combination full-sort oracle was adapted to the direction-only child.
All 824 engine tests passed; a release build completed in 4m00s with SHA-256
`b86f22a3ce1fd027e3e38a292517fb082466f6790de7427751870f6f634cea32`.

An adjacent unprofiled trial-then-control pair used the same 30,000-document,
60-second, three-node sort-only workload as above. Here the control was the
immediate retained `db244133...` candidate, NOT `606854e7...`. Actual hashes,
top-level and executed configurations were checked, with zero errors on both
sides. No compiler, reference server or profiler competed with measurement.

| Metric | Immediate retained candidate | Trial | Change |
| --- | ---: | ---: | ---: |
| Throughput ops/s | 1372.43 | 1336.69 | -2.60% |
| Sort/filter mean ms | 2.9044 | 2.9819 | +2.67% |
| Sort/filter p95 ms | 5.2379 | 5.4117 | +3.32% |

The trial did not improve the target workload, so its runtime and test-adapter
changes were removed; the general full-sort oracle remains. Reduced string
copying is not treated as proof of lower end-to-end latency. This pair does not
establish why latency increased, but supplies no performance evidence for
adoption. No further mixed-load or live OpenSearch validation was run for this
rejected binary, and no functional acceptance is inferred for it from another
candidate's reports.

Artifacts under `sort-orders-only/` are `static-sort-{before,after}-1/summary.json`,
`static-sort-comparison.json` and the archived `steelsearch-rejected` executable.
Parent logs use `sort-orders-only-`. `target/release/steelsearch` was restored
from `steelsearch-before-sort-key-reuse` and its SHA-256 rechecked as
`db244133...`. These measurements are diagnostic comparisons of development
binaries, not release baselines. No optimization is adopted from this trial.
After restoration, the engine suite passed 824/824 with no failures or ignored
tests (`sort-orders-only-restored-engine-tests.log`, 18.32s test execution).
Formatting and `git diff --check` passed; the retained full-sort oracle remains
unchanged from before this trial.
The full performance-preservation goal remains unverified; no tolerance or
publication approval is assumed. All measurement processes stopped.

### Rejected Sort-Key Buffer Reuse Trial

A 30-second sort-only diagnostic profiled the retained `db244133...` executable
on three nodes with 30,000 seeded documents, four clients, three shards and one
replica. Sampling started after seeding at 99 Hz, using the existing isolated
libprofiler wrapper without changing the allocator. All three recorded process
hashes match the retained executable. The load completed with zero errors and
is explicitly `diagnostic_only`; its throughput is not acceptance evidence.

The node-1 profile contains 1,354 samples. Cumulative samples include 325 (24.0%)
in `search_tantivy_count_and_top_docs_with_scores` and 71 (5.2%) under a segment
collector's `collect`. Source inspection of the explicit multi-field sort
branch connects that wrapper to `NativeMultiSortCollector`. These overlapping
cumulative samples identify a used path, not a before/after regression cause;
generic/stripped symbol labels are not more precise attribution. Raw profiles,
matching process metadata, the symbolized text and portable symbolized profile
are under `shared-put-record/cpu-profile-sort-current/`.

The trial retained rejected/evicted sort-key vectors as a per-segment scratch
buffer instead of allocating one for every candidate document. Comparison,
encoding and merge rules were unchanged. Engine tests passed 825/825; node
library/executable tests passed 585/585 and 457/457. The trial release build
finished in 4m04s with SHA-256
`7ed433069c7d0126bfc6b08b4fb8fc7b8ee8563ea9c49cac7e6d6630ae5dd0f2`.

Unprofiled adjacent sort-only runs (candidate then immediate `db244133...`
control, 30,000 documents, 60 seconds, three nodes) had matching configurations
and actual hashes, with zero errors. Throughput rose 1363.78 to 1378.17 ops/s
(+1.06%); mean latency fell 1.05% and p95 fell 5.2718 to 5.1758ms (-1.82%).
This small one-pair diagnostic benefit was insufficient for adoption.

A separate 60-second seven-operation mixed pair against the original
`606854e7...` development baseline used 5,000 seeded documents and four clients.
Both actual executable identities and top-level/executed configurations passed
comparison checks; all four executions had zero errors.

| Topology | Baseline ops/s | Trial ops/s | Throughput change |
| --- | ---: | ---: | ---: |
| Single node | 726.55 | 725.39 | -0.16% |
| Three nodes | 902.82 | 920.47 | +1.96% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | +4.82% | +8.71% | -0.98% | -1.52% |
| lexical | +3.44% | +0.76% | -0.35% | -0.32% |
| ranking | -0.90% | -1.01% | -1.65% | -1.20% |
| facet | -2.90% | -2.91% | -4.44% | -7.02% |
| sort_filter | +1.46% | +3.20% | -1.21% | -0.13% |
| nested | -1.77% | +0.09% | -2.48% | -2.31% |
| refresh | +3.41% | +6.54% | -0.84% | +1.30% |

A further adjacent single-node mixed pair compared the trial directly against
the immediate `db244133...` candidate (trial first), with the same 60-second
workload and zero errors. Throughput fell 760.81 to 748.65 ops/s (-1.60%).

| Operation | Trial vs immediate candidate mean change | p95 change |
| --- | ---: | ---: |
| write | +0.85% | +2.33% |
| lexical | +2.39% | +4.70% |
| ranking | +0.58% | -1.76% |
| facet | +2.18% | +1.97% |
| sort_filter | +1.88% | +3.57% |
| nested | +0.75% | +3.53% |
| refresh | +3.43% | +0.58% |

All seven means increased in that direct comparison. These runs do not prove
why cross-operation latency changed, but do not support retaining the trial
as performance-preserving. The scratch-buffer runtime change and its specific
buffer-identity test were therefore removed. The general full-sort oracle was
retained: 224 sort-width/order/offset/limit combinations, three segments with
different arrival orders, missing values, encoded extrema and ties. It checks
segment top windows and merged pagination against full-sort results.
After restoration, the full engine suite passed 824/824 with zero failures or
ignored tests (`sort-key-reuse-restored-engine-tests.log`, 18.29s test execution).
Formatting and `git diff --check` also passed. The initial 823-test candidate
verification above predates this retained additional oracle test.

The rejected binary is archived at `sort-key-reuse/steelsearch-rejected`.
`target/release/steelsearch` was restored from `steelsearch-before-sort-key-reuse`
and its SHA-256 rechecked as `db244133...`; there is no new accepted production
optimization from this trial. Reports under `sort-key-reuse/` are
`static-sort-{before,after}-1/summary.json`, `static-sort-comparison.json`,
`core-performance-{before,after}-1/summary.json`, `core-performance-comparison.json`,
`immediate-single-{before,after}-1/summary.json` and
`immediate-single-comparison.json`. Parent test/build logs use `sort-key-reuse-`.
None compare a published release or OpenSearch. The trial received no new live
OpenSearch suite validation and was not adopted. Earlier functional evidence
for the restored `db244133...` executable remains separate from trial evidence.
No tolerance, significance claim, release approval or performance-preservation
completion is inferred. Benchmark and profiler processes have stopped.

## Previous Isolated Error-Location Candidate

Candidate SHA-256: `ef45bec167dcb445f1d9b9c071a42dba36aecca1fceedb48196590cdc9fe3697`.
The release build completed in 4m15s.

Further diagnosis found a real source-preservation regression in the
`4e019c4c...` candidate below. The `serde_json/raw_value` feature, enabled for
combined-fields error token locations, also changes ordinary `Value` parsing
for an object whose first key is `$serde_json::private::RawValue`. A fresh HTTP
PUT/GET round trip stored `{"payload":{"$serde_json::private::RawValue":"42"}}`
as `{"payload":42}`. The actual `606854e7...` development binary preserved the
object. Raw GET responses are `fixed-work/raw-key-current.json` and
`fixed-work/raw-key-before.json` under the common target directory.

The source repair removes the global feature and confines structured Serde
visitors and read-position tracking to the existing error-only function. It
does not implement a separate JSON grammar. Regression tests cover source
preservation, whitespace/escaped operator positions, nested values and invalid
input. The core fixture now includes
`document_source_internal_raw_value_key_parity`. Node executable tests passed
457/457, node library tests 584/584 and engine tests 823/823. The new location
and document-source tests passed explicitly. Dependency feature inspection
confirms `raw_value` is no longer enabled for os-node. This prevents new source
corruption; it cannot reconstruct original objects already stored incorrectly.

Fresh isolated OpenSearch 3.7.0-SNAPSHOT comparisons passed 1180 core, 922 strict
and 79 semantic cases, zero failures/skips. The new source-preservation case is
a passing live comparison, not only a local assertion. The original 27 core
failure entries (16 distinct cases) were independently re-audited as passing;
two original plugin failures remain excluded. Release-note tests passed 20/20,
benchmark tool tests 30/30 and search-compat tool tests 15/15.

Reports, reference identities and `original-failure-closure.json` are under
`target/core-sort-parser-fixes-20260906/isolated-error-location/`. Build/test
logs in the parent directory use the `isolated-error-location-` prefix.
The old `4e019c4c...` executable is archived as
`steelsearch-before-isolated-error-location`; its previous green suite did not
cover this bug and must not be used to clear that executable for release.
The fixed-work diagnostic results below belong to `4e019c4c...`, not this new
executable.

### Fresh 60-Second Mixed Pair

An adjacent candidate-then-baseline pair used the seven-operation core mix,
5,000 seeded documents, four clients and 60 seconds per topology. The baseline
is the actual `606854e7...` development executable, not the previous published
release, OpenSearch or the immediately preceding candidate. Both executable
hashes and matching top-level/executed configurations were verified. Development
persistence settings are unchanged; production durability parity is not claimed.

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 724.40 | 736.78 | +1.71% |
| Three nodes | 899.61 | 927.86 | +3.14% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | +2.47% | +2.62% | -0.14% | -1.72% |
| lexical | +1.98% | +0.41% | -0.37% | -1.74% |
| ranking | -2.45% | -2.98% | -4.74% | -7.75% |
| facet | -5.58% | -7.10% | -7.17% | -8.59% |
| sort_filter | +1.97% | +0.39% | +1.08% | +0.29% |
| nested | -2.93% | -3.44% | -2.71% | -6.82% |
| refresh | -0.88% | +0.54% | -3.57% | -4.01% |

All four scenarios completed with zero errors. Sources in the isolated-error
directory are `core-performance-before-1/summary.json`,
`core-performance-after-1/summary.json` and `core-performance-comparison.json`.
The p95 changes compare individual runs, not pooled percentiles. Single-node
write, lexical and sort means increased; three-node sort mean also increased.
Aggregate throughput does not waive these observations, and no tolerance or
significance conclusion is assumed. A longer/repeated timed comparison of
`ef45bec1...` remains necessary; the older candidate's 180-second and fixed-work
results do not verify this new executable. Full performance preservation and
the active goal remain incomplete.

The parser repair is retained to prevent the directly reproduced source
corruption while preserving the original error-location contract. No build,
reference server or profiler competed with timed measurement. All temporary
servers and measurement sessions were stopped afterwards. No commit, tag,
push, release publication or remote permission change was performed.

### Fresh 180-Second Pair Across Both Topologies

A baseline-then-candidate pair used the same seven-operation core mix, 5,000
seeded documents, four clients and 180 seconds per topology, with actual
`606854e7...` / `ef45bec1...` executables. Hashes and top-level/executed workload
equality were checked; all four scenarios completed with zero errors.

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 572.29 | 606.59 | +5.99% |
| Three nodes | 775.10 | 799.37 | +3.13% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | +0.40% | -0.77% | +0.42% | -0.30% |
| lexical | -2.49% | -7.61% | +0.65% | +1.55% |
| ranking | -4.10% | -5.40% | -2.98% | -4.16% |
| facet | -9.37% | -10.74% | -6.87% | -10.12% |
| sort_filter | -3.62% | -7.51% | -0.38% | -1.32% |
| nested | -6.99% | -8.63% | -4.80% | -6.53% |
| refresh | -6.55% | -5.42% | -2.43% | -1.68% |

Sources under `isolated-error-location/` are `long-core-before-1/summary.json`,
`long-core-after-1/summary.json` and `long-core-comparison.json`. Do not pool
these with 60-second runs. This longer pair preserves aggregate gains but
does not establish preservation of write mean or three-node lexical latency.
No tolerance or statistical significance is assumed.

Source inspection during these runs found that `handle_put_doc_route` clones
the full source even when native writes are deferred, then deep-clones the
stored record before insertion. A scoped trial now shares the stored record
with `Arc`, clones source only inside the existing native-write branch and
releases its local owner before refresh/persistence. Mapping/sequence handling,
routing, refresh policy and response fields are unchanged. This trial is NOT
part of the `ef45bec1...` measurements above. Node library tests passed 585/585,
node executable tests 457/457 and engine tests 823/823. The new behavioral test
covers source versions, held snapshots, routing, refresh visibility and rejected
stale writes, and also passed in a separate process with native-write deferral
enabled. Further build, live comparison and performance evidence is recorded
for the separate shared PUT-record candidate above, not for `ef45bec1...`.

## Previous Shared-Segment ID Candidate

Candidate SHA-256: `4e019c4c6d91c27db48bad41866e4663f39a8850117a760ab245af8cdef52b77`.
The release build completed in 4m07s. Immutable document-ID arrays are now
shared per segment in `TantivySearchState` and `TantivyDocIdLookup`. Previously,
reusing an unchanged segment cloned its entire vector and every ID string on
each refresh. Reuse still requires matching segment ID and document count;
new/merged segments rebuild their arrays. Query matching, refresh visibility,
commit behavior, source data and persisted formats are unchanged.

The engine suite passed 823/823, including a new test covering pointer-identical
reuse over three appends, deletion without rewriting the ID array, merge
invalidation, equality with a completely rebuilt lookup, old searcher/snapshot
validity, and empty/missing-field lookup behavior. Fresh isolated OpenSearch
3.7.0-SNAPSHOT comparisons passed 1179 core, 922 strict and 79 semantic cases,
zero failures/skips. The original 27 core failure entries (16 distinct cases)
were independently re-audited as passing; two original plugin failures remain
excluded, not passed. Release policy tests passed 20/20 and benchmark tool
tests passed 30/30.

Reports, reference identities and `original-failure-closure.json` are under
`target/core-sort-parser-fixes-20260906/shared-segment-ids/`. Unit/build logs
are `shared-segment-ids-unit-tests.log` and
`shared-segment-ids-release-build.log` in the parent directory. The previous
`943dac3f...` binary is archived as `steelsearch-before-shared-segment-ids` there.
The functional pass alone does not establish performance preservation or
authorize release publication.

### Fresh 60-Second Mixed Pair

Fresh candidate-then-baseline runs used the seven-operation core mix, 5,000
seeded documents, four clients and 60 seconds per topology. The baseline is
the actual `606854e7...` original development binary, NOT a published release,
OpenSearch or the immediately preceding collector candidate. Actual hashes and
matching top-level/executed configurations were checked. Development persistence
settings remain in effect; this is not production durability parity evidence.

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 711.86 | 734.90 | +3.24% |
| Three nodes | 903.03 | 922.88 | +2.20% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | +1.77% | +0.43% | +1.09% | +1.57% |
| lexical | +2.55% | -1.30% | +0.04% | +0.34% |
| ranking | -3.97% | -3.34% | -3.19% | -4.01% |
| facet | -7.32% | -8.38% | -5.49% | -6.05% |
| sort_filter | -0.97% | +3.32% | -0.57% | -1.23% |
| nested | -5.57% | -7.19% | -0.65% | -1.80% |
| refresh | -1.58% | -0.31% | -3.61% | -3.49% |

All four scenarios completed with zero errors. Sources in the shared-segment
directory are `core-performance-before-1/summary.json`,
`core-performance-after-1/summary.json` and `core-performance-comparison.json`.
The existing `refresh_tantivy_doc_id_lookup_nanos.delta` counters decreased
from 2,753,908,891 to 2,393,995,688 (-13.07%) for single-node and from
1,016,817,198 to 875,239,728 (-13.92%) for three-node. Successful writes were
7,625 / 7,866 and 9,637 / 9,830 respectively. These sampled native counters
support reduced lookup work, not an end-to-end attribution or an adjustment
that removes the measured latency increases.
Per-run p95 values are not pooled. Refresh improved, but write and some lexical
and sort-tail increases remain; aggregate throughput does not waive them.
No tolerance is assumed and full performance preservation is not yet verified.

### Fresh 180-Second Mixed Pair

A fresh candidate-then-baseline three-node pair used the same core mix,
5,000 seeded documents and four clients for 180 seconds each. Actual binary
hashes were `4e019c4c...` and `606854e7...`; both hashes and matching top-level
and executed configurations were verified. Throughput was 776.33 / 804.74 ops/s
(+3.66%), with zero errors on both sides.

| Operation | Mean latency change | Per-run p95 change |
| --- | ---: | ---: |
| write | +0.44% | -0.77% |
| lexical | -0.32% | -0.67% |
| ranking | -2.95% | -4.64% |
| facet | -7.66% | -10.57% |
| sort_filter | -0.64% | -0.63% |
| nested | -4.34% | -5.27% |
| refresh | -4.43% | -1.52% |

Sources in the shared-segment directory are `long-three-node-before-1/summary.json`,
`long-three-node-after-1/summary.json` and `long-three-node-comparison.json`.
All seven p95 values decreased, but write mean increased by 0.44%. These are
one pair, not an equivalence/significance estimate. They do not remove the
shorter workload's write/lexical and single-node sort-tail increases above.

Lookup counter deltas were 4,710,416,741 / 4,575,697,309 ns (-2.86%), with
24,562 / 25,492 successful writes. The longer closed-loop run grows the corpus;
do not pool it with 60-second runs or normalize away observed regressions using
write counts. Shared segment arrays are retained on exact functional tests,
live compatibility and measured refresh benefit. Full performance preservation
remains unverified. Next work is to reproduce and attribute remaining write
and short-load lexical/sort-tail increases; a fixed-work diagnostic may help
separate unequal corpus growth, but must not replace or hide timed-load results.

All benchmark sessions completed and no temporary benchmark, profiler or
OpenSearch daemons remained afterwards. No compiler or reference server ran
during the performance measurements. No release, tag, commit, push or remote
permission change was performed. The repair/performance goal remains active.

### Equal-Request Diagnostics

Supplementary diagnostics held work at 12,000 operations per client (48,000
per topology), using the same four clients, seven-operation core mix, 5,000
seeded documents and actual `606854e7...` / `4e019c4c...` binaries. Candidate
then baseline order was used. Every client completed its budget; actual request
content digests and operation counts matched across binaries, with zero errors.
The 600-second duration setting is only a watchdog. Cross-client ordering and
refresh batching can still differ. Hashing is outside the latency timer but
inside wall throughput, so these are explicitly diagnostic-only, not release
speed evidence or substitutes for the timed-load observations above.

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | +0.69% | -1.43% | +0.20% | -1.99% |
| lexical | -1.55% | -1.52% | -1.02% | -0.21% |
| ranking | -5.58% | -6.91% | -3.38% | -3.25% |
| facet | -9.20% | -11.63% | -6.34% | -5.98% |
| sort_filter | -0.38% | -0.02% | -0.97% | -2.78% |
| nested | -5.67% | -6.66% | -3.25% | -1.45% |
| refresh | -7.23% | -4.79% | -3.98% | -5.93% |

Diagnostic wall throughput was 671.01 / 709.07 ops/s (+5.67%) for single-node
and 862.93 / 889.02 (+3.02%) for three-node. Every search mean and every p95
decreased, but write mean still increased. This does not prove corpus growth
caused the timed lexical/sort observations or establish statistical equivalence.

A subsequent baseline-then-candidate write-only diagnostic fixed 4,000 writes
per client (16,000 per topology), with no measured search/refresh requests.
Actual requests again matched, and all completed without errors. Single-node
write mean changed -0.13%, p95 -0.16%, wall throughput -0.08% (1033.58 / 1032.77).
Three-node write mean changed -1.29%, p95 -1.24%, throughput +1.20%
(1012.95 / 1025.06). An isolated write latency regression did not recur in this
pair; mixed-load interference and run variation remain possible, not established
explanations. The source-preservation bug above is separate, directly reproduced
evidence; it is not inferred from these small timing changes.

Artifacts under `target/core-sort-parser-fixes-20260906/fixed-work/` are
`core-{before,after}-1/summary.json`, `core-comparison-1.json`,
`write-{before,after}-1/summary.json` and `write-comparison-1.json`.
`fixed-work.py` delegates request construction and cluster/binary handling to
the existing tools; `compare-fixed-work.py` checks actual hashes, exact work,
request digests/configurations and errors. Both retain diagnostic flags.
`test_fixed_work.py` passed 12 tests. No runtime binary changed during these
diagnostics, and their servers were stopped before the parser repair tests.

## Previous Document-Address Collector Candidate

Candidate SHA-256: `943dac3f1a88e19138807ef36fd6282fff4550cf579005b3b562279b318b6705`.
The release build completed in 4m05s. The two unordered native document lookup
paths now collect addresses in vectors, then sort and deduplicate at merge,
instead of building per-segment and merged hash sets. Tantivy still performs
query matching and deletion filtering; scoring and source filtering are unchanged.

The engine suite passed 822/822. New collector tests compare exact membership
against Tantivy's library collector across multiple segments, successive deletes
and nine query forms, and exercise duplicate callbacks, ordering and ignored
scores. Fresh isolated OpenSearch 3.7.0-SNAPSHOT comparisons passed 1179 core,
922 strict and 79 semantic cases, with zero failures/skips. The original 27
core failure entries (16 distinct cases) were re-audited as passing; the two
original plugin failures remain excluded, not passed.

Reports and `original-failure-closure.json` are under
`target/core-sort-parser-fixes-20260906/doc-address-collector/`. Unit/build logs
are `doc-address-collector-unit-tests.log` and
`doc-address-collector-release-build.log` in the parent directory.

An adjacent candidate-then-control ranking diagnostic used 30,000 fixed
documents, three nodes, four clients, 60 seconds and no measured writes or
refreshes. The control is the immediately preceding `23e0d96b...` development
binary, NOT a published release or OpenSearch.

| Metric | Previous candidate | New candidate | Change |
| --- | ---: | ---: | ---: |
| Throughput (ops/s) | 821.13 | 880.53 | +7.23% |
| Ranking mean (ms) | 4.8598 | 4.5315 | -6.76% |
| Ranking p95 (ms) | 9.8912 | 8.9079 | -9.94% |

Both runs had zero errors. Sources are `static-ranking-before-1/summary.json`,
`static-ranking-after-1/summary.json` and `static-ranking-comparison.json` in
the same directory. Executable hashes and workload equality were checked.
This targeted diagnostic does not establish mixed-load performance preservation.

### Fresh 60-Second Mixed Pair

Candidate-then-baseline runs used the seven-operation core mix, 5,000 seeded
documents, four clients, three shards and 60 seconds per topology. The baseline
is `606854e7a59628ab3c7cb1bccd1a01970aba3f29793eaeb8993b94b0e4043486`,
the original development binary before the sort/parser repairs, NOT the
immediately preceding candidate, a previous published release or OpenSearch.
Development persistence settings remain in effect; these are not production
durability parity measurements.

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 702.27 | 737.85 | +5.07% |
| Three nodes | 903.52 | 912.39 | +0.98% |

| Operation | Single mean change | Single p95 change | Three mean change | Three p95 change |
| --- | ---: | ---: | ---: | ---: |
| write | -0.30% | -1.76% | +0.81% | +0.09% |
| lexical | -1.07% | -0.38% | -0.67% | -0.47% |
| ranking | -5.82% | -5.20% | -1.09% | +0.48% |
| facet | -8.94% | -8.64% | -3.38% | -5.29% |
| sort_filter | -2.43% | -6.56% | +1.76% | +2.66% |
| nested | -6.80% | -7.77% | -3.67% | -6.40% |
| refresh | -1.29% | -0.61% | +1.54% | -0.98% |

All four scenarios had zero errors. Actual executable hashes and top-level and
executed workload configurations were checked. Sources in the collector
directory are `core-performance-before-1/summary.json`,
`core-performance-after-1/summary.json` and `core-performance-comparison.json`.
The p95 changes compare individual runs, not pooled percentiles. All single-node
metrics decreased, but three-node increases remain and are not hidden by the
throughput improvement. This is one pair, not a significance estimate.
No regression tolerance or publication approval is assumed.

### Fresh 180-Second Mixed Pair

A baseline-then-candidate three-node pair used the same seven-operation mix,
5,000 seeded documents and four clients for 180 seconds each. Actual executable
hashes were again `606854e7...` and `943dac3f...`; the comparison helper checked
both hashes and matching top-level/executed configurations. Throughput was
776.53 / 798.96 ops/s (+2.89%), with zero errors on both sides.

| Operation | Mean latency change | Per-run p95 change |
| --- | ---: | ---: |
| write | -0.30% | -0.30% |
| lexical | -0.51% | -0.80% |
| ranking | -2.62% | -1.76% |
| facet | -6.85% | -8.30% |
| sort_filter | -0.23% | +0.62% |
| nested | -5.41% | -6.61% |
| refresh | +1.41% | +4.51% |

Sources in the collector directory are `long-three-node-before-1/summary.json`,
`long-three-node-after-1/summary.json` and `long-three-node-comparison.json`.
Do not pool these with the 60-second runs: writes grow the corpus during the
measurement. The new collector is retained on its functional and measured
ranking benefit. Ranking's earlier long-run increase did not recur in this
pair, but refresh and sort-tail increases remain. Their significance and cause
are not established by one pair. Full performance preservation is unverified,
and the active repair/performance goal is not complete. Next verification
should focus on reproducibility and attribution of refresh and sort-tail costs,
without using aggregate throughput to waive them.

No compiler, reference server or profiler competed with these measurements.
All benchmark sessions completed successfully and no temporary benchmark or
OpenSearch daemons remained after the runs. Release policy tests passed 20/20;
no tag, commit, push, remote permission change or publication was performed.

### Repeated 180-Second Pair Before Shared-Segment Trial

A second pair reversed the order (candidate then baseline), still using the
actual `943dac3f...` and `606854e7...` binaries and identical 180-second settings.
Throughput was 773.15 / 795.59 ops/s (+2.90%), with zero errors. Sources are
`long-three-node-before-2/summary.json`, `long-three-node-after-2/summary.json`
and `long-three-node-comparison-2.json` in the collector directory.

| Operation | Second-pair mean change | Second-pair p95 change | Two-run weighted mean change |
| --- | ---: | ---: | ---: |
| write | +0.52% | -0.19% | +0.11% |
| lexical | +0.75% | +0.19% | +0.12% |
| ranking | -2.07% | -2.98% | -2.35% |
| facet | -7.86% | -11.60% | -7.36% |
| sort_filter | -0.15% | -1.21% | -0.19% |
| nested | -4.22% | -5.68% | -4.82% |
| refresh | -1.09% | -1.38% | +0.15% |

`long-three-node-comparison-pooled.json` checks all four configurations and
hashes, and weights operation means by request counts. Pooled throughput is
774.84 / 797.28 ops/s (+2.90%); p95 values remain per-run, not pooled.
Refresh and sort-tail increases from the first pair did not repeat in the
second pair. This weakens a claim of a consistent regression but does not
establish equivalence or justify an unapproved tolerance. No failures occurred.

The first pair processed 24,567 baseline writes and 25,293 candidate writes;
the closed-loop corpus growth differs. Existing refresh counters and source
inspection identified a separate avoidable cost: `build_tantivy_doc_id_lookup`
deep-clones every unchanged segment's ID vector and strings on reuse. A scoped
trial shares immutable per-segment vectors, retaining segment-ID/max-doc reuse
guards and rebuilding new/merged segments. That trial is not part of the
`943dac3f...` measurements above; its tests and performance must be verified
separately before making an adoption claim.

## Previous Borrowed-ID Candidate

Candidate SHA-256: `23e0d96b126c3532bb026d21e135bd9e2d888dc40c66a2465bca3a1c2432f7f9`.
The release build completed in 4m05s. The scoped native nested candidate
collector now returns borrowed parent IDs; only callers requiring owned IDs
clone them at the ownership boundary. The paginated search path consumes the
borrowed set directly. Ordering, deduplication, shard selection, refresh
visibility and source fallback admission are unchanged.

The engine suite passed 819/819, including a new test that verifies duplicate
parents, unrefreshed parents, missing paths/terms, case-insensitive source
fallback and pointer identity with the original strings. Fresh isolated
OpenSearch 3.7.0-SNAPSHOT comparisons passed 1179 core, 922 strict and 79
semantic cases, zero failures/skips. The original 27 core failure entries
were independently re-audited as passing comparisons. Reports and
`original-failure-closure.json` are under
`target/core-sort-parser-fixes-20260906/borrowed-nested-ids/`.
Unit/build logs are `borrowed-nested-ids-unit-tests.log` and
`borrowed-nested-ids-release-build.log` in the parent directory.

The fixed 30,000-document nested diagnostic measured 689.57 ops/s and 5.7880ms
mean latency, versus 653.79 ops/s and 6.1060ms for the earlier `60bfbdcd...`
run: +5.47% throughput, -5.21% mean latency, zero errors. Candidate p95 was
9.8212ms versus 10.3639ms. Sources are `static-nested-after-1/summary.json`
and `static-nested-comparison.json`; the comparison links the previous raw
report and checks matching configurations and actual executable hashes.
These runs were not adjacent. This diagnostic isolates the nested path, not
the real mixed workload, a previous published release or OpenSearch speed.
Fresh adjacent 60-second core mixed-workload runs completed in candidate then
baseline order. The baseline is the original `606854e7...` development binary,
not the immediately preceding candidate or a published release.

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 709.64 | 732.96 | +3.29% |
| Three nodes | 897.79 | 911.82 | +1.56% |

| Operation | Single-node mean latency change | Three-node mean latency change |
| --- | ---: | ---: |
| write | -1.06% | -0.44% |
| lexical | -2.83% | -0.64% |
| ranking | -1.65% | -1.17% |
| facet | -5.13% | -2.52% |
| sort_filter | -0.31% | -1.26% |
| nested | -6.17% | -3.45% |
| refresh | -3.19% | -1.00% |

All four scenarios had zero errors. All 14 mean latencies decreased; 13 per-run
p95 values decreased, while three-node lexical p95 increased by 0.05%. These
are one short pair, not proof that every latency metric is preserved or a
statistically established tail regression. No tolerance has been assumed.
Reports are `core-performance-after-1/summary.json`,
`core-performance-before-1/summary.json` and `core-performance-comparison.json`
under the same borrowed-nested-ids directory. Actual hashes and top-level/
executed workload equality were checked. Temporary servers and compilers were
stopped before performance runs and no temporary servers remained afterwards.

The borrowed-ID change is retained on this functional and targeted-performance
evidence. The longer follow-up below confirms its nested benefit but does not
establish preservation of the other operations. The goal is not marked
complete and no release/tag/publication is authorized.

### Current 180-Second Mixed Pair

A fresh baseline-then-candidate three-node pair used 180 seconds per run, the
same seven-operation core mix, 5,000 seeded documents, four clients and the
same actual `606854e7...` / `23e0d96b...` executables. Throughput increased from
774.79 to 778.47 ops/s (+0.48%), with zero errors on both sides.

| Operation | Mean latency change | Per-run p95 change |
| --- | ---: | ---: |
| write | +0.87% | +2.14% |
| lexical | -0.31% | +0.75% |
| ranking | +1.76% | +3.09% |
| facet | -1.02% | -2.64% |
| sort_filter | +0.34% | +1.83% |
| nested | -5.15% | -8.26% |
| refresh | -0.08% | +0.37% |

Sources under the borrowed-nested-ids directory are
`long-three-node-before-1/summary.json`, `long-three-node-after-1/summary.json`
and `long-three-node-comparison.json`. Configuration equality and executable
identities were checked. Do not pool these with the shorter runs or hide the
increases behind the aggregate throughput improvement. One pair does not
establish statistical significance, and no regression tolerance is assumed.
The nested improvement persists, while full performance preservation remains
unverified. No source or executable changes occurred during these measurements.

### Current Fixed-Corpus Ranking Diagnostic

The ranking workload uses `multi_match`, phrase/term should clauses and a
numeric range filter, without an explicit field sort. A supplementary adjacent
baseline-then-candidate pair fixed the corpus at 30,000 documents and used
`ranking=100`, three nodes, four clients and 60 seconds, without measured writes
or refreshes. Throughput was 813.04 / 810.17 ops/s (-0.35%), mean latency
4.9087 / 4.9257ms (+0.35%) and p95 9.8358 / 9.8692ms (+0.34%), with zero errors.
Sources are `static-ranking-before-1/summary.json`,
`static-ranking-after-1/summary.json` and `static-ranking-comparison.json` in
the same directory. This is a diagnostic pair, not release acceptance evidence.

The smaller increase without writes/refreshes means their interference cannot
be assumed to explain the entire mixed-load observation. Source inspection
confirms that default relevance comparison uses score comparison and identity
tie-breaking, not the modified integer missing-sort comparator. This does not
prove which path causes the measured difference, nor rule out measurement
variation. Further attribution is required before another runtime change.
All temporary servers were confirmed stopped after the diagnostic.

### Ranking CPU Attribution and Rejected Scoring Trials

Fresh 30-second ranking-only CPU profiles used 30,000 seeded documents, four
clients and three nodes. Seeding was excluded and sampling ran at 99 Hz per
daemon, with only the extracted `libprofiler` preloaded (not a replacement
allocator). The same development persistence settings were used on both
sides. Both diagnostic loads completed with zero errors; their throughput
is NOT performance acceptance evidence. Process metadata verifies current
`23e0d96b...` and baseline `606854e7...` on all three nodes.

Directories under `borrowed-nested-ids/` are `cpu-profile-ranking-current/`
and `cpu-profile-ranking-before/`, each with `diagnostic-load.json`,
`profile-metadata.json`, the matching `steelsearch` archive and per-node
`cluster/node-*/cpu.prof.0` files. Analyze nodes separately. The initial
`node-1-full.txt` reports used relocated executable paths and contain unresolved
addresses; they are not attribution evidence. Correct `node-1-symbolized.txt`
reports used the original matching executable paths. Portable
`node-1-symbolized.profile` files preserve symbols for future use; the current
profile was reread after rebuilding the executable and reproduced the same
sample counts and function names in `node-1-portable-check.txt`.

Node 1 had 2,642 current and 2,658 baseline samples. Source-field lookup accounts
for 611/2642 and 612/2658 cumulative samples (about 23% in both), and document
scoring for 1082/2642 and 1066/2658 (about 40%). The parallel candidate-document
collection closure accounts for 845/2642 and 885/2658 (about 32-33%). These
overlap caller frames and must not be added; shared costs do not establish a
new regression. Stripped libc nearest-symbol labels are not used for diagnosis.

A filter-first scoring trial passed 820 engine tests, but inspection showed
the ranking candidate query already includes its range filter. The runtime
trial was removed before a release build rather than asserting an unmeasured
benefit. Log: `bool-filter-first-unit-tests.log` in the common target parent.

A subsequent trial removed the temporary `should` score vector while retaining
evaluation order, floating sum identity, score order, minimum-should-match and
first-error propagation. A 245-query/four-document oracle compared score bits
and error results against the original algorithm, including large boosts and
negative zero. All 820 engine tests passed. Its release build completed in
4m07s with SHA-256
`861139277ad82736087967abf8512c5e6ce4dedb8822d0d59cea33ad29d4c404`.
Fresh isolated OpenSearch comparisons passed 1179/922/79 cases and the original
27 failures were re-audited. Logs and reports use the `bool-should-accumulation`
prefix/directory under the common target parent.

An adjacent candidate-then-control fixed-corpus ranking pair was unfavorable:
candidate 799.68 ops/s versus control `23e0d96b...` 815.89 (-1.99%), mean
4.9903ms versus 4.8916ms (+2.02%), p95 9.9758ms versus 9.8422ms, zero errors.
`bool-should-accumulation/static-ranking-comparison.json` links the source
reports and validates matching configurations and actual hashes. No mixed
performance claim is made for this rejected trial.

The `should` runtime change was reverted and the preserved `23e0d96b...`
executable restored, not misrepresented as a fresh build. The score/error
regression test remains. Excluding only that new test from the source in memory
reproduces the pre-trial engine blob `07f1d4eb304a481aa8a79ea98e3e905045d82295`.
The rejected executable remains at `bool-should-accumulation/steelsearch-rejected`.
Post-revert engine verification passed 820/820, zero failures/ignored tests,
in `bool-should-accumulation-reverted-unit-tests.log`. No temporary benchmark,
reference, profiler, or compiler processes remained after verification.

The next attribution target is candidate collection. Installed Tantivy 0.21.1
uses a per-segment HashSet and a second merged HashSet in `DocSetCollector`;
the engine uses this collector at both sites in
`search_documents_for_tantivy_query_unordered`. Any replacement must preserve
the full matching address set, deletion filtering and score-free collection,
and be verified against the library collector before claiming an improvement.
No collector replacement is implemented in this follow-up.

## Prior Borrowed-Term Candidate

Candidate SHA-256: `60bfbdcdaaed31cf722e0a6ca9af99eea72f46e259b99cc477d6bcdf79bfa36f`.
The original in-scope failure list is repaired: 27/27 core suite-case entries
(16 unique cases); the two plugin entries are excluded, not passing.
Fresh live core/strict/semantic comparisons passed 1179/922/79 cases with
zero failures or skips. The latest engine library suite passed 818 tests.

Two alternating candidate/baseline rounds, 60 seconds per topology per run,
used the same core workload and verified distinct executables. Pooled throughput:

| Topology | Development baseline ops/s | Candidate ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 711.26 | 724.58 | +1.87% |
| Three nodes | 902.33 | 914.84 | +1.39% |

All eight measured scenarios had zero request errors. All 14 operation/topology
weighted mean latencies decreased. However, the arithmetic mean of the two
per-run p95 values for three-node nested requests increased by 0.12%; this is
NOT a pooled p95 or a statistically established regression. No tolerance has
been assumed, and literal preservation of every latency metric is not proven.
Earlier baseline runs also varied, so these short measurements do not establish
a universal improvement. Details and raw report links are in the borrowed-term
keys section below. This comparison is NOT against a previous published release
or OpenSearch and is NOT production release approval.

### Longer Three-Node Follow-Up

A preselected 180-second baseline/candidate comparison did not establish
latency preservation. Baseline throughput was 774.09 ops/s and candidate
780.81 ops/s (+0.87%), both with zero errors. The workload duration matches
within this pair; do not compare these rates directly with the 60-second runs.

| Operation | Mean latency change | Per-run p95 change |
| --- | ---: | ---: |
| write | -0.60% | -0.26% |
| lexical | +0.56% | +0.93% |
| ranking | +0.02% | -1.49% |
| facet | -3.39% | -4.77% |
| sort_filter | -0.42% | -1.47% |
| nested | +1.04% | +0.58% |
| refresh | -1.30% | -1.61% |

Source reports are `long-three-node-before-1/summary.json` and
`long-three-node-after-2/summary.json` under
`target/core-sort-parser-fixes-20260906/borrowed-term-keys/`.
`long-three-node-comparison.json` validates configuration equality and the
same distinct executable hashes as above. These are one longer pair, not a
statistical confidence interval or grounds to waive increases.

The intervening `long-three-node-after-1` failed before measured requests:
node 3 logged `AddrInUse`, followed by a connection-refused error during index
preparation. Its `invalid-run.json` excludes it from performance evidence.
The replacement used HTTP 26230-26232 and transport 27230-27232, outside this
host's ephemeral range 32768-60999. No collision owner was established and no
system port configuration was changed. All temporary servers were stopped.

Inspection of `LoadRunner.run_operation` confirms that writes add unique
`live-{client_id}-{counter}` documents. Successful writes were 24,502 before
and 24,705 after, in addition to the 5,000 seeded documents. Faster throughput
therefore changes the document population during this time-bounded workload.
This is a possible latency confound, not proof that it explains the increases.
A matched-document diagnostic is needed to isolate nested execution cost;
the real mixed-workload increases above remain visible and unresolved.

The original failure list was independently re-audited against all three
current live reports. `original-failure-closure.json` records source paths and
SHA-256 hashes and every original/current case name: 29 original failures,
2 excluded plugin entries, 27 passing comparison entries, 16 unique core cases.
Five source-filter case names changed from `applied` to `rejected`; their
reference/current status 400 and step names were checked explicitly. This is
not a claim that the original reports archived complete request bodies.
The reproducible audit is `audit-original-failures.py` in the same directory.
The functional fixes remain verified; the no-performance-degradation goal
remains active and release approval remains withheld.

### Fixed-Corpus Nested Diagnostic

A supplementary comparison fixed the corpus at 30,000 documents, with
`nested=100`, no measured writes or refreshes, three nodes, four clients and
60 seconds of load. This isolates the search path; it does not replace the
mixed-workload acceptance requirement or establish a production result.
The original baseline and candidate hashes remain `606854e7...` and `60bfbdcd...`.

| Metric | Development baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| Throughput ops/s | 657.98 | 653.79 | -0.64% |
| Nested mean ms | 6.0671 | 6.1060 | +0.64% |
| Nested p95 ms | 10.3347 | 10.3639 | +0.28% |

Both runs had zero errors. Sources under the borrowed-term-keys directory are
`static-nested-before-1/summary.json`, `static-nested-after-1/summary.json` and
`static-nested-comparison.json`. The comparator checks matching workload and
actual binary identities. These are a single diagnostic pair, not a confidence
interval. The increase remains present without document growth, so growth alone
cannot be assumed to explain away the earlier mixed-workload observation.

Code inspection found that two native nested hit paths collect candidate
documents and then call `native_nested_query_is_proven_by_child_ordinals_scoped`,
which constructs child-ordinal sets again to check whether the index proves the
query. This is a potential redundant cost shared by both builds, not a proven
new regression. Existing per-node CPU profiles of the older `62dd4554...` build
also include this broader candidate path; they do not profile the current
`60bfbdcd...` executable. Any optimization must retain the distinction between
index-proven candidates and source-validated fallback, shard selection and
refresh visibility. No runtime change was made on this evidence alone.
Temporary servers were confirmed stopped after the diagnostic.

### Nested Admission Trial (Rejected)

A trial replaced materialized child-ordinal existence checks with borrowed
term-posting lookups and equivalent bool admission checks. A 457-query matrix
matched the existing materialized predicate, including missing terms/fields,
empty intersections, unsupported leaves and should thresholds. All 819 engine
tests passed. The release build completed in 4m08s with SHA-256
`04db8a1c574c9e073d2a7a3bb2b855f17867cebdb408a79833e2bfc52b320a2a`.
Fresh isolated OpenSearch comparisons passed 1179 core, 922 strict and 79
semantic cases, zero failures/skips, and the original 27 core failures were
re-audited successfully. Reports are under
`target/core-sort-parser-fixes-20260906/nested-admission/`.

The fixed 30,000-document nested diagnostic measured 650.33 ops/s, versus
653.79 for the prior `60bfbdcd...` run: -0.53% throughput and +0.53% mean latency,
both error-free. `static-nested-comparison.json` preserves the raw sources and
verified identities; these runs were not adjacent and do not establish a
statistically significant regression. The subsequent 60-second mixed core run
measured 715.72 ops/s single-node and 910.17 three-node, zero errors, in
`core-performance-after-1/summary.json`. There was no fresh paired mixed control,
so no regression percentage is asserted from those values.

Closer dispatch inspection explains why this trial was not a suitable fix for
the observed workload: the default-relevance nested page path (`size: 10`)
collects candidate IDs directly and does not invoke the admission recheck
changed by this trial. The optimized recheck belongs to full-hit collection
paths. This does not prove those paths cannot benefit, but there is no measured
benefit for the requested workload and the change is not adopted.

All trial runtime changes and its trial-only test were reverted. The engine
source blob is again `47100fe14bbae1524d6b9c2497bc5c6152dbbae5`, identical to
the start of the trial. `target/release/steelsearch` was restored from the
preserved `60bfbdcd...` executable, not misrepresented as a fresh build.
The rejected executable is archived as `nested-admission/steelsearch-rejected`.
Unit logs are `nested-admission-unit-tests.log` and
`nested-admission-reverted-unit-tests.log` in the parent directory.
The post-revert engine suite passed 818/818, with no failures or ignored tests.
All temporary servers and compilers were confirmed stopped after verification.
The remaining investigation must target page candidate collection, not waive
the documented mixed-workload or fixed-corpus latency increases.

## Correction: Before/After Performance Evidence Invalid

The before/after performance claims below, including -0.71%, +1.18%, -0.88%,
and +0.50%, are WITHDRAWN. Launcher logs show that the benchmark matrix ignored
`STEELSEARCH_BINARY_PATH` and selected `target/release/steelsearch` for both
sides. The manually recorded before hashes therefore did not identify the
executables actually launched. Those paired reports remain diagnostic history,
not valid regression or release-to-release evidence. The incomplete
`core-performance-before-1` run has the same selection problem and additionally
failed during three-node setup; it is not acceptance evidence.

The runner now honors explicit binary selection, rejects invalid overrides,
records actual executable path/SHA-256 per scenario, verifies the executable
has not changed during the run, and records the target's root identity response.
Fresh before/after measurements are required. Functional compatibility results
are unaffected by this benchmark-launcher defect. OpenSearch comparison numbers
still describe the actual current-binary runs, subject to the development-mode
and workload limitations documented below.

### First Verified Core Performance Pair

After repairing binary selection, fresh 60-second measurements completed with
distinct per-scenario executable identities. Source reports are
`target/core-sort-parser-fixes-20260906/core-performance-verified-before-1/summary.json`
and `core-performance-verified-after-1/summary.json` under the same parent.
The derived `core-performance-verified-comparison-1.json` records the actual
executable metadata, all seven operation latency comparisons, and configuration
equality. The before build is after the ingest/aggregation repairs but before
the sort/parser repairs, NOT the previous published release.

| Topology | Before ops/s | After ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 716.13 | 724.80 | +1.21% |
| Three nodes | 919.45 | 911.57 | -0.86% |

All four scenarios had zero request errors. Both use the core-only operation
mix and identical workload settings. The three-node decrease is not waived;
one pair does not prove performance preservation. The before hash is
`606854e7a59628ab3c7cb1bccd1a01970aba3f29793eaeb8993b94b0e4043486`;
the after hash is
`eb8b5526550411158505e07d21507422eaaee63e7fcb775257c188b310aadbbd`.
This evidence supersedes the invalid labelled before/after comparisons below,
not the separate OpenSearch mixed-workload comparison.

### Release Notes Policy Implemented

`docs/releases/README.md` and `template.md` define mandatory topology-level
throughput and all 14 core operation/topology latency rows, with both previous
published release and pinned OpenSearch comparisons. `tools/release_notes.py`
generates and verifies tables from raw reports; `tools/publish-release.py`
requires validation, an explicit publish flag, the actual most recently
published release label, and an existing remote tag before publication. It
attaches the raw evidence and never overwrites an existing release. The CI
workflow checks bundles and rejects version tags with missing notes/evidence.

Verification: 18 release policy tests and 30 benchmark tests passed; workflow
YAML parsed with read-only permissions; diff whitespace checks passed. No tag,
release or remote permission change was made. Administrator UI/API bypass is
not prevented by repository files: remote status-check and credential policies
must be configured separately. Policy validation is not production approval.

### Borrowed String Comparison Optimization

Follow-up inspection found that the engine's scalar comparator cloned both
strings into temporary JSON values before checking RFC3339 ordering. It now
passes the original borrowed JSON values to the same date parser. Date parsing,
fallback lexical ordering and exact integer comparisons are unchanged.

The engine library suite passed 816/816 with no ignored tests after this
change. The added test covers offset-normalized date equality/order, invalid
date strings, subsecond ordering, signed/unsigned integer boundaries, floats,
booleans and incompatible values in both comparison directions. Log:
`target/core-sort-parser-fixes-20260906/borrowed-string-engine-tests.log`.
The previous executable is retained at
`target/core-sort-parser-fixes-20260906/steelsearch-before-borrowed-string-comparison`
with hash `eb8b5526550411158505e07d21507422eaaee63e7fcb775257c188b310aadbbd`.
Fresh release-build, HTTP comparison and performance results for the new
executable are required before attributing an improvement to this optimization.

The new release build completed successfully (4m06s) with SHA-256
`62dd45548538f723274ff65daaf00d54247eb6fef46b08f74c579f6a23e04b0f`.
Fresh isolated OpenSearch 3.7.0-SNAPSHOT comparisons in
`target/core-sort-parser-fixes-20260906/borrowed-string/` passed core search
1179/1179, strict 922/922, and semantic 79/79, with no failed or skipped cases.
Reports are `core-search-compat-report.json`, `core-search-strict-report.json`
and `core-search-semantic-report.json`. All temporary comparison servers and
compilers were confirmed stopped before starting the core performance run.

The first performance run for this executable achieved 722.39 ops/s single-node
and 908.73 ops/s three-node, with zero errors. A subsequent repeat of the actual
before executable achieved 720.99 and 926.87, also with zero errors. Including
the earlier before run (716.13 / 919.45), pooled before throughput is
718.56 / 923.16. The candidate is therefore +0.53% / -1.56% against that pooled
baseline. This is two before samples and one candidate sample, not two complete
paired experiments. The three-node decrease remains unresolved.
`target/core-sort-parser-fixes-20260906/borrowed-string/performance-comparison.json`
records source reports, actual hashes, workload equality and per-operation data.

A separate exploratory numeric-comparator microbenchmark is preserved as
`target/core-sort-parser-fixes-20260906/compare-numbers.rs` and `compare-numbers.csv`.
It uses the release serde_json library, optimized thin-LTO compilation,
black-boxed operands, and four alternating rounds per numeric operand family.
Checking for floating operands before attempting exact integer conversions
reduced measured comparator time by 18.41% for floating operands and 44.58% for
mixed float/integer operands; integer families also improved in this run.
Sampled boundary results match in both comparison directions. This is an
exploratory microbenchmark, not HTTP throughput evidence or release acceptance.
At that measurement stage the float-first candidate was not yet applied to
runtime code; the following section records its subsequent implementation.

### Float-First Numeric Comparison (Rejected)

A trial changed the engine and HTTP fallback scalar comparators to test for floating operands
before attempting exact signed/unsigned integer conversions. When both operands
are integers, exact comparison remains unchanged; mixed float/integer values
retain the existing floating comparison contract. This avoids failed integer
conversion checks on the common floating-value path.

Full library verification passed 817 engine tests and 582 node tests, with no
ignored tests. Each module adds a 19-by-19 numeric operand matrix comparing the
new ordering against the previous implementation, including signed/unsigned
extrema, adjacent integers above 2^53, negative zero, fractional values and large
floating values. Log:
`target/core-sort-parser-fixes-20260906/float-first-unit-tests.log`.
The previous executable is retained as
`target/core-sort-parser-fixes-20260906/steelsearch-before-float-first-comparison`
with SHA-256 `62dd45548538f723274ff65daaf00d54247eb6fef46b08f74c579f6a23e04b0f`.
The new executable still requires fresh HTTP and server-performance evidence;
the microbenchmark alone does not establish goal completion.

The release build completed in 4m08s with SHA-256
`89fd9a20ffc6dc2f8a6ffeaad4fffb521615c192fa6b34a1d6f5555b5d578601`.
Fresh isolated OpenSearch comparisons in
`target/core-sort-parser-fixes-20260906/float-first/` passed core search
1179/1179, strict 922/922 and semantic 79/79, with zero failures or skips.
The three `core-search-*-report.json` files identify these runs. Comparison
servers and compilers were stopped before the core performance measurement.

Release-note validation additionally checks matching synthetic source array
dimensions, because the generator retains its embedding number array even
when vector/hybrid query weights are zero. The table now discloses that payload
size. All 19 release-note tests passed after adding the mismatch regression.

The live HTTP experiment did NOT reproduce the microbenchmark improvement:

| Topology | Control (62dd4554) ops/s | Candidate (89fd9a20) ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 722.27 | 713.31 | -1.24% |
| Three nodes | 918.25 | 891.07 | -2.96% |

Both runs used the identical 60-second core workload with zero request errors.
The candidate ran first, immediately followed by the preserved control binary;
actual executable identities are recorded in each report. The complete
comparison is `target/core-sort-parser-fixes-20260906/float-first/rejected-comparison.json`.
The float-first runtime change was reverted. Its numeric operand matrix tests
were retained under the neutral `scalar_comparison_preserves_numeric_operand_matrix`
name. Full post-revert unit tests passed 817 engine and 582 node tests:
`target/core-sort-parser-fixes-20260906/float-first-reverted-unit-tests.log`.

`target/release/steelsearch` was restored from the preserved, previously built
and HTTP-verified `62dd4554...` executable, not represented as a newly built
artifact. Runtime source is back to that implementation; retained changes from
the rejected trial are test-only. The rejected `89fd9a20...` executable is kept
at `target/core-sort-parser-fixes-20260906/steelsearch-float-first-rejected`.
The original functional repairs and borrowed-string optimization remain.

Further performance analysis is still needed. An unprivileged `perf stat`
probe was rejected by the host's `perf_event_paranoid=4` policy. No global
profiling permissions were changed. The user has been asked to clarify the
acceptable repeated-measurement regression tolerance; no answer or default
selection has been assumed. The goal is not marked complete.

### User-Space Profiling and Borrowed Term Keys

CPU profiling was collected without changing kernel permissions or installing
system packages. Ubuntu's `google-perftools` and `libgoogle-perftools4t64`
2.15-3build1 packages were extracted under
`target/core-sort-parser-fixes-20260906/profiling-tools/`. Only `libprofiler`
was preloaded into diagnostic SteelSearch daemons; the allocator was not
replaced. Its SHA-256 is
`64b52c20bf1794570c9012a49a62f4b954b9d3559396f1cb363a433b1c9f0a9f`.

The existing load generator ran the same three-node core mix. Sampling began
after corpus seeding and stopped after the measured workload, at 99 Hz per
process. Both current `62dd4554...` and before `606854e7...` runs had zero
request errors; PID/executable hashes and sampling boundaries are recorded in
`cpu-profile-current/profile-metadata.json` and
`cpu-profile-before/profile-metadata.json` under the same target parent.
The runs are diagnostic-only, not throughput acceptance evidence. The release
note validator now rejects diagnostic reports/scenarios; its 20 tests and the
30 benchmark tests passed.

Interpret profiles per node. The combined ASLR-address report contains unresolved
addresses and is not used for attribution; some stripped libc symbol labels
are also ambiguous. Node 1's full Rust-symbol report shows the simple bucket
collector at 167/1906 cumulative samples in current and 163/1980 in before,
about 8-9% in both. Cumulative samples overlap caller frames and are not additive.
This identifies a shared cost, not proof that the latest fixes caused it.

Inspection of that collector found a string clone on every terms-count update,
including existing keys. Its counting map now borrows `&str` keys from the
stable input documents and creates owned strings when rendering results.
Counting, tie ordering, minimum counts, merge carriers and fallback admission
are unchanged. The engine's full 818-test suite passed, including a new direct
collector test for repeated/unique/missing values, array fallback, and owned
results that remain valid after dropping the engine. Log:
`target/core-sort-parser-fixes-20260906/borrowed-term-keys-unit-tests.log`.
The release build completed in 4m00s with SHA-256
`60bfbdcdaaed31cf722e0a6ca9af99eea72f46e259b99cc477d6bcdf79bfa36f`.
Fresh isolated comparisons against OpenSearch 3.7.0-SNAPSHOT passed core
1179/1179, strict 922/922 and semantic 79/79, with no failures or skips.
Reports are the three `core-search-*-report.json` files under
`target/core-sort-parser-fixes-20260906/borrowed-term-keys/`.
All comparison servers and compilers were stopped before the uninstrumented
performance run.

Uninstrumented runs under that directory completed in this order:
`core-performance-after-1`, `core-performance-before-1`,
`core-performance-after-2`, `core-performance-before-2`. Each contains
`summary.json` and both topology reports. Candidate single-node throughput was
721.39 / 727.78 ops/s and three-node throughput 915.75 / 913.94; baseline
single-node throughput was 706.25 / 716.26 and three-node 903.39 / 901.26.
`performance-comparison.json`, generated by the adjacent `compare-runs.py`,
checks actual hashes, top-level and executed workload equality, and zero errors.
It retains all samples and computes throughput from total successes/elapsed
time and mean latency weighted by sample count. Per-run p95 values are retained
separately, not incorrectly pooled.

| Operation | Single-node mean latency change | Three-node mean latency change |
| --- | ---: | ---: |
| write | -0.74% | -1.26% |
| lexical | -1.10% | -1.06% |
| ranking | -0.45% | -0.45% |
| facet | -4.32% | -4.03% |
| sort_filter | -0.96% | -0.15% |
| nested | -1.01% | -0.11% |
| refresh | -2.85% | -0.84% |

Negative latency change is faster. The arithmetic mean of per-run nested p95
on three nodes increased by 0.12%; the other 13 p95 sample means decreased.
No regression tolerance is assumed. These short development-mode tests support
the allocation optimization but do not prove every metric is unchanged under
production load. The development baseline is also not a published release.
The dedicated previous-release and OpenSearch release evidence remains separate.
After all runs, no temporary benchmark/reference servers remained. Release
policy tests passed 20/20, benchmark tests 30/30, and `git diff --check` passed.

The original `606854e7...` development baseline is now archived as
`target/core-sort-parser-fixes-20260906/steelsearch-original-core-baseline`.
It is not the previous published release. Matching profile binaries are also
archived as `cpu-profile-current/steelsearch` and `cpu-profile-before/steelsearch`
so later symbolization does not accidentally use the rebuilt executable.
No release, tag, or remote permission change was made.

## Inspected State

- HEAD: `af7cdd2bd214d78560a4a7f22837b8a0a2f8e051`, with uncommitted changes.
- Reused binary: `target/release/steelsearch`, built earlier on 2026-09-06.
- Binary SHA-256: `0fa7514d9138a1c07df4f3deb06292a16590e6666428a7a8595278c5fef9ea22`.
- No runtime implementation changes were made during this diagnostic.

## Fresh Verification

The following full fixtures ran against the reused SteelSearch binary without
an OpenSearch target. They establish standalone fixture behavior, not fresh
live OpenSearch parity or clean-build provenance.

| Fixture | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| search-compat | 1195 | 0 | 0 |
| search-strict-compat | 926 | 0 | 0 |
| document-write-semantic-compat | 78 | 0 | 0 |

Reports are under `target/release-diagnostic-20260906/`, using the fixture
names above with `-report.json` suffixes. Commands used
`STEELSEARCH_BINARY_PATH=/home/ubuntu/steelsearch/target/release/steelsearch
tools/run-search-compat.sh`, the corresponding `--fixture`, and `--report`.

The aggregate gate was run to completion with:

```sh
RUSTUP_TOOLCHAIN=nightly RUSTFLAGS=-Awarnings python3 tools/run-native-closure-validation.py --batch native-closure-status-current --format json
```

`target/native-closure-status-current.json` was regenerated for the inspected
HEAD and dirty worktree. Both aggregate checks failed. Its summary reports
`current_evidence_ready=false`, `final_cutover_ready=false`, and
`runtime_peer_backpressure_ready=true`. A passing peer-backpressure subgate
does not establish current transport coverage or overall distributed readiness.

## Confirmed Blockers

1. Existing required-search, search/strict, PIT, and broad E2E reports exceed
   the seven-day freshness limit (approximately 52-55 days old). Direct checker
   runs confirmed stale-report rejection. Historical passing case counts cannot
   substitute for current live comparison evidence.
2. Runtime backpressure and fairness batches each select the absent test
   `runtime_thread_pool_classes_drain_independently_under_mixed_backlog`.
   Cargo exits zero with no matching test; the runner correctly rejects the
   zero-test result. The separate write/maintenance independent-drain test exists
   and is already registered, so merely replacing the missing name with that
   name would duplicate coverage rather than restore the missing contract.
3. The release inventory admits zero of eight required release-record items:
   benchmark coverage, load coverage, chaos coverage, packaging verification,
   rolling-upgrade coverage, load comparison, PIT E2E coverage, and promotion
   gate suite. This means eligible evidence is missing, not necessarily that
   every artifact file is absent. The recent performance matrix alone does not
   satisfy the release benchmark attachment contract.
4. REST coverage, transport coverage, and release-readiness tooling also fail
   the current aggregate gate. Their underlying errors need targeted diagnosis;
   do not classify every failure as stale evidence without inspecting it.
5. The promotion-suite wrapper exceeded its 120-second timeout. A descendant
   checker continued with PPID 1 after the wrapper terminated, demonstrating
   incomplete timeout cleanup. It subsequently exited; final process inspection
   found no remaining Python, Cargo, rustc, Java, or SteelSearch processes.
   This is not proof of the reported Codex termination cause.
6. The worktree is not clean and the release commit has not been fixed.

Security, startup/bootstrap, source-compatibility, materialization inventory,
mixed-cluster coverage, and non-native inventory groups passed their configured
checks. These are bounded gate results, not unrestricted production claims.

## Performance Evidence

The existing latest matrix
`target/search-benchmark-matrix-api-exists-query-parser-boundary-full-20260906/summary.json`
reports 730.151244 ops/s for SteelSearch single-node and 893.163170 ops/s for
three-node, with zero request errors. Both exceed the required 95% baseline
floors of 708.005827 and 853.335516 ops/s. No new performance run was needed for
this read-only runtime diagnostic; this is a 30-second, 5000-document matrix,
not production soak evidence.

## Next Work

1. Restore the missing independent-drain test contract and verify both affected
   runtime batches without weakening zero-test rejection.
2. Repair timeout descendant cleanup and retain actionable failure diagnostics.
3. Regenerate required live OpenSearch comparisons, then investigate remaining
   REST/transport/readiness failures and renew the eight release-record items.
4. Select a release commit and run final provenance and clean-worktree checks.
5. Continue the semantic and distributed gaps in the API implementation ledger;
   do not redefine the full replacement objective as fixture-only completion.

## Follow-up: Validation Timeout Cleanup

The external validation runner now creates a dedicated POSIX process group for
each command and kills that group on timeout before draining its output and
reaping the direct child. This covers wrapper descendants that remain in the
group; descendants that deliberately create their own sessions are outside this
cleanup mechanism. Non-POSIX systems retain direct-child termination.

Timeout output is now collected as text, avoiding the previous possibility of
`TimeoutExpired.output` bytes causing JSON serialization failure. The timeout
still reports failure, never a passing or skipped check. Runtime code and
performance paths were not changed.

Validation:

- `python3 -m unittest tools/test_native_closure_validation.py`: 33 passed,
  including a real wrapper/descendant timeout and silent-timeout JSON output.
- `python3 -m unittest tools/test_native_closure_status_report.py tools/test_native_closure_status_checker.py`:
  170 tests, 168 passed, 2 failed. The unresolved failures are
  `test_cli_can_reuse_existing_current_evidence_report_for_final_cutover_check`
  and `test_complete_readiness_attachments_mark_final_cutover_ready`; both
  expected readiness for their synthetic evidence but received failure.
- `git diff --check`: passed.

The aggregate release gate has not been rerun after this tool-only correction.
The NO-GO decision and other blockers remain in force.

## Follow-up: Readiness Test Evidence

The two failing status-report tests are now fixed. Their shared synthetic
evidence helper wrote an empty packaging object and omitted promotion command
metadata. The real inventory checker correctly rejected that data as missing
`packaging_verified` and `promotion_gate_suite` evidence.

The helper now supplies the packaging build, executable, and consistent
workspace-version fields, and obtains promotion commands from the real suite's
`CHECKS` list. This change only affects temporary test artifacts. It does not
alter readiness policy or turn actual release evidence into passing evidence.
Assertion failures now include the returned diagnostics rather than empty
stderr alone.

Verification after this correction:

- Both previously failing tests passed individually.
- `python3 -m unittest tools/test_native_closure_status_report.py tools/test_native_closure_status_checker.py`:
  all 170 tests passed.
- `python3 -m unittest tools.test_release_evidence_inventory -k promotion_gate_suite`:
  both failed-suite and missing-required-check rejection tests passed.
- `git diff --check`: passed.

This resolves the two unit-test failures recorded in the timeout follow-up.
It does not prove the complete release-readiness-tooling batch passes, since
that batch also checks other tests, documentation counts, and source drift.
The aggregate NO-GO decision remains unchanged pending fresh release evidence
and the remaining runtime/coverage repairs.

## Follow-up: Runtime Gate References

The absent independent-drain test was traced to commit `8925f42c`, which renamed
and updated it to `runtime_thread_pool_prioritizes_maintenance_over_queued_search`.
The implementation blocks search admission while maintenance is active or
queued; the current test verifies that policy and eventual completion of both
requests. Reintroducing the old independent search/maintenance behavior would
contradict the existing scheduler.

Both backpressure and fairness gate references now select the current
maintenance-priority test. The separate write/maintenance independent-drain
test remains registered exactly once in each batch. No runtime policy, test
assertion, zero-test rejection, or required batch was removed to obtain a pass.

Verification:

- `python3 -m unittest tools/test_native_closure_validation.py`: 34 passed.
- `RUSTUP_TOOLCHAIN=nightly RUSTFLAGS=-Awarnings python3 tools/run-validation-batch-group.py runtime-backpressure runtime-fairness`:
  28 and 13 validation entries passed, respectively; zero failures and zero
  empty test selections.
- `RUSTUP_TOOLCHAIN=nightly RUSTFLAGS=-Awarnings python3 tools/run-native-closure-validation.py --batch runtime-controls-current --format json`:
  aggregate passed; all 10 constituent batches passed, with 124 validation
  entries, zero failures, and zero empty test selections. Entries can overlap
  between batches and are not a unique-test count.
- `git diff --check`: passed.

This resolves the runtime gate blocker in the original diagnostic. The earlier
aggregate status artifact predates this correction; a fresh runtime subgate
does not by itself update or approve the complete release gate. No performance
benchmark was rerun because only gate registration and its tests changed.

## Follow-up: Isolated Live Search Comparison

Fresh full comparisons used the existing release binary and local OpenSearch
`3.7.0-SNAPSHOT`, build `f991609d190dfd91c8a09902053a7bbfe0c27b3e`, Lucene 10.4.0.
The reference distribution does not expose k-NN or ML Commons plugin surfaces.
Each authoritative suite ran with an initially empty OpenSearch data directory
and a fresh SteelSearch node. Reports and their unified summary are in
`target/release-live-20260906/isolated/`.

| Suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| search-compat | 1162 | 17 | 16 |
| search-strict | 910 | 12 | 4 |
| search-semantic | 79 | 0 | 0 |

The unified report has 29 failed suite-case entries (17 distinct case names),
20 unresolved skips, and no missing cases. This is a three-suite search report,
not a broad security/durability/distributed validation. It is intentionally
not promoted to the canonical successful-release evidence paths.

Confirmed differences requiring follow-up:

- Four ingest simulation cases lack `_ingest.timestamp` on SteelSearch. Any
  eventual comparison must validate timestamp presence/format while accounting
  for independently generated values, rather than requiring identical times.
- Invalid `combined_fields.operator` lacks OpenSearch's
  `x_content_parse_exception` wrapper and nested illegal-argument cause.
- `search_after_missing_sort_search` and `sort_unmapped_with_type_search`
  disagree on numeric missing-sort-value representation.
- Date histogram extended bounds omit empty boundary buckets on SteelSearch.
- Geo centroid differs at encoded-coordinate precision.
- Metric and pipeline extended stats omit population/sampling response fields.
- Five GET/MGET source-overlap cases return 200 on SteelSearch and 400 on
  OpenSearch. The current source's `FetchSourceContext` constructor explicitly
  rejects identical include/exclude entries. This contradicts the historical
  admission claim; the ledger now flags it rather than treating it as closed.
- `bad_knn_vector_dimension` fails on the plugin-free reference because its
  query parser has no k-NN surface. Rerun against a plugin-enabled reference
  before classifying that case as an implementation defect. The 20 plugin
  skips likewise remain unverified, not passing evidence.

Initial shared-reference runs are preserved outside `isolated/` for diagnosis:
strict had 26 failures and semantic had 16. Reusing reference state introduced
extra indices into alias, CAT, wildcard, and root-search results. Clean-node
reruns reduced those to 12 and zero, respectively. Do not use the shared-node
results as the authoritative defect list, and isolate both targets by suite in
future full comparisons.

PIT-only verification:

```sh
python3 tools/check-pit-e2e-coverage.py target/release-live-20260906/isolated/unified-opensearch-e2e-report.json --require-all-pit-passed --max-report-age-seconds 3600 --format text
```

Passed: 233 PIT case entries, all 17 required cases compared, zero non-passing
PIT cases. The checker also reports the 29 non-PIT failures and 20 skips; its
success does not approve the overall search or release gate.

All three temporary OpenSearch nodes and all fixture SteelSearch processes
were stopped. Runtime implementation was not changed during this evidence
refresh. Next implementation should address the confirmed live differences,
starting with source filtering and parser errors, and verify them against this
explicit reference build before renewing broader release artifacts.

## Core Scope and Source-Filter Correction

The user explicitly excluded plugins from release support. The current
candidate is `core-no-plugins`: k-NN and ML Commons plugin APIs are unsupported,
not deferred passing checks. The 18 distinct search/strict plugin case names
are fixed in `tools/fixtures/release-core-plugin-exclusions.json` and supplied
to both runner and checker using:

```sh
export SEARCH_COMPAT_EXCLUDE_CASES="$(jq -r '.excluded_cases | join(",")' tools/fixtures/release-core-plugin-exclusions.json)"
```

This removes the plugin-dependent dimension error and plugin skips from core
acceptance. It does not remove core failures or convert the old full aggregate
report into a passing core release report.

The five source-filter failures are fixed against OpenSearch 3.7:

- GET document/source and MGET query/per-document filters reject identical
  include/exclude entries with an illegal-argument response and root cause.
- A root MGET `_source` object is rejected as a parsing exception; it is not a
  valid root filter option, even when the filter entries are distinct.
- Distinct wildcard selectors remain valid. Unit tests cover that distinction
  and existing stored-field read behavior.

Fresh core-only full search comparison on initially empty nodes:
`target/source-overlap-reject-20260906/verified/core-search-compat-report.json`:
1166 passed, 11 failed, zero skipped. All five corrected cases passed.
The same five strict cases passed in
`target/source-overlap-reject-20260906/verified/strict-source-overlap-report.json`.
The initial pre-correction root-body error mismatch is preserved in the parent
directory and is superseded by these verified reports.

Remaining core failures are four ingest simulation timestamp cases, one
combined-fields error wrapper, two missing-sort-value cases, and four
aggregation cases. Source-filter admission claims in the older ledger are
superseded by `API-DOC-READ-SOURCE-FILTER-REJECT-002`.

The existing `minilm-knn` performance workload was retained solely for baseline
comparability, not as a plugin support claim. The new matrix under
`target/search-benchmark-matrix-core-source-overlap-reject-full-20260906/`
measured 724.88 ops/s single-node and 897.64 ops/s three-node, zero request
errors, both above the 95% baseline floors. The remaining core failures still
prevent approval; plugin implementation is no longer on this release backlog.

## Core Ingest and Aggregation Corrections

Eight more core failures are corrected against the same OpenSearch 3.7 build:

- Ingest simulation now emits a generated UTC RFC3339 timestamp. The runner
  validates its date and timestamp syntax before normalizing the volatile
  instant; missing, malformed, and non-string timestamps remain failures.
- Aggregation merge cleanup no longer deletes public population/sampling
  variance, standard-deviation, and deviation-bound fields as internal data.
- The date-histogram parser defaults `min_doc_count` to zero, matching both
  OpenSearch and the existing fallback implementation. Extended bounds now
  include empty buckets; explicit positive minimum counts remain supported.
- Native geo-centroid collection applies the existing Lucene coordinate
  encoding/decoding helpers before averaging, matching doc-value precision.

Fresh, independently initialized reference nodes produced these reports:

| Suite | Passed | Failed | Skipped | Report under `target/core-failure-fixes-20260906/` |
| --- | ---: | ---: | ---: | --- |
| Core search | 1174 | 3 | 0 | `core-search-compat-report.json` |
| Core strict | 918 | 2 | 0 | `core-search-strict-report.json` |
| Core semantic | 79 | 0 | 0 | `core-search-semantic-report.json` |

The remaining three distinct failures are:

- `combined_fields_operator_invalid_error_search`: OpenSearch wraps the enum
  error in `x_content_parse_exception` with the operator token's input position.
- `search_after_missing_sort_search` and `sort_unmapped_with_type_search`:
  missing long sort values are null instead of `9223372036854775807`.
  A correction must also preserve pagination when the returned sentinel is
  supplied as the next cursor, including ties and descending/missing modes.

Focused verification passed: all 133 query-DSL unit tests, 14 native aggregation
tests, one empty/singleton statistics cleanup test, the ingest route unit test,
and all 14 search-runner tests. Interval-rounding tests explicitly request
positive counts; the extended-bounds test checks default empty-bucket filling.
The core failure goal remains active and release approval is still withheld.

The full performance matrix completed under
`target/search-benchmark-matrix-core-ingest-aggregation-full-20260906/summary.json`.
It retained the existing `minilm-knn` workload for measurement comparability,
not plugin support. All four scenario request-error counts were zero; neither
topology reported a metric slower than its OpenSearch reference.

| SteelSearch topology | ops/s | Change from previous source-filter run | Change from fixed baseline | 95% baseline floor |
| --- | ---: | ---: | ---: | ---: |
| Single node | 731.22 | +0.87% | -1.88% | 708.01 |
| Three nodes | 882.31 | -1.71% | -1.77% | 853.34 |

Both throughput results meet the previously recorded 5% regression allowance.
These are single-run measurements, not proof of zero performance degradation:
the three-node result is lower than the preceding run. No compilation or other
compatibility suites ran concurrently with the benchmark. Temporary comparison
nodes and benchmark processes were stopped after verification.

## Remaining Core Failures Corrected

The final three recorded core search failures are corrected:

- Invalid `combined_fields.operator` errors now retain the underlying enum
  cause inside `x_content_parse_exception`. Error-only parsing of borrowed raw
  JSON locates the offending token without hard-coded offsets. Multiline and
  escaped-key/value requests matched the live OpenSearch reference at `[3:17]`
  and `[1:46]`, respectively; the original fixture matches at `[1:96]`.
- Native search resolves integer sort types under existing metadata locks.
  Missing integer values use signed 64-bit extrema according to sort direction.
  The fallback path also resolves `_first`/`_last` into numeric missing values,
  using the same execution sort for ordering, cursor comparison, and output.
- Integer comparisons preserve exact signed/unsigned values instead of first
  converting them to floating point. Tests include adjacent 64-bit limits,
  real limit values tied with missing values, secondary keys, ascending and
  descending order, and full repeated-cursor traversal.

The two previously failing sort fixtures now compare exact sort arrays rather
than only numeric shapes. Two additional cursor-exhaustion cases reuse the
returned missing-long sentinel. Neither fixture skips a core failure.

Fresh isolated live reports under `target/core-sort-parser-fixes-20260906/`:

| Suite | Passed | Failed | Skipped | Report |
| --- | ---: | ---: | ---: | --- |
| Core search | 1179 | 0 | 0 | `core-search-compat-report.json` |
| Core strict | 922 | 0 | 0 | `core-search-strict-report.json` |
| Core semantic | 79 | 0 | 0 | `core-search-semantic-report.json` |

Focused regression verification passed: 109 engine sort tests, nine node
sort/parser tests, the broad query-DSL route test, and 15 runner tests. The
release binary built successfully; formatting and diff-whitespace checks pass.
The 18 plugin case exclusions remain unchanged. These results close the
recorded core-search compatibility failures, not the broader production,
security, durability, packaging, or mixed-cluster release gates discussed above.

### Parser/Sort Performance Investigation

The first full matrix for the parser/sort correction is
`target/search-benchmark-matrix-core-sort-parser-full-20260906/summary.json`:
720.40 ops/s single-node and 882.27 ops/s three-node, zero request errors in
all scenarios, and no slower metric than the OpenSearch reference. Both exceed
the fixed 95% baseline floors, but a single measurement cannot establish
absence of degradation.

The prior release executable remained in Cargo's dependency cache, allowing
direct alternating before/after runs on empty nodes with identical configuration.
`target/core-sort-parser-fixes-20260906/paired-performance-summary.json` records
both executable hashes, four input reports, per-run metrics, and pooled results:

| Topology | Before pooled ops/s | After pooled ops/s | Change |
| --- | ---: | ---: | ---: |
| Single node | 730.43 | 724.03 | -0.88% |
| Three nodes | 886.45 | 890.85 | +0.50% |

Every paired run had zero request errors. The historical 5% allowance is met,
but the single-node decrease is explicitly retained, not normalized away or
claimed as zero. The before binary hash is
`606854e7a59628ab3c7cb1bccd1a01970aba3f29793eaeb8993b94b0e4043486`.
The initially corrected binary hash is
`1fc430364f07d283ee021677ef42abaf04d5e04602b11f35199873220c8a52a8`;
that executable is preserved as
`target/core-sort-parser-fixes-20260906/steelsearch-before-numeric-dispatch-optimization`.

Follow-up optimization moves exact integer checks inside the numeric-value
branch, avoiding extra type checks for string/boolean comparisons. It preserves
the boundary-value contract. Its release build and final comparison/performance
verification must supersede the initially corrected binary before completion.

### Final Numeric-Dispatch Verification

The optimized release executable has SHA-256
`eb8b5526550411158505e07d21507422eaaee63e7fcb775257c188b310aadbbd`.
Fresh, isolated OpenSearch comparisons under
`target/core-sort-parser-fixes-20260906/optimized/` passed:

| Suite | Passed | Failed | Skipped | Report |
| --- | ---: | ---: | ---: | --- |
| Core search | 1179 | 0 | 0 | `core-search-compat-report.json` |
| Core strict | 922 | 0 | 0 | `core-search-strict-report.json` |
| Core semantic | 79 | 0 | 0 | `core-search-semantic-report.json` |

The full node library suite passed 581/581 and the engine library suite passed
815/815, with no ignored tests. Logs are `node-unit-tests-verified.log` and
`engine-unit-tests-final.log` in that directory. The audit updated stale
expectations for integer missing-sort values, source-filter conflicts, public
statistics fields, and quantized centroids. Snapshot tests now use isolated
absolute temporary repository paths with verification enabled. These are test
corrections, not an expansion of plugin support; the 18 release exclusions
remain unchanged. The compatibility runner's 15 unit tests also passed.

The full performance matrix for this executable is
`target/search-benchmark-matrix-core-numeric-dispatch-full-20260906/summary.json`.
SteelSearch achieved 720.88 ops/s single-node and 883.74 ops/s three-node;
OpenSearch achieved 225.97 and 86.06 respectively. All four scenarios had zero
request errors, and neither comparison reported a slower SteelSearch metric.
Both SteelSearch results exceed the historical 95% baseline floors. This short
benchmark is not a production soak test or a plugin-support claim.

The following historically labelled before/after pairs are WITHDRAWN: the
launcher selected the same executable for both sides. They are retained in
`target/core-sort-parser-fixes-20260906/optimized/paired-performance-summary.json`.
The intended before binary was the retained executable after the
ingest/aggregation fixes, but it was not actually selected for these runs.

| Topology | Invalid before label ops/s | Invalid after label ops/s | Withdrawn change |
| --- | --- | --- | ---: |
| Single node | 720.98, 722.32 | 724.81, 735.49 | +1.18% |
| Three nodes | 886.02, 891.20 | 882.58, 881.98 | -0.71% |

All runs had zero request errors, but these pairs establish neither a
before/after decrease nor performance preservation. Use only the verified
distinct-executable measurements above for development regression analysis.

### Original Failure-List Progress

The original 29 failed suite-case entries contained two plugin-dependent
`bad_knn_vector_dimension` entries. Excluding those as requested leaves 27 core
entries, representing 16 distinct case names. All 27 entries now pass live
comparison: 27/27 (100%) of the original in-scope failures are repaired and
verified. The two plugin entries are excluded, not fixed or counted as passing.
This progress denominator is neither the entire release gate nor the number of
unique implementation changes. No production release or tag is approved here.

### Performance Comparison Boundaries

The 3.19x single-node and 10.27x three-node throughput ratios compare the
optimized SteelSearch executable with Docker OpenSearch 2.19.0, not the
OpenSearch 3.7.0-SNAPSHOT used for functional compatibility. They come from
the short mixed workload including vector/hybrid requests. Plugin exclusion
from functional acceptance does not turn that workload into a core-only test.

The benchmark launcher disables per-write shared-runtime-state persistence
and per-request shared-state synchronization for SteelSearch, and enables
deferred development-shard persistence and deferred native writes until refresh.
Consequently these ratios do not establish equivalent production durability,
distributed guarantees, or a general core-only performance advantage. The
before/after SteelSearch comparison uses the same launcher settings on both
sides and is a regression diagnostic, not a production-readiness certificate.

A separate core-request before/after measurement excludes vector and hybrid
operations, uses 60 seconds per topology, and retains the existing non-vector
operation weights. The load runner omits the k-NN setting and mapping when
those operation weights are zero. Its result must be reported separately from
the historical mixed-workload baseline. The formerly reported 0.71% decrease
was invalidated by the executable-selection defect, not waived by changing
the workload.
