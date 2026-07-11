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

## Current Source Evidence

- `os-cluster-state::publication_full_state_receive_apply_replaces_local_cache`
  pins full-state receive/apply cache replacement, and
  `os-cluster-state::publication_full_state_ack_requires_monotonic_version`
  pins the publication apply/ack path rejecting equal or stale full-state
  versions.
- `os-cluster-state::publication_full_state_ack_rejects_regressive_term` and
  `os-cluster-state::publication_diff_ack_rejects_regressive_term` pin full and
  delta publication rejection before ack when the incoming coordination term
  regresses.
- `os-cluster-state::publication_diff_apply_acknowledges_only_after_successful_apply`
  pins delta apply before acknowledgement.
- `os-cluster-state::repeated_publication_diff_apply_requires_monotonic_versions_before_ack`
  pins repeated diff publication monotonicity and rejects equal or stale
  versions before acknowledgement.
- `os-cluster-state::publication_reject_integration_preserves_cache_and_withholds_ack`
  pins reject paths that preserve the previous cache and withhold ack.
- `os-cluster-state::publication_ordering_observation_records_apply_ack_and_reject_events`
  pins the report-schema-shaped receive/apply/ack/reject observation fields for
  full, delta, and rejected publication cases.

## Ack Timing And Ordering Invariants

- `receive` must happen before `apply`.
- `apply` must happen before `ack`.
- `ack` must be tied to the publication round actually applied.
- a rejected publication must not produce an `ack` event for the rejected round.

## Report Schema Requirements

Every publication-ordering artifact should include:

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
2. publication harness output should emit the source-level observation schema
   for live full and delta cases.
