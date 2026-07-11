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
- live `publish_state` request decode/apply now uses the Rust-native
  full-state/diff publication path; the old Java parse helper path has been
  removed from the runtime.
- `publish_state` response payload generation now defaults to the Rust-native
  `PublishWithJoinResponse` writer path, with the Java builder retained only as
  an explicit diagnostic fallback.
- TCP-backed publication proposal/apply collection validates an OpenSearch
  cluster-state transport action frame, validates full-state publication
  apply-before-ack semantics, and records round-level transport transcripts in
  the development coordination status, including acknowledged nodes,
  payload-validated nodes, semantic-validated nodes, and proposal/apply
  failures.
- publication transport transcripts now include structured per-follower
  validation events for proposal/apply connect, action-frame validation, and
  publication-semantics validation, including pass/fail status and failure
  reasons.
- mixed-failure validation event tests now cover proposal/apply invalid address
  failures and proposal/apply transport connect failures as structured
  per-follower transcript events.
- validation event tests now also inject proposal/apply action-frame failures
  and publication-semantics failures through the same collector path, fixing the
  transcript shape for pass-before-fail ordering and failure cleanup.
- the mixed-cluster coverage gate now requires `multi-node-transport-admin`
  reports to carry proposal/apply publication validation events, so live
  transport-admin evidence cannot pass with only REST/PIT forwarding cases.
- the `multi-node-transport-admin` report producer now fetches
  `/_steelsearch/dev/cluster` from node A and attaches the live coordination
  block, including publication validation transcripts, to the top-level report
  consumed by the gate.
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
- periodic liveness now keeps bounded multi-round lagging-follower catch-up
  state, backs catch-up scheduling off across multiple ticks, defers node-left
  publication retry while the catch-up window is pending, and clears the state
  after catch-up success or follower removal.
- development coordination status now exposes structured publication catch-up
  transcripts with tick, node, version, state UUID, scheduled due tick, attempt
  count, and applied outcome for lagging follower catch-up paths.

The remaining gap is that publication is not yet modeled as a repeated
leader-driven pipeline with proposal, follower validation, commit
acknowledgement, apply, and durable follower catch-up stages.

## Replacement Blockers

The main blockers are:

- live transport publication proposal/apply collection is TCP-backed,
  action-frame-validated, publication-semantics-validated, and transcripted,
  live `publish_state` decode/apply is Rust-native, and response generation is
  native-first; remaining direct Java `publish_state` request/response
  validation should exercise captured mixed-cluster payloads rather than helper
  fallbacks;
- the distinct commit-versus-apply lifecycle is modeled locally and surfaced in
  transcripts, including per-follower validation events and focused
  mixed-failure validation coverage; broader live mixed-cluster transcript
  evidence is still incomplete;
- repeated-publication, restore-time follower catch-up, reachable lagging
  follower catch-up, bounded multi-round catch-up scheduling primitives, and
  structured catch-up transcripts exist, but mixed-failure follower validation
  transcript coverage is still incomplete;
- publication failure now feeds liveness/fault state for active rounds, and
  node-left retry can drive a follow-up publication round after the bounded
  backoff catch-up window expires; the next gap is running and archiving the
  live mixed-cluster validation transcript artifact under the current gate.

## Required Tests

- repeated publication round artifacts with evolving term/version/state UUID;
- protocol-level publication proposal/ack/apply exchange tests;
- commit-success but apply-failure coverage;
- multi-round lagging-follower catch-up scheduling transcripts;
- publication failure driving bounded retry backoff after catch-up scheduling
  transitions.

## Required Implementation

The remaining work should move in these leaves:

1. transport-backed follower proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up support;
3. live mixed-cluster validation transcript artifact refresh after bounded
   backoff scheduling and publication health failure.

## Required Implementation Order

1. transport-backed proposal/ack/apply lifecycle;
2. repeated publication and follower catch-up;
3. live mixed-cluster validation transcript artifact refresh after bounded
   backoff scheduling.
