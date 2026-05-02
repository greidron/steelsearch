# Decoded Cluster-State Cache Fail-Closed Policy

This policy defines how the external-interop cache must behave when decoded
cluster-state becomes stale, incomplete, or unavailable. The goal is to reject
unsafe forwarding and stale reads before they can create silent divergence.

## Decision Matrix

| Case | Expected decision | Why | Affected surface |
| --- | --- | --- | --- |
| stale metadata cache | reject read/write forwarding that depends on stale metadata | index resolution, alias expansion, and routing decisions cannot rely on stale decoded state | read coordination and write forwarding |
| cache refresh miss | reject until a fresh authoritative view is decoded or operator policy says observe-only | absence of a refresh result is not proof that the old cache is still valid | forwarded read/write paths |
| remote disconnect | reject forwarding and surface remote-unavailable transcript | disconnected upstream means the cached state may no longer be authoritative | forwarded read/write paths and cluster observation |
| publication lag beyond declared bound | reject forwarding and stale-cache reads | declared interop boundary requires bounded cache freshness | read coordination and metadata-dependent forwarding |

## Operator-Visible Transcript Rules

- every stale-cache reject path must name:
  - the stale or missing cache condition;
  - the route/action family being rejected;
  - that fail-closed behavior was chosen instead of stale forwarding.
- remote disconnect must be distinct from stale cache age:
  - `remote disconnect` means the upstream is unavailable now;
  - `stale cache age` means the upstream may exist but the local decoded view is
    too old to trust.

## Immediate Follow-up

1. reject fixtures should encode stale metadata cache, cache refresh miss, and
   remote disconnect separately.
2. forwarding allowlist work should consume this policy rather than weakening
   it implicitly.
