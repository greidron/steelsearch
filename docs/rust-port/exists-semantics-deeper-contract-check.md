# exists-semantics-deeper-contract-check

## Purpose

Check whether any deeper semantic evidence or external contract expectation
requires a stronger `exists` promise than the bounded field-presence contract
currently pinned in the repo-local pass.

## Upstream notes

- originating gap summary:
  `docs/rust-port/tantivy-native-gap-analysis.md`
- preceding bounded-semantics follow-on note:
  `docs/rust-port/exists-semantics-follow-on.md`

## Why this is now the narrower remaining question

- Repo-local docs already frame the current standalone surface in bounded
  field-presence terms.
- The runtime already narrows the supported query shape to
  `{"exists":{"field":"..."}}` and evaluates it as a bounded
  `field present && non-null` check.
- Nearby semantic evidence now also pins:
  - explicit unsupported-shape `400`
  - present-field hit behavior
  - present-but-null non-match behavior
- Official OpenSearch docs also align with much of that bounded reading:
  - `_field_names` is described as indexing field names that contain non-null
    values for `exists` query support
  - `null` is described as equivalent to an empty field unless a `null_value`
    mapping is configured
- So the remaining uncertainty is no longer "is there still a large missing
  local `exists` implementation seat?".
- It is now the narrower question of whether any deeper semantic evidence or
  external contract expectation still requires something stronger than that
  bounded contract.

## Suggested check targets

- deeper code paths or consumers that might imply stronger `exists` semantics
- external or unpublished contract docs that describe broader `exists`
  behavior
- issue threads, design notes, or compatibility discussions that mention
  stronger `exists` expectations explicitly
- downstream tests/examples, if any are available, that would fail under the
  current bounded `field present && non-null` reading

## Decision boundary

- If stronger semantic or contract evidence is found, reopen through:
  `docs/rust-port/exists-semantics-change-direction.md`
- Otherwise, keep this as a bounded semantic note and do not reopen it as a
  broader implementation axis.

## Current default reading

- No such stronger evidence has been surfaced in the current repo-local pass.
- So this task should be treated as a targeted confirmation check, not as a
  sign that a broader `exists` reopen is already likely.
- Practical stop-point reading:
  unless some concrete deeper semantic or external contract evidence can
  actually be surfaced, this targeted check should not by itself reopen the
  bounded `exists` note as broader implementation work.

## Review status after the current pass

- Within the current repo-local evidence boundary, this targeted check now
  looks close to a practical stop-point.
- The next meaningful move is not another broad local wording/code-path pass,
  but a more targeted attempt to surface concrete deeper semantic or external
  contract evidence if any such evidence exists at all.
