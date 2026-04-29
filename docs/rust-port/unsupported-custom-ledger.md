# Unsupported Cluster-State Custom Ledger

This ledger records OpenSearch cluster-state named writeables that Rust
intentionally rejects with `UnsupportedNamedWriteable` until a typed decoder and
fixture coverage exist.

Current open entries: none.

## Built-In Registry Audit

The OpenSearch `3.7.0` built-in cluster-state custom registry was audited
against local `../OpenSearch` source in `ClusterModule#getNamedWriteables()`.
All built-in `Metadata.Custom` and top-level `ClusterState.Custom` entries are
represented in the Rust reader registries documented in
`cluster-state-custom-registry.md`.

No built-in custom is intentionally deferred at this point, so there are no
compatibility-ledger rows to add. Plugin-provided custom metadata remains out of
scope until a concrete plugin interop target is selected.

## Live Probe Checks

2026-04-21 live probe against local Java OpenSearch `3.7.0-SNAPSHOT` completed
with `cluster_state_remaining_bytes=0` and no `UnsupportedNamedWriteable`
error. The minimal single-node state exposed only the built-in
`index-graveyard` metadata custom, which is already covered by the Rust reader
registry, so no new ledger row was added.

## Recording Template

When a live probe fails with `UnsupportedNamedWriteable`, add a row before
widening decode support.

| Date | OpenSearch version | Section | Name | Reproducer | Captured error | Decoder plan | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | 3.x.y or commit SHA | `metadata.custom` or `cluster_state.customs` | custom name | command or REST setup | exact error line | prefix fields to decode, fixture needed | open |

## Policy

- Unknown cluster-state customs must fail closed rather than being skipped.
- Add a Java fixture or live transcript before marking an entry decoded.
- Update `wire-protocol.md` summary keys when a newly decoded custom exposes
  stable identity fields through `os-tcp-probe`.
- Close a ledger row only after `cargo test --workspace` and the live or fixture
  transcript both show `cluster_state_remaining_bytes=0`.

## Current Reader Registry Coverage

Top-level cluster-state customs:

- `repository_cleanup`
- `snapshot_deletions`
- `restore`
- `snapshots`

Metadata customs are tracked in `cluster-state-custom-registry.md`; current
reader registry coverage matches the built-in OpenSearch `ClusterModule`
metadata custom registration set plus the selected workload-management path.
