# Netty close-hint branch decision note

Status: closed as a side branch, with the mixed-membership main blocker still unresolved.

## What this branch established

1. The original `hint[unknown]` rows in the mixed Java-primary / Rust-replica probe were not evidence of a distinct close path.
2. They were overwhelmingly an ordering race where close TRACE fired before later `channelInactive` hint recording.
3. Adding `explicitLocalClose` in `Netty4TcpChannel.close()` removed most unknown hints.
4. Moving close TRACE emission into `Netty4MessageChannelHandler.channelInactive()` and leaving the close-future listener as fallback removed the remaining `unknown` rows in the clean split-target probe.
5. In the unknown-free clean artifact, the dominant hint across named node first-close rows and action-bearing selected channels is `explicitLocalClose`.
6. The lone `closeFutureIntercepted` residue is a benign early-listener outlier, not a competing stale-sibling model.

## Key artifacts

- Baseline close-hint artifact: `/tmp/java-rust-mixed-membership-netty-close-hint.latest.json`
- Clean split-target artifact with explicitLocalClose patch: `/tmp/java-rust-mixed-membership-split-overlay-targets-clean.latest.json`
- Clean split-target artifact with channelInactive-emitted close TRACE: `/tmp/java-rust-mixed-membership-channelinactive-trace.latest.json`

## Decision

This branch does not change the main mixed-membership blocker classification.

The Netty close-hint side branch is sufficiently resolved for current purposes because:

- `hint[unknown]` was reduced from a tracing race to a source-level explanation.
- The stronger ordering patch removed `unknown` rows in the clean split-target probe.
- The remaining single `closeFutureIntercepted` row is only `1/75` first-close rows and does not affect the dominant model.

Therefore the practical next step is not further Netty hint polishing.
The practical next step is to return to the mixed-membership mainline blocker analysis with this branch treated as a closed side investigation.

## Return point to the mainline backlog

Return to the mixed-membership blocker mainline after recording this branch conclusion.
The next mainline question is whatever `tasks.md` lists next outside this Netty close-hint sub-branch.
