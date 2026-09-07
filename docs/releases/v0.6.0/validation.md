# v0.6.0 Validation Record

Source implementation commit: `d987c0677374dfd88f0d393b9ad9c486b1ace31c`.
The subsequent release commit adds documentation and evidence only.
`build-provenance.json` records the final clean local-crate build and its exact
match to the benchmark executable. The GitHub release is source plus evidence;
no multi-platform binary/container certification is claimed.

## Results

| Check | Result |
| --- | --- |
| Engine library | 825 passed |
| Node library | 585 passed |
| Query DSL library | 133 passed |
| Daemon binary, one test thread | 457 passed |
| Daemon binary, initial parallel run | 456 passed, one plugin cache test failed; isolated retry passed |
| Release policy | 24 passed |
| Benchmark tools | 30 passed |
| Search comparison tools | 15 passed |
| Native closure runner tools | 34 passed |
| Native closure status tools | 21 passed |
| Root cluster/node comparison tools | 4 passed |
| Formatting and diff whitespace | Passed |
| Fresh live core / strict / semantic / write | 1180 / 922 / 79 / 78 passed, zero failures/skips |
| Original failure closure | 27 core entries passed, two plugin entries excluded |
| Mandatory release performance format | Passed locally; publication also requires the tag's policy CI |

These unit-tool tests do not mean the broader production readiness gate passed.
The existing vector promotion checker still rejects missing/non-passing plugin
evidence; plugins remain unsupported and excluded, not relabelled as passing.
The vector reject-ledger schema check passes. The initial parallel plugin-cache
test failure remains a test isolation/repeatability limitation, not proven fixed
by the passing serial run.

## Evidence

`performance-evidence.zip` is produced by the validated publisher from the
committed five-file bundle. `steelsearch-v0.6.0-validation.tar.gz` includes final
build provenance, prior published-source build provenance, raw live comparisons,
reference identities, unit logs, development-control comparison summaries and
the discarded shared-cache build report. `SHA256SUMS` covers that supplementary
archive. The initial discarded executable is not distributed as a release binary.

The retained candidate's final source rebuild has SHA-256
`db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57`.
Its first shared-cache rebuild had SHA-256 `83a5e8f8...` and reproduced four
already-repaired aggregation failures. The local release artifacts had been
replaced while building the previous published source in another worktree.
Cleaning every workspace package's release artifacts and rebuilding reproduced
the retained executable exactly; fresh live comparison then passed all suites.
The published-source reference itself was built from a newly checked-out,
unmodified tag and its locked dependencies; its recorded identity is unchanged.

Performance comparisons remain single 60-second runs per system/topology,
with the environment and durability differences disclosed in the release notes.
Strict performance preservation versus the separate development control remains
unproven. User approval to publish v0.6.0 does not waive that separate objective
or authorize a production OpenSearch cutover.
