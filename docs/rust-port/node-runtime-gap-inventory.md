# Node Runtime And Configuration Gap Inventory

This document scopes the remaining runtime and configuration gap between the
current `steelsearch` daemon and the local OpenSearch `Node` baseline. It is a
planning artifact for the backlog item `Close node runtime and configuration
gaps versus OpenSearch`.

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document is primarily about the first two profiles. For the latter two,
node-runtime concerns overlap with transport, coordination, publication, and
recovery inventories that are tracked separately.

Source anchors:

- OpenSearch runtime wiring:
  - `server/src/main/java/org/opensearch/node/Node.java`
  - generated inventory:
    [`docs/rust-port/generated/source-node-runtime-components.tsv`](/home/ubuntu/steelsearch/docs/rust-port/generated/source-node-runtime-components.tsv)
- Steelsearch daemon entrypoint:
  - [`crates/os-node/src/main.rs`](/home/ubuntu/steelsearch/crates/os-node/src/main.rs)
- Steelsearch architecture/profile docs:
  - [`docs/rust-port/architecture.md`](/home/ubuntu/steelsearch/docs/rust-port/architecture.md)
  - [`docs/rust-port/development-replacement-profile.md`](/home/ubuntu/steelsearch/docs/rust-port/development-replacement-profile.md)
  - [`docs/rust-port/source-compatibility-matrix.md`](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md)

## Current Steelsearch Runtime Shape

The current daemon is intentionally small:

- parses a narrow set of daemon args/env vars;
- binds a REST listener;
- initializes a development cluster view and production-membership manifest;
- registers development/default compatibility endpoints;
- starts REST service and blocks until shutdown;
- explicitly warns that production security and multi-node runtime are not
  complete.

This matches the documented project stage: a development replacement daemon,
not a production-equivalent OpenSearch node.

## Current Evidence

The repository already proves a meaningful node-runtime baseline:

- `steelsearch` starts a working REST daemon with persisted local state;
- development and compatibility routes can be registered and served
  coherently;
- readiness reporting exists;
- selected multi-node Steelsearch-native scenarios are exercised elsewhere in
  the repo;
- production claims are intentionally gated rather than silently implied.

That evidence is enough to support development replacement work. It is not yet
enough to claim production-equivalent node lifecycle behavior for
`standalone`, let alone `secure standalone` or mixed-cluster profiles.

## Replacement Blockers

The runtime blockers are not route-list problems. They are node-lifecycle
problems:

- startup is not yet guarded by the same class of concrete preflight checks as
  OpenSearch `Node`;
- runtime controls such as task tracking, scheduling, accounting, and
  background services are still partial or absent;
- module/plugin registration remains monolithic relative to OpenSearch runtime
  composition;
- config and identity presentation still needs a stricter accepted/ignored/
  rejected contract;
- authoritative restart-safe behavior still depends on durability work tracked
  in the gateway and metadata persistence inventories.

The checklist that later failure-path tests should derive from is tracked in
[startup-preflight-checklist.md](/home/ubuntu/steelsearch/docs/rust-port/startup-preflight-checklist.md).

## OpenSearch Node Surface Still Missing

The local OpenSearch `Node` wiring inventory shows runtime subsystems that are
not yet present as authoritative Steelsearch equivalents. Representative
examples from the generated inventory:

- plugin/module loading:
  - `PluginsService`
  - `ScriptModule`
  - `AnalysisModule`
  - `ClusterModule`
  - `IndicesModule`
  - `SearchModule`
  - `GatewayModule`
  - `TelemetryModule`
- cluster/runtime services:
  - `ClusterService`
  - `BatchedRerouteService`
  - `MetaStateService`
  - `PersistedClusterStateService`
  - `RemoteClusterStateService`
  - `SystemTemplatesService`
  - `UsageService`
  - `FsHealthService`
- registries and format boundaries:
  - `NamedWriteableRegistry`
  - `NamedXContentRegistry`
  - `DataFormatRegistry`
- operational/runtime helpers:
  - `TaskResourceTrackingService`
  - `NetworkService`
  - `ResourceWatcherService`
  - `RemoteStoreNodeService`

Steelsearch has partial or development-only substitutes for some of these
surfaces, but not authoritative OpenSearch-equivalent runtime wiring.

The current operator-visible control surface inventory is tracked in
[current-runtime-control-surface-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/current-runtime-control-surface-inventory.md).

## Gap Class 1: Bootstrap And Preflight

OpenSearch has a much richer startup contract than the current daemon.

Missing or incomplete areas:

- bootstrap checks beyond local argument parsing;
- production-mode startup gates for runtime dependencies, not just release and
  security evidence;
- fail-closed validation for filesystem, networking, and role combinations;
- startup ordering guarantees between metadata persistence, membership,
  transport, and REST availability;
- stronger consistency between `/_steelsearch/readiness` blockers and startup
  refusal conditions.

Current Steelsearch evidence:

- production mode is explicitly gated and can fail closed;
- development mode still starts with a reduced runtime and advisory warnings.

Required next implementation direction:

- move from "production mode blocked by policy checklist" to "node startup is
  blocked by concrete runtime preflight checks".

Required tests:

- startup refusal fixture for absent/readonly/locked data paths;
- startup refusal fixture for invalid bind/config combinations;
- readiness/startup consistency probe showing blocked startup and blocked
  readiness use the same underlying gate reasons.

## Gap Class 2: Thread Pools, Task Tracking, And Runtime Controls

OpenSearch runtime behavior depends on subsystems Steelsearch still lacks or
only approximates:

- OpenSearch-shaped thread-pool model;
- cancellable task registry and task hierarchy;
- request-header propagation and task-local metadata;
- circuit breaker hierarchy and memory accounting parity;
- usage/hot-threads/task telemetry fidelity;
- resource watcher and background maintenance scheduling behavior.

Current Steelsearch evidence:

- `os-rest` already models selected header behavior such as content negotiation,
  warning headers, and `X-Opaque-Id`;
- readiness and selected operational endpoints exist;
- full task and thread-pool runtime controls are not present as authoritative
  equivalents.

Required next implementation direction:

- define a Rust-native runtime control model that is intentionally
  OpenSearch-shaped at the API boundary, rather than adding route stubs without
  real scheduling or accounting semantics.

Required tests:

- task cancellation and throttling probes that touch real runtime state;
- queue/backpressure smoke tests for administrative and search/write workloads;
- telemetry probes that verify task and runtime status is not merely synthetic.

## Gap Class 3: Plugin And Module Boundaries

OpenSearch runtime is heavily assembled from modules and plugin extension
points. The current Steelsearch daemon still hard-wires most behavior.

Missing or incomplete areas:

- explicit module loading boundary for search, mapper, ingest, repository, and
  script features;
- runtime registration boundary for transport actions and REST handlers outside
  the built-in development surface;
- formal plugin API for Rust-native extensions;
- explicit handling policy for Java plugin ABI incompatibility;
- lifecycle rules for loading, rejecting, and reporting unsupported modules.

Current Steelsearch evidence:

- the workspace already has crate-level decomposition (`os-rest`, `os-engine`,
  `os-plugin-knn`, etc.);
- daemon runtime assembly is still monolithic compared with OpenSearch `Node`.

Required next implementation direction:

- expose module/feature registration as runtime wiring, not just crate
  composition.

Required tests:

- startup transcript showing registered modules/features per profile;
- reject-path tests for unsupported/disabled modules;
- explicit reporting tests for Rust-native feature registration versus missing
  Java plugin ABI.

## Gap Class 4: User-Facing Runtime Identity And Config Hygiene

The binary name is now `steelsearch`, but runtime/config presentation still
needs tightening across the stack.

Remaining identity/config work:

- ensure logs, help text, Docker entrypoints, readiness output, and runbooks use
  the same user-facing terminology;
- tighten flag/env-var contract and document supported/unsupported settings;
- define which OpenSearch config keys are accepted, ignored with warning, or
  rejected fail-closed;
- separate development-only config from future production config;
- align daemon mode, readiness categories, and documented cutover rules.

Required implementation direction:

- make accepted, ignored-with-warning, and rejected-fail-closed config keys
  explicit in user-facing docs and code;
- ensure CLI help, logs, readiness output, and runbooks all use the same
  profile language as the replacement roadmap.

Required tests:

- CLI/help text snapshot tests for supported/unsupported settings;
- readiness/log terminology smoke tests;
- fail-closed config parsing tests for unsupported production-only settings.

## Implementation Order

Recommended implementation sequence for this backlog item:

1. bootstrap/preflight contract and startup refusal rules;
2. runtime control model: task tracking, cancellation, thread pools, breakers;
3. module/plugin registration boundary;
4. user-facing config and identity cleanup.

This order is deliberate. Without a stricter startup contract, adding more
routes and services only increases ambiguity. Without runtime controls,
additional API coverage will not behave like OpenSearch under load or failure.

## Required Implementation

For backlog purposes, the minimum implementation slices from this document are:

1. concrete startup/preflight checks with refusal semantics;
2. authoritative runtime control model for tasks, scheduling, and accounting;
3. explicit module and feature registration boundary;
4. user-facing config contract and identity cleanup.
