# Development Concerns Audit

This document gathers the phase documents, development-time concern inventories,
test/audit entrypoints, and current known gaps that were previously spread
across `docs/rust-port/*` and `docs/api-spec/*`.

It is not a replacement milestone. It is the operator/developer-facing map of:

- which documents explain the major design decisions;
- which documents capture unresolved or historically difficult areas;
- which harnesses currently prove behavior against OpenSearch;
- which quality signals still do not exist as first-class tooling.

## 1. Core Phase Documents

These are the primary phase-definition documents and should be read first.

- [milestones.md](/home/ubuntu/steelsearch/docs/rust-port/milestones.md)
  - top-level phase boundaries and definition of done
- [phase-a1-standalone-fullset-closure.md](/home/ubuntu/steelsearch/docs/rust-port/phase-a1-standalone-fullset-closure.md)
  - standalone replacement closure and release gate
- [phase-b-safe-interop.md](/home/ubuntu/steelsearch/docs/rust-port/phase-b-safe-interop.md)
  - external Java OpenSearch interop as coordinator/observer/gated forwarder
- [phase-c-peer-node-compat.md](/home/ubuntu/steelsearch/docs/rust-port/phase-c-peer-node-compat.md)
  - same-cluster peer-node participation, reports, and release gate
- [interop-mode.md](/home/ubuntu/steelsearch/docs/rust-port/interop-mode.md)
  - the Phase B vs Phase C operating-model boundary
- [validation-profiles.md](/home/ubuntu/steelsearch/docs/rust-port/validation-profiles.md)
  - canonical profile ownership for comparison and release-gating evidence

## 2. Development-Time Concern Inventories

These documents capture the hardest implementation concerns that shaped the
project while it was being built. They are the right place to understand why a
feature was difficult or why a release gate was designed conservatively.

### Coordination and cluster-state concerns

- [cluster-coordination-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/cluster-coordination-gap-inventory.md)
- [coordination-election-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-election-gap-inventory.md)
- [coordination-publication-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-publication-gap-inventory.md)
- [coordination-gateway-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-gateway-gap-inventory.md)
- [coordination-liveness-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-liveness-gap-inventory.md)
- [coordination-metadata-persistence-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-metadata-persistence-gap-inventory.md)
- [coordination-task-queue-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-task-queue-gap-inventory.md)
- [coordination-cluster-manager-task-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-cluster-manager-task-gap-inventory.md)
- [coordination-voting-config-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-voting-config-gap-inventory.md)
- [coordination-multi-node-failure-test-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/coordination-multi-node-failure-test-gap-inventory.md)
- [cluster-state.md](/home/ubuntu/steelsearch/docs/rust-port/cluster-state.md)
- [cluster-state-custom-registry.md](/home/ubuntu/steelsearch/docs/rust-port/cluster-state-custom-registry.md)
- [unsupported-custom-ledger.md](/home/ubuntu/steelsearch/docs/rust-port/unsupported-custom-ledger.md)

### Metadata, routing, shard-lifecycle, and write-path concerns

- [metadata-routing-allocation-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/metadata-routing-allocation-gap-inventory.md)
- [node-runtime-gap-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/node-runtime-gap-inventory.md)
- [shard-lifecycle.md](/home/ubuntu/steelsearch/docs/rust-port/shard-lifecycle.md)
- [write-path-compatibility.md](/home/ubuntu/steelsearch/docs/rust-port/write-path-compatibility.md)
- [local-recovery-store-compatibility.md](/home/ubuntu/steelsearch/docs/rust-port/local-recovery-store-compatibility.md)
- [snapshot-import-policy.md](/home/ubuntu/steelsearch/docs/rust-port/snapshot-import-policy.md)

### Transport, wire, and source-compatibility concerns

- [wire-protocol.md](/home/ubuntu/steelsearch/docs/rust-port/wire-protocol.md)
- [version-gates.md](/home/ubuntu/steelsearch/docs/rust-port/version-gates.md)
- [transport-action-priority.md](/home/ubuntu/steelsearch/docs/rust-port/transport-action-priority.md)
- [source-compatibility-inventory.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-inventory.md)
- [source-compatibility-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/source-compatibility-matrix.md)

### Broader planning and production follow-on concerns

- [development-replacement-profile.md](/home/ubuntu/steelsearch/docs/rust-port/development-replacement-profile.md)
- [full-opensearch-replacement-plan.md](/home/ubuntu/steelsearch/docs/rust-port/full-opensearch-replacement-plan.md)
- [production-replacement-epics.md](/home/ubuntu/steelsearch/docs/rust-port/production-replacement-epics.md)
- [production-performance-validation.md](/home/ubuntu/steelsearch/docs/rust-port/production-performance-validation.md)
- [production-security-baseline.md](/home/ubuntu/steelsearch/docs/rust-port/production-security-baseline.md)
- [production-operations-runbook.md](/home/ubuntu/steelsearch/docs/rust-port/production-operations-runbook.md)

## 3. Current Test And Scenario Evidence

### Workspace test inventory

Current workspace test inventory command:

```bash
cargo test --workspace -- --list | wc -l
```

Current observed count:

- `628`

This is a test inventory count, not a line-coverage percentage.

### Coverage tooling status

Current observed commands:

```bash
cargo llvm-cov --version
bash tools/run-coverage-audit.sh
```

Current result:

- `cargo-llvm-cov 0.6.15`
- [run-coverage-audit.sh](/home/ubuntu/steelsearch/tools/run-coverage-audit.sh)
  now emits a canonical audit artifact:
  - `target/coverage-audit/coverage-audit-report.json`

Implication:

- there is now a first-class coverage audit entrypoint;
- line/branch percentage is measurable locally with `cargo llvm-cov`;
- quality is currently proved by fixture-driven tests, live probes, and
  milestone harnesses rather than by a coverage percentage target.

### Phase A family comparison/scenario coverage

Canonical entrypoint:

- [run-phase-a-acceptance-harness.sh](/home/ubuntu/steelsearch/tools/run-phase-a-acceptance-harness.sh)

Current family/profile coverage:

- `root-cluster-node`
  - cluster health, allocation explain, cluster settings, cluster state, root,
    tasks, stats
- `index-metadata`
  - index lifecycle, mappings, settings, aliases, templates,
    data-stream/rollover
- `document-write-path`
  - single-doc CRUD, refresh, bulk, routing
- `search`
  - strict lexical search family compare
- `search-execution`
  - multi-shard execution/accounting profile
- `snapshot-migration`
  - snapshot lifecycle plus migration cutover integration
- `vector-ml`
  - vector search compare and ML model-surface profile
- `transport-admin`
  - multi-node transport/admin report set

Representative fixture set:

- `tools/fixtures/root-cluster-node-compat.json`
- `tools/fixtures/index-lifecycle-compat.json`
- `tools/fixtures/single-doc-crud-compat.json`
- `tools/fixtures/bulk-compat.json`
- `tools/fixtures/search-strict-compat.json`
- `tools/fixtures/search-execution-compat.json`
- `tools/fixtures/snapshot-lifecycle-compat.json`
- `tools/fixtures/migration-cutover-integration.json`
- `tools/fixtures/vector-search-compat.json`
- `tools/fixtures/ml-model-surface-compat.json`
- `tools/fixtures/multi-node-transport-admin.json`

### Phase B interop coverage

Canonical entrypoint:

- [run-phase-b-interop-harness.sh](/home/ubuntu/steelsearch/tools/run-phase-b-interop-harness.sh)

Current report families:

- handshake
- cluster-state cache
- read forwarding
- search forwarding
- version gates
- custom metadata
- failure injection
- optional write forwarding

### Phase C mixed-cluster coverage

Canonical entrypoint:

- [run-phase-c-mixed-cluster-harness.sh](/home/ubuntu/steelsearch/tools/run-phase-c-mixed-cluster-harness.sh)

Current report families:

- join
- publication
- allocation
- recovery
- write replication
- failure
- reject ledger

## 4. API Scenario-Test Coverage Reading Rule

The repository is not organized as "one OpenSearch side-by-side test per route".

Instead, it uses three evidence styles:

- family-level OpenSearch comparison fixtures for standalone API surfaces;
- profile-level live probes for interop and mixed-cluster behavior;
- fixture-driven fail-closed tests for unsupported or safety-critical states.

That means:

- many APIs do have OpenSearch comparison coverage,
- but the proof is family/profile based rather than one test case per individual
  route path.

This is strongest for:

- standalone REST families in Phase A / A-1;
- interop coordinator behavior in Phase B;
- mixed-cluster peer-node behavior in Phase C.

That gap is now partially closed by:

- [route-evidence-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/generated/route-evidence-matrix.md)

The proof is still family/profile oriented, but there is now a generated
route-to-evidence ownership matrix.

## 5. Swagger / OpenAPI Status

Current status:

- generated OpenAPI spec exists:
  - [openapi.json](/home/ubuntu/steelsearch/docs/api-spec/generated/openapi.json)
- generated route evidence matrix exists:
  - [route-evidence-matrix.md](/home/ubuntu/steelsearch/docs/api-spec/generated/route-evidence-matrix.md)
- server now serves:
  - `GET /openapi.json`
  - `GET /docs`
  - `GET /swagger`
  - `GET /swagger-ui`
- Swagger UI is currently served as an HTML shell that loads
  `swagger-ui-dist` from CDN.

Operationally:

- starting the server exposes a live OpenAPI document and Swagger UI page;
- API documentation still lives primarily in `docs/api-spec/*`, but there is
  now a generated machine-readable spec and served browser UI.

## 6. Current Known Gaps

- No canonical percentage-based coverage gate in CI/local tooling yet.
- Swagger UI currently depends on CDN assets rather than vendored local assets.
- API comparison proof still exists mainly at family/profile granularity.
- `docs/api-spec/generated/rest-routes.md` is still a generated inventory and
  should not be read as the release-gate source of truth for milestone claims.

## 7. Recommended Next Follow-Up

If this repo needs stronger auditability beyond the current milestone harnesses,
the next highest-value additions are:

1. wire `cargo llvm-cov` into CI and define an explicit threshold policy;
2. harden the generated OpenAPI so it becomes part of a release-auditable
   route contract rather than only an inventory-derived spec;
3. vendor Swagger UI assets locally if offline/self-contained serving matters.
