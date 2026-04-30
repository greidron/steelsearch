# Steelsearch Production Replacement Epics

This document turns the explicit non-goals in
`docs/rust-port/development-replacement-profile.md` into tracked production
replacement epics. Each epic defines:

- the minimum entry criteria before the epic can be considered production-ready;
- what remains explicitly out of scope even after the epic is opened;
- the validation environment or command that must pass before the epic can be
  treated as closed.

This is an execution index, not a claim that the epics are already complete.

## Epic 1: Production Security Parity

References:

- `docs/rust-port/production-security-baseline.md`
- `docs/rust-port/production-operations-runbook.md`

Minimum entry criteria:

- HTTP TLS and transport TLS are enforced in production mode.
- Authentication and authorization are enforced for document, index, cluster,
  snapshot, k-NN, and ML routes.
- Index permissions, audit logging, tenant isolation, and secure settings are
  enabled as production blockers, not development stubs.
- Secret material for connectors and repositories is stored outside plaintext
  cluster metadata.
- `GET /_steelsearch/readiness` reports no security blockers in production mode.

Explicit out of scope:

- Byte-for-byte OpenSearch Security plugin API parity.
- Java plugin ABI compatibility.
- Development-mode insecure shortcuts promoted into production.

Validation environment and command:

- Environment: secured single-node production boot with certs, credentials, and
  secure settings configured.
- Command shape:

  ```bash
  STEELSEARCH_MODE=production \
  tools/run-development-replacement-gate.sh
  ```

- Plus the secured environment checks described in
  `docs/rust-port/production-security-baseline.md`.

## Epic 2: Rolling Upgrade Support

References:

- `docs/rust-port/development-replacement-profile.md`
- `docs/rust-port/source-compatibility-matrix.md`
- `docs/rust-port/full-opensearch-replacement-plan.md`

Minimum entry criteria:

- Mixed-version Steelsearch nodes can join the same cluster across the
  supported upgrade window.
- Cluster-state publication, transport handshakes, and shard routing remain
  compatible across that window.
- Restart ordering, quorum preservation, and rollback steps are defined and
  rehearsed.
- Readiness evidence includes successful rolling restart and rejoin under load.

Explicit out of scope:

- Mixed Java/OpenSearch data-node rolling upgrades.
- Cross-major upgrade promises without explicit test coverage.
- Direct Lucene/JVM bridge-based upgrade shortcuts.

Validation environment and command:

- Environment: multi-node Steelsearch cluster with at least one old-version and
  one new-version node, plus shard allocation and search traffic during the
  rollout.
- Command shape: dedicated rolling-upgrade rehearsal script or test target,
  still to be added, that boots the mixed-version cluster and validates restart
  sequencing, publication health, and rollback.

## Epic 3: Complete REST/Transport Coverage

References:

- `docs/api-spec/README.md`
- `docs/rust-port/source-compatibility-matrix.md`
- `docs/rust-port/phase-a1-standalone-fullset-closure.md`

Minimum entry criteria:

- Production-required REST endpoints and transport actions are inventoried and
  classified as implemented, intentionally unsupported/fail-closed, or deferred
  behind a documented blocker.
- Implemented surfaces preserve OpenSearch-compatible status codes, error
  shapes, and response contracts where replacement requires them.
- Unsupported surfaces fail closed with explicit compatibility errors instead of
  partial success.

Explicit out of scope:

- Full OpenSearch plugin ABI coverage.
- Non-production admin APIs with no replacement requirement.
- Undocumented partial compatibility that cannot be tested end to end.

Validation environment and command:

- Environment: Steelsearch-only validation plus explicit OpenSearch comparison
  where the surface exists on both systems.
- Command shape:

  ```bash
  tools/run-development-replacement-gate.sh
  RUN_OPENSEARCH_COMPARISON=1 tools/run-opensearch-compare.sh
  ```

## Epic 4: Mixed-Cluster Safety Boundaries

References:

- `docs/rust-port/interop-mode.md`
- `docs/rust-port/local-recovery-store-compatibility.md`
- `docs/rust-port/development-replacement-profile.md`

Minimum entry criteria:

- Unsupported mixed-cluster topologies fail closed before data-node admission.
- Handshake, version, and membership fencing make unsupported Java/OpenSearch
  participation explicit.
- The allowed mixed-mode scope, if any, is documented with exact safety
  boundaries and failure modes.

Explicit out of scope:

- Silent best-effort mixed data-node membership.
- Direct reuse of OpenSearch shard stores without a dedicated recovery contract.
- Java plugin compatibility as a side effect of cluster join support.

Validation environment and command:

- Environment: mixed-mode rehearsal with Steelsearch and Java/OpenSearch nodes,
  including unsupported join attempts and fail-closed assertions.
- Command shape: dedicated multi-node safety rehearsal, still to be added, that
  proves supported joins succeed and unsupported compositions are rejected.

## Epic 5: Full Snapshot/Restore Parity

References:

- `docs/rust-port/snapshot-import-policy.md`
- `docs/rust-port/production-operations-runbook.md`
- `docs/rust-port/source-compatibility-matrix.md`

Minimum entry criteria:

- Repository registration, verification, snapshot create/status/delete/cleanup,
  and restore all behave correctly on live nodes.
- Corrupt, stale, partial, or incompatible snapshot metadata fails closed.
- Snapshot restore is usable as a production cutover and rollback primitive for
  supported Steelsearch-native repositories.
- The supported import policy for OpenSearch-origin data remains explicit.

Explicit out of scope:

- Direct OpenSearch snapshot import as a first replacement gate.
- Repository types not covered by a live validation environment.
- Silent metadata repair of corrupted snapshots.

Validation environment and command:

- Environment: live daemon or multi-node snapshot rehearsal with repository
  verification, create, cleanup, restore, restart, and corruption scenarios.
- Command shape: repository/snapshot restore rehearsal plus the replacement gate
  after restore. Exact production rehearsal script is still to be added.

## Epic 6: Benchmark/Load/Chaos Readiness

References:

- `docs/rust-port/production-performance-validation.md`
- `docs/rust-port/production-operations-runbook.md`

Minimum entry criteria:

- Benchmark, sustained load, and chaos/fault-injection workloads are defined
  for supported replacement scenarios.
- Thresholds exist for latency, throughput, error rate, memory growth,
  relocation/recovery duration, and publication lag.
- Reports are archived and treated as release evidence, not informal logs.

Explicit out of scope:

- Production claims based only on local smoke tests.
- Load parity for unsupported workloads.
- Chaos coverage without reproducible reports and thresholds.

Validation environment and command:

- Environment: single-node and multi-node clusters with representative write,
  search, vector, restore, and restart traffic.
- Command shape:

  ```bash
  RUN_HTTP_LOAD_TESTS=1 \
  tools/run-http-load-baseline.py --base-url http://127.0.0.1:9200 \
  --output target/http-load-baseline.json
  ```

- Plus the multi-node, comparison, and chaos coverage defined in
  `docs/rust-port/production-performance-validation.md`.

## Epic 7: Direct Shard-Store Reuse and Lucene/JVM Bridge Compatibility

References:

- `docs/rust-port/local-recovery-store-compatibility.md`
- `docs/rust-port/development-replacement-profile.md`

Minimum entry criteria:

- A clear decision exists: either keep this permanently out of scope or define a
  dedicated compatibility track with invariants, recovery rules, and validation
  evidence.
- No production replacement language relies on accidental Lucene/JVM reuse.

Explicit out of scope:

- Implicit reuse of OpenSearch shard data paths.
- Mixed-cluster data-node promises that assume a Lucene bridge exists.

Validation environment and command:

- Environment: explicit local-recovery or bridge compatibility rehearsal, if
  this epic is reopened.
- Command shape: none today; this remains a blocked epic until a dedicated
  recovery/store validation harness is added.

## Epic 8: Production-Grade Multi-Tenant Isolation

References:

- `docs/rust-port/production-security-baseline.md`
- `docs/rust-port/development-replacement-profile.md`

Minimum entry criteria:

- Tenant and namespace boundaries are enforced for data access, model access,
  snapshot access, and operational APIs.
- Noisy-neighbor and cross-tenant leakage checks exist for logs, errors, and
  audit events.
- Readiness explicitly blocks production mode until tenant isolation evidence is
  present.

Explicit out of scope:

- Development-only single-tenant assumptions promoted into production.
- Soft advisory separation without enforcement and audit evidence.

Validation environment and command:

- Environment: secured multi-tenant rehearsal with at least two tenants and
  cross-tenant deny checks.
- Command shape: dedicated authz/isolation rehearsal, still to be added, plus
  production readiness validation.

## Cross-Epic Validation Rule

No single epic closes the production replacement question by itself. Production
replacement requires:

1. the epic-specific validation above;
2. a green `tools/run-development-replacement-gate.sh`;
3. a green live-daemon `tools/run-development-replacement-gate-e2e.sh`; and
4. explicit operator evidence in the production runbooks for the target cutover
   environment.
