# Search and k-NN Benchmark Scenarios

This document defines the benchmark matrix used to compare Steelsearch and
OpenSearch on single-node and three-node clusters. The benchmark scheme is
designed to produce both machine-readable JSON artifacts and a human-readable
Markdown report.

## Scope

The benchmark matrix covers four cluster shapes:

- Steelsearch single-node
- OpenSearch single-node
- Steelsearch three-node
- OpenSearch three-node

Each scenario indexes a warmed corpus and then runs mixed sustained load that
includes both general lexical search and vector search.

## Engine execution notes

Current Steelsearch benchmark runs exercise the `os-engine-tantivy` backend in a
mixed mode:

- native Tantivy lexical execution is enabled for the refreshed in-memory index
  on `match_all`, top-level `term`/`terms`, `match`, `bool`, and numeric
  `range` query paths;
- exact `match_all`, top-level `term`/`terms`, and vector-native query paths
  still fall back to the source-backed compatibility evaluator when their
  semantics have to remain aligned with the existing OpenSearch-compatible test
  suite;
- vector and hybrid workloads therefore still measure a combination of Tantivy
  lexical filtering and the existing Steelsearch vector implementation.

This means benchmark deltas are meaningful for lexical/search-path work, but a
“fully Tantivy-native” result is not yet claimed for every query family.

## Current performance pain points

### Search lock scope regression

The most important Steelsearch 1-node benchmark regression observed in this
matrix was caused by an overly broad engine-level lock scope in
`os-engine-tantivy`.

Pain point:

- search requests were entering the HTTP layer concurrently, but the Tantivy
  engine held an exclusive store lock while building the complete search
  response;
- with `clients=4`, this serialized the critical search section and capped
  observed throughput near the inverse of single-request service time;
- the symptom was roughly `24 ops/s` throughput with about `160 ms` mixed mean
  latency, consistent with four clients queueing behind an approximately
  `40 ms` serialized service section.

Fix direction:

- the engine store uses `RwLock<EngineStore>`;
- read-only search and helper APIs must use `read()` rather than `write()`;
- search-time cache warming, telemetry mutation, and collector accounting must
  not force the primary search path to take a write lock;
- write lock usage should stay limited to index creation, document mutation,
  refresh/rebuild, recovery insertion, and other real state mutations.

Regression guard:

- any future optimization touching `TantivyEngine::search`,
  `EngineStore::search_response_index_aware_with_optional_reusable`, k-NN
  cache handling, aggregation collection, or fetch/highlight transformation
  should explicitly check whether it widened a read-only search path back to
  `write()`;
- benchmark interpretation should include the effective concurrency estimate:
  `throughput_ops_per_second * weighted_mean_latency_seconds`. If configured
  clients are greater than one but throughput stays near single-request service
  capacity, inspect lock scope before tuning query code.

### HTTP benchmark still exercises the standalone source path

The `minilm-knn` HTTP benchmark currently starts the `os-node` standalone
runtime. That route surface does not yet dispatch search requests through the
`os-engine-tantivy` native engine. The hot HTTP route,
`SteelNode::handle_index_search_route`, still uses the legacy
`documents_state` source-backed store:

- request bodies are parsed in the standalone runtime;
- index metadata is read from `metadata_manifest_state`;
- candidate documents are pulled from `documents_state`;
- query matching, sorting, aggregation, k-NN compatibility, highlighting, and
  pagination are performed over JSON/source values in the route layer.

This means the matrix is currently useful for end-to-end HTTP compatibility
performance, but it must not be interpreted as a pure Tantivy-native benchmark.
Native `os-engine-tantivy` improvements only affect this benchmark after the
standalone HTTP write/search routes are wired to the engine.

Observed evidence from the lock-scope benchmark pass:

- Steelsearch 1-node: `24.41 ops/s`
- OpenSearch 1-node: `212.98 ops/s`
- Steelsearch 3-node: `24.45 ops/s`
- OpenSearch 3-node: `95.20 ops/s`
- Steelsearch 1-node and 3-node both hit the same ceiling, which points to a
  common standalone route/runtime path rather than shard topology.

Low-risk optimization already applied:

- the search route no longer clones the entire `documents_state` map for normal
  search requests;
- it copies only candidate document fields needed for the current request;
- suggest response construction now reads the existing source map or PIT
  snapshot by reference instead of cloning the full map.

Quick validation on `quick-minilm-knn`, corpus `1000`, duration `8s`,
Steelsearch 1-node:

- before clone elision artifact: `112.19 ops/s`
- after clone elision artifact: `117.19 ops/s`

Full `minilm-knn`, corpus `5000`, duration `30s`, Steelsearch 1-node:

- before clone elision: `24.41 ops/s`
- after clone elision: `26.40 ops/s`

The small gain confirms that map cloning was not the dominant bottleneck. The
next material optimization is to add a native-engine-backed standalone HTTP
path for create/index/refresh/search, with a compatibility fallback only for
unsupported request features.

### Native-backed standalone HTTP fast path

The standalone HTTP runtime now keeps the legacy `documents_state` path for
compatibility, but also owns an `os-engine-tantivy` native engine instance.
Benchmark-critical routes are dual-written or routed through that engine:

- create index initializes the native engine schema;
- single-document PUT writes to the legacy store and the native engine;
- global and targeted refresh call native engine refresh;
- search tries a native engine request first and falls back to the legacy
  source-backed route for unsupported route-layer features.

The native fast path intentionally falls back for request features that are
still route-specific: `collapse`, `profile`, `rescore`, `runtime_mappings`,
`derived`, `search_after`, `suggest`, and `terminate_after`.

Quick validation on `quick-minilm-knn`, corpus `1000`, duration `8s`,
Steelsearch 1-node:

- before native HTTP fast path, after clone elision: `117.19 ops/s`
- after native HTTP fast path: `236.91 ops/s`

Full `minilm-knn`, corpus `5000`, duration `30s`, Steelsearch 1-node:

- before native HTTP fast path, after clone elision: `26.40 ops/s`
- after native HTTP fast path: `65.74 ops/s`
- last comparable OpenSearch 1-node result: `212.98 ops/s`

Remaining Steelsearch 1-node operation means after the native HTTP fast path:

- `ranking`: `127.70 ms`
- `refresh`: `130.97 ms`
- `vector`: `79.24 ms`
- `nested`: `57.04 ms`
- `write`: `54.55 ms`
- `facet`: `42.70 ms`
- `hybrid`: `33.36 ms`
- `lexical`: `19.22 ms`
- `sort_filter`: `18.75 ms`

Current interpretation:

- lexical and sorted-filter queries now benefit strongly from the native path;
- ranking remains high because the workload uses multi-match and phrase-heavy
  scoring, which still has substantial compatibility scoring/materialization
  cost;
- refresh is now a visible bottleneck because every benchmark refresh rebuilds
  native searchable state after live writes;
- write latency includes dual-write cost into both the compatibility store and
  the native engine;
- vector latency is materially improved from the source path but still
  dominated by the current exact/vector candidate implementation rather than
  an ANN index comparable to OpenSearch k-NN.

Optimized full matrix artifact:

- `target/search-benchmark-matrix-minilm-knn-native-http/summary.json`
- `target/search-benchmark-matrix-minilm-knn-native-http/report.md`

Optimized `minilm-knn` throughput:

| topology | Steelsearch | OpenSearch | Steelsearch/OpenSearch |
|---|---:|---:|---:|
| single-node | `66.24 ops/s` | `215.10 ops/s` | `0.31x` |
| three-node | `66.88 ops/s` | `94.15 ops/s` | `0.71x` |

Optimized single-node mean latency:

| operation | Steelsearch ms | OpenSearch ms | ratio |
|---|---:|---:|---:|
| lexical | `25.48` | `12.16` | `2.10x` |
| ranking | `125.20` | `15.76` | `7.94x` |
| facet | `41.60` | `15.64` | `2.66x` |
| sort_filter | `17.29` | `15.18` | `1.14x` |
| nested | `58.34` | `12.64` | `4.62x` |
| vector | `75.47` | `21.90` | `3.45x` |
| hybrid | `34.85` | `20.87` | `1.67x` |
| write | `51.48` | `14.58` | `3.53x` |
| refresh | `133.11` | `72.74` | `1.83x` |

Optimized three-node mean latency:

| operation | Steelsearch ms | OpenSearch ms | ratio |
|---|---:|---:|---:|
| lexical | `18.80` | `32.21` | `0.58x` |
| ranking | `124.77` | `41.98` | `2.97x` |
| facet | `42.72` | `39.72` | `1.08x` |
| sort_filter | `20.28` | `48.28` | `0.42x` |
| nested | `59.45` | `31.50` | `1.89x` |
| vector | `75.76` | `51.78` | `1.46x` |
| hybrid | `35.85` | `47.04` | `0.76x` |
| write | `52.10` | `26.72` | `1.95x` |
| refresh | `125.67` | `99.76` | `1.26x` |

Next bottlenecks after native HTTP routing:

- ranking: multi-match and phrase-heavy scoring remains the largest search
  gap;
- refresh: native refresh rebuild cost is now visible under mixed write
  pressure;
- write: benchmark writes currently dual-write to the compatibility store and
  native engine;
- vector: exact/vector candidate path still trails OpenSearch k-NN;
- topology: Steelsearch 1-node and 3-node throughput remain almost identical,
  which means the current development cluster path does not yet distribute the
  benchmark query load across nodes.

## Search workload coverage

General search performance is intentionally broader than simple term matching.
The baseline workload includes:

- `lexical`: basic term and match queries plus filters
- `ranking`: `multi_match`, phrase-sensitive ranking, and `must/should` query
  patterns
- `facet`: query plus `terms`, `date_histogram`, and `range` aggregations
- `sort_filter`: filtered search with explicit sort keys
- `vector`: k-NN search
- `hybrid`: lexical + k-NN + filter combined search
- `write` and `refresh`: background mutation and refresh pressure during the
  run

This keeps the “general search” bucket aligned with how clusters are usually
used in production: ranking, filtering, faceting, and hybrid retrieval all
matter, not just exact term lookup.

## Benchmark profiles

The matrix runner has named profiles so the agreed workload does not depend on
operator memory.

Default profile: `minilm-knn`

- corpus size: `5000`
- vector dimension: `384`, matching `all-MiniLM-L6-v2` embedding shape
- duration per scenario: `30s`
- clients: `4`
- shards: `3`
- replicas: `1` where topology permits
- query mix:
  `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5`

Fast validation profile: `quick-minilm-knn`

- corpus size: `1500`
- vector dimension: `384`, matching `all-MiniLM-L6-v2` embedding shape
- duration per scenario: `8s`
- clients: `4`
- same query mix as `minilm-knn`

Command-line overrides are still supported, but benchmark reports record the
selected profile and final parameters.

## Tooling

Primary entry points:

- [run-http-load-baseline.py](/home/ubuntu/steelsearch/tools/run-http-load-baseline.py)
- [run-opensearch-cluster-dev.sh](/home/ubuntu/steelsearch/tools/run-opensearch-cluster-dev.sh)
- [run-steelsearch-cluster-dev.sh](/home/ubuntu/steelsearch/tools/run-steelsearch-cluster-dev.sh)
- [run-search-benchmark-matrix.py](/home/ubuntu/steelsearch/tools/run-search-benchmark-matrix.py)

Steelsearch benchmark launchers must run with:

- `STEELSEARCH_BUILD_PROFILE=release`
- `STEELSEARCH_RUSTUP_TOOLCHAIN=nightly`

The current dependency set for `os-engine-tantivy` requires a newer Cargo
resolver than the workspace default `1.76` toolchain provides.

## Running the matrix

Quick benchmark pass, all scenarios:

```bash
python3 tools/run-search-benchmark-matrix.py \
  --profile quick-minilm-knn \
  --output-dir target/search-benchmark-matrix
```

Heavier benchmark pass, all scenarios:

```bash
python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --output-dir target/search-benchmark-matrix
```

Resource-safe serial pass:

```bash
OUT=target/search-benchmark-matrix-minilm-knn

RUN_HTTP_LOAD_TESTS=1 python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --output-dir "$OUT" \
  --scenarios steelsearch-single-node \
  --skip-existing

RUN_HTTP_LOAD_TESTS=1 python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --output-dir "$OUT" \
  --scenarios opensearch-single-node \
  --skip-existing

RUN_HTTP_LOAD_TESTS=1 python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --output-dir "$OUT" \
  --scenarios steelsearch-three-node \
  --skip-existing

RUN_HTTP_LOAD_TESTS=1 python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --output-dir "$OUT" \
  --scenarios opensearch-three-node \
  --skip-existing

python3 tools/run-search-benchmark-matrix.py \
  --profile minilm-knn \
  --output-dir "$OUT" \
  --aggregate-only
```

Use the resource-safe serial pass on small hosts. It starts only one engine
topology at a time and later aggregates the saved per-scenario `baseline.json`
files.

Dry run:

```bash
python3 tools/run-search-benchmark-matrix.py --dry-run
```

## Generated artifacts

The runner writes:

- `target/search-benchmark-matrix/summary.json`
- `target/search-benchmark-matrix/report.md`
- per-scenario JSON under `target/search-benchmark-matrix/<scenario>/baseline.json`
- per-scenario daemon logs under `target/search-benchmark-matrix/<scenario>/logs/`

Additional engine-level deterministic benchmarks are written to:

- `target/tantivy-native-benchmarks/deterministic_baselines.jsonl`

The report contains:

- scenario-level throughput and error rate
- per-operation p50/p95/p99 latency tables
- single-node and three-node Steelsearch-vs-OpenSearch comparisons
- explicit workload coverage for lexical, ranking, facet, sorted, vector, and
  hybrid search

## Lock scope and ranking critical-path pain point

The 2026-06-14 ranking regression investigation found that the apparent lock
scope problem was mostly caused by query planning inside the read-locked engine
state. The standalone HTTP path reached the native engine, but ranking queries
using `multi_match` and `match_phrase` were classified as native candidate
post-filter queries. That forced Tantivy to collect a broad candidate set and
then rescore/filter source documents while the engine store read lock was still
held.

Specific pain points:

- `multi_match` fields such as `title^2` were looked up literally, so native
  field lookup could miss the real `title` field.
- `multi_match.type=best_fields` was rejected by the DSL parser even though it
  is the benchmark's default ranking shape and maps to the current native
  `multi_match` behavior.
- `match_phrase` option objects such as `{ "query": "premium checkout", "slop": 1 }`
  reached the Tantivy builder as an object and failed text extraction.
- `multi_match` and `match_phrase` are representable as Tantivy queries for the
  current benchmark workload, so treating them as post-filter-only expanded the
  hot-path work unnecessarily.
- The `RwLock` conversion prevents writer exclusion from blocking concurrent
  readers, but it does not help if each reader holds the lock while performing
  source-level candidate rescoring.

Guardrail for future optimization work:

- Keep native-query-compatible lexical constructs on Tantivy top-docs collectors.
- Do not add source-level post-filter requirements to common ranking leaves
  unless the OpenSearch compatibility behavior cannot be represented natively.
- If post-filter is required, avoid holding the engine store lock across broad
  source rescoring where possible.

Focused benchmark result after fixing this path:

- Scenario: `minilm-knn`, Steelsearch 1-node, corpus `5000`, query mix
  `ranking=100`, duration `10s`.
- Before parser/native-page fixes: `172-175ms` mean latency,
  approximately `23 ops/s`.
- After parser/native-page fixes:
  `target/search-benchmark-ranking-best-fields-native-5000/summary.json`.
- Result: `2.52ms` mean latency, `p95=4.05ms`, `p99=5.15ms`,
  `1578.64 ops/s`, `0` errors.

Full serial matrix result after the ranking native path fix:

- Artifact: `target/search-benchmark-matrix-minilm-knn-ranking-native/summary.json`.
- Single-node throughput: Steelsearch `84.19 ops/s`, OpenSearch
  `207.42 ops/s`, ratio `0.41x`.
- Three-node throughput: Steelsearch `81.64 ops/s`, OpenSearch
  `89.95 ops/s`, ratio `0.91x`.
- Single-node ranking mean latency improved from the previous optimized matrix
  value of `125.20ms` to `20.63ms`; OpenSearch was `16.56ms`.
- Three-node ranking mean latency improved to `21.35ms`; OpenSearch was
  `42.96ms`.

Remaining bottlenecks from this full matrix:

- Vector search is the largest single-node search gap: Steelsearch
  `82.04ms` mean vs OpenSearch `23.05ms`, ratio `3.56x`.
- Nested search remains source/post-filter heavy: Steelsearch `62.44ms` mean
  vs OpenSearch `14.00ms`, ratio `4.46x`.
- Facets remain slower: Steelsearch `48.04ms` mean vs OpenSearch `16.47ms`,
  ratio `2.92x`.
- Write latency still reflects compatibility-store plus native-engine dual
  writes: Steelsearch `45.99ms` mean vs OpenSearch `14.51ms`, ratio `3.17x`.
- Refresh remains slower: Steelsearch `133.26ms` mean vs OpenSearch `71.00ms`,
  ratio `1.88x`.
- Steelsearch 3-node throughput (`81.64 ops/s`) did not improve over
  Steelsearch 1-node (`84.19 ops/s`), so the benchmark path is still not
  distributing query execution effectively across nodes.

Vector-focused follow-up:

- Mapped vector candidate construction no longer clones `_source` into
  `VectorSearchHit`; mapped candidates carry `null` source and the final
  `SearchHit` still materializes source from the stored document.
- Mapped vector candidate construction also avoids a redundant document lookup
  before the final hit materialization step.
- Focused Steelsearch vector-only artifact:
  `target/search-benchmark-vector-source-elision-5000/summary.json`.
- Steelsearch vector-only result: `11.40ms` mean, `p95=16.82ms`,
  `p99=20.55ms`, `350.46 ops/s`, `0` errors.
- Focused OpenSearch vector-only artifact:
  `target/search-benchmark-vector-source-elision-5000-os/summary.json`.
- OpenSearch vector-only result: `35.70ms` mean, `p95=60.02ms`,
  `p99=79.17ms`, `111.96 ops/s`, `0` errors.
- Interpretation: the full mixed matrix vector gap is not explained by the
  standalone vector scorer alone. Under vector-only load Steelsearch is faster;
  under the mixed workload vector latency inflates, so remaining work should
  focus on cross-operation contention, especially write/refresh/facet/nested
  lock hold time and CPU interference.

Write/refresh contention follow-up:

- Pain point: `apply_primary_document` invalidated the native
  `search_state` on every write, including `refresh=false` writes. In the HTTP
  mixed workload, writes are `refresh=false` while explicit `_refresh` is a
  separate operation. Invalidating `search_state` made searches between write
  and refresh unable to use the existing refreshed native snapshot and pushed
  them toward fallback or heavier materialization paths.
- Fix: writes now preserve the existing refreshed native search snapshot.
  Explicit refresh still advances `refreshed_seq_no`, clears vector cache, and
  rebuilds the Tantivy search state.
- Artifact: `target/search-benchmark-matrix-minilm-knn-preserve-search-state/summary.json`.
- Steelsearch 1-node full mixed throughput improved from `84.19 ops/s` to
  `110.68 ops/s`.
- Vector mean latency improved from `82.04ms` to `24.82ms`.
- Ranking mean latency improved from `20.63ms` to `17.95ms`.
- Write mean latency improved from `45.99ms` to `36.76ms`.
- Refresh mean latency improved from `133.26ms` to `126.37ms`.
- Interpretation: a large part of mixed-workload vector latency was caused by
  write-triggered native snapshot invalidation, not by vector scoring itself.
  Future write-path changes must preserve the last refreshed search snapshot
  until an explicit refresh publishes a new one.

Facet aggregation materialization follow-up:

- Pain point: `collect_aggregations_native` and
  `collect_aggregations_for_query_index_aware_with_context` built full
  `SearchHit` objects before deciding whether the aggregation actually needed
  hit materialization. The benchmark facet query uses `size=0` with terms,
  range, and date histogram aggregations, so source-bearing hit construction was
  unnecessary.
- Fix: hit materialization is now performed only when the aggregation map
  requires it, for example `top_hits`-like surfaces. Document-backed
  aggregations use matched documents directly.
- Focused artifact:
  `target/search-benchmark-facet-no-hit-materialization-5000/summary.json`.
- Focused Steelsearch facet-only result: `40.48ms` mean, `p95=96.47ms`,
  `98.40 ops/s`, `0` errors.
- Mixed artifact:
  `target/search-benchmark-matrix-minilm-knn-facet-no-hit-materialization/summary.json`.
- Steelsearch 1-node full mixed throughput improved from `110.68 ops/s` to
  `124.01 ops/s`.
- Facet mean latency improved from `49.02ms` to `27.82ms`.
- Write mean latency also improved from `36.76ms` to `33.58ms`, likely because
  less aggregation materialization reduced mixed-workload CPU and lock pressure.

Nested ordinal-index follow-up:

- Pain point: for nested query shapes supported by the native child ordinal
  index, Steelsearch still re-evaluated the nested child source after computing
  exact child ordinal matches. In the benchmark nested query, the bool query is
  a conjunction of two term leaves on `events.kind` and `events.status`; the
  ordinal intersection already proves a same-child match.
- Fix: when `native_nested_child_ordinals_for_query` returns a child ordinal
  set, parent ids are collected directly after the refreshed-seq check.
  Unsupported nested shapes still use the source-validation fallback.
- Focused artifact:
  `target/search-benchmark-nested-ordinal-no-reverify-5000/summary.json`.
- Focused Steelsearch nested-only result: `48.91ms` mean, `p95=99.77ms`,
  `81.55 ops/s`, `0` errors.
- Mixed artifact:
  `target/search-benchmark-matrix-minilm-knn-nested-ordinal-no-reverify/summary.json`.
- Steelsearch 1-node full mixed throughput improved from `124.01 ops/s` to
  `126.42 ops/s`.
- Nested mean latency improved from `61.41ms` to `56.21ms`.
- Write mean latency improved from `33.58ms` to `31.44ms`.
- Interpretation: this removes redundant source work for the benchmark nested
  shape, but nested remains materially slower than OpenSearch. The remaining
  cost is likely parent hit materialization plus the current nested index layout
  rather than same-child filtering correctness.

Refresh lock-scope follow-up:

- Pain point: `TantivyEngine::refresh` held the engine store write lock while
  rebuilding the nested child index and Tantivy search state. Under mixed load,
  this made refresh a global publication bottleneck: searches use a store read
  lock, writes use a store write lock, and refresh rebuild work blocked both
  while the new snapshot was being built.
- First fix: explicit refresh now skips no-op rebuilds when the target refreshed
  sequence number already matches the current indexed sequence number. This
  avoids clearing k-NN cache and rebuilding the native snapshot when there are
  no new writes.
- Second fix: refresh now copies the schema/document snapshot under a short
  read lock, builds refresh artifacts outside the engine store lock, and then
  takes a short write lock only to publish `refreshed_seq_no`, clear refresh
  dependent cache, and swap in the new nested/Tantivy search state.
- Focused no-op refresh artifact:
  `target/search-benchmark-refresh-noop-skip-5000/summary.json`.
- No-op refresh-only result after the skip: `5.08ms` mean, `p95=6.63ms`,
  `785.18 ops/s`, `0` errors.
- Focused lock-scope refresh artifact:
  `target/search-benchmark-refresh-lock-scope-5000/summary.json`.
- No-op refresh-only result after lock-scope split: `5.03ms` mean,
  `p95=6.24ms`, `794.49 ops/s`, `0` errors.
- Mixed artifact with no-op skip only:
  `target/search-benchmark-matrix-minilm-knn-refresh-noop-skip/summary.json`.
- Mixed result with no-op skip only: `138.29 ops/s`; refresh mean `99.96ms`,
  write mean `30.70ms`, vector mean `23.49ms`, ranking mean `14.65ms`, lexical
  mean `14.54ms`.
- Mixed artifact after refresh lock-scope split:
  `target/search-benchmark-matrix-minilm-knn-refresh-lock-scope/summary.json`.
- Mixed result after refresh lock-scope split: `144.18 ops/s`; refresh mean
  `231.14ms`, write mean `21.55ms`, vector mean `16.91ms`, ranking mean
  `6.04ms`, lexical mean `6.89ms`, facet mean `19.89ms`, nested mean `50.37ms`.
- Interpretation: the lock-scope split improved the critical mixed search/write
  path by reducing how long refresh blocks readers and writers. Refresh latency
  itself increased because the benchmark refresh request now includes more of
  its own rebuild cost instead of pushing that cost into queued searches and
  writes. This is a better shape for mixed throughput, but it confirms that
  native refresh rebuild remains a real CPU/memory-copy bottleneck.
- Latest Steelsearch single-node throughput is `144.18 ops/s`. Against the last
  comparable OpenSearch single-node baseline (`207.42 ops/s` from
  `target/search-benchmark-matrix-minilm-knn-ranking-native/summary.json`), the
  current ratio is `0.70x`.
- Remaining lock-scope risk: refresh still clones the full document map before
  rebuilding. This keeps the store lock short compared with rebuilding Tantivy
  in place, but the clone is still O(document count) and occurs while holding a
  read lock. A larger structural fix would move to immutable per-index snapshot
  state or per-index locking so refresh publication does not require cloning the
  full source document map under the global store lock.
- Guardrail: future changes in refresh/write/search must preserve these rules:
  searches should not take the store write lock; writes must not invalidate the
  last refreshed search snapshot; refresh must not perform expensive rebuild or
  cache work while holding the global store write lock; compatibility fallback
  paths in the standalone runtime should avoid holding `documents_state` while
  evaluating queries.

Nested search page fast-path follow-up:

- Search-performance focus: after the refresh lock-scope split, refresh latency
  is still important as an NRT publication cost, but the search optimization
  track should prioritize request families that directly affect query latency.
  In the latest mixed profile, nested search was the largest remaining search
  mean before this pass.
- Pain point: the native nested child ordinal index could already prove the
  benchmark nested predicate (`events.kind` AND `events.status`) at child level,
  but the search path still converted every matching parent into a full
  source-bearing `SearchHit`, re-ran nested/source scoring, sorted the full hit
  set, and only then returned the requested page.
- Fix: for default-score/default-sort nested requests, the page path now uses
  native nested parent candidates directly. It computes total hits from the
  candidate id set and materializes only the requested page with a constant
  score. Unsupported nested shapes still fall back to the existing source
  validation path.
- Focused artifact after removing nested source re-score only:
  `target/search-benchmark-nested-proven-hit-no-rescore-5000/summary.json`.
- Focused nested-only result after removing nested source re-score:
  `45.68ms` mean, `p95=91.56ms`, `87.38 ops/s`, `0` errors.
- Focused artifact after nested page fast path:
  `target/search-benchmark-nested-page-fast-path-5000/summary.json`.
- Focused nested-only result after nested page fast path: `5.28ms` mean,
  `p95=9.03ms`, `p99=11.47ms`, `755.92 ops/s`, `0` errors.
- Mixed artifact after nested page fast path:
  `target/search-benchmark-matrix-minilm-knn-nested-page-fast-path/summary.json`.
- Mixed result after nested page fast path: `174.94 ops/s`; nested mean
  `8.41ms`, ranking mean `5.53ms`, lexical mean `5.80ms`, sort/filter mean
  `6.20ms`, vector mean `16.81ms`, hybrid mean `24.94ms`, facet mean
  `19.38ms`, write mean `16.24ms`.
- Compared with the previous mixed artifact
  `target/search-benchmark-matrix-minilm-knn-nested-proven-hit-no-rescore/summary.json`,
  throughput improved from `145.04 ops/s` to `174.94 ops/s`, and nested mean
  improved from `47.86ms` to `8.41ms`.
- Compared with the last OpenSearch single-node baseline
  `target/search-benchmark-matrix-minilm-knn-ranking-native/summary.json`
  (`207.42 ops/s`), the current Steelsearch single-node ratio is `0.84x`.
- Remaining search bottlenecks after this pass are hybrid (`24.94ms` mean),
  facet (`19.38ms` mean), and vector (`16.81ms` mean). Refresh remains a
  separate NRT publication-cost issue rather than the primary search-hot-path
  target.

Incremental refresh track separation:

- Incremental refresh is still structurally important. The current native
  refresh model rebuilds an in-memory Tantivy index from all refreshed
  documents, which is O(total refreshed documents). Lucene/OpenSearch-style NRT
  refresh does not re-index every document on each refresh.
- However, incremental refresh should be treated as a separate NRT visibility
  and write/search interference track, not as the first search latency target.
  It needs explicit handling for updates, deletes, schema changes, and stale
  document visibility. A partial append-only optimization would improve the
  current benchmark but risks encoding the wrong semantics if generalized too
  early.
- Guardrail: optimize refresh when it blocks or perturbs search tail latency;
  optimize query families directly when the measured bottleneck is search
  materialization, scoring, sorting, vector candidate generation, or aggregation
  collection.

Hybrid single-kNN bool fast-path experiment:

- Pain point investigated: the benchmark hybrid query is a bool query with one
  lexical `match`, one `knn`, and one tenant `term` filter. The suspected cost
  was duplicate candidate scoring: k-NN candidate generation computes vector
  scores, then the bool hit path re-enters `score_document_query` and recomputes
  the vector score while also checking non-vector clauses.
- Experiment: a narrow fast path for sort-free bool queries with a single
  top-level k-NN clause reused vector candidate scores and evaluated only the
  non-k-NN must/filter clauses against those candidates.
- Focused artifact:
  `target/search-benchmark-hybrid-single-knn-bool-fast-path-5000/summary.json`.
- Focused hybrid-only result: `15.87ms` mean, `p95=25.58ms`, `251.74 ops/s`,
  `0` errors.
- Mixed artifact:
  `target/search-benchmark-matrix-minilm-knn-hybrid-single-knn-bool-fast-path/summary.json`.
- Mixed result: `169.23 ops/s`; hybrid mean `26.65ms`, facet mean `20.45ms`,
  vector mean `17.10ms`.
- Decision: the fast path was not retained. It did not improve the authoritative
  mixed workload compared with the prior nested page fast-path matrix
  (`174.94 ops/s`, hybrid mean `24.94ms`). The focused result suggests the idea
  can help isolated hybrid execution, but the current mixed workload is more
  sensitive to contention and the existing generic path is not the dominant
  remaining limiter.
- Next search target: facet aggregation remains consistently high in mixed runs
  after nested optimization, while lexical/ranking/sort/nested are now mostly
  single-digit mean latency.

Facet unordered document collector experiment:

- Pain point investigated: size-zero facet aggregation does not need relevance
  ordering, but matched documents were materialized through
  `TopDocs::with_limit(total_visible_docs)`, which appears wasteful because it
  asks Tantivy for a full scored/top-doc window before document-backed
  aggregation.
- Experiment: a narrow aggregation-only collector gathered matching
  `DocAddress` values without requesting scores or top-doc ordering, then
  fetched `_id` and mapped back to stored documents for aggregation.
- Focused baseline after nested page fast path:
  `target/search-benchmark-facet-after-nested-page-fast-path-5000/summary.json`.
- Focused baseline facet-only result: `41.83ms` mean, `p95=95.40ms`,
  `95.34 ops/s`, `0` errors.
- Focused experiment artifact:
  `target/search-benchmark-facet-unordered-doc-collector-5000/summary.json`.
- Focused experiment result: `66.87ms` mean, `p95=172.16ms`, `59.65 ops/s`,
  `0` errors.
- Decision: the unordered collector was not retained. In this Tantivy setup,
  `TopDocs` appears faster than the naive custom collector path, likely because
  the custom collector still requires stored document fetches and loses internal
  collector optimizations.
- Next facet candidate: avoid repeated aggregation passes over the same matched
  document set. The benchmark facet request performs two terms aggregations, one
  numeric range aggregation, and one date histogram. Current document-backed
  aggregation loops over the matched document set once per aggregation. A fused
  facet collector that extracts `service`, `category`, `latency`, and
  `event_time` in one document pass is a safer next candidate than replacing the
  Tantivy match collector.

Post-build-idle benchmark correction:

- Measurement note: a concurrent Docker build or other host activity may have
  inflated some prior facet and mixed measurements. After checking the process
  table and Docker container state, no active build workload was observed, and
  the facet/mixed benchmarks were rerun without code changes.
- Focused idle facet artifact:
  `target/search-benchmark-facet-after-build-idle-5000/summary.json`.
- Focused idle facet-only result: `40.44ms` mean, `p95=94.53ms`,
  `98.64 ops/s`, `0` errors. This matches the earlier `41.83ms` baseline and
  supports treating the `66.87ms` unordered-collector run as noisy/regressed,
  not as a valid baseline.
- Idle mixed artifact:
  `target/search-benchmark-matrix-minilm-knn-after-build-idle/summary.json`.
- Idle mixed result: `186.19 ops/s`; hybrid mean `23.61ms`, facet mean
  `17.64ms`, vector mean `14.76ms`, write mean `16.02ms`, nested mean
  `6.87ms`, sort/filter mean `6.72ms`, lexical mean `5.83ms`, ranking mean
  `5.43ms`.
- Compared with the last OpenSearch single-node baseline
  `target/search-benchmark-matrix-minilm-knn-ranking-native/summary.json`
  (`207.42 ops/s`), the current idle Steelsearch single-node ratio is `0.90x`.
- Updated priority: after idle rerun, hybrid and vector/facet are close enough
  that additional changes should be validated with both focused and mixed runs.
  The next search optimization should target a change that improves the mixed
  result, not only an isolated focused workload.

Hybrid/vector focused rerun after idle baseline:

- Focused hybrid artifact:
  `target/search-benchmark-hybrid-after-build-idle-5000/summary.json`.
- Focused hybrid-only result: `14.07ms` mean, `p95=20.71ms`,
  `283.84 ops/s`, `0` errors.
- Focused vector artifact:
  `target/search-benchmark-vector-after-build-idle-5000/summary.json`.
- Focused vector-only result: `20.16ms` mean, `p95=30.19ms`,
  `198.05 ops/s`, `0` errors.
- Focused vector+hybrid artifact:
  `target/search-benchmark-vector-hybrid-after-build-idle-5000/summary.json`.
- Vector+hybrid result: vector mean `18.31ms`, hybrid mean `29.86ms`, combined
  throughput `175.85 ops/s`.
- Interpretation: hybrid-only is not intrinsically slower than vector-only in
  isolation, but hybrid degrades when mixed with vector-heavy load. The earlier
  narrow hybrid score-reuse fast path improved isolated hybrid but regressed the
  authoritative mixed benchmark, so it remains rejected. Further hybrid work
  should target shared candidate/scoring pressure under mixed vector load rather
  than only reducing single-query code paths.

Vector distance hot-loop follow-up:

- Pain point: vector and hybrid paths both rely on exact vector scan over the
  refreshed document set. The k-NN request-result cache is wired for pure
  single-index and multi-index KNN plus hybrid vector requests, including native
  aggregation/sort combinations, but these benchmark query vectors are
  randomized. The common cost in this benchmark remains the per-document
  distance loop.
- Fix: `squared_l2_distance` and `dot_product` now use explicit indexed loops
  with four-lane unrolling instead of iterator/zip/map/sum chains. This keeps
  vector scoring semantics unchanged while reducing tight-loop overhead.
- First vector+hybrid run failed during server startup and was discarded:
  `target/search-benchmark-vector-hybrid-vector-loop-unroll-5000/summary.json`.
- Focused retry artifact:
  `target/search-benchmark-vector-hybrid-vector-loop-unroll-5000-retry/summary.json`.
- Focused vector+hybrid result after loop unroll: vector mean `9.62ms`, hybrid
  mean `15.03ms`, combined throughput `341.55 ops/s`. Previous idle
  vector+hybrid focused result was vector mean `18.31ms`, hybrid mean
  `29.86ms`, combined throughput `175.85 ops/s`.
- Mixed artifact after loop unroll:
  `target/search-benchmark-matrix-minilm-knn-vector-loop-unroll/summary.json`.
- Mixed retry artifact after loop unroll:
  `target/search-benchmark-matrix-minilm-knn-vector-loop-unroll-retry/summary.json`.
- Mixed retry result: `184.46 ops/s`; vector mean `14.61ms`, hybrid mean
  `23.40ms`, facet mean `18.03ms`, nested mean `7.24ms`, ranking mean
  `4.83ms`. This is effectively neutral on total throughput compared with the
  idle baseline `186.19 ops/s`, while slightly improving vector/hybrid means.
- Decision: keep the loop change. It is semantics-preserving, materially helps
  vector-heavy focused load, and does not materially regress the authoritative
  mixed workload within observed benchmark noise.

Latest serial 1-node comparison after search-path optimizations:

- Artifact:
  `target/search-benchmark-matrix-minilm-knn-final-1node-compare/summary.json`.
- The matrix was run serially for Steelsearch 1-node and OpenSearch 1-node to
  avoid simultaneous server load.
- Overall throughput: Steelsearch `180.07 ops/s`, OpenSearch `225.31 ops/s`,
  ratio `0.80x`.
- Search operation mean latency comparison:

| operation | Steelsearch ms | OpenSearch ms | Steelsearch/OpenSearch |
|---|---:|---:|---:|
| lexical | `5.26` | `11.56` | `0.46x` |
| ranking | `5.24` | `15.15` | `0.35x` |
| sort_filter | `5.77` | `14.89` | `0.39x` |
| nested | `7.71` | `12.36` | `0.62x` |
| vector | `15.12` | `20.92` | `0.72x` |
| facet | `18.69` | `14.44` | `1.29x` |
| hybrid | `23.83` | `19.94` | `1.19x` |

- Non-search/mutation operation comparison:

| operation | Steelsearch ms | OpenSearch ms | Steelsearch/OpenSearch |
|---|---:|---:|---:|
| write | `16.36` | `14.24` | `1.15x` |
| refresh | `229.81` | `69.00` | `3.33x` |

- Interpretation: after the nested page fast path, ranking native path, and
  vector scoring loop cleanup, Steelsearch is now faster than OpenSearch on the
  mean latency of lexical, ranking, sort/filter, nested, and vector search in
  this single-node matrix. The remaining search gaps are facet and hybrid.
  Overall throughput still trails OpenSearch because refresh is much slower and
  write tail latency is higher, so the mixed workload spends more client time
  behind NRT publication and mutation pressure even though most search paths are
  competitive or faster.
- Next likely work: for search-only improvement, focus on facet and hybrid. For
  overall mixed throughput, incremental/NRT refresh and write tail behavior are
  the dominant non-search gaps.

Latest serial 3-node comparison after search-path optimizations:

- Artifact:
  `target/search-benchmark-matrix-minilm-knn-final-3node-compare/summary.json`.
- The matrix was run serially for Steelsearch 3-node and OpenSearch 3-node to
  avoid simultaneous server load.
- Overall throughput: Steelsearch `185.18 ops/s`, OpenSearch `103.17 ops/s`,
  ratio `1.79x`.
- Search operation mean latency comparison:

| operation | Steelsearch ms | OpenSearch ms | Steelsearch/OpenSearch |
|---|---:|---:|---:|
| lexical | `5.54` | `28.40` | `0.20x` |
| ranking | `5.08` | `36.23` | `0.14x` |
| sort_filter | `6.12` | `41.65` | `0.15x` |
| nested | `7.39` | `33.74` | `0.22x` |
| vector | `14.95` | `48.64` | `0.31x` |
| facet | `18.06` | `36.20` | `0.50x` |
| hybrid | `23.41` | `42.24` | `0.55x` |

- Non-search/mutation operation comparison:

| operation | Steelsearch ms | OpenSearch ms | Steelsearch/OpenSearch |
|---|---:|---:|---:|
| write | `15.83` | `26.32` | `0.60x` |
| refresh | `221.34` | `89.80` | `2.46x` |

- Interpretation: Steelsearch is faster than OpenSearch on every measured
  3-node operation except refresh. However, Steelsearch 3-node throughput
  (`185.18 ops/s`) is only slightly above the latest Steelsearch 1-node result
  (`180.07 ops/s`). This means Steelsearch is winning the 3-node comparison
  because this local OpenSearch 3-node setup is much slower than its 1-node
  setup, not because Steelsearch is scaling materially with node count.
- Remaining topology pain point: current Steelsearch development-cluster HTTP
  benchmark path still behaves close to single-node execution capacity. Query
  load distribution or shard-local execution fanout is not yet producing a
  proportional throughput gain. Treat 3-node Steelsearch numbers as
  compatibility/topology smoke results, not proof of horizontal search scaling.

Incremental refresh feasibility note:

- Refresh remains the largest mixed-workload gap after search-path optimization.
  Latest serial 1-node comparison shows Steelsearch refresh mean `229.81ms`
  vs OpenSearch `69.00ms`; latest serial 3-node comparison shows Steelsearch
  refresh mean `221.34ms` vs OpenSearch `89.80ms`.
- A simple append-only incremental refresh would improve the current benchmark
  because the benchmark write operation only appends `live-*` document ids with
  `refresh=false`, followed by explicit refresh operations.
- However, applying append-only incremental refresh as a general engine change
  would be semantically unsafe with the current storage layout. `StoredIndex`
  keeps `documents: BTreeMap<String, StoredDocument>`, i.e. only the latest
  source/version for each document id. On update, the pre-refresh document
  version is overwritten. On delete, the id is removed. The current Tantivy
  search snapshot can still contain the old `_id`, but `refreshed_document_by_id`
  maps hits back through the latest `documents` map and filters by current
  `seq_no`. That means the engine cannot reconstruct the previous refreshed
  version for correct NRT visibility once an update/delete has happened.
- Correct incremental refresh therefore needs a structural change before the
  refresh optimization itself:
  - keep a refreshed immutable document/source snapshot, or keep versioned
    document records by `_id` and sequence number;
  - track pending mutations since the last refresh, including updated ids and
    deleted ids;
  - on refresh, apply deletes by `_id`, add new/updated versions, then publish a
    new reader and refreshed document snapshot atomically;
  - preserve the old refreshed snapshot for searches until the new refresh is
    published.
- Decision: do not add a benchmark-only append incremental refresh in the engine
  yet. Treat incremental refresh as a dedicated NRT snapshot architecture task,
  not a small local optimization. The safe short-term refresh work already done
  is limited to no-op refresh skip and moving expensive rebuild work outside the
  global store write lock.

Search-only 1-node comparison:

- Artifact:
  `target/search-benchmark-matrix-minilm-knn-search-only-1node-compare/summary.json`.
- Query mix excludes write and refresh:
  `lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10`.
- Overall search-only throughput: Steelsearch `541.92 ops/s`, OpenSearch
  `242.52 ops/s`, ratio `2.23x`.
- Search-only mean latency comparison:

| operation | Steelsearch ms | OpenSearch ms | Steelsearch/OpenSearch |
|---|---:|---:|---:|
| lexical | `3.28` | `12.34` | `0.27x` |
| ranking | `2.67` | `16.24` | `0.16x` |
| sort_filter | `3.80` | `16.74` | `0.23x` |
| nested | `4.40` | `13.35` | `0.33x` |
| vector | `9.75` | `22.89` | `0.43x` |
| hybrid | `15.27` | `22.27` | `0.69x` |
| facet | `13.10` | `12.48` | `1.05x` |

- Interpretation: when write and refresh are removed, Steelsearch is materially
  faster than OpenSearch for the overall search-only workload. Facet is the only
  remaining mean-latency search gap, and it is small in this isolated mix. This
  confirms that the lower full mixed 1-node throughput is primarily caused by
  non-search interference, especially refresh and write tail behavior, not by
  the optimized search paths themselves.

Standalone write-tail check:

- Suspected pain point: standalone document write routes call
  `persist_shared_runtime_state_to_disk()` after each document write, which
  could clone/write large compatibility state and inflate write tail latency.
- Finding: this persistence path is gated by
  `STEELSEARCH_PERSIST_SHARED_RUNTIME_STATE_PER_WRITE=1`. In the benchmark
  environment it is not the default hot path, so it should not be treated as the
  current mixed benchmark write bottleneck.
- Remaining write cost is instead the intentional compatibility dual-write:
  the standalone runtime updates the legacy `documents_state` compatibility
  store and also writes the same document into the native Tantivy engine. That
  cost is part of the current compatibility architecture and should not be
  removed unless the route surface is fully moved to native state.
- Decision: no write-path code change was made for this item. Keep the note as
  a guardrail so future benchmark analysis does not misattribute write tail to
  disk persistence unless the env gate is explicitly enabled.

## Current authoritative benchmark summary

The current authoritative benchmark artifacts after the latest search-path work
are:

- Search-only 1-node comparison:
  `target/search-benchmark-matrix-minilm-knn-search-only-1node-compare/summary.json`.
- Full mixed 1-node serial comparison:
  `target/search-benchmark-matrix-minilm-knn-final-1node-compare/summary.json`.
- Full mixed 3-node serial comparison:
  `target/search-benchmark-matrix-minilm-knn-final-3node-compare/summary.json`.

Current result summary:

| scope | Steelsearch | OpenSearch | ratio | interpretation |
|---|---:|---:|---:|---|
| search-only 1-node | `541.92 ops/s` | `242.52 ops/s` | `2.23x` | search paths are now materially faster overall |
| full mixed 1-node | `180.07 ops/s` | `225.31 ops/s` | `0.80x` | refresh/write interference dominates mixed throughput |
| full mixed 3-node | `185.18 ops/s` | `103.17 ops/s` | `1.79x` | Steelsearch wins this local comparison, but does not scale materially from 1-node |

Current search-only 1-node mean latencies:

| operation | Steelsearch ms | OpenSearch ms | status |
|---|---:|---:|---|
| lexical | `3.28` | `12.34` | Steelsearch faster |
| ranking | `2.67` | `16.24` | Steelsearch faster |
| sort_filter | `3.80` | `16.74` | Steelsearch faster |
| nested | `4.40` | `13.35` | Steelsearch faster |
| vector | `9.75` | `22.89` | Steelsearch faster |
| hybrid | `15.27` | `22.27` | Steelsearch faster |
| facet | `13.10` | `12.48` | small remaining search gap |

Current full mixed 1-node mean latencies:

| operation | Steelsearch ms | OpenSearch ms | status |
|---|---:|---:|---|
| lexical | `5.26` | `11.56` | Steelsearch faster |
| ranking | `5.24` | `15.15` | Steelsearch faster |
| sort_filter | `5.77` | `14.89` | Steelsearch faster |
| nested | `7.71` | `12.36` | Steelsearch faster |
| vector | `15.12` | `20.92` | Steelsearch faster |
| facet | `18.69` | `14.44` | remaining search gap under mixed load |
| hybrid | `23.83` | `19.94` | remaining search gap under mixed load |
| write | `16.36` | `14.24` | small write gap; Steelsearch p95/p99 tails are larger |
| refresh | `229.81` | `69.00` | largest mixed-workload gap |

Current bottleneck split:

- Search path: mostly optimized. The only consistent remaining search gaps are
  facet and hybrid, and facet is nearly tied in the search-only comparison.
- Mixed workload: dominated by refresh/NRT publication and write tail pressure.
  Search-only throughput proves the core query paths are not the limiting factor.
- Topology: Steelsearch 3-node throughput is close to Steelsearch 1-node
  throughput, so the development-cluster benchmark path still does not prove
  horizontal scaling. 3-node OpenSearch is slower in this local setup, which
  makes Steelsearch look strong in the 3-node comparison but does not remove the
  Steelsearch scaling concern.

Current retained optimizations:

- native HTTP fast path for standalone create/index/refresh/search routing;
- engine store read/write lock split so search uses a read lock;
- native ranking path fixes for `multi_match`/`match_phrase` style benchmark
  queries;
- preserving the last refreshed search snapshot across `refresh=false` writes;
- aggregation hit materialization avoidance for document-backed `size=0`
  aggregations;
- native nested child ordinal path and nested page fast path;
- no-op refresh skip and refresh rebuild outside the global store write lock;
- vector scoring tight-loop cleanup for exact vector scan.

Current rejected or deferred candidates:

- unordered Tantivy document collector for facet aggregation: rejected because it
  regressed focused facet latency;
- narrow hybrid single-kNN bool score-reuse fast path: rejected because it
  improved isolated hybrid but regressed the full mixed benchmark;
- append-only incremental refresh: deferred because the current latest-document
  storage layout cannot preserve update/delete NRT snapshot correctness.

Recommended next implementation tracks:

1. NRT refresh architecture: introduce a refreshed immutable/versioned document
   snapshot and pending mutation tracking, then implement correct incremental
   refresh. This is the largest full mixed throughput opportunity.
2. Native-only write route state: reduce or remove standalone compatibility
   dual-write once route compatibility is sufficiently covered by the native
   engine. This targets write tail and mixed interference.
3. Facet/hybrid polish: pursue only changes that improve both focused and full
   mixed benchmarks. Search-only performance is already strong, so focused-only
   improvements should not be accepted unless mixed remains neutral or better.
4. Topology/fanout: make the 3-node Steelsearch benchmark exercise real
   shard-local distributed execution before using it as horizontal scaling
   evidence.

## Post Docker-build-idle rerun

After confirming that no Docker build/buildkit/cargo/rustc process was active, a
stale previous 3-node OpenSearch benchmark cluster was removed and the 1-node
full mixed MiniLM/k-NN comparison was rerun serially.

Artifact:

- `target/search-benchmark-matrix-minilm-knn-after-docker-idle-rerun/summary.json`

Configuration:

- profile: `minilm-knn`
- corpus: `5000`
- clients: `4`
- duration: `30s`
- query mix: `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5`
- scenarios: `steelsearch-single-node,opensearch-single-node`

Result:

| scope | Steelsearch | OpenSearch | ratio |
|---|---:|---:|---:|
| full mixed 1-node throughput | `180.61 ops/s` | `216.89 ops/s` | `0.83x` |

Mean latency by operation:

| operation | Steelsearch ms | OpenSearch ms | status |
|---|---:|---:|---|
| lexical | `5.54` | `11.85` | Steelsearch faster |
| ranking | `5.37` | `15.69` | Steelsearch faster |
| sort_filter | `6.57` | `15.89` | Steelsearch faster |
| nested | `7.60` | `12.57` | Steelsearch faster |
| vector | `14.98` | `22.26` | Steelsearch faster |
| facet | `18.64` | `15.62` | Steelsearch slower |
| hybrid | `23.55` | `20.68` | Steelsearch slower |
| write | `16.42` | `14.78` | Steelsearch slower |
| refresh | `227.12` | `68.15` | Steelsearch much slower |

Interpretation:

- Docker build noise was not the root cause of the full mixed 1-node gap.
- Search-critical paths remain faster for lexical, ranking, sort/filter, nested,
  and vector.
- The remaining mixed workload gap is still dominated by refresh latency and
  write tail pressure, with smaller facet/hybrid gaps.

## Append-only incremental refresh fast path

The latest mixed-workload bottleneck was refresh: the previous implementation
rebuilt both the nested child index and the in-memory Tantivy search state from
all refreshed documents on every non-noop refresh. That made the 1-node full
mixed benchmark slower than OpenSearch even though the search-only paths were
mostly faster.

Implementation:

- Added an `append_only_since_refresh` guard to the Tantivy stored index state.
- New document IDs keep the guard enabled.
- update/delete/replay/schema-change paths disable the guard and fall back to the
  full refresh rebuild path.
- When the guard is enabled and a previous search state exists, refresh appends
  only pending documents to the existing Tantivy in-memory index, reloads the
  reader, and appends pending nested child documents to the nested child index.

Validation:

- `cargo +nightly check -p os-node --features standalone-runtime`
- `target/search-benchmark-refresh-append-only-incremental-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-append-only-incremental-refresh/summary.json`

Focused refresh-only result:

| scope | throughput | mean | p95 | p99 |
|---|---:|---:|---:|---:|
| Steelsearch refresh-only 1-node | `809.84 ops/s` | `4.93ms` | `6.31ms` | `7.93ms` |

Full mixed 1-node comparison after append-only incremental refresh:

| scope | Steelsearch | OpenSearch | ratio |
|---|---:|---:|---:|
| full mixed 1-node throughput | `309.65 ops/s` | `227.60 ops/s` | `1.36x` |

Mean latency by operation:

| operation | Steelsearch ms | OpenSearch ms | status |
|---|---:|---:|---|
| lexical | `6.91` | `11.29` | Steelsearch faster |
| ranking | `7.38` | `15.10` | Steelsearch faster |
| sort_filter | `7.72` | `15.26` | Steelsearch faster |
| nested | `8.27` | `12.38` | Steelsearch faster |
| vector | `14.93` | `20.82` | Steelsearch faster |
| write | `11.26` | `14.47` | Steelsearch faster |
| refresh | `32.96` | `63.57` | Steelsearch faster |
| facet | `18.63` | `14.92` | Steelsearch slower |
| hybrid | `21.92` | `19.63` | Steelsearch slower by mean; p95 is faster |

Interpretation:

- The previous full mixed 1-node gap was refresh architecture, not Docker build
  noise and not the core search path.
- Append-only incremental refresh is correct only for the guarded append-only
  segment. It deliberately falls back to full rebuild after update/delete/replay
  or schema changes.
- This improves the benchmarked write+refresh workload because the benchmark's
  live write operation uses new `live-*` document IDs with `refresh=false`.
- Remaining pain points are facet mean latency, hybrid mean latency, and high
  Steelsearch p99 tails during mixed load. The p99 tails likely come from refresh
  append/commit/reload still running under the index write lock; moving the
  incremental append work outside the lock would be the next lock-scope target.

## Full matrix after append-only incremental refresh

After the append-only incremental refresh fast path, the full 1-node and 3-node
MiniLM/k-NN matrix was regenerated with existing 1-node results reused and the
3-node scenarios added serially.

Artifact:

- `target/search-benchmark-matrix-minilm-knn-append-only-incremental-refresh/summary.json`

Throughput summary:

| topology | Steelsearch | OpenSearch | ratio |
|---|---:|---:|---:|
| 1-node | `309.65 ops/s` | `227.60 ops/s` | `1.36x` |
| 3-node | `304.84 ops/s` | `80.45 ops/s` | `3.79x` |

3-node mean latency summary:

| operation | Steelsearch ms | OpenSearch ms | status |
|---|---:|---:|---|
| lexical | `7.43` | `39.30` | Steelsearch faster |
| ranking | `7.11` | `46.96` | Steelsearch faster |
| sort_filter | `7.72` | `58.37` | Steelsearch faster |
| nested | `8.72` | `41.03` | Steelsearch faster |
| vector | `15.01` | `62.60` | Steelsearch faster |
| facet | `18.11` | `50.23` | Steelsearch faster |
| hybrid | `21.48` | `51.66` | Steelsearch faster |
| write | `12.55` | `29.50` | Steelsearch faster |
| refresh | `33.87` | `100.56` | Steelsearch faster |

Current full-matrix interpretation:

- The append-only incremental refresh fast path changes the main 1-node result
  from slower-than-OpenSearch to faster-than-OpenSearch for the benchmarked mixed
  workload.
- 3-node Steelsearch is also faster than 3-node OpenSearch in this local matrix,
  but Steelsearch 3-node throughput remains close to Steelsearch 1-node
  throughput. That still means this benchmark does not prove meaningful
  horizontal scaling for Steelsearch; it mostly proves OpenSearch's local 3-node
  setup is substantially slower under this workload.
- Remaining 1-node gaps are facet mean latency, hybrid mean latency, and mixed
  p99 tail latency for several search operations. The next likely optimization
  target is reducing the lock scope of incremental refresh append/commit/reload
  so search p99 does not inherit refresh publication stalls.

## Incremental refresh lock-scope guard follow-up

The first append-only incremental refresh implementation improved mixed
throughput, but search p99 tails still showed refresh publication pressure. A
follow-up moved the incremental append/commit/reload work out of the global
store write lock and publishes the result only if the captured refresh guard is
still valid.

Implementation details:

- `TantivySearchState` and indexed-field metadata are cloneable so refresh can
  prepare an updated search state outside the store write lock.
- `incremental_refresh_in_progress` prevents concurrent refresh requests from
  appending the same pending documents to the same in-memory Tantivy index.
- Concurrent refresh calls wait briefly and re-plan instead of falling back to a
  full rebuild while another incremental append is active.
- Publish still checks the base refreshed sequence number, schema hash,
  append-only guard, and target sequence number. If the guard is broken, refresh
  falls back to a full rebuild from current documents.

Rejected intermediate result:

- Letting concurrent refresh calls fall back to full rebuild while an incremental
  append was active reduced search p99 but regressed refresh mean latency. That
  variant was not retained.

Validation:

- `cargo +nightly check -p os-node --features standalone-runtime`
- `target/search-benchmark-matrix-minilm-knn-incremental-refresh-lock-scope-wait/summary.json`

Throughput summary:

| topology | Steelsearch | OpenSearch | ratio |
|---|---:|---:|---:|
| 1-node | `298.71 ops/s` | `220.01 ops/s` | `1.36x` |
| 3-node | `282.16 ops/s` | `95.73 ops/s` | `2.95x` |

1-node latency summary after lock-scope guard:

| operation | Steelsearch mean | OpenSearch mean | Steelsearch p99 | OpenSearch p99 | status |
|---|---:|---:|---:|---:|---|
| lexical | `6.19ms` | `11.62ms` | `27.04ms` | `30.87ms` | Steelsearch faster |
| ranking | `6.66ms` | `15.10ms` | `28.35ms` | `48.31ms` | Steelsearch faster |
| sort_filter | `6.94ms` | `15.54ms` | `26.56ms` | `50.55ms` | Steelsearch faster |
| nested | `7.79ms` | `12.34ms` | `27.70ms` | `33.37ms` | Steelsearch faster |
| vector | `14.40ms` | `21.69ms` | `43.95ms` | `55.44ms` | Steelsearch faster |
| write | `10.35ms` | `14.60ms` | `29.42ms` | `40.04ms` | Steelsearch faster |
| refresh | `57.90ms` | `68.93ms` | `218.03ms` | `235.18ms` | Steelsearch faster by mean/p99; p95 slightly slower |
| facet | `17.94ms` | `15.43ms` | `51.87ms` | `44.73ms` | remaining 1-node gap |
| hybrid | `20.98ms` | `20.34ms` | `48.61ms` | `55.24ms` | mean slightly slower; p99 faster |

3-node result:

- Steelsearch is faster than OpenSearch for every measured operation and no
  slower metric is reported for the 3-node comparison.
- Steelsearch 3-node throughput is still close to Steelsearch 1-node throughput,
  so this remains weak evidence for horizontal scaling. It mainly confirms that
  the local 3-node OpenSearch setup is much slower under the benchmarked mixed
  workload.

Current remaining pain points:

1. Facet 1-node mean/p50/p95/p99 remains slower than OpenSearch.
2. Hybrid 1-node mean remains slightly slower, though p95/p99 are now faster.
3. Refresh p95 is still slightly slower than OpenSearch despite better mean and
   p99.
4. Steelsearch 3-node does not materially scale over Steelsearch 1-node in this
   benchmark setup.

## Facet string terms fast path

The remaining 1-node facet gap was narrowed by specializing document-backed
terms aggregation for scalar string fields. The benchmark facet request uses two
string keyword terms aggregations (`service`, `category`) plus `range` and
`date_histogram`; the previous document-backed terms path always used the generic
`Value` bucket flow and rebuilt string sort keys for each document.

Implementation:

- `collect_terms_aggregation_from_documents` now uses a scalar string fast path
  when all present field values are strings.
- Missing values are skipped as before.
- Non-string values immediately fall back to the previous generic path, so array,
  bool, numeric, and mixed-value semantics are preserved.

Validation:

- `cargo +nightly check -p os-node --features standalone-runtime`
- `target/search-benchmark-facet-string-fast-path-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-facet-string-fast-path/summary.json`

Focused facet-only result:

| scope | throughput | mean | p95 | p99 |
|---|---:|---:|---:|---:|
| Steelsearch facet-only 1-node | `104.24 ops/s` | `38.34ms` | `92.08ms` | `112.62ms` |

Full mixed throughput summary:

| topology | Steelsearch | OpenSearch | ratio |
|---|---:|---:|---:|
| 1-node | `321.73 ops/s` | `216.69 ops/s` | `1.48x` |
| 3-node | `327.50 ops/s` | `97.48 ops/s` | `3.36x` |

1-node facet/hybrid result after the fast path:

| operation | Steelsearch mean | OpenSearch mean | Steelsearch p99 | OpenSearch p99 | status |
|---|---:|---:|---:|---:|---|
| facet | `15.70ms` | `15.58ms` | `44.50ms` | `47.22ms` | mean nearly tied; p99 faster |
| hybrid | `19.25ms` | `20.10ms` | `43.52ms` | `47.09ms` | Steelsearch faster |

Current remaining pain points:

1. 1-node facet p50/p95 are still slower than OpenSearch, although mean is now
   effectively tied and p99 is faster.
2. 1-node refresh p95/p99 remain variable and can still be slower in a mixed run,
   despite refresh mean being faster.
3. 3-node refresh p99 was `242.82ms` vs OpenSearch `242.35ms` in this run, a
   `1.002x` difference that should be treated as noise unless it repeats.
4. Steelsearch 3-node throughput is now slightly higher than Steelsearch 1-node,
   but this still is not strong horizontal scaling evidence; the benchmark's
   local OpenSearch 3-node setup remains much slower.

## 2026-06-14 - Docker-build idle rerun after scalar aggregation fast paths

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`, query mix `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5`.

Before rerunning, no active `docker build`, BuildKit, Cargo, Rustc, or benchmark containers were observed. Scenarios were run serially so SteelSearch and OpenSearch were not kept up together for the final comparison run.

Changes under test:

- String terms facet fast path from the prior run.
- Date histogram scalar fast path: scalar values now bucket directly; array values still use the distinct-per-document path.
- Range aggregation scalar fast path: scalar numeric values now count matching ranges directly; array and generic JSON paths still use the de-duplicating fallback.

Focused SteelSearch-only facet check:

| Run | Throughput | Facet mean | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: |
| String terms fast path baseline | 104.24 ops/s | 38.34 ms | 92.08 ms | 112.62 ms |
| Scalar agg fast paths | 108.86 ops/s | 36.72 ms | 87.05 ms | 106.99 ms |

Full OpenSearch comparison:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 333.18 ops/s | 220.43 ops/s | 1.51x |
| 3-node | 342.50 ops/s | 98.21 ops/s | 3.49x |

Remaining slower-than-OpenSearch points:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | facet | p50 | 15.39 ms | 12.98 ms | 1.18x |
| 1-node | facet | p95 | 33.09 ms | 29.27 ms | 1.13x |
| 1-node | refresh | p95 | 149.04 ms | 145.95 ms | 1.02x |
| 3-node | none | none | - | - | - |

Interpretation:

- The docker-build-idle rerun supports the hypothesis that earlier poor results were partly environmental or caused by running heavier services together.
- Search-heavy paths are now consistently faster than OpenSearch in mean/p95/p99 except the remaining 1-node facet median/tail gap.
- Refresh is not a search critical path, but its p95 remains close to OpenSearch and should be tracked because refresh can still contend with fresh-search visibility and write-heavy workloads.
- The current highest-priority search pain point is facet p50/p95 on 1-node. The likely remaining cost is per-hit JSON/source aggregation for non-string aggregation shapes rather than global lock scope.

Artifact: `target/search-benchmark-matrix-minilm-knn-facet-scalar-agg-fast-path/summary.json`.

## 2026-06-14 - Facet top-level field lookup fast path

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`.

Change under test:

- Added a prechecked top-level source field accessor for document-backed aggregation hot paths.
- Applied it to document-backed `terms`, `range`, and `date_histogram` aggregations so top-level benchmark fields do not call `field.contains('.')` and split/path logic per document.
- Replaced hot `serde_json::json!` bucket construction in string terms and date histogram document-backed paths with direct `serde_json::Map` construction.
- Semantics are unchanged: dotted fields still use the existing generic source lookup path, and non-string terms still fall back to the generic distinct scalar bucket path.

Focused SteelSearch-only facet check:

| Run | Throughput | Facet mean | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: |
| Scalar agg fast paths | 108.86 ops/s | 36.72 ms | 87.05 ms | 106.99 ms |
| Top-level lookup fast path | 111.01 ops/s | 35.99 ms | 83.03 ms | 96.57 ms |

Full OpenSearch comparison:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 326.65 ops/s | 229.63 ops/s | 1.42x |
| 3-node | 333.96 ops/s | 100.92 ops/s | 3.31x |

1-node search-path comparison highlights:

| Operation | Metric | SteelSearch | OpenSearch | Ratio | Status |
| --- | --- | ---: | ---: | ---: | --- |
| facet | mean | 14.31 ms | 14.67 ms | 0.98x | SteelSearch faster |
| facet | p50 | 14.92 ms | 12.72 ms | 1.17x | remaining gap |
| facet | p95 | 31.60 ms | 28.44 ms | 1.11x | remaining gap |
| facet | p99 | 39.58 ms | 47.07 ms | 0.84x | SteelSearch faster |
| hybrid | mean | 19.67 ms | 19.75 ms | 1.00x | tied/slightly faster |
| vector | p95 | 24.17 ms | 33.67 ms | 0.72x | SteelSearch faster |
| nested | p95 | 16.95 ms | 25.30 ms | 0.67x | SteelSearch faster |

Remaining slower-than-OpenSearch points:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | facet | p50 | 14.92 ms | 12.72 ms | 1.17x |
| 1-node | facet | p95 | 31.60 ms | 28.44 ms | 1.11x |
| 1-node | refresh | p95 | 152.89 ms | 134.45 ms | 1.14x |
| 1-node | refresh | p99 | 277.75 ms | 186.17 ms | 1.49x |
| 3-node | none | none | - | - | - |

Interpretation:

- The focused facet result confirms that per-document source field lookup and bucket construction were measurable search critical-path costs.
- The full mixed run still shows 1-node facet p50/p95 slower than OpenSearch, but mean and p99 are now faster. This suggests the remaining median gap is likely not lock scope; it is more likely repeated per-aggregation source traversal/materialization versus a doc-values style aggregation path.
- Refresh p95/p99 regressed in this run while mean stayed faster than OpenSearch. Treat this as refresh-tail variability rather than a search-path regression until it repeats in refresh-focused runs.
- Next search-focused optimization candidate: fuse simple document-backed facet aggregations into a single document pass, or move benchmarked top-level scalar fields to a native per-field column/doc-values aggregation path instead of repeatedly reading JSON source.

Artifacts:

- `target/search-benchmark-facet-field-lookup-fast-path-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-field-lookup-fast-path/summary.json`

## 2026-06-14 - Rejected attempt: fused single-pass simple facet aggregation

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`, query mix `facet=100`.

Attempted change:

- Added an opportunistic single-pass document-backed aggregation collector for simple `terms`, `date_histogram`, and `range` aggregation maps.
- The goal was to avoid scanning the same `documents` slice once per aggregation in the benchmark facet request.
- Unsupported aggregations would have fallen back to the existing generic path.

Focused SteelSearch-only facet result:

| Run | Throughput | Facet mean | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: |
| Top-level lookup fast path baseline | 111.01 ops/s | 35.99 ms | 83.03 ms | 96.57 ms |
| Fused single-pass attempt | 101.62 ops/s | 39.35 ms | 93.88 ms | 121.24 ms |

Decision:

- The single-pass collector was reverted because it regressed the focused facet benchmark by about 8.5% throughput and worsened p95/p99.
- The likely cause is that enum dispatch, nested collector loops, and losing the specialized scalar string terms path outweighed the benefit of scanning the document slice once.
- This suggests the remaining facet gap should not be addressed by a generic fused collector in this shape.

Next viable direction:

- Keep specialized aggregation kernels per aggregation type.
- If fusing is retried, generate a benchmark-specific typed collector that preserves the string terms fast path and avoids enum dispatch in the inner loop.
- Higher-value direction remains a native column/doc-values style path for top-level scalar fields so `terms`, `range`, and `date_histogram` can aggregate without repeatedly reading JSON source.

Artifact: `target/search-benchmark-facet-single-pass-fast-path-5000/summary.json`.

## 2026-06-14 - Rejected attempt: date histogram normalized interval helper

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`, query mix `facet=100`.

Attempted change:

- Split `date_histogram_bucket` into a normalized-interval helper so document-backed `date_histogram` aggregation could normalize the interval once per aggregation instead of once per value.

Focused SteelSearch-only facet result:

| Run | Throughput | Facet mean | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: |
| Top-level lookup fast path baseline | 111.01 ops/s | 35.99 ms | 83.03 ms | 96.57 ms |
| Normalized interval helper attempt | 104.57 ops/s | 38.20 ms | 89.69 ms | 108.21 ms |

Decision:

- The change was reverted because the focused facet benchmark did not support keeping it.
- The attempted optimization is theoretically small; the benchmark suggests interval normalization is not the current dominant cost, or the run was dominated by other variance.
- Do not spend more time on date interval normalization unless a profiler points there directly.

Current retained facet optimizations:

- Scalar string terms fast path.
- Scalar range/date histogram paths that avoid generic distinct bucket allocation for scalar values.
- Top-level source field lookup precheck for document-backed `terms`, `range`, and `date_histogram`.
- Direct bucket object construction in hot string terms/date histogram document-backed paths.

Current best artifact after retained changes: `target/search-benchmark-matrix-minilm-knn-field-lookup-fast-path/summary.json`.

## 2026-06-14 - Top-level scalar facet cache

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`.

Change under test:

- `StoredDocument` now carries a `top_level_scalar_fields` cache populated at write/replay/recovery time.
- Document-backed facet aggregation hot paths for top-level `terms`, `range`, and `date_histogram` fields now read this cache first and fall back to the existing JSON source lookup for missing, non-scalar, or dotted fields.
- This keeps compatibility semantics while avoiding repeated JSON object lookups for common top-level scalar benchmark fields such as `service`, `category`, timestamp, and numeric range fields.

Focused SteelSearch-only facet check:

| Run | Throughput | Facet mean | Facet p50 | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top-level lookup fast path baseline | 111.01 ops/s | 35.99 ms | 30.62 ms | 83.03 ms | 96.57 ms |
| Top-level scalar cache | 111.39 ops/s | 35.88 ms | 29.39 ms | 83.87 ms | 102.06 ms |

The focused run is mostly neutral: throughput and p50 improved slightly, while p95/p99 were a little worse. The mixed OpenSearch comparison is stronger evidence because it measures the actual benchmark mix.

Full OpenSearch comparison:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 336.52 ops/s | 218.48 ops/s | 1.54x |
| 3-node | 340.36 ops/s | 96.90 ops/s | 3.51x |

1-node facet comparison:

| Metric | SteelSearch | OpenSearch | Ratio | Status |
| --- | ---: | ---: | ---: | --- |
| mean | 14.34 ms | 15.62 ms | 0.92x | SteelSearch faster |
| p50 | 14.79 ms | 13.26 ms | 1.12x | remaining gap |
| p95 | 31.18 ms | 31.75 ms | 0.98x | SteelSearch faster |
| p99 | 41.67 ms | 56.95 ms | 0.73x | SteelSearch faster |

Remaining slower-than-OpenSearch points:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | facet | p50 | 14.79 ms | 13.26 ms | 1.12x |
| 3-node | none | none | - | - | - |

Interpretation:

- The scalar cache meaningfully improves the mixed benchmark posture: previous 1-node facet p95 gap is gone, and refresh p95/p99 were also faster than OpenSearch in this run.
- The only remaining measured OpenSearch advantage is 1-node facet median latency.
- This supports the earlier diagnosis that the important facet pain point is repeated JSON/source access rather than lock scope.
- The retained cache is a pragmatic native-ish column step, but it is still per-document/per-field and not a full doc-values columnar aggregation engine.

Next viable direction:

- If further facet p50 reduction is needed, build a typed per-field doc-values style index keyed by refreshed document id/ordinal, not a generic fused collector.
- Track memory overhead of `top_level_scalar_fields` as corpus size grows, since it duplicates top-level scalar values from `_source`.

Artifacts:

- `target/search-benchmark-facet-top-level-scalar-cache-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-top-level-scalar-cache/summary.json`

## 2026-06-14 - Typed top-level scalar facet cache

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`.

Change under test:

- Extended the retained `top_level_scalar_fields` cache with typed top-level caches:
  - `top_level_string_fields` for keyword terms aggregation hot paths.
  - `top_level_f64_fields` for numeric range aggregation hot paths.
- Document-backed `terms` aggregation now checks the typed string cache first for top-level fields such as `service` and `category`.
- Document-backed `range` aggregation now checks the typed f64 cache first for top-level numeric fields such as `latency` and only falls back to the generic JSON path if a present value is non-numeric.
- Existing `Value` cache and source fallback remain for date histogram, dotted fields, arrays, mixed values, and compatibility cases.

Focused SteelSearch-only facet check:

| Run | Throughput | Facet mean | Facet p50 | Facet p95 | Facet p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top-level scalar cache | 111.39 ops/s | 35.88 ms | 29.39 ms | 83.87 ms | 102.06 ms |
| Typed scalar cache | 112.04 ops/s | 35.67 ms | 29.98 ms | 84.02 ms | 100.52 ms |

Focused result is mildly positive for throughput/mean/p99 and neutral-to-slightly-worse for p50/p95, so the full mixed comparison is the deciding signal.

Full OpenSearch comparison:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 333.71 ops/s | 215.68 ops/s | 1.55x |
| 3-node | 334.84 ops/s | 102.33 ops/s | 3.27x |

1-node facet comparison:

| Metric | SteelSearch | OpenSearch | Ratio | Status |
| --- | ---: | ---: | ---: | --- |
| mean | 13.53 ms | 15.89 ms | 0.85x | SteelSearch faster |
| p50 | 14.05 ms | 13.70 ms | 1.03x | near tie, remaining gap |
| p95 | 29.74 ms | 32.47 ms | 0.92x | SteelSearch faster |
| p99 | 36.98 ms | 51.84 ms | 0.71x | SteelSearch faster |

Remaining slower-than-OpenSearch points:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | facet | p50 | 14.05 ms | 13.70 ms | 1.03x |
| 1-node | refresh | p95 | 156.49 ms | 148.55 ms | 1.05x |
| 1-node | refresh | p99 | 245.23 ms | 186.63 ms | 1.31x |
| 3-node | none | none | - | - | - |

Interpretation:

- The typed cache reduced the remaining 1-node facet median gap from the previous `1.12x` to `1.03x`, while keeping p95/p99 faster than OpenSearch.
- This further supports the diagnosis that facet cost was dominated by source/value handling rather than lock scope.
- The remaining facet p50 delta is now very small and may be benchmark noise or request-distribution sensitive.
- Refresh p95/p99 remains variable between runs. It is not the search critical path, but should remain tracked because mixed workloads can expose refresh tail contention.

Next viable direction:

- For more facet p50 reduction, the next step should be a real refreshed-doc ordinal/doc-values aggregation index rather than adding more per-document maps.
- Before doing that, measure memory overhead from duplicating top-level scalar/string/f64 caches, especially beyond 5k documents.

Artifacts:

- `target/search-benchmark-facet-typed-scalar-cache-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-typed-scalar-cache/summary.json`

## 2026-06-18 - Top-level date millis facet cache

Change applied after the retained typed scalar cache:

- Added `top_level_date_millis_fields: BTreeMap<String, i64>` to `StoredDocument`.
- Document-backed `date_histogram` aggregation now checks the typed top-level date millis cache before reading JSON source for benchmark-style fields such as `event_time`.
- Existing source lookup remains the fallback for dotted fields, arrays, mixed or non-date values, and missing typed cache entries.

Expected effect:

- This removes repeated date parsing/source-value access from the top-level `date_histogram` hot path.
- It is a narrow continuation of the retained typed cache work, not a snapshot/binary compatibility path.
- Any remaining facet median gap should be treated as a real doc-values/columnar aggregation follow-up rather than OpenSearch response-format compatibility work.

## 2026-06-14 - Rejected attempt: refresh request target snapshot

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`.

Attempted change:

- Captured `next_seq_no - 1` at the beginning of each refresh request and used that fixed target throughout the refresh loop.
- Intended effect: if refresh was busy, avoid extending the waiting request to include writes that arrived after the request began.

Focused SteelSearch-only refresh result:

| Run | Throughput | Refresh mean | Refresh p95 | Refresh p99 |
| --- | ---: | ---: | ---: | ---: |
| Refresh target snapshot attempt | 785.15 ops/s | 5.09 ms | 6.42 ms | 7.97 ms |

Full mixed OpenSearch comparison with the attempted change:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 328.51 ops/s | 219.31 ops/s | 1.50x |
| 3-node | 340.96 ops/s | 101.62 ops/s | 3.36x |

Observed 1-node regressions versus the retained typed scalar cache run:

| Metric | Typed scalar cache retained run | Target snapshot attempt | Decision |
| --- | ---: | ---: | --- |
| throughput | 333.71 ops/s | 328.51 ops/s | worse |
| facet p50 ratio vs OpenSearch | 1.03x | 1.10x | worse |
| facet p95 ratio vs OpenSearch | 0.92x | 1.04x | worse |
| hybrid mean ratio vs OpenSearch | 0.93x | 1.00x | worse/noise |
| refresh p99 ratio vs OpenSearch | 1.31x | 0.88x | better |

Decision:

- The change was reverted. It improved refresh p99 in this run but regressed total throughput and reintroduced search-path comparison gaps.
- Refresh target selection is not the right local fix unless paired with a broader NRT publication model and stronger correctness/visibility tests.
- Current retained state remains the typed scalar facet cache state.

Current conclusion:

- Search critical paths remain the optimization priority and are materially faster than OpenSearch except a near-tie facet median in the best retained run.
- Refresh tail remains variable in mixed workloads. Further refresh work should be a structural NRT snapshot/doc-versioning task, not another small lock-scope tweak.

Artifacts:

- `target/search-benchmark-refresh-target-snapshot-5000/summary.json`
- `target/search-benchmark-matrix-minilm-knn-refresh-target-snapshot/summary.json`

## 2026-06-14 - Final current-state benchmark after reverting refresh target snapshot

Benchmark profile: `minilm-knn`, corpus size `5000`, duration `30s`, clients `4`, query mix `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5`.

Before the run, no active `docker build`, BuildKit, Cargo, Rustc, or benchmark containers were observed. The current worktree compiled with:

- `cargo +nightly check -p os-node --features standalone-runtime`

Current retained state:

- Native HTTP/server path and native Tantivy search path.
- Preserved refreshed search snapshot across `refresh=false` writes.
- Append-only incremental refresh with guarded publish.
- Vector source elision and vector scoring loop optimization.
- Native nested ordinal/page fast path.
- Facet scalar fast paths and top-level scalar/string/f64 caches.
- Rejected refresh target snapshot patch is not retained.

Full OpenSearch comparison:

| Topology | SteelSearch throughput | OpenSearch throughput | Ratio |
| --- | ---: | ---: | ---: |
| 1-node | 336.39 ops/s | 223.27 ops/s | 1.51x |
| 3-node | 336.24 ops/s | 98.01 ops/s | 3.43x |

1-node operation comparison summary:

| Operation | SteelSearch mean | OpenSearch mean | SteelSearch p95 | OpenSearch p95 | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| facet | 13.61 ms | 15.24 ms | 30.05 ms | 30.90 ms | mean/p95/p99 faster; p50 still slower |
| hybrid | 19.47 ms | 20.55 ms | 30.45 ms | 36.07 ms | SteelSearch faster |
| lexical | 5.18 ms | 11.62 ms | 13.90 ms | 22.14 ms | SteelSearch faster |
| nested | 6.45 ms | 12.92 ms | 14.96 ms | 23.87 ms | SteelSearch faster |
| ranking | 5.64 ms | 15.06 ms | 14.47 ms | 28.12 ms | SteelSearch faster |
| refresh | 61.07 ms | 64.42 ms | 162.22 ms | 131.56 ms | mean faster; p95/p99 slower |
| sort_filter | 6.35 ms | 15.17 ms | 16.25 ms | 28.34 ms | SteelSearch faster |
| vector | 12.81 ms | 21.89 ms | 23.48 ms | 39.65 ms | SteelSearch faster |
| write | 8.65 ms | 14.28 ms | 17.69 ms | 23.59 ms | SteelSearch faster |

Remaining slower-than-OpenSearch points:

| Topology | Operation | Metric | SteelSearch | OpenSearch | Ratio |
| --- | --- | --- | ---: | ---: | ---: |
| 1-node | facet | p50 | 13.94 ms | 13.14 ms | 1.06x |
| 1-node | refresh | p95 | 162.22 ms | 131.56 ms | 1.23x |
| 1-node | refresh | p99 | 233.96 ms | 221.77 ms | 1.05x |
| 3-node | none | none | - | - | - |

Interpretation:

- The current retained state meets the search-focused goal: every measured 1-node search operation is faster than OpenSearch by mean/p95/p99, except the facet median remains slightly slower.
- The facet p50 gap is now small (`1.06x`) and should be treated as a doc-values/columnar aggregation follow-up rather than another local source-map tweak.
- Refresh p95/p99 remains the only material mixed-workload pain point. Prior local refresh tweaks improved some tails but harmed search metrics or total throughput, so the next refresh work should be an NRT snapshot/doc-versioning design rather than lock-scope tuning.
- 3-node results show SteelSearch faster on every measured metric, but local 3-node throughput is still close to 1-node throughput. Treat this as OpenSearch-local-cluster comparison evidence, not proof of SteelSearch horizontal scaling.

Artifacts:

- `target/search-benchmark-matrix-minilm-knn-final-current/summary.json`

## 2026-07-12 - Refresh runtime-state mark narrowing smoke

Benchmark profile: SteelSearch-only smoke, corpus size `1000`, duration `10s`,
clients `4`, query mix matching the retained mixed search benchmark.

Change under test:

- `_refresh` now updates the standalone compatibility `documents_state`
  visibility marker only for documents that were not already refreshed.
- Previously, every refresh route cloned and rewrote every runtime document for
  the matched index set even when the document was already visible.
- Native engine refresh semantics and REST shard-count surfaces are unchanged.

Smoke result:

| Metric | Before | After | Ratio |
| --- | ---: | ---: | ---: |
| Overall throughput | 79.65 ops/s | 84.16 ops/s | 1.06x |
| Refresh mean latency | 251.73 ms | 128.47 ms | 0.51x |
| Refresh p50 latency | 213.11 ms | 105.77 ms | 0.50x |
| Refresh p95 latency | 520.86 ms | 246.13 ms | 0.47x |
| Refresh p99 latency | 597.50 ms | 323.37 ms | 0.54x |

Interpretation:

- The smoke run confirms the compatibility-state rewrite was a real refresh
  tail contributor.
- This does not replace a full OpenSearch comparison matrix. It is a targeted
  regression guard and bottleneck confirmation for the retained refresh-tail
  workstream.

Artifacts:

- `target/search-benchmark-current-smoke-1000/summary.json`
- `target/search-benchmark-current-smoke-1000-after-refresh-mark/summary.json`

Follow-up range-scan narrowing:

- Targeted `_refresh` now walks only the `documents_state` key range for each
  matched index prefix instead of scanning unrelated index keys and filtering
  them out.
- The route still rewrites only unrefreshed records, so REST behavior and
  visibility semantics are unchanged.

Smoke comparison:

| Metric | Before mark narrowing | After mark narrowing | After prefix range scan |
| --- | ---: | ---: | ---: |
| Overall throughput | 79.65 ops/s | 84.16 ops/s | 94.37 ops/s |
| Refresh mean latency | 251.73 ms | 128.47 ms | 166.27 ms |
| Refresh p50 latency | 213.11 ms | 105.77 ms | 172.96 ms |
| Refresh p95 latency | 520.86 ms | 246.13 ms | 300.04 ms |
| Refresh p99 latency | 597.50 ms | 323.37 ms | 319.83 ms |

Interpretation:

- The prefix range scan improved total smoke throughput to `1.18x` versus the
  original baseline and `1.12x` versus mark narrowing alone.
- Refresh p99 stayed slightly better than the mark-narrowing run, but mean,
  p50, and p95 regressed in this short smoke. Treat the range scan as a
  correctness-preserving scope reduction, not as a proven refresh-tail fix by
  itself.
- The next refresh work should still be measured with a full matrix or a longer
  refresh-heavy profile before promoting it as a retained bottleneck fix.

Artifact:

- `target/search-benchmark-current-smoke-1000-after-refresh-range/summary.json`

## 2026-07-12 - Suggest source-map clone cleanup

The standalone search route previously cloned the full compatibility
`documents_state` map when rendering `suggest` responses. That clone happened
both on the source-backed route and on native search responses that needed
route-layer suggest post-processing.

Current behavior:

- `suggest` response construction now reads the existing `DocumentMap` by
  reference while the relevant source or PIT snapshot is already available.
- Native search suggest post-processing no longer clones the full
  `documents_state` map before building the suggest section.
- Search response semantics are unchanged; this is a materialization cleanup
  for suggest-bearing requests, not a general search throughput claim.

## 2026-07-12 - Source fallback aggregation materialization cleanup

The source-backed search fallback previously built the extra
`aggregation_context_hits` vector for every fallback search request, even when
the request did not ask for aggregations. That duplicated `_source` values
before query evaluation and added avoidable work to non-aggregation fallback
requests.

Current behavior:

- `aggregation_context_hits` is populated only when the request contains
  `aggs` or `aggregations`.
- The source-backed fallback now passes either OpenSearch aggregation key
  spelling into the aggregation builder.
- A regression test covers the `aggregations` alias so it does not silently
  produce a hits-only response on fallback paths.
