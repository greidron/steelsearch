# Restricted Index Prefix Inventory

This document is the source of truth for secure standalone restricted/system
index access-control planning. It lists the prefix families that later
`allowed/denied` probes must cover.

## Reading Rules

- `restricted` means access should default to deny for non-admin roles unless a
  later document explicitly carves out an exception.
- `system` means platform-owned metadata rather than user data.
- `probe direction` tells the next authz fixture pass what to verify.
- This inventory is intentionally prefix-oriented so alias-bypass and wildcard
  coverage can reuse the same source list.

## Prefix Inventory

| Prefix / pattern | Class | Typical ownership | Why it is sensitive | Probe direction |
| --- | --- | --- | --- | --- |
| `.opensearch*` | restricted + system | core platform metadata | catches platform-managed internal indices and future hidden descendants | default deny for `reader`/`writer`; explicit admin-only checks |
| `.plugins*` | restricted + system | plugin-owned metadata | plugin state often carries configuration, saved objects, or derived internal data | default deny for `reader`/`writer`; explicit admin-only checks |
| `.tasks*` | restricted + system | task manager / async bookkeeping | may expose task payloads, cancellation targets, or internal execution state | deny non-admin direct reads and wildcard expansion |
| `.security*` | restricted + system | security/authz metadata | may expose users, roles, mappings, cert metadata, or auth internals | strict admin-only read/write; no reader/writer exceptions |
| `.kibana*` | restricted + system | dashboard / saved-object style metadata | user-facing application state but still platform-owned and privilege-sensitive | treat as restricted until profile-specific exception exists |
| `.dashboards*` | restricted + system | OpenSearch Dashboards metadata | same class of saved objects and app-owned state as `.kibana*` | treat as restricted until explicit allowlist exists |
| `.opendistro*` | restricted + legacy system | legacy distribution metadata | old plugin/system state can remain present during migration and must not be exposed by default | deny by default; cover migration-era wildcard matching |
| `.*` via wildcard expansion | mixed hidden/system | any hidden or system namespace | broad wildcard access is the easiest bypass path | wildcard expansion must not silently include restricted prefixes for non-admin roles |

## Initial Role Policy

| Role | Default policy against restricted prefixes |
| --- | --- |
| `reader` | deny direct reads, deny wildcard expansion, deny alias indirection |
| `writer` | deny direct reads/writes, deny wildcard expansion, deny alias indirection |
| `admin` | allow explicit access subject to route-specific authz and audit checks |

## Allowed / Denied Matrix

| Prefix family | Representative route | `reader` | `writer` | `admin` | Current evidence |
| --- | --- | --- | --- | --- | --- |
| `.opensearch*` | `GET /.opensearch-restricted-authz*/_search` | deny | deny | allow | fixture cases for `reader` deny and `admin` allow |
| `.plugins*` | `GET /.plugins-restricted-authz*/_search` | deny | deny | allow | fixture cases for `writer` deny and `admin` allow |
| `.tasks*` | `GET /.tasks*/_search` | deny | deny | admin-only planned | inventory only; fixture pending |
| `.security*` | `GET /.security*/_settings` | deny | deny | admin-only planned | inventory only; fixture pending |
| `.*` wildcard expansion | `GET /*/_search` with hidden/system targets | deny implicit expansion | deny implicit expansion | explicit admin-only planned | inventory only; wildcard fixture pending |
| alias -> restricted concrete index | `GET /restricted-authz-alias/_search` | deny | deny | allow | fixture cases for alias-bypass deny/allow now present |

## Profile-Specific Hidden/System Read Policy

| Profile | Hidden user-data namespaces | Restricted system namespaces | Why |
| --- | --- | --- | --- |
| `single-node-secure` | no implicit read allowance; explicit allowlist required later | admin-only | simplest secure-standalone default; avoid accidental leakage before hidden-index semantics are fully implemented |
| `multi-node-secure` | no implicit read allowance; explicit allowlist required later | admin-only | keeps distributed/system coordination metadata protected while multi-node security parity is still incomplete |

Interpretation rules:

- Hidden does not mean readable by default.
- System/restricted namespaces stay admin-only in both profiles until a later
  document explicitly introduces an allowlist exception.
- If a future profile allows hidden-but-not-system reads, that distinction must
  be expressed here before fixture expectations are relaxed.

## Immediate Follow-up Probes

1. `GET /.opensearch*/_search` and `GET /.plugins*/_search` for `reader`/`writer` should fail closed.
2. `GET /.security*/_settings` and `GET /.tasks*/_search` should remain admin-only.
3. `GET /*/_search` with hidden/system expansion attempts must not leak restricted prefixes to non-admin roles.
4. Alias-backed access to restricted concrete indices must be denied unless a later profile-specific allowlist says otherwise.

## Notes

- This inventory is intentionally broader than the currently implemented secure
  harness. The goal is to avoid under-classifying hidden prefixes and then
  patching holes later.
- If a prefix later becomes profile-specific rather than globally restricted,
  update this document first and only then relax the fixture matrix.
