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
- TCP-backed publication proposal/apply collection records round-level
  transport transcripts in the development coordination status, including
  acknowledged nodes and proposal/apply failures.
- publication health feedback that turns active publication transport/apply
  failures into follower fault records and local-manager fencing when the failed
  round no longer has an applied quorum.
- node-left publication retry support that removes failed follower targets from
  joined/voting state and starts the next publication round without promoting the
  failed active round to completed state.
- periodic liveness now schedules the node-left publication retry before
  fencing a local manager when the remaining applied voters still satisfy
  quorum.
- rejoining follower catch-up can apply a restored committed active publication
  round and allow that round to become completed on the next publication.
- periodic liveness now attempts live TCP-backed catch-up for reachable lagging
  publication followers before treating the follower as failed and scheduling a
  node-left retry.

The remaining gap is that publication is not yet modeled as a repeated
leader-driven pipeline with proposal, follower validation, commit
acknowledgement, apply, and durable follower catch-up stages.

## Replacement Blockers

The main blockers are:

- live transport publication proposal/apply collection is TCP-backed and
  transcripted, but it still needs protocol-level request/response payload
  validation beyond reachability;
- the distinct commit-versus-apply lifecycle is modeled locally and surfaced in
  transcripts, but full protocol-level follower validation remains incomplete;
- repeated-publication, restore-time follower catch-up, and reachable lagging
  follower catch-up primitives exist, but broader multi-round catch-up
  scheduling is still incomplete;
- publication failure now feeds liveness/fault state for active rounds, and
  node-left retry can drive a follow-up publication round; broader retry
  backoff and catch-up scheduling are still incomplete.

## Required Tests

- repeated publication round artifacts with evolving term/version/state UUID;
- protocol-level publication proposal/ack/apply exchange tests;
- commit-success but apply-failure coverage;
- multi-round lagging-follower catch-up scheduling transcripts;
- publication failure driving retry backoff and catch-up scheduling transitions.

## Required Implementation

The remaining work should move in these leaves:

1. transport-backed follower proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up support;
3. retry backoff and catch-up scheduling after publication health failure.

## Required Implementation Order

1. transport-backed proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up;
3. retry backoff and catch-up scheduling.
