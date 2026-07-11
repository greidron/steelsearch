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
  monotonicity, regressive-term rejection before ack, and reject-withhold-ack
  behavior.
- source-level publication ordering observations with schema-shaped
  receive/apply/ack/reject fields for full, delta, and rejected publication
  cases.
- publication health feedback that turns active publication transport/apply
  failures into follower fault records and local-manager fencing when the failed
  round no longer has an applied quorum.
- node-left publication retry support that removes failed follower targets from
  joined/voting state and starts the next publication round without promoting the
  failed active round to completed state.

The remaining gap is that publication is not yet modeled as a repeated
leader-driven pipeline with proposal, follower validation, commit
acknowledgement, apply, and durable follower catch-up stages.

## Replacement Blockers

The main blockers are:

- no live transport publication proposal/ack/apply exchange with followers;
- the distinct commit-versus-apply lifecycle is modeled locally but not yet
  transported as a live follower exchange;
- no repeated-publication or lagging-follower catch-up path;
- publication failure now feeds liveness/fault state for active rounds, and
  node-left retry can drive a follow-up publication round; automatic retry
  scheduling is still incomplete.

## Required Tests

- repeated publication round artifacts with evolving term/version/state UUID;
- transport-backed publication proposal/ack/apply exchange tests;
- commit-success but apply-failure coverage;
- lagging or rejoining follower catch-up transcripts;
- publication failure driving automatic retry scheduling transitions.

## Required Implementation

The remaining work should move in these leaves:

1. transport-backed follower proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up support;
3. automatic retry scheduling after publication health failure.

## Required Implementation Order

1. transport-backed proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up;
3. automatic retry scheduling.
