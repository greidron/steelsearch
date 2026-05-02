# Publication Ordering Probe Matrix

This matrix defines the current backlog for same-cluster publication
receive/apply/ack ordering evidence.

## Case Matrix

| Case | What must be observed | Why it matters |
| --- | --- | --- |
| full publication | receive -> apply -> ack ordering for a full-state publication | proves initial or non-delta publication does not skip acknowledgement ordering |
| delta publication | receive -> delta apply -> ack ordering for a delta update | proves delta-vs-full behavior is not silently collapsed |
| repeated publication | multiple publication rounds with evolving term/version/state UUID | proves later rounds do not regress monotonicity or re-ack stale state |
| rejected publication | explicit reject/fail path before ack | proves followers do not acknowledge a publication they could not apply |

## Ack Timing And Ordering Invariants

- `receive` must happen before `apply`.
- `apply` must happen before `ack`.
- `ack` must be tied to the publication round actually applied.
- a rejected publication must not produce an `ack` event for the rejected round.

## Report Schema Requirements

Every future publication-ordering artifact should include:

- `publication_case`
- `term_before`
- `term_after`
- `version_before`
- `version_after`
- `state_uuid_before`
- `state_uuid_after`
- `received`
- `applied`
- `acked`
- `rejected`
- `monotonicity_assertions`

## Immediate Follow-up

1. allocation and peer-recovery probes should reuse the same term/version/state
   UUID vocabulary.
2. publication harness output should record full and delta cases in the same
   schema.
