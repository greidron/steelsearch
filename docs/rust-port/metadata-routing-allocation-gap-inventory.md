# Metadata, Routing, and Allocation Gap Inventory

This note narrows the remaining work under
`Implement authoritative metadata, routing, and shard allocation behavior.`

## Current implemented baseline

The current Rust port already has:

- gateway-backed persistence for cluster metadata and routing snapshots
- coordination-owned fencing for publication, restart replay, and task-queue
  recovery
- REST and daemon paths that can read and rewrite cluster metadata manifests
- development-only routing/allocation views that preserve shard ownership data
  instead of rebuilding it only from the local node

## Current limitation

The runtime still behaves like a snapshot decoder plus local rewrite helpers,
not an authoritative cluster-manager metadata engine.

That leaves three concrete gaps:

1. Metadata mutations are not modeled as full OpenSearch state transitions.
   The code can mirror index metadata, aliases, templates, settings, and
   routing, but it does not yet own the complete mutation lifecycle for create,
   delete, open, close, mapping updates, data streams, views, and custom
   metadata.
2. Shard allocation behavior is still simplified. There is no full decider
   layer for disk watermarks, awareness, delayed allocation, stale primary
   handling, reroute planning, or allocation explain parity.
3. Some REST/runtime paths still succeed against a reduced metadata model where
   OpenSearch would enforce a stricter state transition or fail closed.

## Remaining work

The remaining work should move in these leaves:

1. Capture the current decode/apply metadata path and split the remaining work
   into explicit authoritative metadata-mutation leaves.
2. Split authoritative metadata mutation into concrete leaves:
   - preserve the current index-create baseline while delete/open/close still
     fail closed
   - index delete/open/close lifecycle
   - keep the current alias/template/component-template/cluster-settings
     mirrored baseline covered so the existing REST and gateway-backed replay
     surface does not regress
   - alias mutation behind cluster-manager-owned transitions
   - keep the current template/component-template mirrored baseline covered so
     the existing REST and gateway-backed replay surface does not regress
   - add cluster-manager-owned template/component-template metadata/task
     surfaces
   - wire template/component-template REST mutations behind manager-owned
     transitions
   - move composable index-template mutation behind a manager-owned transition
     instead of leaving `/_index_template` on the mirrored registry path
   - cluster-settings mutation behind cluster-manager-owned transitions
   - split mapping/data-stream/view/custom metadata mutation into:
     - add manager-owned mapping metadata/task surfaces
     - wire mapping updates behind manager-owned transitions
     - explicit fail-closed baseline for data streams and views
     - custom metadata persistence behind manager-owned transitions, split into:
       - repository custom metadata:
         - keep the current repository REST and gateway-backed replay baseline
           explicit
         - add cluster-manager-owned repository metadata/task surfaces
         - wire repository REST mutations behind manager-owned transitions
       - snapshot restore/delete lifecycle custom metadata:
         - keep the current snapshot restore/delete/cleanup baseline explicit
         - split manager-side task/metadata surface from REST wiring
         - add cluster-manager-owned snapshot restore/delete lifecycle
           metadata/task surfaces
         - wire snapshot delete lifecycle requests behind manager-owned
           transitions
         - wire snapshot restore lifecycle requests behind manager-owned
           transitions
      - ingest/search pipeline and stored-script custom metadata:
        - split pipeline and stored-script work into separate leaves
        - split pipeline work into ingest and search pipeline leaves
        - move ingest pipeline custom metadata behind manager-owned
          transitions:
          - add manager-owned ingest pipeline metadata/task surfaces
          - split request-path work into route registration and local
            metadata sync leaves
          - add `/_ingest/pipeline/{id}` request paths behind manager-owned
            transitions
          - keep local ingest pipeline metadata and manager-owned state in
            sync through the same request path
        - move search pipeline custom metadata behind manager-owned
          transitions:
          - split search pipeline work into manager-side task/metadata
            surface and request-path wiring leaves
          - add manager-owned search pipeline metadata/task surfaces
          - wire search pipeline request paths behind manager-owned
            transitions:
            - split request-path work into route registration and local
              metadata sync leaves
            - add `/_search/pipeline/{id}` request paths behind
              manager-owned transitions
            - keep local search pipeline metadata and manager-owned state in
              sync through the same request path
        - move stored-script custom metadata behind manager-owned transitions:
          - split stored-script work into manager-side task/metadata
            surface and request-path wiring leaves
          - add manager-owned stored-script metadata/task surfaces
          - wire stored-script request paths behind manager-owned
            transitions
      - persistent-task, decommission, weighted-routing, and workload-group
        custom metadata
        - split persistent-task, decommission, weighted-routing, and
          workload-group custom metadata into separate manager-owned
          transition leaves
        - move persistent-task custom metadata behind manager-owned
          transitions
          - add manager-owned persistent-task metadata/task surfaces
          - split persistent-task wiring into publisher and request-path
            leaves
          - route persistent-task publishers through manager-owned
            transitions
          - back active `/_tasks` surfaces from manager-owned
            persistent-task metadata
          - back recent completed `/_tasks` surfaces from manager-owned
            persistent-task snapshots
        - move decommission attribute custom metadata behind
          manager-owned transitions:
          - split decommission work into manager-side task/metadata
            surface and request-path wiring leaves
          - add cluster-manager-owned decommission metadata/task surfaces
          - wire decommission request paths behind manager-owned
            transitions:
            - split request-path work into route registration and local
              manager sync leaves
            - add decommission awareness PUT/DELETE/GET request paths
              behind manager-owned transitions
            - keep decommission request responses and local manager-owned
              metadata in sync through the same request path
        - move weighted-routing custom metadata behind manager-owned
          transitions:
          - split weighted-routing work into manager-side task/metadata
            surface and request-path wiring leaves
          - add cluster-manager-owned weighted-routing metadata/task
            surfaces
          - add a focused regression that asserts cluster-manager task
            application can store and clear manager-owned
            weighted-routing metadata
          - wire weighted-routing request paths behind manager-owned
            transitions
          - add a focused regression that asserts weighted-routing
            PUT/GET/DELETE request paths round-trip through local and
            manager-owned weighted-routing state
        - move workload-group custom metadata behind manager-owned
          transitions:
          - split workload-group custom metadata into manager-side
            task/metadata surface and request-path wiring leaves
          - add cluster-manager-owned workload-group metadata/task
            surfaces
          - add a focused regression that asserts cluster-manager task
            application can store and clear manager-owned
            workload-group metadata
          - split workload-group request-path work into model-group
            register wiring and remaining request surface leaves
          - keep `/_plugins/_ml/model_groups/_register` routed through
            the manager-owned workload-group transition path, with a
            focused regression that verifies model-group registration
            also populates manager-owned workload-group metadata
          - split the remaining workload-group request-path work into
            read-surface and non-register lifecycle leaves
          - split workload-group read request-path work into registry
            read/search surfaces and REST wiring leaves
          - add manager-backed workload-group read surfaces so
            workload-group metadata can be queried independently of
            model-group registration
          - wire workload-group GET request paths to the manager-owned
            workload-group metadata
          - add a focused regression that asserts `/_wlm` and
            `_list/wlm_stats` GET routes read manager-owned
            workload-group metadata
          - split the remaining non-register workload-group lifecycle
            request-path work into create, update, and delete leaves
          - add manager-backed workload-group create surfaces
          - add a focused regression that asserts PUT and POST
            /_wlm/workload_group populate manager-owned workload-group
            metadata
          - add manager-backed workload-group update surfaces
          - add a focused regression that asserts PUT
            /_wlm/workload_group/{name} mutates manager-owned
            workload-group metadata
          - add manager-backed workload-group delete surfaces
          - add a focused regression that asserts DELETE
            /_wlm/workload_group/{name} clears manager-owned
            workload-group metadata
3. Split authoritative routing and shard-allocation behavior into concrete
   leaves:
   - allocation decider coverage now exists for disk watermarks,
     awareness, delayed allocation, role gating, same-shard protection,
     and relocation throttling
   - reroute planning behind explicit cluster-manager-owned transitions:
     - keep the current cluster-manager reroute task surface and
       manager-side shard routing mutation baseline explicit
     - split the remaining reroute planning work into request-surface
       wiring and residual local rewrite replacement leaves
     - split explicit reroute request-surface work into route
       registration and focused regression leaves
     - `POST /_cluster/reroute` is now backed by the manager-owned
       reroute task surface
     - focused regression now asserts explicit reroute requests enqueue
       and apply manager-owned reroute tasks
     - split the remaining local simplified allocation rewrite cleanup
       into development read-surface fallback removal and residual
       non-manager mutation-path removal
     - split development allocation read-surface fallback removal into
       cluster-health and allocation-explain leaves
     - cluster health already prefers manager-owned routing when the
       standalone cluster-manager runtime is present
     - focused regression now asserts `/_cluster/health` prefers
       manager-owned routing over development manifest snapshots
     - allocation explain now prefers manager-owned routing when the
       standalone cluster-manager runtime is present
     - focused regression now asserts `/_cluster/allocation/explain`
       prefers manager-owned routing over development manifest snapshots
     - split the remaining non-manager mutation-path cleanup into:
       - development manifest-persistence rewrites that still mirror
         routing/allocation as an authoritative shard-movement source,
         now split into:
         - write-time overwrite paths that still replace
           manager-owned routing/allocation state during development
           metadata persistence
         - focused regression already asserts gateway-backed metadata
           persistence preserves manager-owned shard ownership metadata
         - restore/read-time trust paths that still prefer persisted
           manifest routing/allocation snapshots over manager-owned
           shard movement state, now covered by manager-first cluster
           health and allocation-explain read surfaces
       - inline shard-routing mutation helpers outside cluster-manager
         task application, now split into:
         - node-loss recovery helpers are now covered by manager-owned
           remove-node and reroute task submission paths, with focused
           regression coverage for queueing behavior
         - create/delete/open/close and snapshot lifecycle helpers
           that still synthesize shard placement locally instead of
           reading manager-owned allocation state, now split into:
           - index lifecycle helpers that still persist locally
             synthesized shard placement during create/delete/open/close,
             now split into:
             - delete-index metadata persistence cleanup is now covered,
               with focused regression asserting surviving indices keep
               manager-owned routing after a delete persists metadata
             - create/open/close metadata persistence cleanup, now split
               into:
               - create-index metadata persistence cleanup is now
                 covered, with manager-owned routing preserved during
                 metadata persistence
               - open/close metadata persistence cleanup is now covered,
                 with manager-owned routing preserved while index state
                 transitions persist metadata
           - snapshot lifecycle helpers that still persist locally
             synthesized shard placement during restore/delete flows,
             now split into:
             - snapshot restore helper cleanup is now covered, with
               manager-owned routing preserved during restore metadata
               persistence
             - snapshot delete helper cleanup is now covered, with
               manager-owned routing preserved while snapshot deletion
               removes local snapshot blobs
   - primary election and stale-primary handling, now split into:
     - keep the current missing-primary replica boolean-flip baseline
       explicit so simplified promotion coverage does not regress while
       authoritative promotion remains open
     - split missing-primary authoritative promotion into started-copy
       selection and primary-term safety leaves
     - deterministic promotion of the most up-to-date started shard
       copy, with stale primary flags cleared instead of flipping the
       first started replica to primary
     - focused regression now asserts missing-primary promotion picks
       the highest-checkpoint started shard copy and clears stale
       primary flags
     - split missing-primary term fencing into:
       - split manager-owned primary-term ownership metadata into:
        - shard-routing storage and manager task-application support
           are now covered, with focused regression asserting routing
           task application seeds ownership epochs
         - promotion-time consumption of that routing-term metadata is
           now covered, with focused regression asserting missing-
           primary selection prefers the higher primary term before
           checkpoint tie-breaks
       - stale missing-primary term fencing, now split into:
         - promotion candidate filtering is now covered, with focused
           regression asserting lower-term started copies are excluded
           before checkpoint tie-breaks
         - recovery-path rejection is now split into:
           - keep the current promotion-time term rewrite baseline
             explicit while per-copy stale ownership retention remains
             open
           - preserving lower-term replica ownership metadata after a
             higher-term promotion remains open
           - catch-up/recovery rejection for lower-term copies against
             promoted primary-term ownership metadata is now covered,
             with focused regression asserting lower-term recovery
             copies are rejected after a higher-term promotion
     - stale-primary handling, now split into:
       - promotion fencing that rejects attempts to elevate a lower-
         term copy over a higher-term ownership epoch
       - recovery fencing that rejects stale convergence paths that do
         not match the active ownership epoch
   - allocation explain parity
4. Close any remaining success-path gaps where Steelsearch still returns a
   simplified metadata answer without the OpenSearch transition or failure
   semantics behind it.
