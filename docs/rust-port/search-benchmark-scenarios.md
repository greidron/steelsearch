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

## Default benchmark shape

The matrix runner defaults to production-oriented values:

- corpus size: `5000`
- vector dimension: `16`
- duration per scenario: `30s`
- clients: `4`
- shards: `3`
- replicas: `1` where topology permits
- query mix:
  `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,vector=15,hybrid=10,refresh=5`

For a faster validation pass, override the corpus size and duration on the
command line.

## Tooling

Primary entry points:

- [run-http-load-baseline.py](/home/ubuntu/steelsearch/tools/run-http-load-baseline.py)
- [run-opensearch-cluster-dev.sh](/home/ubuntu/steelsearch/tools/run-opensearch-cluster-dev.sh)
- [run-steelsearch-cluster-dev.sh](/home/ubuntu/steelsearch/tools/run-steelsearch-cluster-dev.sh)
- [run-search-benchmark-matrix.py](/home/ubuntu/steelsearch/tools/run-search-benchmark-matrix.py)

## Running the matrix

Quick benchmark pass:

```bash
python3 tools/run-search-benchmark-matrix.py \
  --output-dir target/search-benchmark-matrix \
  --corpus-size 1500 \
  --duration-seconds 8 \
  --clients 4
```

Heavier benchmark pass:

```bash
python3 tools/run-search-benchmark-matrix.py \
  --output-dir target/search-benchmark-matrix \
  --corpus-size 5000 \
  --duration-seconds 30 \
  --clients 4
```

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

The report contains:

- scenario-level throughput and error rate
- per-operation p50/p95/p99 latency tables
- single-node and three-node Steelsearch-vs-OpenSearch comparisons
- explicit workload coverage for lexical, ranking, facet, sorted, vector, and
  hybrid search
