# Replacement Claim Exit Criteria

This document separates `REST parity complete` from `OpenSearch replacement
ready` and fixes the minimum evidence required for each replacement profile.

## REST Parity Complete Versus OpenSearch Replacement Ready

`REST parity complete` means a route family exists and the supported request,
response, error, and idempotency contract is covered by bounded standalone
evidence.

`OpenSearch replacement ready` means the relevant route families are present and
the target profile also has the durability, security, and distributed evidence
required for real replacement claims.

Promotion rule:

- Route presence alone is never enough for a replacement claim.
- The stronger claim requires every parity class listed below for the target
  profile.

## Parity Classes

| Parity class | Definition | Minimum evidence artifact family |
| --- | --- | --- |
| Route parity | Route registration, request envelope, status code, and response shape are OpenSearch-shaped for the supported subset. | generated route ledgers, OpenAPI artifacts, route compare fixtures |
| Semantic parity | Supported parameters, error paths, idempotency, selector expansion, and state transitions match the documented contract. | semantic and strict compat fixtures, stateful probe reports, targeted unit tests |
| Durability parity | Restart, replay, metadata persistence, manifest ownership, and on-disk compatibility are bounded and auditable. | restart smoke reports, durability compare reports, replay/manifest fixtures, on-disk policy docs |
| Security parity | Authn/authz, TLS, restricted-index access, and redaction guarantees are fixed for secure use. | security authz fixtures, security harness reports, redaction smoke, PKI/bootstrap policy fixtures |
| Distributed parity | Join, publication, allocation, recovery, replication, and mixed-failure behavior are bounded for interop or peer-node claims. | phase-B/phase-C harness reports, publication/allocation/recovery/replication schemas, mixed-cluster failure artifacts |

## Minimum Evidence By Parity Class

| Parity class | Minimum docs | Minimum fixtures / schemas | Minimum harness / report |
| --- | --- | --- | --- |
| Route parity | [README.md](/home/ubuntu/steelsearch/docs/api-spec/README.md), [source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md) | route ledgers, route-specific compat fixtures | generated API spec artifact test and route compare report |
| Semantic parity | [search-parameter-coverage-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/search-parameter-coverage-matrix.md), [document-write-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/document-write-semantic-gap-matrix.md), [snapshot-migration-semantic-gap-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/snapshot-migration-semantic-gap-matrix.md) | semantic and strict compat fixtures, stateful probe ledgers | `tools/probe_stateful_route_ledger.py`, compat runner reports, route-family unit tests |
| Durability parity | [gateway-manifest-ownership.md](/home/ubuntu/steelsearch/docs/rust-port/gateway-manifest-ownership.md), [gateway-replay-recovery-policy.md](/home/ubuntu/steelsearch/docs/rust-port/gateway-replay-recovery-policy.md), [on-disk-state-upgrade-boundary.md](/home/ubuntu/steelsearch/docs/rust-port/on-disk-state-upgrade-boundary.md) | manifest/replay/durability fixtures | `tools/run-node-restart-smoke.sh`, `tools/run-durability-compat.sh` |
| Security parity | [security-role-route-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/security-role-route-matrix.md), [restricted-index-prefix-inventory.md](/home/ubuntu/steelsearch/docs/api-spec/restricted-index-prefix-inventory.md), [security-redaction-baseline.md](/home/ubuntu/steelsearch/docs/api-spec/security-redaction-baseline.md) | `security-authz-compat.json`, PKI/bootstrap policy fixtures | `tools/run-security-compat-harness.sh`, `tools/check-security-redaction-smoke.sh` |
| Distributed parity | [phase-b-safe-interop.md](/home/ubuntu/steelsearch/docs/rust-port/phase-b-safe-interop.md), [phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md) | handshake/cache/publication/allocation/recovery/replication schemas and transcript fixtures | `tools/run-phase-b-gap-harness.sh`, `tools/run-phase-c-gap-harness.sh` |

## Production Profile Readiness Checklists

### `standalone`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | route/semantic matrices, cutover runbook, snapshot/restore completeness matrix | Supported standalone surfaces are documented with explicit partial or fail-closed rules. |
| Required fixtures | search/document-write/snapshot semantic fixtures, startup preflight failures, restart smoke profiles | Representative happy-path and error-path fixtures exist for supported standalone routes. |
| Required harnesses | stateful route probe, migration acceptance harness, restart smoke, durability compare | Latest standalone reports complete without unresolved blocker rows for supported workflows. |
| Required pass conditions | route parity + semantic parity + durability parity | No unsupported or partial surface is silently treated as replacement-ready. |

### `secure standalone`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | standalone docs plus security role matrix, restricted-prefix inventory, redaction baseline | Security-sensitive route families have explicit minimum-role and deny-path policy. |
| Required fixtures | `security-authz-compat.json`, security bootstrap policy, PKI layout, restricted-index probes | Representative `401`, `403`, restricted-index, and redaction cases are fixed. |
| Required harnesses | security compat harness, redaction smoke, standalone restart and durability harnesses | Secure profile passes authn/authz and secret-handling checks in addition to standalone checks. |
| Required pass conditions | route parity + semantic parity + durability parity + security parity | Secure profile cannot be promoted while authn/authz or secret-handling remains stubbed. |

### `external interop`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | secure standalone docs when applicable plus handshake/version-skew matrix, stale-cache policy, interop allowlist | Every allowed and denied external interop action is explicitly classified. |
| Required fixtures | handshake reject cases, stale-cache reject cases, unsupported forwarded actions, mixed-mode transcripts | Version-skew and stale-cache failure paths are fixed with reject transcripts. |
| Required harnesses | `tools/run-phase-b-gap-harness.sh`, security harness where secure interop is claimed | Mixed-mode disconnect/publication/metadata failure profiles produce bounded fail-closed reports. |
| Required pass conditions | route parity + semantic parity + durability parity + distributed parity, plus security parity when secure | External interop cannot claim readiness while cache invalidation or unsupported forwarding remains ambiguous. |

### `same-cluster peer-node`

| Requirement type | Required items | Pass condition |
| --- | --- | --- |
| Required docs | interop docs plus join reject matrix, publication ordering matrix, allocation/relocation matrix, peer recovery matrix, replication matrix | Join/publication/recovery/replication lifecycle is documented as an auditable contract. |
| Required fixtures | join reject transcripts, publication/allocation/recovery/replication schemas, mixed-cluster failure profiles | Each mixed-cluster lifecycle has a report schema and representative failure artifact. |
| Required harnesses | `tools/run-phase-c-gap-harness.sh`, durability and restart harnesses, secure harnesses when claimed | Crash, stale replica, recovery interruption, and replication retry paths produce bounded reports. |
| Required pass conditions | all five parity classes | Peer-node readiness is blocked until the distributed lifecycle is evidenced end to end. |

## Go / No-Go Checklists

### Operator Go / No-Go

| Profile | Go only if | No-Go if |
| --- | --- | --- |
| `standalone` | Supported route families, migration acceptance, restart smoke, and durability compare all pass for the intended workload. | Any required cutover, restore, replay, or restart artifact is missing or failing. |
| `secure standalone` | Standalone checks pass and security harness plus redaction smoke pass with the intended credentials and TLS material. | Any authn/authz path, restricted-index policy, or redaction baseline is unresolved. |
| `external interop` | Secure checks pass when applicable and phase-B harness reports no unresolved fail-open behavior. | Handshake, version-skew, stale-cache, or unsupported forwarding remains undocumented or failing. |
| `same-cluster peer-node` | Phase-C lifecycle reports exist for join/publication/allocation/recovery/replication/failure and all required schemas are satisfied. | Any mixed-cluster lifecycle is only documented as planned or lacks bounded failure evidence. |

### Developer Go / No-Go

| Profile | Go only if | No-Go if |
| --- | --- | --- |
| `standalone` | Route rows are backed by semantic and durability artifacts, not only by API shape. | A route is marked `Partial` or `No` without a closing artifact plan. |
| `secure standalone` | Security-sensitive routes have explicit allow/deny fixtures and secure harness coverage. | Secure claims rely on stubbed security paths or undocumented credential policy. |
| `external interop` | Every forwarded or coordinated action is either on the allowlist or explicitly rejected. | A mixed-mode action can silently fall through, stale-cache reads can succeed, or version skew lacks a reject transcript. |
| `same-cluster peer-node` | Join, publication, allocation, recovery, replication, and crash paths each have schema-backed evidence. | Any peer-node capability is argued from route presence or documentation alone. |

## Compatibility Row Anchors

Use these anchors when mapping `Partial` or `No` rows from
[source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md):

- `#area-root-and-basic-node-identity`
- `#area-cluster-health-state-allocation-and-node-stats`
- `#area-index-create-get-delete-and-mappings-settings`
- `#area-document-write-read-and-refresh`
- `#area-rest-bulk`
- `#area-rest-search`
- `#area-knn-vector-indexing-and-query-search`
- `#area-knn-plugin-rest-and-model-apis`
- `#area-ml-commons-neural-search-and-model-serving`
- `#area-snapshot-and-restore`
- `#area-migration-and-replacement-tooling`
- `#area-steelsearch-multi-node-runtime`
- `#area-native-transport-frame-and-opensearch-probe-compatibility`
- `#area-security-and-access-control`
- `#area-opensearch-comparison-harness`
- `#area-java-opensearch-data-node-compatibility`
- `#area-java-plugin-abi-compatibility`

## Area Backlog Map

### <a id="area-root-and-basic-node-identity"></a>Root and basic node identity

Promote only after route and semantic parity are evidenced through the route
ledger, stateful probes, and compatibility matrix updates.

### <a id="area-cluster-health-state-allocation-and-node-stats"></a>Cluster health, state, allocation, and node stats

Promote only after semantic parity and distributed parity are evidenced through
runtime-control, allocation, and same-cluster lifecycle artifacts.

### <a id="area-index-create-get-delete-and-mappings-settings"></a>Index create/get/delete and mappings/settings

Promote only after semantic parity, durability parity, and secure mutation
controls are evidenced through mapping/settings fixtures and restart artifacts.

### <a id="area-document-write-read-and-refresh"></a>Document write/read and refresh

Promote only after semantic parity and durability parity are evidenced through
document-write matrices, restart smoke, and conflict/routing fixtures.

### <a id="area-rest-bulk"></a>REST `_bulk`

Promote only after semantic parity, security parity, and durability parity are
evidenced through bulk metadata/error-path fixtures and secure write probes.

### <a id="area-rest-search"></a>REST `_search`

Promote only after semantic parity and secure or profile-specific evidence are
complete for supported DSL families and failure-path handling.

### <a id="area-knn-vector-indexing-and-query-search"></a>k-NN vector indexing and query search

Promote only after semantic parity, durability parity, and replacement-grade
vector ranking evidence exist for the claimed vector subset.

### <a id="area-knn-plugin-rest-and-model-apis"></a>k-NN plugin REST and model APIs

Promote only after semantic parity and security parity cover cache/model
lifecycle, and distributed parity is explicit for any clustered claim.

### <a id="area-ml-commons-neural-search-and-model-serving"></a>ML Commons, neural search, and model serving

Promote only after semantic parity, security parity, and durability/runtime
isolation evidence exist for deployment and task lifecycle behavior.

### <a id="area-snapshot-and-restore"></a>Snapshot and restore

Promote only after semantic parity, durability parity, and migration/cutover
evidence cover restore safety, metadata preservation, and rollback.

### <a id="area-migration-and-replacement-tooling"></a>Migration and replacement tooling

Promote only after cutover runbooks, unsupported-feature detection, and
acceptance harness evidence prove bounded migration and rollback behavior.

### <a id="area-steelsearch-multi-node-runtime"></a>Steelsearch multi-node runtime

Promote only after durability parity and distributed parity exist for quorum,
restart, recovery, and failure-mode handling.

### <a id="area-native-transport-frame-and-opensearch-probe-compatibility"></a>Native transport frame and OpenSearch probe compatibility

Promote only after external interop and peer-node distributed parity cover
handshake, decode, action classification, and failure-mode evidence.

### <a id="area-security-and-access-control"></a>Security and access control

Promote only after security parity is satisfied by authn/authz, TLS,
restricted-index, and redaction artifacts.

### <a id="area-opensearch-comparison-harness"></a>OpenSearch comparison harness

Promote only after the harness surface is broad enough to support each claimed
profile rather than isolated feature families.

### <a id="area-java-opensearch-data-node-compatibility"></a>Java OpenSearch data-node compatibility

Remain blocked until same-cluster distributed parity exists for mixed
membership, recovery, replication, and failure handling.

### <a id="area-java-plugin-abi-compatibility"></a>Java plugin ABI compatibility

Remain blocked until a separate compatibility track explicitly opens Java plugin
loading and execution as an in-scope goal.
