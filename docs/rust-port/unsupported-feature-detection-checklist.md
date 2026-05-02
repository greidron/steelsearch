# Unsupported Feature Detection Checklist

This checklist defines which source-side features must be screened before a
standalone cutover. Its purpose is to separate hard migration blockers from
bounded degraded cases and to make the detection method explicit.

## Classification Rules

- `migrate-blocking` means cutover must stop until the feature is removed,
  translated, or explicitly supported.
- `degraded-but-allowed` means the workload may proceed only if the operator
  accepts the bounded semantic gap and records the waiver.

## Feature Inventory

| Feature family | Representative feature | Classification | Why | Detection method |
| --- | --- | --- | --- | --- |
| Search DSL | unsupported vector/k-NN options outside current fail-closed surface | migrate-blocking | target semantics are not equivalent and may reject or mis-evaluate requests | fixture-based + API-based |
| Search DSL | unsupported rescore/highlight/suggest options outside the documented bounded subset | migrate-blocking | request semantics are not safely preservable in the current standalone target | fixture-based + API-based |
| Search DSL | documented partial features such as bounded `profile`, partial `function_score`, partial `script_score` | degraded-but-allowed | route exists but semantics are intentionally narrower | fixture-based + metadata-based workload review |
| Plugin feature | Java plugin-owned state without a typed Rust-native translator | migrate-blocking | plugin state is outside the standalone replacement boundary | metadata-based |
| Plugin feature | OpenSearch Security / plugin APIs not represented in the current bounded security harness | migrate-blocking | authz/authn semantics are incomplete for unsupported plugin-specific state | API-based + metadata-based |
| Mapping feature | unsupported field types or mapping parameters without explicit bounded evidence | migrate-blocking | restore/search behavior may diverge silently | metadata-based + fixture-based |
| Mapping feature | bounded metadata families already covered by settings/mappings/templates/data-stream preservation evidence | degraded-but-allowed | target preserves a bounded subset, not full OpenSearch mapping space | metadata-based |
| Index feature | restricted/system index namespaces required by the source workload | migrate-blocking unless the target profile explicitly supports the same namespace policy | hidden/system state is not general-purpose application data | metadata-based + API-based |
| Index feature | alias/template/data-stream usage within the documented bounded preservation set | degraded-but-allowed | preserved in bounded form, but not full production replacement semantics | metadata-based + fixture-based |

## Detection Method Categories

### API-based

Use live route calls or exported API summaries to detect:

- unsupported route/option usage;
- restricted/system index access requirements;
- plugin/security API dependencies;
- snapshot/repository and migration helper coverage.

### Metadata-based

Inspect source-side metadata to detect:

- unsupported mappings and field types;
- plugin-owned templates, scripts, or settings;
- restricted index namespaces;
- alias/data-stream/template usage outside the bounded target contract.

### Fixture-based

Use repo-local compatibility fixtures and reports to detect:

- bounded search semantics that are already proven;
- fail-closed unsupported options;
- metadata preservation coverage;
- snapshot/migration cutover evidence that already exists.

## Operator Decision Rule

- any `migrate-blocking` feature stops Phase 1 until removed, translated, or
  explicitly reclassified by new evidence.
- any `degraded-but-allowed` feature requires a recorded waiver tied to the
  bounded target semantics and the exact workload scope.

## Immediate Follow-up

1. Phase 1 of the standalone cutover runbook should treat this checklist as a
   required input.
2. snapshot/restore completeness matrix should cross-reference these blockers.
3. future acceptance harness work should emit a machine-readable blocker list.
