# Vector Search And ML APIs

## Milestone Gate

- Primary gate: `Phase A` for the explicitly supported standalone replacement
  subset.
- Later extension: `Phase B` for interop validation where Steelsearch must
  compare behavior against Java OpenSearch plugin surfaces.
- Final extension: `Phase C` only if same-cluster vector/ML behavior requires
  peer-node compatibility rather than standalone API parity.

## Phase A Vector/ML Reading Rule

Read the current Phase A vector/ML surface along four separate axes:

- mapping declaration subset
  - what `knn_vector` field shapes can be parsed, persisted, and queried later
- query/runtime subset
  - what `knn` and hybrid request forms can execute with stable bounded
    semantics
- plugin-shaped operational routes
  - what `/_plugins/_knn/*` and `/_plugins/_ml/*` surfaces are present as
    bounded standalone APIs
- production/runtime depth
  - cache enforcement, task lifecycle, authorization, transport parity, and
    model runtime isolation

Do not collapse these axes into a single `Implemented` claim.

Phase A replacement only requires:

- bounded `knn_vector` mapping support for the documented subset;
- bounded `knn` / hybrid search support for the documented subset;
- explicit fail-closed behavior outside that subset;
- enough model-serving/vector-search surface to exercise the documented
  standalone development flows.

Phase A does not by itself claim:

- OpenSearch k-NN plugin engine parity;
- full ML Commons task/runtime parity;
- same-cluster Java plugin compatibility;
- production-grade vector/ML isolation or authorization depth.

## k-NN And Vector Indexing

| Surface | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `knn_vector` mapping | Declares vector fields and engine/method metadata for k-NN search. | Implemented for the current Rust-native vector/search extension subset. | Partial |
| `knn` query | Executes vector nearest-neighbor search, optionally with filters and method parameters. | Implemented for the supported subset, including selected filter and hybrid flows. | Partial |
| Hybrid lexical + vector search | Combines BM25-like lexical behavior with vector retrieval. | Supported in the current development surface for selected flows. | Partial |

### `knn_vector` supported-subset contract

Current Phase A mapping contract is bounded to:

- top-level field type:
  - `type = knn_vector`
- required dimensional declaration:
  - `dimension`
- bounded method/engine metadata that Steelsearch explicitly documents for its
  Rust-native path
- compatibility with the documented vector query subset only

Current fail-closed reading rule:

- unsupported engine families
- unsupported score spaces
- byte/binary vector encodings
- nested/vector-runtime combinations outside the documented subset

must stay explicit reject paths rather than being read as partial success.

### `knn` / hybrid supported-subset contract

Current Phase A query/runtime contract is bounded to:

- `knn` query with the documented vector field subset
- selected filter coupling that Steelsearch documents as supported
- hybrid lexical + vector flows where the lexical side stays inside the current
  Phase A search subset
- stable response reading through:
  - hit presence
  - bounded total hits
  - documented vector/hybrid request acceptance

Current non-claims:

- exact OpenSearch score fusion parity
- exact tie-breaking parity across lexical/vector blends
- every OpenSearch method parameter or rescoring mode
- nested/geo/scripted vector ranking parity

Current fail-closed reading rule:

- unsupported `knn` method parameters
- unsupported hybrid composition shapes
- unsupported vector query/runtime combinations

must return explicit reject behavior rather than silently degrading into lexical
search or opaque fallback ranking.

Major remaining k-NN gaps relative to OpenSearch:

- native engine parity and broader score-space parity;
- byte/binary vector support;
- nested semantics parity;
- exact ranking parity for all OpenSearch k-NN modes;
- full method-parameter compatibility;
- stronger cache and native-memory enforcement;
- transport action parity for the k-NN plugin.

## k-NN Plugin Routes

Current docs and source inventory show Steelsearch has partial OpenSearch-shaped
coverage for routes under `/_plugins/_knn`.

Representative route families:

- stats;
- warmup / clear-cache;
- bounded `knn` / hybrid runtime search through the main `_search` path.

Current runtime-connected evidence:

- `SteelNode::handle_rest_request(...)` now serves:
  - `PUT /{index}` with `knn_vector` mappings in the bounded subset
  - `POST /{index}/_search` for bounded `knn` and hybrid (`bool.must`) flows
  - `GET /_plugins/_knn/stats`
  - `POST /_plugins/_knn/warmup/{index}`
  - `POST /_plugins/_knn/clear_cache/{index}`
- a workspace-visible main-side test now drives those routes through the actual
  runtime path and checks:
  - `knn` hit ordering
  - hybrid hit ordering
  - unsupported parameter fail-closed
  - warmup/stats/clear-cache bounded shapes

Current compare note:

- local `vector-ml` acceptance scope now exits cleanly;
- when the local OpenSearch target lacks the k-NN plugin surface
  (`index.knn` / `knn_vector` parsing), vector compare cases are recorded as
  explicit degraded-source skips rather than Steelsearch mismatches.
- warmup;
- clear cache;
- model get/delete/search/train.

These are represented in Steelsearch, but not yet with full OpenSearch
transport/runtime parity.

## ML Commons

| Surface | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Model groups and registration | Registers model metadata and grouping. | Development subset exists. | Partial |
| Deploy / undeploy | Controls model runtime availability. | Development subset exists. | Partial |
| Predict / embedding flow | Uses ML model output for vector workflows. | Development subset exists and is usable in Steelsearch-native flows. | Partial |
| Model search and rerank | Operational and query-time model use. | Partial implementation exists. | Partial |
| Task lifecycle | Tracks asynchronous ML work. | Full OpenSearch task lifecycle parity is not present. | Planned |
| Connectors and authz boundaries | External model/service integration and access control. | Not production-grade today. | Planned |

## Production Boundary

The current vector and ML surface is useful for development replacement,
especially for:

- vector field ingestion;
- k-NN search;
- selected model-serving-to-vector-search flows.

It is not yet sufficient for production replacement because it still lacks:

- complete plugin transport behavior;
- complete task/runtime lifecycle parity;
- production isolation and authorization;
- broader engine/runtime support;
- release-grade performance and memory evidence.
