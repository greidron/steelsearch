# Peer Recovery Probe Matrix

This matrix defines the current same-cluster peer-recovery backlog for
file-chunk, translog, and finalize ordering evidence.

## Direction Matrix

| Direction | Why it must be isolated |
| --- | --- |
| Java -> Rust | verifies Rust target behavior against Java-origin recovery source semantics |
| Rust -> Java | verifies Rust source behavior does not violate Java target expectations |

## Recovery-Phase Matrix

| Case | What must be observed | Why it matters |
| --- | --- | --- |
| interrupted recovery | recovery stops mid-stream with explicit incomplete state | proves partial recovery does not masquerade as finalized shard readiness |
| resumed recovery | interrupted recovery can resume or explicitly restart with bounded semantics | proves restart/resume behavior is not ambiguous |
| finalized recovery | finalize completes after file-chunk and translog phases in order | proves shard handoff reaches a stable end state |

## Required Assertions Per Direction

Every direction and case should record:

- data checksum assertion for transferred file/chunk state;
- translog or operation-log continuity assertion;
- document visibility assertion after finalize or bounded resume;
- explicit source/target role in the artifact.

## Report Schema Requirements

Every future peer-recovery artifact should include:

- `direction`
- `recovery_case`
- `source_node`
- `target_node`
- `file_chunk_phase`
- `translog_phase`
- `finalize_phase`
- `data_checksum_ok`
- `doc_visibility_ok`
- `final_state`

## Immediate Follow-up

1. write-replication semantics should reuse the same checksum/doc-visibility
   vocabulary where applicable.
2. crash/restart mixed-cluster harnesses should consume the same interrupted vs
   resumed recovery distinction.
