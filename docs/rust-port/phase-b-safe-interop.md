# Phase B: Safe Java OpenSearch Interop

## Goal

`Phase B` is the first mixed-mode stage after standalone replacement.

`Phase A` and `Phase A-1` prove that Steelsearch can run as a standalone
OpenSearch replacement cluster. `Phase B` does not change that goal. Instead,
it adds a second operating mode:

- Steelsearch remains outside the Java OpenSearch cluster membership set;
- Steelsearch can observe, decode, and selectively coordinate against a live
  Java OpenSearch cluster;
- unsupported mixed-mode behavior must fail closed before it can corrupt
  cluster state, shard state, or write ordering.

The target is not shard ownership, cluster join, or peer-node publication
acknowledgement. The target is a safe interop boundary.

When `Phase B` appears in API or milestone documents, it should be read as:

- external transport client / observer / coordinator behavior;
- optional write forwarding only behind explicit safety gates;
- fail-closed rejection before any unsupported mixed-mode contract can execute.

## Boundary Against Phase A-1 And Phase C

Keep work in `Phase B` only when all of the following are true:

- Java OpenSearch still owns cluster membership and shard lifecycle;
- Steelsearch acts as an external transport client, observer, coordinator, or
  validated forwarder;
- failure of the feature can be made safe by rejection, fallback, or local
  cache invalidation without participating as a peer node.

Move work back to `Phase A-1` when:

- the behavior is still purely standalone;
- no Java OpenSearch transport or mixed-mode validation is required.

Move work to `Phase C` when:

- Steelsearch must advertise itself as a Java-compatible discovery node;
- Steelsearch must own primaries or replicas inside a Java cluster;
- Steelsearch must acknowledge publications, join elections, relocate shards,
  run peer recovery, or participate in same-cluster write replication.

## Operating Model

The canonical `Phase B` operating model is the one defined in
[interop-mode.md](/home/ubuntu/steelsearch/docs/rust-port/interop-mode.md):

- external transport client
- local decoded cluster-state cache
- read-mostly by default
- write forwarding only behind explicit safety gates
- fail-closed rejection for unsupported transport, metadata, wire-version, or
  routing situations

Canonical non-goals during `Phase B`:

- no discovery participation
- no cluster-manager role
- no shard allocation target
- no primary or replica ownership
- no peer recovery
- no relocation target
- no publication acknowledgement as a real node

## Validation Profile Rule

`Phase B` validation must be profile-driven just like `Phase A-1`, but the
profiles differ because the source system is now an actual Java OpenSearch
cluster rather than only a side-by-side REST source target.

Canonical `Phase B` profile families:

- `interop-baseline`
  - one Steelsearch coordinator/interoperability node
  - one or more Java OpenSearch nodes
  - read-only cluster-state polling and read/search forwarding
- `interop-write-forwarding`
  - same as baseline plus explicit write-forwarding gate enabled
  - only for actions whose request/response and routing safety are validated
- `interop-version-gate`
  - multiple Java OpenSearch versions or wire-version fixtures
  - verifies fail-closed behavior for incompatible versions and gated payloads
- `interop-metadata-customs`
  - source cluster emits supported and unsupported metadata customs/named
    writeables
  - verifies cache acceptance versus rejection behavior
- `interop-failure-injection`
  - source node loss, stale cluster-state base UUID, routing holes, undecodable
    payloads, remote transport exceptions
  - verifies fail-closed mixed-mode behavior

`Phase B` claims must not rely on narrative transcripts alone. Each claim needs:

- a runtime-connected Steelsearch path;
- a Java OpenSearch source target or fixture with the required behavior;
- a reusable compatibility runner or explicit integration test;
- a canonical report artifact.

## Canonical Version Range And Wire Gates

The first `Phase B` source target is the local Java OpenSearch `3.7.0`
baseline already used by the current source compatibility inventory.

Canonical baseline:

- OpenSearch product version id:
  - `3_070_099`
- transport version id:
  - `137_287_827`
- minimum compatible transport version id:
  - `136_407_827`
- discovery-node stream-address gate:
  - `137_237_827`

Current `Phase B` rule:

- claims of live Java interop start from this `3.7.0` baseline;
- lower or alternate source versions may be added later as explicit profile
  expansions, not as implicit compatibility claims;
- incompatible wire versions must fail closed before any mixed-mode execution;
- the canonical fixture for this baseline lives in
  `tools/fixtures/interop-handshake-compat.json`.

## Phase B Capability Areas

### 1. Transport Handshake And Node Identity

Steelsearch must:

- connect to Java transport addresses;
- complete handshake and version negotiation;
- decode remote node identity, cluster name, and cluster UUID;
- reject unsupported wire versions and unknown handshake-critical payloads.

Required evidence:

- golden fixtures for transport frame and handshake decode;
- live Java interop probes across the supported version range;
- fail-closed cases for incompatible versions or undecodable handshakes.

### 2. Cluster-State Read, Cache, And Diff Safety

Steelsearch must:

- fetch full cluster-state responses from Java OpenSearch;
- maintain a compatibility-aware local cache;
- apply publication diffs only when `from_uuid` matches the cached state;
- reject unsupported metadata customs, top-level customs, and named writeables
  before replacing the cache;
- keep the previous cache on incompatibility.

Required evidence:

- fixture-backed decode coverage for metadata/routing/custom payloads;
- live cache refresh tests against Java OpenSearch;
- stale-base diff rejection;
- unsupported custom metadata rejection with prior-cache preservation.
- canonical fail-closed custom fixture:
  `tools/fixtures/interop-cluster-state-custom-fail-closed.json`

### 3. Routing Plan And Read/Coordination Interop

Steelsearch must:

- compute routing plans for read/search forwarding from cached routing tables;
- resolve shard copies to Java discovery nodes;
- forward validated read/search requests to the correct Java nodes;
- return OpenSearch-shaped REST responses to clients;
- fail closed on missing routing, missing discovery nodes, or unsupported
  request shapes.

Required evidence:

- cluster/metadata read forwarding integration tests;
- search forwarding parity on representative request families;
- routing-hole and unsupported-query rejection tests.
- canonical search routing planner fixture:
  `tools/fixtures/interop-search-routing-plan.json`
- canonical `_search` forwarding policy fixture:
  `tools/fixtures/interop-search-forwarding-policy.json`
- canonical representative search forwarding probe:
  `tools/probe_interop_search_forwarding_profile.sh`
- canonical initial read-only inventory:
  `tools/fixtures/interop-read-action-inventory.json`
- canonical live baseline probe:
  `tools/probe_interop_read_forwarding_profile.sh`
- canonical fail-closed planner fixture:
  `tools/fixtures/interop-read-forwarding-fail-closed.json`

The canonical initial `_search` forwarding policy is intentionally narrower than
the standalone `Phase A-1` search surface.

Accepted initial forwarding family:

- query families:
  - `match_all`
  - `term`
  - `range`
  - `bool.filter`
- request options:
  - `sort`
  - `from`
  - `size`
  - `track_total_hits`

Rejected until explicit forwarding coverage exists:

- `aggregations`
- `highlight`
- `suggest`
- `scroll`
- `PIT`
- `search_after`
- `rescore`
- `collapse`
- `script_score`
- `function_score`
- `nested`
- `geo_distance`
- `knn`
- `hybrid`
- `runtime_mappings`

### 4. Transport Action Compatibility Ledger

Steelsearch must classify Java transport actions into:

- accepted and executable in `Phase B`;
- accepted only for read-only/coordinating use;
- explicitly rejected;
- deferred to `Phase C`.

This ledger must exist per action family, not only as prose.

Canonical initial `interop-baseline` read-only dispositions:

- `implemented`
  - `cluster:monitor/health`
  - `cluster:monitor/state`
  - `cluster:monitor/stats`
  - `cluster:monitor/task`
  - `cluster:monitor/tasks/lists`
  - `cluster:monitor/nodes/stats`
  - `indices:admin/get`
  - `indices:admin/aliases/get`
  - `indices:monitor/settings/get`
  - `indices:admin/data_stream/get`
- `rejected`
  - `cluster:monitor/allocation/explain`
  - `cluster:monitor/nodes/info`
- `Phase C`
  - `cluster:monitor/nodes/liveness`

Required evidence:

- source-derived transport inventory with explicit Phase B disposition;
- per-action request/response fixtures where accepted;
- fail-closed tests where rejected.

Canonical source-derived transport inventory:

- `tools/fixtures/interop-transport-action-inventory.json`
- accepted-action evidence ledger:
  `tools/fixtures/interop-accepted-transport-action-evidence.json`
- reject ledger:
  `tools/fixtures/interop-reject-ledger.json`

### 5. Safe Write Forwarding

`Phase B` is read-mostly by default. Write forwarding is optional and gated.

If enabled for selected actions, Steelsearch must:

- require an explicit config gate;
- compute a primary-shard routing plan from cached cluster state;
- forward only validated write actions;
- preserve OpenSearch-shaped success and error envelopes;
- reject retry/partial-failure situations that are not yet proven safe.

Recommended initial scope:

- single-document `index`
- single-document `delete`
- single-document `update`
- bounded `_bulk`

Canonical config contract:

- env:
  - `STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED=true|false`
- CLI:
  - `--interop.java_write_forwarding_validated true|false`
- default:
  - `false`
- rule:
  - no Java write forwarding path may execute unless this gate is explicitly
    enabled

Canonical representative happy-path probe:

- `tools/probe_interop_write_forwarding_profile.sh`

Canonical bounded `_bulk` policy:

- accepted representative happy-path:
  - homogeneous bounded `_bulk` where all items succeed and the response has
    `errors=false`
- rejected:
  - any partial-failure envelope where source returns mixed success/error items
    with `errors=true`
- canonical probe:
  - `tools/probe_interop_bulk_forwarding_profile.sh`

Canonical fail-closed write-forwarding fixture:

- `tools/fixtures/interop-write-forwarding-fail-closed.json`
- required rejects:
  - gate disabled
  - primary shard unresolved in cached routing
  - retry-sensitive update/write shapes outside the validated contract

Out of initial scope unless separately proven:

- shard-ownership-sensitive retries
- recovery-time writes
- mixed-cluster replica semantics
- publication-coupled writes

### 6. Version Gates, Named Writeables, And Custom Metadata

Steelsearch must maintain explicit compatibility ledgers for:

- wire-version gates
- unknown transport actions
- unknown request/response payloads
- unsupported top-level customs
- unsupported metadata customs
- unsupported plugin payloads

Required evidence:

- fixture coverage by version gate
- live rejection probes where the source emits unsupported material
- canonical error/report classification

### 7. Failure Injection And Safety Proof

`Phase B` must prove safe failure, not just happy-path interop.

Required cases:

- remote node unavailable
- stale cluster-state diff base UUID
- routing target missing
- undecodable transport error payload
- remote transport exception unwrap
- unsupported action before send
- unsupported metadata/custom while refreshing cache
- write-forwarding gate disabled

Canonical failure-injection ledger:

- `tools/fixtures/interop-failure-injection.json`

## Canonical Report Set

`Phase B` should converge on the following report families:

- `interop-handshake-report.json`
- `interop-cluster-state-cache-report.json`
- `interop-read-forwarding-report.json`
- `interop-search-forwarding-report.json`
- `interop-write-forwarding-report.json`
- `interop-version-gates-report.json`
- `interop-custom-metadata-report.json`
- `interop-failure-injection-report.json`

These reports should live under a dedicated compare tree for the `Phase B`
runner, analogous to the `Phase A-1` acceptance harness.

Canonical runner:

- `tools/run-phase-b-interop-harness.sh`
- canonical artifact tree:
  - `target/phase-b-interop/interop-handshake-report.json`
  - `target/phase-b-interop/interop-cluster-state-cache-report.json`
  - `target/phase-b-interop/interop-read-forwarding-report.json`
  - `target/phase-b-interop/interop-search-forwarding-report.json`
  - `target/phase-b-interop/interop-version-gates-report.json`
  - `target/phase-b-interop/interop-custom-metadata-report.json`
  - `target/phase-b-interop/interop-failure-injection-report.json`
  - optional when write forwarding is explicitly claimed:
    - `target/phase-b-interop/interop-write-forwarding-report.json`

## Exit Criteria

`Phase B` is complete only when:

- Steelsearch can safely act as an external transport client against the target
  Java OpenSearch versions;
- cluster-state read/cache/diff behavior is runtime-backed and fail-closed on
  unsupported customs or stale bases;
- selected cluster/metadata/search forwarding flows are validated end-to-end;
- any enabled write-forwarding surface is explicitly gated, routing-safe, and
  report-backed;
- unknown action/payload/version situations are rejected before unsafe mixed-
  mode execution;
- documentation and compatibility ledgers classify accepted, rejected, and
  deferred interop surfaces unambiguously;
- no `Phase B` claim depends on same-cluster membership semantics that belong
  to `Phase C`.

## Completion Checklist

Treat `Phase B` as complete only when all of the following are true:

- canonical interop profiles exist and clean-pass for the accepted `Phase B`
  surface;
- transport handshake/version gating is fixture-backed and live-probed;
- cluster-state cache refresh and diff-application safety are proven;
- cluster/metadata/search forwarding reports clean-pass;
- any enabled write-forwarding family has explicit gate, routing proof, and
  failure-injection coverage;
- unsupported customs, unknown actions, and incompatible versions fail closed;
- `docs/api-spec/*` and `docs/rust-port/*` describe `Phase B` as external
  interop/coordinating behavior, not peer-node participation;
- remaining mixed-cluster peer-node work is explicitly deferred to `Phase C`.
