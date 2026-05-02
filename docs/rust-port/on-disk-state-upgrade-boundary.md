# On-Disk State Compatibility And Upgrade Boundary

This document defines the current policy boundary for persisted Steelsearch
state. It is a compatibility and operator-safety baseline, not a statement that
every file family already carries the final schema machinery.

## Versioned State Schema Matrix

| File family | Requires explicit schema/version | Why | Compatibility rule |
| --- | --- | --- | --- |
| `shared-runtime-state.json` | yes | restart depends on interpreting persisted runtime-local state deterministically | reject unknown or incompatible schema versions |
| `cluster_metadata_manifest` | yes | authoritative metadata generation pointer must not be guessed across versions | reject incompatible manifest version; do not auto-upgrade in place |
| gateway-owned cluster metadata payloads | yes | settings, aliases, templates, data streams, and cluster metadata replay must remain generation-safe | require explicit compatible decoder; otherwise fail closed |
| production-membership manifest | yes | membership and manager-facing identity state must not silently drift across versions | reject incompatible schema and require explicit migration path |
| shard manifest family | yes | shard-local recovery and routing continuity depend on stable on-disk semantics | reject incompatible schema unless an explicit offline migrator exists |
| rebuildable local caches/projections | optional but recommended | derived state may be discarded, but version tagging still helps safe rebuild decisions | may rebuild when missing or incompatible, but must not masquerade as authoritative state |

## Backward-Incompatible Change Guardrails

- any backward-incompatible change to an authoritative file family must:
  - bump an explicit schema/version marker;
  - document whether older state is readable, rejected, or migratable;
  - update operator-facing restart and migration guidance.
- do not silently reinterpret older authoritative bytes under a new schema.
- do not write a new authoritative schema unless startup/replay code can also
  detect and reject unsupported older or newer generations safely.

## Auto-Migrate Policy

Current baseline policy:

- incompatible authoritative on-disk state must not be auto-migrated during
  normal startup;
- normal startup must fail closed when it detects an incompatible authoritative
  schema;
- migration, if supported, must be explicit and operator-invoked through a
  dedicated tool or documented offline process.

This means:

- `shared-runtime-state.json`, manifest files, gateway metadata payloads, and
  shard manifests must not be rewritten speculatively during startup;
- rebuildable caches may be dropped and regenerated, but only when they are
  clearly classified as derived state;
- any future auto-migrate proposal is a separate compatibility track and must
  come with its own evidence and rollback plan.

## Operator-Facing Decision Rules

| Detection result | Expected behavior |
| --- | --- |
| compatible authoritative schema | continue startup/replay |
| unknown authoritative schema version | fail closed before readiness |
| known incompatible authoritative schema version | fail closed before readiness; require explicit migration tool/process |
| incompatible derived-only cache schema | discard/rebuild if authoritative inputs are intact; otherwise fail closed |

## Immediate Follow-up

1. durability compare and replay probes should record schema/version markers once
   they are present on disk.
2. migration/cutover work should reference this policy when deciding whether a
   converter is allowed.
3. any future upgrade tool must prove rollback and non-destructive operation
   against authoritative file families.
