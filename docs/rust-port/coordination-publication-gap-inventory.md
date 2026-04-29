# Coordination Publication Gap Inventory

This note scopes the remaining gap between the current Steelsearch
development-only publication flow and an OpenSearch-style coordination
publication pipeline.

## Current State

- Discovery, pre-vote, election, voting exclusions, and joint-consensus quorum
  helpers now exist in the daemon-owned coordination runtime.
- Development coordination still publishes exactly one synthetic cluster-state
  update per startup path.
- Publication is not modeled as a repeated leader-driven pipeline with
  proposal, follower validation, commit acknowledgement, apply, and durable
  follower catch-up stages.

## Concrete Gaps

1. Publication round model
   - There is no explicit publication round object that tracks
     state uuid, version, term, target voters, acknowledgements, apply status,
     and timeout/failure state across multiple updates.

2. Follower publication wire/runtime
   - There is no live transport publication request/response exchange for
     cluster-state publication to followers.
   - Followers do not separately validate, acknowledge, and apply repeated
     publications from the elected cluster-manager.

3. Commit versus apply lifecycle
   - Commit and apply are collapsed into the single current development publish
     path.
   - There is no staged transition from proposed publication to committed
     publication to follower-applied publication.

4. Repeated publications
   - The current runtime does not support a second or later publication round
     with updated version/state lineage.
   - There is no follower catch-up path for lagging or rejoining nodes.

5. Leader/follower coordination checks
   - Leader publication does not incorporate follower validation responses and
     apply acknowledgements as distinct coordination signals.
   - Publication failure handling does not feed back into leader health,
     follower health, or rerun logic.

## Recommended Implementation Order

1. Add explicit publication round state in `ClusterCoordinationState`.
2. Add transport-framed publication proposal/ack/apply wire primitives.
3. Execute repeated publication rounds over live transport.
4. Split commit from follower apply tracking.
5. Feed publication failures into existing liveness/fault-detection logic.
