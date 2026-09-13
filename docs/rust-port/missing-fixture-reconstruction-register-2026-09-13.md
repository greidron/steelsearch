# Missing Fixture Reconstruction Register

## Rule

The seven preserved inputs listed here are unavailable. A current-reference fixture
may be added under a new `tools/fixtures/` name, but it is new coverage, not a
recovery of the original immutable input. It must not be renamed to the missing path
or counted as completing the strict 41-input preserved run.

Each replacement must record its source request shapes, pinned OpenSearch execution
report, and scope. It must leave the original row marked unavailable. This follows
the functional failure ledger and keeps current compatibility evidence separate from
historical proof.

`git rev-list --all --objects` was checked on 2026-09-13 and contains none of the
seven original paths. No commit-history recovery is currently available.

## Inventory

| Missing immutable input | Current status | Separately named current-reference coverage |
| --- | --- | --- |
| `target/core-replacement-c05/bool-minimum-compat.json` | Unavailable. The documented original had 10 boundary inputs, positive/negative variants, 1/3 shards, and hit/score/total/count/value-count assertions. | Not yet reconstructed. Build a new minimal boundary fixture from the documented dimensions and a fresh pinned OpenSearch report. |
| `target/core-replacement-c05/nested-bool-canonical-compat.json` | Unavailable. Original request content is not recoverable. | Not yet reconstructed. Establish a narrow nested-bool corpus and canonical request shapes from a fresh reference. |
| `target/core-replacement-c05/nested-bool-final-compat.json` | Unavailable. Original request content is not recoverable. | Not yet reconstructed. Keep it distinct from the canonical replacement and document any added edge case. |
| `target/core-replacement-c06/pipeline-selection-compat.json` | Unavailable. | `tools/fixtures/search-pipeline-selection-replacement-compat.json`, covering eight documented single/multi-index, size, and sibling pipeline-aggregation shapes. |
| `target/core-replacement-c06/native-ranking-audit/reference-fixture.json` | Unavailable. | `tools/fixtures/search-native-compound-ranking-compat.json`, a broader 60-case current-reference ranking fixture. It is not byte-equivalent to the original audit artifact. |
| `target/core-replacement-c06/native-minimum-one/single-hit-reference-fixture.json` | Unavailable at its original path. | `tools/fixtures/search-native-bool-minimum-one-scores-compat.json` is byte-identical to the formerly recorded single-hit content, but remains a separately named permanent regression fixture. |
| `target/core-replacement-c06/native-minimum-one/stable-reference-fixture.json` | Unavailable. Original request content is not recoverable. | The minimum-one permanent fixture provides related coverage but is not asserted to reproduce this separate stable-reference input. |

## Admission Checklist

1. Use a new `tools/fixtures/*-replacement-compat.json` name and put the missing
   original path in its provenance note.
2. Run the fixture against a clean pinned OpenSearch instance and the candidate with
   raw responses preserved.
3. Apply only scoped comparator rules: execution-time metadata is type/range checked;
   documents and documented result contracts remain exact.
4. Keep the strict preserved inventory missing count unchanged and report the new
   fixture result separately.
