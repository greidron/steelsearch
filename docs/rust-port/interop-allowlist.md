# External Interop Allowlist

This document defines the current bounded allowlist for external Java
OpenSearch interop. It does not claim broad mixed-mode support; it fixes which
surfaces are allowed, under what preconditions, and why the rest must reject.

## Read Coordination Allowlist

| Route / family | Transport action class | Preconditions | Fail-closed reason if preconditions are not met |
| --- | --- | --- | --- |
| cluster observation and decoded state reads | handshake, bounded probe, bounded cluster-state observation | peer handshake succeeds; decoded cluster-state cache is fresh enough for the declared profile; upstream remains connected | stale cache, unsupported metadata shape, or remote disconnect makes the local decoded view non-authoritative |
| bounded read coordination that depends only on documented decoded metadata | probe/observation-only action family | route is in the declared interop profile allowlist; index/alias resolution does not require unsupported metadata families | missing metadata, stale publication, or unsupported routing shape would make the read silently unsafe |

## Write Forwarding Allowlist

| Route / family | Transport action class | Preconditions | Fail-closed reason if preconditions are not met |
| --- | --- | --- | --- |
| explicitly profiled write-forwarding paths only | allowlisted forwarding action only | profile explicitly enables forwarding; request shape is in bounded supported subset; decoded metadata is fresh; upstream remains connected | forwarding outside the bounded subset could corrupt ordering or route against stale metadata |
| no generic write forwarding | all non-allowlisted write/admin actions | none; default is reject | unsupported write forwarding must reject before transport dispatch rather than guessing at action semantics |

## Unsupported Forwarded Action Rule

- if a transport action is not explicitly listed in the bounded forwarding
  allowlist, reject it before dispatch.
- if a route depends on a transport action that is only `planned` or
  unvalidated in the current inventories, reject it before dispatch.

Linked inventories:

- [transport-actions.md](/home/ubuntu/steelsearch/docs/api-spec/generated/transport-actions.md)
- [transport-action-priority.md](/home/ubuntu/steelsearch/docs/rust-port/transport-action-priority.md)

## Immediate Follow-up

1. reject fixtures should pin representative unsupported forwarded actions.
2. mixed-mode failure harnesses should use this allowlist as their precondition
   source.
