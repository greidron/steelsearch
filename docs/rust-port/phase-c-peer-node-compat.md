# Phase C: Same-Cluster Peer-Node Compatibility

## Goal

`Phase C` is the first stage where Steelsearch is allowed to behave like a real
Java OpenSearch cluster member rather than an external interop client.

`Phase A` and `Phase A-1` prove standalone replacement.
`Phase B` proves safe external interop.
`Phase C` begins only when Steelsearch must join the same cluster as Java
OpenSearch nodes and participate in coordination, shard lifecycle, write
replication, and recovery without violating Java OpenSearch invariants.

The target is not "more forwarding." The target is peer-node correctness.

## Boundary Against Phase B

Keep work in `Phase C` only when at least one of the following is true:

- Steelsearch must appear as a `DiscoveryNode` to Java OpenSearch.
- Steelsearch must pass join validation and become part of cluster membership.
- Steelsearch must receive and apply cluster-state publications as a peer node.
- Steelsearch must own primaries or replicas in a mixed Java/Rust cluster.
- Steelsearch must participate in peer recovery, relocation, or retention-lease
  exchange.
- Steelsearch must replicate writes across mixed Java/Rust shard copies.

Do not keep work in `Phase B` once it depends on membership, shard ownership,
recovery, or publication acknowledgement semantics.

## Canonical Phase C Operating Model

The canonical `Phase C` operating model is mixed-cluster peer participation:

- at least one Java OpenSearch node and one Steelsearch node in the same
  cluster;
- Java remains the initial compatibility source of truth;
- Steelsearch may be admitted only after handshake, join, publication,
  allocation, recovery, and write-path safety gates pass;
- unsupported membership or shard-lifecycle situations must fail closed before
  data movement or acknowledgement.

The first acceptable `Phase C` rollout shape is conservative:

- Java cluster-manager ownership remains fixed at first;
- Steelsearch joins first as a non-cluster-manager data-capable peer;
- shard allocation is admitted only for explicitly validated index families;
- mixed primaries may remain out of scope until replica and recovery semantics
  are proven.

## Validation Profiles

`Phase C` claims must be profile-driven and topology-driven.

Canonical initial profile families:

- `mixed-cluster-join`
  - one Java cluster-manager/data node
  - one Steelsearch joining node
  - proves handshake, join validation, membership visibility, and clean reject
    behavior
- `mixed-cluster-publication`
  - same topology, but with repeated cluster-state updates
  - proves publication receive/apply/ack behavior and fail-closed publication
    rejection
- `mixed-cluster-allocation`
  - one Java node plus one Steelsearch node
  - proves shard allocation admission, routing-table convergence, and fail-closed
    allocation reject cases
- `mixed-cluster-recovery`
  - at least one relocating or recovering shard between Java and Steelsearch
  - proves file/chunk/translog/finalize flow plus retention leases
- `mixed-cluster-write-replication`
  - mixed primary/replica topology for a bounded write family
  - proves seq_no/primary_term/global-checkpoint/refresh visibility behavior
- `mixed-cluster-failure`
  - node loss, publication mismatch, relocation interruption, stale replica,
    and restart scenarios

Every Phase C claim needs:

- a canonical profile family;
- a reusable runner or integration harness;
- machine-readable reports;
- explicit fail-closed cases for unsupported or unsafe topology states.

## Capability Areas

### 1. Discovery And Join Admission

Steelsearch must:

- encode a Java-compatible discovery identity;
- advertise only validated node roles;
- pass compatibility checks for cluster name, cluster UUID, version gates, and
  node attributes;
- reject unsupported join attempts before they mutate cluster membership.

Required evidence:

- source-derived join contract fixture:
  `tools/fixtures/mixed-cluster-join-admission.json`
- canonical reject fixture:
  `tools/fixtures/mixed-cluster-join-reject.json`
- live prerequisite probe runner:
  `tools/probe_mixed_cluster_join_profile.sh`
- canonical aggregate report runner:
  `tools/run_mixed_cluster_join_profile.sh`
- live mixed-cluster join probe;
- reject cases for incompatible cluster UUID, wire-version mismatch, and
  unsupported role advertisement;
- report showing Java cluster membership after join.

### 2. Cluster-State Publication, Apply, And Acknowledgement

Steelsearch must:

- receive cluster-state publications from Java;
- apply full states and supported diffs in order;
- reject stale diff bases, unknown named writeables, or unsupported customs
  without corrupting local state;
- acknowledge publications only after successful apply.

Required evidence:

- publication stream integration harness;
- fail-closed publication reject cases;
- canonical aggregate report runner:
  `tools/run_mixed_cluster_publication_profile.sh`
- membership-visible ack report.

### 3. Allocation Admission And Routing Convergence

Steelsearch must:

- accept shard allocation only for validated index families;
- expose routing-table state consistent with Java cluster-manager decisions;
- reject unsupported allocation commands, shard states, or store contracts
  before shard ownership starts.

Required evidence:

- source-derived allocation admission fixture:
  `tools/fixtures/mixed-cluster-allocation-admission.json`
- live routing convergence probe runner:
  `tools/probe_mixed_cluster_allocation_profile.sh`
- canonical reject fixture:
  `tools/fixtures/mixed-cluster-allocation-fail-closed.json`
- canonical aggregate report runner:
  `tools/run_mixed_cluster_allocation_profile.sh`
- mixed-cluster allocation profile with routing convergence checks;
- reject cases for unsupported store type, missing allocation id, or invalid
  shard state transitions.

### 4. Peer Recovery And Relocation

Steelsearch must:

- participate in recovery start, file/chunk transfer, translog replay, and
  finalize stages;
- preserve Java-compatible checkpoint and retention-lease behavior;
- fail closed on unsupported recovery source or relocation state.

Required evidence:

- canonical recovery wire fixture:
  `tools/fixtures/mixed-cluster-recovery-wire.json`
- bounded peer recovery integration runner:
  `tools/probe_mixed_cluster_recovery_profile.sh`
- canonical fail-closed fixture:
  `tools/fixtures/mixed-cluster-recovery-fail-closed.json`
- canonical aggregate report runner:
  `tools/run_mixed_cluster_recovery_profile.sh`
- bounded recovery/relocation harness;
- artifact tree for start/chunk/translog/finalize stages;
- interruption and rollback failure cases.

### 5. Mixed-Cluster Write Replication

Steelsearch must:

- accept replicated operations with Java-compatible sequencing;
- preserve `_seq_no`, `_primary_term`, version, checkpoint, and refresh
  semantics;
- reject unsupported write families before partial replication can occur.

Required evidence:

- canonical replicated action family fixture:
  `tools/fixtures/mixed-cluster-write-replication.json`
- mixed primary/replica write harness;
- bounded action family allow-list;
- fail-closed reject cases for unsupported write action or stale term/seq_no.
- canonical aggregate report runner:
  `tools/run_mixed_cluster_write_replication_profile.sh`

### 6. Failure Handling And Restart Safety

Steelsearch must:

- survive Java-node loss, Steelsearch-node loss, restart, and rejoin scenarios;
- reject stale publications, stale replicas, or routing holes before corruption;
- prove safe recovery after interruption.

Required evidence:

- failure-injection topology runner:
  `tools/probe_mixed_cluster_failure_profile.sh`
- restart/rejoin reports;
- explicit reject ledger for non-admitted mixed-cluster states:
  `tools/fixtures/mixed-cluster-failure-ledger.json`
- canonical aggregate report runner:
  `tools/run_mixed_cluster_failure_profile.sh`

## Canonical Report Set

`Phase C` should converge on the following report families:

- `mixed-cluster-join-report.json`
- `mixed-cluster-publication-report.json`
- `mixed-cluster-allocation-report.json`
- `mixed-cluster-recovery-report.json`
- `mixed-cluster-write-replication-report.json`
- `mixed-cluster-failure-report.json`
- `mixed-cluster-reject-ledger.json`

These reports should live under a dedicated compare tree for the `Phase C`
runner, analogous to `Phase A-1` and `Phase B`.

Canonical runner:

- `tools/run-phase-c-mixed-cluster-harness.sh`

## Release Gate

Treat `Phase C` as complete only when all of the following are true:

- canonical mixed-cluster profiles exist and clean-pass for the accepted Phase C
  surface;
- join, publication, allocation, recovery, and write replication each have
  runtime-backed evidence;
- unsupported mixed-cluster states fail closed before ownership or data
  movement;
- docs and ledgers clearly distinguish accepted mixed-cluster peer behavior from
  still-deferred work.

## Completion Checklist

- mixed-cluster join runner exists and clean-passes
- mixed-cluster publication/apply/ack runner exists and clean-passes
- mixed-cluster allocation runner exists and clean-passes
- mixed-cluster recovery runner exists and clean-passes
- mixed-cluster write replication runner exists and clean-passes
- mixed-cluster failure runner exists and clean-passes
- canonical reject ledger covers unsupported membership, publication, routing,
  recovery, and write states
- `docs/api-spec/*` and `docs/rust-port/*` describe `Phase C` as peer-node
  mixed-cluster participation rather than external interop
