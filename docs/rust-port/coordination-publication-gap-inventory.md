# Coordination Publication Gap Inventory

This note scopes the remaining gap between the current Steelsearch
development-only publication flow and an OpenSearch-style coordination
publication pipeline.

Replacement profile scope:

- `standalone`
- `secure standalone`
- `external interop`
- `same-cluster peer-node`

This document is primarily about `external interop` and `same-cluster
peer-node`, where publication ordering and acknowledgement semantics become
cluster-safety requirements.

## Current Evidence

The repository already has:

- discovery, pre-vote, election, voting exclusions, and joint-consensus quorum
  helpers in the daemon-owned coordination runtime;
- a development coordination path that can publish one synthetic cluster-state
  update per startup path;
- publication-shaped primitives that are enough for focused local tests.
- explicit publication-round state in the daemon-owned coordination runtime,
  including target, acked, applied, missing, failure, quorum, completion, and
  persistence fields;
- `os-cluster-state` publication apply tests for full-state cache replacement,
  full-state monotonic apply-before-ack, delta apply-before-ack, repeated diff
  monotonicity, and reject-withhold-ack behavior.

The remaining gap is that publication is not yet modeled as a repeated
leader-driven pipeline with proposal, follower validation, commit
acknowledgement, apply, and durable follower catch-up stages.

## Replacement Blockers

The main blockers are:

- no live transport publication proposal/ack/apply exchange with followers;
- the distinct commit-versus-apply lifecycle is modeled locally but not yet
  transported as a live follower exchange;
- no repeated-publication or lagging-follower catch-up path;
- no feedback from publication failure into liveness or rerun logic.

## Required Tests

- repeated publication round artifacts with evolving term/version/state UUID;
- transport-backed publication proposal/ack/apply exchange tests;
- commit-success but apply-failure coverage;
- lagging or rejoining follower catch-up transcripts;
- publication failure driving leader/follower health transitions.

## Required Implementation

The remaining work should move in these leaves:

1. transport-backed follower proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up support;
3. failure feedback into liveness, health, and rerun logic.

## Required Implementation Order

1. transport-backed proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up;
3. failure feedback into liveness and rerun logic.
