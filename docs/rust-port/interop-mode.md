# Java OpenSearch Interop Mode

## Decision

The first coordinating-only interop mode is an external transport client, not a
cluster-joining OpenSearch node.

Steelsearch may connect to Java OpenSearch transport ports, complete handshakes,
read cluster state, and send selected transport actions. It must not advertise
itself as a discovery node, cluster-manager candidate, ingest node, or data
node in the Java cluster until the membership and write-path contracts are
implemented and validated.

Read every `Phase B` claim through that boundary first:

- external coordinator or observer behavior is in scope;
- peer-node membership, shard ownership, recovery, and publication semantics
  remain out of scope until `Phase C`, where they are owned by
  `tools/run-phase-c-mixed-cluster-harness.sh` and the `mixed-cluster-*`
  report family.

## Rationale

Joining the cluster is more than speaking the transport stream format. A joined
node participates in discovery, publication, cluster-state application,
compatibility checks, node roles, task routing, and allocation decisions. A data
or cluster-manager-capable node also becomes part of write, recovery, and
failure semantics. The current Rust implementation can decode and apply parts
of cluster state and can execute local standalone search behavior, but it does not yet
implement the full Java node lifecycle contract.

The external transport-client mode keeps the compatibility boundary narrow:

- outbound handshakes and selected request/response actions
- local decoded cluster-state cache
- REST coordination and forwarding from Steelsearch to Java nodes
- fail-closed behavior when transport, metadata, or response shapes are not
  supported

## Explicit Non-Goals For This Mode

- no Java cluster membership
- no shard allocation target
- no primary or replica ownership
- no cluster-manager election participation
- no publication acknowledgements as a real node
- no mixed-cluster recovery

## Discovery Constraints

Steelsearch must not participate in Java OpenSearch discovery in the external
transport-client mode.

Allowed behavior:

- connect directly to configured Java transport addresses
- perform transport handshakes
- read remote node identity and version information
- read cluster state through selected transport actions
- keep its own local cache of discovered Java nodes

Disallowed behavior:

- publish Steelsearch as a `DiscoveryNode`
- join the cluster coordination subsystem
- respond to discovery pings as a cluster member
- accept cluster-state publications as a real voting or non-voting node
- persist Java cluster UUID or voting configuration as local membership state

## Cluster-Manager Constraints

Steelsearch must not become cluster-manager-capable in this mode.

It must not advertise cluster-manager, master-eligible, voting-only, ingest, or
data roles to Java OpenSearch. Any cluster-manager behavior must remain
read-only and observational:

- read the elected cluster-manager from decoded cluster state
- use cluster state to choose Java target nodes for forwarded requests
- fail closed if the cluster-manager identity, term, version, or node list
  cannot be decoded safely

It must not:

- participate in elections
- acknowledge publications as a joined node
- submit cluster-state updates as a local node
- alter voting configuration exclusions
- make allocation decisions

## Safety Constraints

The external transport-client mode is read-mostly by default. Writes may be
forwarded to Java nodes only when the specific transport action and response
shape have compatibility coverage.

Required safety behavior:

- reject unsupported transport actions before sending them
- reject unsupported cluster-state custom metadata while updating the local
  cache
- keep Rust-native data-node behavior isolated from Java mixed-cluster behavior
- treat Java wire-version mismatches as compatibility failures unless an
  explicit version-gated path exists
- translate Java transport errors into OpenSearch-shaped REST errors without
  retrying unsafe writes automatically

## Data-Node Participation Guard

The `steelsearch` daemon keeps Java OpenSearch data-node participation disabled
by default.
Any configuration that attempts to enable Java data-node participation must be
rejected until write-path safety exists.

This guard does not disable the standalone Rust-native Tantivy engine used by
the local standalone REST surface. It only blocks advertising or using Steelsearch as a
Java mixed-cluster data node.

## Remote Cluster-State Updates

The first remote cluster-state update mode is polling.

Steelsearch should periodically send selected cluster-state transport requests
to configured Java nodes and replace or update its local decoded cache from the
response. It must not subscribe to publication traffic as a joined node in the
external transport-client mode.

Full cluster-state responses seed the local typed cache. Publication diffs may
be applied only when the diff `from_uuid` matches the cached state UUID; a
mismatch or missing base state is a compatibility failure and requires a full
refresh before continuing.

Cache updates validate custom metadata compatibility before replacing the
current state. If metadata customs declare entries that are not represented by
the typed supported fields, or top-level cluster-state custom names are not in
the built-in supported set, Steelsearch rejects the update and keeps the prior
cache unchanged.

Search forwarding starts with a routing-plan step. Given requested index names,
Steelsearch reads the cached routing table, picks started shard copies, resolves
their `current_node_id` through discovery nodes, and groups target transport
addresses by Java node. Missing cluster state, missing index routing, missing
started shard copies, or missing discovery nodes are fail-closed routing errors.

Write forwarding has an additional safety gate. `steelsearch` rejects write
routing by default and only computes a Java target after
`java_write_forwarding_validated` is enabled. Once enabled, the route must
resolve to a started primary shard in the cached routing table and then to a
known discovery node; otherwise the write is rejected before any transport
action is sent.

Transport errors returned by Java nodes are translated into OpenSearch-shaped
REST errors before they leave the coordinating shell. `RemoteTransportException`
wrappers are unwrapped to their effective cause when present, while undecodable
transport error payloads become `transport_serialization_exception` responses
with a bad-gateway status.

The default polling interval is 5 seconds. The interval is configurable so live
interop probes can use shorter loops without changing the safety model.

## Advancement Criteria

Cluster join can be reconsidered only after Steelsearch has:

- discovery and node membership behavior compatible with the target OpenSearch
  version
- complete role advertisement and role-specific safety checks
- full cluster-state publication application and acknowledgement behavior
- write-path sequencing, primary term, translog, refresh, and recovery semantics
  for any data-node role
- live Java interop probes showing fail-closed handling for unsupported
  metadata, actions, and version-gated wire paths
