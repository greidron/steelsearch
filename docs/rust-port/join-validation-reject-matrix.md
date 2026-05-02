# Join Validation Reject Matrix

This matrix defines the current same-cluster peer-node join reject backlog. The
goal is to separate mismatch classes and pin the operator-visible rejection
reason expected from Steelsearch alongside the Java baseline that later harnesses
must capture.

## Reject Matrix

| Mismatch class | Expected join decision | Why reject | Operator-visible reject reason |
| --- | --- | --- | --- |
| discovery identity mismatch | reject | peer identity does not match expected discovery/member identity contract | `join rejected: discovery identity mismatch` |
| node role mismatch | reject | joining node advertises an incompatible or unsupported same-cluster role set | `join rejected: incompatible node role` |
| version mismatch | reject | mixed-cluster join cannot proceed without an explicitly validated version gate | `join rejected: incompatible version` |
| cluster UUID mismatch | reject | authoritative cluster identity diverges and must not be merged implicitly | `join rejected: cluster UUID mismatch` |

## Transcript Handling Rule

- every reject case should store:
  - Java baseline transcript markers;
  - Steelsearch transcript markers;
  - the mismatch class that triggered the reject.
- the Steelsearch transcript must fail closed before the node is treated as
  joined or cluster-participating.

## Immediate Follow-up

1. publication and allocation probes should reuse the same mismatch vocabulary.
2. harness work should record Java and Steelsearch transcripts side by side for
   every reject class.
