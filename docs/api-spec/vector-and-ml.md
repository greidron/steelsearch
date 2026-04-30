# Vector Search And ML APIs

## Milestone Gate

- Primary gate: `Phase A` for the required standalone vector/ML replacement
  surface owned by the `vector-ml` profile.
- Later extension: `Phase B` for interop validation where Steelsearch must
  compare behavior against Java OpenSearch plugin surfaces.
- Final extension: `Phase C` only if same-cluster vector/ML behavior requires
  peer-node compatibility rather than standalone API parity.

## Phase A Vector/ML Reading Rule

Read the current Phase A vector/ML surface along four separate axes:

- mapping declaration contract
  - what `knn_vector` field shapes can be parsed, persisted, and queried later
- query/runtime contract
  - what `knn` and hybrid request forms can execute with stable standalone
    semantics
- plugin-shaped operational routes
  - what `/_plugins/_knn/*` and `/_plugins/_ml/*` surfaces are present as
    bounded standalone APIs
- production/runtime depth
  - cache enforcement, task lifecycle, authorization, transport parity, and
    model runtime isolation

Do not collapse these axes into a single `Implemented` claim.

Phase A-1 replacement now requires and validates:

- bounded `knn_vector` mapping support for the documented subset;
- bounded `knn` / hybrid search support for the documented subset;
- explicit fail-closed behavior outside that subset;
- enough model-serving/vector-search surface to exercise the documented
  standalone operator flows.

Phase A does not by itself claim:

- OpenSearch k-NN plugin engine parity;
- full ML Commons task/runtime parity;
- same-cluster Java plugin compatibility;
- production-grade vector/ML isolation or authorization depth.

## k-NN And Vector Indexing

| Surface | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| `knn_vector` mapping | Declares vector fields and engine/method metadata for k-NN search. | Live standalone route family with strict compare on the canonical k-NN-capable OpenSearch profile. | Partial |
| `knn` query | Executes vector nearest-neighbor search, optionally with filters and method parameters. | Live standalone route family with strict compare for the documented happy-path and error-envelope contract. | Partial |
| Hybrid lexical + vector search | Combines BM25-like lexical behavior with vector retrieval. | Live standalone route family with strict compare for the documented lexical/vector composition and error handling. | Partial |

### `knn_vector` supported-subset contract

Current standalone mapping contract is:

- top-level field type:
  - `type = knn_vector`
- required dimensional declaration:
  - `dimension`
- bounded option/readback subset:
  - `data_type = float`
  - `mode = in_memory`
  - `compression_level`
  - `doc_values`
  - `store`
  - `method.name = hnsw`
  - `method.engine = lucene`
- compatibility with the documented vector query subset only

Current strict-profile shared subset note:

- the canonical OpenSearch strict fixture excludes field-level `_meta` on
  `knn_vector`, because the current Docker-backed OpenSearch source target
  rejects that mapping parameter even though Steelsearch readback preserves it
  on its own live route tests.

Current fail-closed reading rule:

- unsupported engine families
- unsupported score spaces
- byte/binary vector encodings
- nested/vector-runtime combinations outside the documented subset

must stay explicit reject paths rather than being read as partial success.

### `knn` / hybrid supported-subset contract

Current standalone query/runtime contract is:

- `knn` query with the documented vector field subset
- selected filter coupling inside the `knn` field object
- hybrid lexical + vector flows where the lexical side stays inside the current
  Phase A search subset, including bounded `bool.should` + `minimum_should_match`
  score/ranking composition
- stable response reading through:
  - hit presence
  - bounded total hits
  - documented vector/hybrid request acceptance
  - bounded `ignore_unmapped` empty-hit behavior
  - bounded `expand_nested` acceptance
  - bounded radial search via `max_distance` / `min_score`
  - bounded `method_parameters` numeric acceptance on the Steelsearch live route

Current strict-profile shared subset note:

- the canonical OpenSearch strict fixture excludes `method_parameters` from
  vector happy-path parity, because the current Docker-backed OpenSearch source
  target rejects that request shape for the chosen `lucene`/`hnsw` mapping.
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

Representative live route families:

- stats;
- warmup / clear-cache;
- bounded model train/get/delete/search;
- bounded `knn` / hybrid runtime search through the main `_search` path.

Current runtime-connected evidence:

- `SteelNode::handle_rest_request(...)` now serves:
  - `PUT /{index}` with `knn_vector` mappings in the documented standalone contract
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
  - bounded model train/get/delete/search shapes

Current compare note:

- local `vector-ml` acceptance scope now uses a Docker-backed OpenSearch source
  target with the `opensearch-knn` plugin surface enabled;
- vector compare no longer degrades into source-side skip on the canonical
  `vector-ml` profile;
- the canonical `vector-search-compat` and Steelsearch-only
  `ml-model-surface-compat` runners now both clean-pass under
  `--scope vector-ml`;
- the common baseline remains non-vector and must not be used as substitute
  evidence for strict vector parity.

## ML Commons

| Surface | OpenSearch meaning | Steelsearch behavior | Status |
| --- | --- | --- | --- |
| Model registration | Registers bounded model metadata. | `POST /_plugins/_ml/models/_register` is live and covered by the Steelsearch-only strict runner owned by `vector-ml`. | Partial |
| Deploy / undeploy | Controls model runtime availability. | `POST /_plugins/_ml/models/{id}/_deploy|_undeploy` is live and covered by the Steelsearch-only strict runner owned by `vector-ml`. | Partial |
| Predict / embedding flow | Uses ML model output for vector workflows. | `POST /_plugins/_ml/models/{id}/_predict` is live and covered by the Steelsearch-only strict runner owned by `vector-ml`. | Partial |
| Model get / search | Operational model lookup. | `GET /_plugins/_ml/models/{id}` and `POST /_plugins/_ml/models/_search` are live and covered by the Steelsearch-only strict runner owned by `vector-ml`. | Partial |
| Model groups, tasks, connectors, authz boundaries | Broader ML Commons lifecycle and external integration. | Not part of the current Phase A-1 claimed surface. | Planned |

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
