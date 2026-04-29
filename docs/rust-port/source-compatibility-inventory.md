# Source Compatibility Inventory

This inventory fixes the OpenSearch source surface that Steelsearch will use for
the replacement compatibility matrix. It is intentionally source-derived: later
classification work should mark each item as implemented, forwarded, stubbed,
planned, or out-of-scope without changing the source baseline.

## Source Baseline

- OpenSearch source: `/home/ubuntu/OpenSearch`
- OpenSearch commit: `f991609d190d`
- k-NN source: `/home/ubuntu/k-NN`
- k-NN commit: `86ad5668acdd`
- Inventory method: source-derived counts plus generated TSV inventories from
  pinned OpenSearch and k-NN commits.
- Count refresh script: `tools/source-compatibility-inventory.sh`
- Matrix refresh script: `tools/source-compatibility-matrix.sh`

Generated machine-readable artifacts:

- `docs/rust-port/generated/source-rest-routes.tsv`
- `docs/rust-port/generated/source-transport-actions.tsv`
- `docs/rust-port/generated/source-search-registrations.tsv`
- `docs/rust-port/generated/source-node-runtime-components.tsv`
- `docs/rust-port/generated/source-compatibility-matrix.tsv`

## Core Action And REST Surface

Source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/action/ActionModule.java`

- Transport action registrations: 148 `actions.register(...)` call sites.
- Core REST handler registrations: 167 `registerHandler.accept(...)` call sites.
- Plugin extension points:
  - `ActionPlugin.getActions()` is folded into the action registry.
  - `ActionPlugin.getRestHandlers(...)` is folded into the REST controller.
- Important action groups present in the source inventory:
  - cluster/node/task administration
  - repository and snapshot operations
  - index lifecycle and mapping operations
  - document CRUD, bulk, mget, term vectors
  - search, scroll, msearch, explain, PIT
  - scripts, ingest pipelines, search pipelines
  - data streams, views, persistent tasks
  - retention leases, dangling indices, remote store, decommissioning

## Search Registration Surface

Source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/search/SearchModule.java`

- Query registrations: 49 `registerQuery(...)` call sites.
- Aggregation registrations: 40 `registerAggregation(...)` call sites.
- Pipeline aggregation registrations: 16 `registerPipelineAggregation(...)`
  call sites.
- Suggester registrations: 4 `registerSuggester(...)` call sites.
- Score function registrations: 7 `registerScoreFunction(...)` call sites.
- Fetch sub-phase registrations: 11 `registerFetchSubPhase(...)` call sites.
- Plugin extension points:
  - `SearchPlugin.getQueries()`
  - `SearchPlugin.getAggregations()`
  - `SearchPlugin.getPipelineAggregations()`
  - `SearchPlugin.getSuggesters()`
  - `SearchPlugin.getRescorers()`
  - `SearchPlugin.getScoreFunctions()`
  - `SearchPlugin.getMovingAverageModels()`
  - `SearchPlugin.getFetchSubPhases(...)`
  - `SearchPlugin.getSearchExts()`
  - query phase searcher and query collector context specs

## Cluster State Surface

Source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/ClusterModule.java`

- Cluster custom registrations: 5 `registerClusterCustom(...)` call sites.
- Metadata custom registrations: 14 `registerMetadataCustom(...)` call sites.
- Named x-content registrations mirror the metadata custom types.
- Inventory includes customs for snapshots, restore state, repositories,
  ingest metadata, search pipeline metadata, script metadata, index graveyard,
  persistent tasks, component templates, composable templates, data streams,
  views, weighted routing, decommission attributes, and workload groups.

## Mapper Surface

Source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/indices/IndicesModule.java`

- Built-in field mapper registrations: 24 `mappers.put(...)` call sites.
- Built-in metadata mapper registrations: 11 `builtInMetadataMappers.put(...)`
  call sites.
- Plugin extension points:
  - `MapperPlugin.getMappers()`
  - `MapperPlugin.getMetadataMappers()`
- Notable built-in mapper families include numeric, range, boolean, binary,
  date, ip, text, keyword, object, nested, completion, field alias, geo point,
  flat object, constant keyword, derived, wildcard, star tree, semantic version,
  and context-aware grouping.

## Ingest, Script, And Repository Surface

Ingest source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/ingest/IngestService.java`

- Processor registry is assembled from `IngestPlugin.getProcessors(...)`.
- System processor registry is assembled from
  `IngestPlugin.getSystemIngestProcessors(...)`.
- Duplicate processor names are rejected during registration.

Script source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/script/ScriptModule.java`

- Script contexts are assembled from `ScriptPlugin.getContexts()`.
- Script engines are assembled from `ScriptPlugin.getScriptEngine(...)`.
- Duplicate context names and engine types are rejected during registration.

Repository source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/repositories/RepositoriesModule.java`

- Built-in repository factories include filesystem repository types.
- Repository plugins contribute public factories via
  `RepositoryPlugin.getRepositories(...)`.
- Repository plugins contribute internal factories via
  `RepositoryPlugin.getInternalRepositories(...)`.
- Duplicate public/internal repository type names are rejected during
  registration.

## k-NN Plugin Surface

Source: `/home/ubuntu/k-NN/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java`

- Plugin shape: one OpenSearch plugin class implements action, mapper, search,
  script, engine, codec, and lifecycle-style extension points.
- Mapper registration:
  - `knn_vector` via `MapperPlugin.getMappers()`.
- Query registration:
  - `knn` query through the search plugin query extension point.
- Transport actions:
  - 12 `new ActionHandler<>(...)` registrations.
  - Includes stats, warmup, model metadata update, training job routing, get
    model, delete model, train model, model cache removal, model search,
    model graveyard update, and cache clear.
- REST routes:
  - 12 `new Route(...)` registrations across 7 REST handler classes.
  - Includes stats, warmup, model get/delete/search/train, and cache clear.
- Runtime components:
  - model DAO and metadata handling
  - model cache and cache rebuild
  - training runner and model index writer
  - circuit breaker service
  - query builder setup
  - k-NN script engine
  - codec service integration

## Matrix Build Notes

- `source-compatibility-matrix.tsv` now provides one generated row per REST
  route, transport action, search registration, and node runtime component.
- Mapper, metadata custom, ingest processor, script engine/context, repository
  type, and plugin-provided extension inventories still need their own
  machine-readable extraction before the matrix can claim full source coverage.
- Data-node binary compatibility is not part of the first classification pass.
  Rows that depend on Lucene segment or JVM transport compatibility should be
  marked out-of-scope for the first standalone Steelsearch milestone and moved
  to the optional Java data-node compatibility track.
- Migration-specific APIs should be tracked separately from native Steelsearch
  shard replication and recovery APIs.
