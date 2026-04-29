# Snapshot Restore Failure Transcript Template

Use this sheet when comparing representative pre-restore failure paths between
Steelsearch and OpenSearch.

## Canonical comparison anchors

Record these fields for both targets:

- request shape
  - repository
  - snapshot
  - restore body subset
- HTTP status
- `error.type`
- boundary noun phrase from `error.reason`
- repository/snapshot identifiers preserved in the response, if any

Do not widen the comparison to non-contract debug details.

## Scenario 1: stale metadata

- declared failure class:
  - stale metadata rejected before restore
- Steelsearch expected anchor:
  - `status = 400`
  - `error.type = snapshot_restore_exception`
  - reason keeps `stale snapshot metadata`
- OpenSearch transcript slot:
  - status:
  - error.type:
  - boundary noun phrase:
  - notes:

## Scenario 2: corrupt metadata

- declared failure class:
  - corrupt metadata rejected before restore
- Steelsearch expected anchor:
  - `status = 400`
  - `error.type = snapshot_restore_exception`
  - reason keeps `corrupt snapshot metadata`
- OpenSearch transcript slot:
  - status:
  - error.type:
  - boundary noun phrase:
  - notes:

## Scenario 3: incompatible metadata

- declared failure class:
  - incompatible metadata rejected before restore
- Steelsearch expected anchor:
  - `status = 400`
  - `error.type = snapshot_restore_exception`
  - reason keeps `incompatible snapshot metadata`
- OpenSearch transcript slot:
  - status:
  - error.type:
  - boundary noun phrase:
  - notes:

## Reading rule

- If OpenSearch and Steelsearch use different prose around the same boundary,
  preserve:
  - status
  - `error.type`
  - the boundary noun phrase
- If the noun phrase changes from stale vs corrupt vs incompatible, prefer
  `mismatch` over broad normalization.
