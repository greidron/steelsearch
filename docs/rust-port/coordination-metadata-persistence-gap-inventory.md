# Coordination Metadata Persistence Gap Inventory

This note narrows the remaining gateway-backed metadata persistence work under
`Persist authoritative coordination state and cluster metadata in a gateway
layer that survives restart and node loss.`

## Current persisted scope

The current gateway path already persists and replays:

- coordination publication state through `PersistedPublicationState`
- gateway-owned cluster state through `PersistedGatewayState`
- a JSON `cluster_metadata_manifest` mirrored into the gateway manifest and the
  gateway-owned metadata file path family
- development metadata content that already includes:
  - cluster UUID
  - index mappings
  - routing table
  - cluster settings
  - aliases
  - legacy/component/composable templates

## Current limitation

The persistence boundary is still development-snapshot driven instead of
authoritative cluster-manager-owned metadata mutation.

The current manifest is written by the development metadata store after local
REST handlers mutate in-memory state. That leaves several gaps:

- there is no explicit authoritative metadata model owned by coordination
- routing and shard ownership are replayed from the development snapshot rather
  than from cluster-manager publication/apply semantics
- cluster settings, aliases, and templates are mirrored as JSON blobs instead
  of versioned metadata mutations with ownership rules
- restart validation only checks gateway startup identity and coordination
  fencing, not whether metadata changes were committed and applied by the
  elected cluster-manager

## Remaining work

The remaining persistence work splits into these leaves:

1. Keep an explicit inventory of the metadata already mirrored through the
   gateway path so future work does not regress settings, aliases, templates,
   routing, and shard ownership coverage silently.
2. Move from gateway-backed development snapshots to authoritative
   cluster-manager-owned persistence for:
   - routing table and shard ownership
   - cluster settings
   - aliases
   - legacy/component/composable templates
3. Persist committed metadata versioning and apply ownership so restart replay
   can reject uncommitted or partially applied metadata changes.
4. Add focused restart/node-loss coverage for authoritative metadata replay once
   the gateway no longer depends on the development metadata store as the source
   of truth.
