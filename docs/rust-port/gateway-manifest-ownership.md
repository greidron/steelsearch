# Gateway Manifest Ownership

This document fixes the current ownership and update-ordering contract for
gateway-backed runtime state. It is a backlog baseline, not a claim that every
rule below is already enforced in code.

## Reading Rules

- `authoritative source` means the file family that must win on restart and on
  corruption-fencing decisions.
- `derived cache` means a file that may be rebuilt from authoritative state and
  therefore must not silently override it.
- `update ordering` means the write/replace order that later replay tests
  should expect and validate.

## Ownership And Update Ordering

| File family | Current role | Authoritative source | Derived cache | Rebuildable | Required update ordering |
| --- | --- | --- | --- | --- | --- |
| `shared-runtime-state.json` | standalone runtime state snapshot used during startup and restart | yes for standalone runtime-local state | no | bounded/manual rebuild only | write new state snapshot only after the corresponding authoritative metadata generation is complete |
| `cluster_metadata_manifest` and gateway-owned cluster metadata files | cluster metadata generation pointer and metadata payload family | yes for cluster metadata | no | no | persist new metadata payload first, then atomically advance the manifest/generation pointer |
| production-membership manifest | persisted view of cluster membership / manager-facing node identity | yes for membership view | no | bounded/manual rebuild only | write membership payload before publishing the manifest generation that points to it |
| shard manifest family | persisted shard-local authoritative state and routing-adjacent recovery input | yes for shard-local restart/recovery | no | no | persist shard payload and checksum first, then advance manifest generation |
| local caches and rebuildable runtime projections | rebuilt helper state derived from authoritative manifests and metadata | no | yes | yes | must never be written in a way that overrides or races ahead of authoritative manifest generations |

## Failure Fence Rules

- concurrent writers must not both advance the same authoritative generation;
  one writer must win and the other must fail closed.
- stale manifests must not be accepted if they point to an older generation than
  the newest durable metadata payload already present on disk.
- truncated manifests or truncated authoritative payloads must fail closed
  before transport or HTTP admission.
- rebuildable caches may be discarded, but their absence must not be mistaken
  for authoritative state loss.

## File-Family Classification Matrix

| File family | Authoritative | Derived | Rebuildable | Replacement blocker if missing/corrupt |
| --- | --- | --- | --- | --- |
| `shared-runtime-state.json` | yes, for standalone-local runtime state | no | bounded/manual only | yes |
| `cluster_metadata_manifest` | yes | no | no | yes |
| gateway-owned cluster metadata payloads | yes | no | no | yes |
| production-membership manifest | yes | no | bounded/manual only | yes |
| shard manifest family | yes | no | no | yes |
| local projection/cache files | no | yes | yes | not by themselves, unless rebuild logic is broken |

## Immediate Follow-up

1. restart-safe replay tests must use this ownership table when deciding
   fail-closed versus rebuildable paths.
2. startup-ordering transcripts must show gateway/manifest load before transport
   and HTTP bind.
3. durability compare harnesses must report authoritative versus derived file
   families separately.
