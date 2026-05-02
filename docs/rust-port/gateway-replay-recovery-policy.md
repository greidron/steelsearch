# Gateway Replay Recovery Policy

This document defines the current restart-safe replay decision surface for
gateway-backed metadata recovery. It is a repo-local policy baseline for later
runtime probes, not a claim that every branch is already implemented.

## Replay Decision Matrix

| Case | Expected decision | Why | Operator-visible transcript expectation | Safe-stop condition |
| --- | --- | --- | --- | --- |
| corrupt metadata payload | fail closed | authoritative metadata cannot be trusted or rebuilt safely | explicit `corrupt metadata` / `gateway replay refused` marker in stderr or startup log | process must stop before transport or HTTP bind |
| missing shard manifest | fail closed unless the target is explicitly rebuildable and documented as derived-only | shard-local authoritative state is required for durable restart/recovery | explicit `missing shard manifest` / `restart fenced` marker | process must stop before serving traffic |
| partial replay state | fail closed for authoritative files, recover only for derived/rebuildable caches | authoritative replay cannot silently mix generations; derived state may be rebuilt | transcript must say whether the missing file was authoritative or rebuildable | if authoritative state is missing or truncated, stop before ready; if only derived state is missing, continue with explicit rebuild transcript |
| node-loss continuity | fail closed or continue only with explicit continuity proof from surviving authoritative gateway artifacts | node loss must not be papered over by development-only reconstruction | transcript must state whether continuity came from surviving authoritative manifest generations | if continuity cannot be proven from authoritative files, stop before ready |

## Replay Interruption Rules

- replay interrupted after authoritative manifest load but before complete
  metadata apply must not be treated as a successful restart.
- replay interrupted while rebuilding derived state may retry only if the
  authoritative manifest generation remains intact.
- any replay path that cannot prove which generation won must fence startup.

## Operator-Visible Error Transcript Rules

- every fail-closed replay path must emit:
  - a cause marker;
  - the authoritative file family involved;
  - a statement that startup was fenced before readiness.
- every recoverable replay path must emit:
  - the derived/rebuildable file family involved;
  - the rebuild or replay action taken;
  - a statement that authoritative state remained intact.

## Immediate Follow-up

1. restart probes should encode these decisions case-by-case instead of using a
   generic `restart failed` bucket.
2. durability compare harnesses should separate authoritative replay evidence
   from rebuild-only cache recovery.
3. startup-ordering and restart smoke harnesses should record the same operator
   transcript markers defined here.
