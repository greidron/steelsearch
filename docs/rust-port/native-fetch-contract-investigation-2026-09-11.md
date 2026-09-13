# Native Fetch REST Contract Repair

Latest directive2026-09-11: benchmarks STOPPED. Finish functional repairs before
benchmarking/optimizing performance, preserving passing tests throughout optimization.
This overrides the older per-unit benchmark steps below; preserve them as history.
Current132d8d6f full HTTP:2383 passed/288 failed/skip0, four improvements and no case
status regression. The repeated performance run was interrupted in run4 (zero-based)
with SIGINT, runner exit2; it is partial evidence, not a complete performance verdict.
No benchmark workers or test containers remain. Do not restart it during functional work.

## Verified Functional Result

Release build completed7m54s, exit0, source unchanged. Executable:
132d8d6fae13571957db6e04bd81f9a8880e2af1e5d275ff79c550f3e4d7fbfc.
Build log SHA35ec351c8b188709d9ebee64fc83b7f0ff67bdd89b93c7ac0952496f0f52d01b.
Full HTTP41 fixtures/2671 cases completed2383 passed/288 failed/zero skipped, no setup
failures, count probe passed, binary/fixtures unchanged, all report hashes verified.
Exactly four original fetch cases improved; all other case statuses are unchanged.
Raw source presence/value and fields match in the12 visibility cases and both repaired
successful fetch responses; invalid-request type/reason match. Error line/column parity
remains unimplemented and is not hidden by this claim.

HTTP execution SHA63c5a3ed6acb66a754bbf65a35e5a4a23019445ef87640a3ed545155559958b0;
artifacts/http-audit.json SHAed12141d7ab398eb65e154cbc1bf01af1c6fbe43fa2e8f42a897195962b71fbb.
Reference: OpenSearch3.7.0-SNAPSHOT buildf991609d190dfd91c8a09902053a7bbfe0c27b3e.
Functionality is improved, not fully compatible or release-ready. The interrupted
benchmark is NOT numeric-budget failure evidence for this candidate: execution was
cancelled at user request, and it must not be resumed during functional repair.

The current candidate build cache was cleaned only after preserving the executable
and logs. To recover disk headroom, inactive target/release was also fully archived:
4817 regular files were hash-verified from the decompressed archive before scoped
cargo clean --release --target-dir target. Cleanup exited0; archive281001623 bytes
and restoration ledger are in artifacts/root-release-cache.tar.gz and
artifacts/root-release-cache.json. Ledger SHA:
5639226c351290354c7a751c995c209443d8277da8a7db4b2808d8b9a6fedee5.
Restore old target/release artifacts from this archive when needed; candidate, initial
v0.6.0, source trees, test/benchmark reports and unrelated Docker services were retained.

Status: implementation draft, not accepted. Parent measured executable7d83e363 has
2379 HTTP passes/292 failures, with the complete six-run/twelve-topology cumulative
performance gate FAIL. Preserve that candidate, its source and all measured evidence.

## Scope And Evidence

Working source: target/core-replacement-c06/native-fetch-contract-source, copied from
native-fetch-visibility-candidate/source. The remaining four cases in
search-native-fetch-projection-contract.json establish these REST boundary defects:

| Request | OpenSearch contract | Draft repair |
| --- | --- | --- |
| `_source:{fetch:false}` | 400 parsing_exception, unknown VALUE_BOOLEAN in fetch | Reject in REST source validation |
| Body `_source_excludes` | 400 parsing_exception, unknown START_ARRAY | Reject source selector siblings before URL merging |
| `fields:[]` with `_source:false` | 200, neither source nor fields | Permit empty fetch list, preserve type checks |
| `_source:[label]` without fetch | Filtered source only | Clear engine projection fields at native REST conversion |

Evidence: native-fetch-visibility-release-live/search-native-fetch-projection-contract-report.json,
including raw OpenSearch responses. Local OpenSearch FetchSourceContext.fromXContent
rejects the fetch object key; SearchSourceBuilder accepts empty fields lists. These
are adapter defects, not missing Tantivy capabilities. No source evaluator, document
scan, replacement scorer or new field reader is introduced. Internal engine source
projection contracts remain unchanged. Existing parsing response helpers preserve
status/type/reason/root_cause; exact source line/column parity is not established.

Source-only requests must not imply REST fields. Native conversion clears the typed
hit fields before JSON serialization when no fetch option is present. It does not
remove source, sort, explanation, inner hits, authentication or authorization checks.
Rejecting body selector siblings must precede the insertion of valid URL selectors;
do not break URL `_source_excludes` or `_source` includes/excludes objects.

## Implementation And Verification

1. Parent edits standalone_runtime.rs only; Terra adds bounded REST regression tests
   in native_fetch_projection_tests.rs. Preserve the previous internal-helper tests.
2. Review the combined diff and freeze a new source manifest. Run the full engine
   suite and full node library/binary suite, preserving failed attempts separately.
   Resolve conflicting expectations against actual reference behavior, not merely
   the new implementation. Focused tests are supplemental diagnostics.
3. Build with a separate target directory and record actual executable/toolchain,
   source manifest, argv, environment and test/build log identities. Do not reuse the
   measured parent executable as this draft's identity.
4. Execute all41 HTTP fixtures/2671 cases, keeping all prior cases, source-visibility
   comparator checks, raw response evidence and reference identity verification.
   Audit added regressions and the four expected improvements individually. Additional
   cases expand the denominator; never drop failures or loosen numeric comparisons.
5. After this implementation unit execute the full non-plugin six-run/twelve-topology
   benchmark before completion. Use identical actual workload, durability, security
   and resource settings for candidate and separately built v0.6.0. Record identities.
   No builds, tests, agents or diagnostic workloads during timed measurement.
6. Require each topology throughput >=95% and each scenario mean/p95/p99 <=105% of
   the fixed initial published v0.6.0, cumulatively. Preserve original evidence and
   main-plan repeat rules. No averaging, offsetting or baseline reset. Over-budget
   candidates remain unaccepted and unreleased; attribution/exclusion or explicitly
   approved exceptions follow the main plan without discarding correctness/safety.

Functional-first sequencing is not a performance waiver. Neither this draft nor its
tests establish a smaller HTTP failure count until the new executable is tested live.

## Initial Test Evidence

The frozen source has2908 files, manifest SHA
e7e44190e7bed7a752f24878b6e6f9a1794cd8539873e27f9e20d5c42476e4c8,
recorded in native-fetch-contract-candidate/artifacts/source.sha256. Exactly two files
differ from the parent: standalone_runtime.rs and native_fetch_projection_tests.rs.
Terra added one REST test covering all four contracts and ordinary/PIT/initial scroll
responses. Parent additionally asserts parsing exception types, nonempty URL results
and independently fetched numeric docvalues after source filtering.

Full engine tests completed exit0:946+7+4+9=966 passed, no failures; compile2m18s,
tests14.33s/8.40s/2.18s/0.17s. Engine log SHA:
f8290edce88c84ef6a2fe4721a97f30deeb095f853746cef0fc63907e1817829.
Full node library/binary tests were started next. Their result and the release/HTTP/
full performance gate are not yet established by this engine-only evidence.

The subsequent full node run completed exit0:684 library+459 binary=1143 passed,
zero failures; compile2m08s, tests4.33s/11.74s. Log SHA:
7ce2768ef85b6f75e45e1425db4257d9ffbdb2c50455a69609a0e076f23703ea.
The complete source manifest was reverified unchanged after both suites. There were
no additional expectation edits after the frozen manifest. New REST regression
assertions pass, but live HTTP improvement and performance acceptance still require
the separately built new executable and full gates. Do not report292->288 yet.
