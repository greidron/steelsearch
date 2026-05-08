# os-node runtime stronger split go/no-go gate

## Decision

Current conclusion: `os-node-runtime` stronger scaffold should stop at design conclusion and is `NO-GO` as the next low-risk patch candidate.

## Why it is no-go right now

1. Current phase1 thin-core split is valid as a governance boundary, but it did not improve `os-node/src/lib.rs` rebuild cost in practice.
2. Warm `cargo build -vv` probe still shows `crates/os-node/src/lib.rs` touches recompiling the giant `os-node` lib unit while `os-node-rest-core` stays fresh.
3. The realistic stronger scaffold is not a small move. It requires the direct closure of:
   - `standalone_runtime.rs` (`28751` lines)
   - route-registration modules `25` files (`6302` lines)
   - `NodeInfo` resolution
4. Total stronger-scaffold scope is `27 files / 35053 lines`, which is too large for the next low-risk patch in the current loop.

## What remains true

1. A stronger performance-oriented split is still more plausible at the `standalone_runtime` giant-body boundary than at the already-small facade side.
2. The current `os-node-rest-core` crate remains useful as a phase1 governance scaffold.
3. The `os-node` crate can continue acting as the facade layer while any future runtime-heavy split moves behind it.

## Go conditions

Re-open the stronger split only if at least one of these is true:

1. The user explicitly asks for the large refactor despite the `27 files / 35053 lines` scope.
2. A narrower intermediate boundary is discovered that materially reduces the closure below the current scope.
3. A concrete performance target is stated that justifies a large structural refactor and cannot be met with smaller changes.

## No-go action for now

1. Keep the current phase1 thin-core scaffold.
2. Treat the stronger split branch as a documented design conclusion, not an active implementation task.
3. Do not start moving `standalone_runtime.rs` and its route-registration closure in the next patch without reopening this gate.
