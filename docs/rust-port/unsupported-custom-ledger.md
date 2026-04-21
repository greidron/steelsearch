# Unsupported Cluster-State Custom Ledger

This ledger records OpenSearch cluster-state named writeables that Rust
intentionally rejects with `UnsupportedNamedWriteable` until a typed decoder and
fixture coverage exist.

Current open entries: none.

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

## Current Dispatch Coverage

Top-level cluster-state customs:

- `repository_cleanup`
- `snapshot_deletions`
- `restore`
- `snapshots`

Metadata customs are tracked in `cluster-state.md`; current dispatch coverage
matches the built-in OpenSearch `ClusterModule` metadata custom registration set
plus the selected workload-management path.
