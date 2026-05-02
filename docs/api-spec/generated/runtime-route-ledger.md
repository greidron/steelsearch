# Runtime Route Ledger

This file records runtime-backed classification for the `planned` and `stubbed` REST inventory in `route-evidence-matrix.md`.

Base URL: `http://127.0.0.1:19200`

## Summary

| runtime_status | count |
| --- | ---: |
| implemented-read | 203 |
| requires-stateful-probe | 168 |

## By family

| family | implemented-read | missing-route | requires-stateful-probe | unprobeable-expression |
| --- | ---: | ---: | ---: | ---: |
| document-and-bulk | 12 | 0 | 29 | 0 |
| index-and-metadata | 54 | 0 | 64 | 0 |
| misc | 9 | 0 | 4 | 0 |
| root-cluster-node | 92 | 0 | 35 | 0 |
| search | 22 | 0 | 26 | 0 |
| snapshot-migration-interop | 7 | 0 | 5 | 0 |
| vector-and-ml | 7 | 0 | 5 | 0 |

## Missing safe read/head routes

| family | method | path | concrete_path | previous_status |
| --- | --- | --- | --- | --- |
