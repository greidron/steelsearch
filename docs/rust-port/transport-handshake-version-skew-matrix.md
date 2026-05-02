# Transport Handshake And Version-Skew Reject Matrix

This matrix defines the current external-interop boundary for transport
handshake acceptance and rejection. It is deliberately narrower than full
transport action compatibility.

## Reading Rules

- `supported` here means supported for the current external interop boundary:
  handshake, probe, and bounded observation, not broad server-side action
  execution.
- `reject` means fail closed rather than guessing at wire compatibility.
- `observe-only` means the peer may be contacted for probe/inspection purposes,
  but action execution still remains outside the accepted boundary.

## Wire-Version Matrix

| Peer wire/version situation | Current decision | Why |
| --- | --- | --- |
| current validated OpenSearch probe target line (`3.7.x` snapshot-era handshake path already exercised by the repository) | supported / observe-only | this is the line with existing live probe evidence for handshake and cluster-state observation |
| peer version that still decodes through the current version gates but lacks explicit acceptance evidence | reject by default | decode capability alone is not enough to claim safe interop |
| newer peer wire version outside current validated gates | reject | field/layout drift may exist and must not be guessed |
| older peer wire version outside current validated gates | reject | backward wire compatibility is not claimed without explicit evidence |
| unknown or malformed reported version | reject | startup/interop must fail closed on ambiguous wire identity |

## Reject Fixture Classes

| Fixture class | Expected decision | Why |
| --- | --- | --- |
| bad handshake frame | reject | malformed or truncated handshake frames must not advance to action negotiation |
| unexpected action after handshake | reject | transport actions outside the accepted interop inventory must not be forwarded or executed implicitly |
| version mismatch | reject | mismatched or unsupported peer version must stop at handshake/negotiation time |

## Linked Action Inventories

Accepted/rejected action treatment must be read alongside:

- [transport-actions.md](/home/ubuntu/steelsearch/docs/api-spec/generated/transport-actions.md)
- [transport-action-priority.md](/home/ubuntu/steelsearch/docs/rust-port/transport-action-priority.md)

The handshake boundary is intentionally stricter than the generated action
inventory. A transport action may be listed as `planned`, but version-skew and
handshake rejection still happen before that action is even considered.

## Immediate Follow-up

1. reject fixtures should pin bad-handshake, unexpected-action, and
   version-mismatch behavior explicitly.
2. stale cluster-state cache and forwarding allowlist work should reference this
   matrix instead of weakening it implicitly.
