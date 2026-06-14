# Tantivy Native Production Readiness Audit

Date: 2026-05-30 UTC

## Verdict

The Tantivy native support work is **green for the current native-readiness gate** in this worktree.

This means the native engine lib suite, native route evidence, native fixture coverage, and search compatibility evidence all pass together. The claim is scoped to the native-readiness/search compatibility gate captured below; it is not a blanket statement that every OpenSearch feature family is fallback-free native.

## Current Evidence

Commands were run from `/home/ubuntu/steelsearch` with non-masked exit status.

| Gate | Result | Evidence file |
| --- | --- | --- |
| Native engine lib suite | `722 passed; 0 failed; 0 ignored`; status `0` | `target/os-engine-tantivy-lib-test-after-native-candidate-sort-fixes.log` |
| Native route coverage | `9/9` case groups passed; `0` missing native route evidence | `target/opensearch-compare-native-route-profile-evidence-green-attempt/native-route-coverage-report.json` |
| Native route fixture coverage | `9/9` planned groups covered; `0` missing, unknown, or unprofiled groups | `target/native-readiness-audit/native-route-fixture-coverage-report.json` |
| Search compatibility | `84 passed; 0 failed; 0 skipped` | `target/search-compat-report.json` |
| Readiness artifact audit | `ok: true` | `target/native-readiness-audit/native-readiness-artifacts-check.json` |

Readiness audit command:

```bash
NATIVE_READINESS_LIB_LOG=target/os-engine-tantivy-lib-test-after-native-candidate-sort-fixes.log \
COMPARE_DIR=target/opensearch-compare-native-route-profile-evidence-green-attempt \
bash tools/run-native-readiness-audit.sh
```

Audit summary:

```json
{
  "ok": true,
  "checks": {
    "lib_suite": { "ok": true, "passed": 722, "failed": 0, "ignored": 0 },
    "native_route_coverage": { "ok": true, "passed": 9, "failed": 0, "missing_native_route_evidence": 0 },
    "native_route_fixture_coverage": { "ok": true, "planned_groups": 9, "covered_groups": 9, "missing_groups": 0 },
    "search_compat": { "ok": true, "passed": 84, "failed": 0, "skipped": 0 }
  }
}
```

## Implementation Notes From Final Repair Pass

The final repair pass focused on native candidate reduction and native aggregation hit ordering regressions.

Key fixes:

1. KNN-containing native search paths now use reduced candidate IDs plus native hit reconstruction instead of broad document scans where route evidence requires native behavior.
2. Bool candidate reduction now caps `minimum_should_match` to the actual should-clause count, including empty-should wrapper cases.
3. Vector-field lexical leaves now avoid over-including unmapped/non-search fields while preserving numeric-array vector term/match candidates.
4. Range reduction on KNN vector fields now reduces to an empty candidate set instead of scanning incompatible source values.
5. Grouped hybrid bool reduction now distinguishes same-vector-field wrappers from multi-vector-field representative intersections.
6. Multi-index native aggregation reduce now preserves the explicit sort order needed by plugin `top_hits` while single-index grouped hybrid top-hits keeps the requested native window order.

The most important behavioral distinction added in the last pass: all-required grouped hybrid should clauses use vector representative preference only when their KNN fields are disjoint. If the same vector field repeats across grouped hybrid wrappers, lexical overlap is preserved so parent wrapper queries keep valid candidates.

## Regression Coverage Confirmed

The targeted regression set passed before the full suite:

1. `hybrid_query_supports_parent_wrapper_around_grouped_representative_hybrid_subtrees`
2. `grouped_hybrid_bool_vector_match_leaf_native_helpers_keep_expected_surface`
3. `grouped_hybrid_bool_vector_match_leaf_reduces_candidate_ids_directly`
4. `grouped_hybrid_bool_vector_term_leaf_native_helpers_keep_expected_surface`
5. `grouped_hybrid_bool_vector_term_leaf_reduces_candidate_ids_directly`
6. `grouped_hybrid_bool_native_helpers_keep_expected_surface_after_reduced_candidate_preference`
7. `grouped_hybrid_bool_page_and_window_helpers_keep_expected_surface_after_reduced_candidate_preference`
8. `single_index_grouped_hybrid_top_hits_native_aggregation_preserves_requested_window`
9. `multi_index_hybrid_uses_vector_native_page_and_aggregation_reduce_with_fast_field_sort`
10. `multi_index_native_page_and_aggregation_reduce_with_fast_field_sort`

The full lib suite then passed with `722/722` tests.

## Current Promotion Criteria Status

| Criterion | Status |
| --- | --- |
| Native engine lib suite passes | Green |
| Native route evidence covers all planned groups | Green |
| Native fixture coverage covers all planned groups | Green |
| Search compatibility report passes | Green |
| Artifact audit passes | Green |

## Remaining Scope Boundaries

The current green status is for the native-readiness/search compatibility evidence gate. Broader product claims still require separate evidence if the scope expands to full OpenSearch replacement behavior, long-running performance, or every OpenSearch query/aggregation family being fallback-free native.

Recommended continuing gates for broader release confidence:

1. Run full workspace checks and any non-lib package suites required by release CI.
2. Refresh benchmark/performance evidence after candidate-reduction changes.
3. Keep route-evidence assertions mandatory for any newly claimed fallback-free native query or aggregation family.
4. Extend OpenSearch comparison beyond the current search compatibility fixture set if the release claim expands beyond native search readiness.
