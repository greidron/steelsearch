# Search and k-NN benchmark report

## Run configuration

- Generated at epoch seconds: `1781400156`
- Corpus size: `1000` documents
- Vector dimension: `384`
- Duration per scenario: `8.0` seconds
- Clients: `4`
- Query mix: `write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,vector=15,hybrid=10,refresh=5`

## Scenario summary

| Scenario | Throughput ops/s | Error rate |
| --- | ---: | ---: |
| Steelsearch 1-node | 112.19 | 0.0000 |

## Steelsearch 1-node

- Base URL: `http://127.0.0.1:44715`
- Manifest: n/a

| Operation | Success | Errors | p50 ms | p95 ms | p99 ms | Mean ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| facet | 134 | 0 | 42.46 | 56.89 | 69.59 | 42.22 |
| hybrid | 54 | 0 | 36.94 | 47.65 | 57.68 | 37.19 |
| lexical | 127 | 0 | 33.30 | 46.24 | 55.42 | 34.17 |
| nested | 78 | 0 | 49.22 | 69.40 | 88.47 | 48.72 |
| ranking | 127 | 0 | 34.01 | 47.25 | 49.07 | 34.38 |
| refresh | 39 | 0 | 9.52 | 17.64 | 18.31 | 9.77 |
| sort_filter | 89 | 0 | 34.87 | 46.42 | 53.41 | 35.22 |
| vector | 128 | 0 | 51.12 | 70.15 | 78.83 | 52.95 |
| write | 125 | 0 | 12.92 | 20.92 | 28.35 | 12.68 |

## Steelsearch vs OpenSearch by topology

## Workload coverage

- `lexical`: warmed match/term + filter search.
- `ranking`: multi-match, phrase-sensitive ranking-oriented search.
- `facet`: query + `terms`, `date_histogram`, and `range` aggregations.
- `sort_filter`: filtered search with explicit sort keys.
- `vector`: k-NN query against the vector field.
- `hybrid`: lexical + k-NN + filter combined query.
