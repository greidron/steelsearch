# Mixed Primary/Replica Write Replication Semantics Matrix

This matrix defines the current same-cluster write-replication backlog for
mixed Java/Rust primary and replica topologies.

## Direction Matrix

| Direction | Why it must be isolated |
| --- | --- |
| primary-on-Java / replica-on-Rust | verifies Rust replica replay honors Java-assigned sequencing and checkpoint semantics |
| primary-on-Rust / replica-on-Java | verifies Rust primary does not emit replica requests that violate Java expectations |

## Sequencing And Visibility Matrix

| Field / behavior | What must be observed |
| --- | --- |
| `_seq_no` | monotonic primary-assigned sequencing across mixed replicas |
| `_primary_term` | epoch correctness across mixed primary ownership |
| local/global checkpoint | checkpoint evolution without regression across primary and replica sides |
| refresh visibility | read visibility after replication and refresh in mixed topology |

## Failure / Retry Matrix

| Case | What must be observed | Why it matters |
| --- | --- | --- |
| partial replica failure | failed replica is visible as failed, not silently treated as successful replication | proves partial failure does not masquerade as convergence |
| retry after partial failure | retry preserves sequencing and checkpoint correctness | proves replay is deterministic after failure |

## Report Schema Requirements

Every future write-replication artifact should include:

- `direction`
- `seq_no_ok`
- `primary_term_ok`
- `checkpoint_ok`
- `refresh_visibility_ok`
- `replica_failure_case`
- `retry_result`

## Immediate Follow-up

1. crash/restart mixed-cluster harnesses should reuse the same direction and
   failure vocabulary.
2. peer recovery and retention-lease probes should align checkpoint semantics
   with this matrix.
