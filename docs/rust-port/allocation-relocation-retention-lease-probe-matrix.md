# Allocation / Relocation / Retention-Lease Probe Matrix

This matrix defines the current same-cluster convergence probe backlog for
allocation, relocation, and retention lease behavior.

## Mixed-Cluster Allocation Allow / Deny Matrix

| Case | Expected decision | Why |
| --- | --- | --- |
| supported mixed-cluster allocation shape | allow | allocation preconditions are satisfied for the declared profile |
| unsupported or unsafe mixed-cluster allocation shape | deny | unsupported allocation could produce divergent shard ownership |

## Relocation Probe Matrix

| Case | What must be observed | Why it matters |
| --- | --- | --- |
| relocation start | relocation enters explicit started state with source/target identity | proves relocation does not stay implicit |
| relocation finalize | finalize moves ownership to the target cleanly | proves no duplicate ownership or incomplete handoff remains |
| relocation interruption | interrupted relocation leaves an explicit fail-closed or resumable state | proves crash/interruption does not silently corrupt shard placement |

## Retention-Lease Probe Matrix

| Case | What must be observed | Why it matters |
| --- | --- | --- |
| retention lease grant | lease is created with explicit owner/sequence context | proves recovery preconditions are explicit |
| retention lease update | lease advances without regressing sequence ownership | proves replication/recovery state stays monotonic |
| retention lease remove | lease removal is explicit and visible in shard state evolution | proves cleanup does not leave stale recovery ownership |

## Shard State Timeline Report Requirements

Every future convergence artifact should include:

- `probe_case`
- `shard_id`
- `source_node`
- `target_node`
- `allocation_decision`
- `relocation_phase`
- `retention_lease_phase`
- `timeline`
- `final_state`

The `timeline` field should be an ordered list of shard-state transitions such
as:

- `allocated`
- `relocation_started`
- `relocation_finalized`
- `relocation_interrupted`
- `lease_granted`
- `lease_updated`
- `lease_removed`

## Immediate Follow-up

1. peer recovery probes should reuse the same source/target and timeline
   vocabulary.
2. replication semantics should consume the same retention-lease monotonicity
   assumptions.
