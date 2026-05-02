# Same-Cluster Peer-Node Gap Inventory

## Scope

This document replaces the earlier `Phase C` milestone narrative with a direct
inventory of what still blocks Steelsearch from behaving as a real Java
OpenSearch peer node inside the same cluster.

The question is not whether a peer-node harness exists. The question is whether
mixed Java/Rust cluster membership is replacement-safe across coordination,
allocation, recovery, replication, and failure semantics.

## Already-Evidenced Ground

The repository already contains mixed-cluster harnesses, compare reports, and
accepted evidence families for join, publication, allocation, recovery,
write-replication, and failure scenarios.

That is necessary groundwork. It is not the same thing as saying all peer-node
contracts are production-complete.

## Remaining Gap Areas

### Discovery And Join Validation

Remaining work:

- strict node identity and role compatibility checks;
- version-skew handling;
- join rejection reason parity;
- persistent membership-state correctness across restart;
- operator-visible diagnosis when join is intentionally rejected.

### Publication Receive / Apply / Acknowledge

Remaining work:

- publication term/version monotonicity guarantees;
- delta-vs-full publication correctness;
- apply ordering under repeated updates;
- acknowledgement semantics under slow apply or reject paths;
- fail-closed behavior on unsupported cluster-state contents.

### Allocation And Routing Convergence

Remaining work:

- shard-routing-table parity across mixed nodes;
- allocation-decider parity for supported profiles;
- relocation start/finalize correctness;
- retention-lease state coherence;
- fail-closed handling for unsupported shard states.

### Peer Recovery

Remaining work:

- file/chunk/translog/finalize ordering parity;
- restart-safe recovery resume behavior;
- recovery abort semantics;
- lease and checkpoint correctness during interrupted recovery;
- mixed Java/Rust source-target matrix coverage.

### Write Replication

Remaining work:

- primary/replica sequencing under mixed topologies;
- `_seq_no`, `_primary_term`, local/global checkpoint correctness;
- refresh visibility across mixed shard copies;
- replica failure semantics;
- retry/replay behavior under interruption.

### Failure, Restart, And Rejection Semantics

Remaining work:

- node crash during publication;
- node crash during relocation or recovery;
- stale replica detection;
- restart with partial on-disk state;
- explicit reject ledgers for unsupported mixed-cluster situations.

## Replacement Significance

Same-cluster peer participation is not optional if Steelsearch is expected to
replace OpenSearch in environments that rely on gradual node-by-node migration.

Without these contracts, operators may still use Steelsearch in standalone or
externally coordinated modes, but they do not yet have a safe basis for mixed
membership cutover.

## Exit Criteria For This Category

This gap category is only closed when the declared mixed-cluster profile has:

- accepted join and reject evidence;
- accepted publication/apply/ack evidence;

Current repo-local publication ordering baseline:

- [publication-ordering-probe-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/publication-ordering-probe-matrix.md)
- [publication-ordering-report-schema.json](/home/ubuntu/steelsearch/tools/fixtures/publication-ordering-report-schema.json)
- accepted allocation and routing convergence evidence;

Current repo-local allocation/relocation baseline:

- [allocation-relocation-retention-lease-probe-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/allocation-relocation-retention-lease-probe-matrix.md)
- [allocation-convergence-report-schema.json](/home/ubuntu/steelsearch/tools/fixtures/allocation-convergence-report-schema.json)
- accepted peer recovery evidence;

Current repo-local peer recovery baseline:

- [peer-recovery-probe-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/peer-recovery-probe-matrix.md)
- [peer-recovery-report-schema.json](/home/ubuntu/steelsearch/tools/fixtures/peer-recovery-report-schema.json)
- accepted write-replication evidence;

Current repo-local write replication baseline:

- [mixed-write-replication-semantics-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/mixed-write-replication-semantics-matrix.md)
- [write-replication-report-schema.json](/home/ubuntu/steelsearch/tools/fixtures/write-replication-report-schema.json)
- accepted failure/restart/reject evidence;

Current repo-local join reject baseline:

- [join-validation-reject-matrix.md](/home/ubuntu/steelsearch/docs/rust-port/join-validation-reject-matrix.md)
- [join-validation-reject-transcripts.json](/home/ubuntu/steelsearch/tools/fixtures/join-validation-reject-transcripts.json)
- [mixed-cluster-failure-profiles.json](/home/ubuntu/steelsearch/tools/fixtures/mixed-cluster-failure-profiles.json)
- [run-phase-c-gap-harness.sh](/home/ubuntu/steelsearch/tools/run-phase-c-gap-harness.sh)
- documented operational limits for profiles that remain unsupported.
