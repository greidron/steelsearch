# Release Work

- Follow `docs/releases/README.md` for every new release, including RCs.
- Never create/push a release tag or publish a GitHub release without explicit
  user approval. Compatibility tests and note-format checks are not approval.
- Include generated per-scenario comparisons with the previous published
  release and OpenSearch. Use actual benchmark executable identities, not
  manually inferred before/after labels. Do not omit regressions or scenarios.
- Use `tools/release_notes.py` to generate/check notes and
  `tools/publish-release.py` for publication. Do not bypass validation with
  direct `gh release create`, generated notes, or a separate API call.
- Do not claim that local policy files configure GitHub permissions or prevent
  administrator bypass. Remote enforcement must be verified separately.

# Compatibility Comparison Semantics

- Separate document/search semantics from execution-dependent auxiliary metadata.
  Do not compare elapsed values such as top-level `took` for exact cross-engine
  equality. Validate their presence, type and valid range instead.
- Keep document contents, IDs, ordering, scores, versions, term statistics,
  timeout flags and partial-failure indicators under their defined contracts.
  Do not blanket-ignore metadata or recursively strip matching field names from
  document content. Add scoped extractor tests for each normalization rule.
- Preserve raw responses and report comparator corrections separately from product
  fixes. This rule does not remove latency measurements from performance gates.
- For default relevance-only searches with `from: 0` (or no `from`) and no `sort`,
  `min_score`, `search_after`, PIT, or scroll control, compare each returned `_score`
  using the explicit bound
  `abs(a-b) <= max(1e-6, 1e-6 * max(abs(a), abs(b)))`. This is a scoped
  cross-engine floating-point compatibility rule, not a general accuracy waiver.
- In that same scope, the relative order of documents with exactly equal emitted
  scores is not a cross-engine contract. Steelsearch must nevertheless return a
  deterministic order for repeated requests against the same index state. Compare
  tied groups canonically only in a dedicated extractor with regression coverage.
- `from > 0`, `min_score`, explicit sorting (including `_score`), `search_after`, PIT,
  scroll, result membership, totals, page boundaries, sort values, and unequal-score
  ranking remain exact. Never apply the score tolerance or tie normalization there.

# Native-First Implementation

- Treat native execution as the primary path to meeting the performance budget.
  Source-level re-evaluation is a major performance risk, not the default solution
  to OpenSearch compatibility gaps.
- Before implementing custom search or scoring logic, inspect the pinned Tantivy
  version's source, APIs and extension points. Record what is supported natively,
  what our integration lacks, and what semantic differences are actually proven
  by minimal comparisons. A current fallback is not evidence of a library limit.
- Prefer native query composition, scorers, collectors and statistics providers.
  Only implement a custom fallback for a demonstrated gap; document why native
  execution or a narrow native extension cannot satisfy the required contract.
- Reassess existing source fallbacks for native replacement before investing in
  further source-level micro-optimizations. Do not remove correctness or safety
  checks without evidence, or silently relax accuracy tolerances to enable it.
- Native execution is a priority, not proof of acceptable performance: retain
  the full-suite verification and fixed cumulative v0.6.0 budget below.

# Implementation Performance Gate

- Latest user directive (2026-09-11) supersedes all older per-unit benchmark rules:
  stop benchmarks and finish functional compatibility repairs FIRST. Do not run
  performance benchmarks or performance-only optimization during this phase.
  Run functional regression tests and HTTP compatibility checks after repairs;
  never weaken assertions, omit failures or silently change accuracy tolerances.
- After each completed functional repair unit, start the full preserved non-plugin
  HTTP fixture suite as a separate verification process before beginning the next
  unit. Do not parallelize fixtures that share mutable target state; continue
  independent diagnosis and implementation while that suite runs. Report the
  last completed full-suite count as "confirmed" and any focused result as
  "provisional" until the suite completes.
- Once functional compatibility is established, run the full non-plugin benchmark
  suite and optimize performance while keeping functional tests passing. If an
  optimization breaks tests, repair or revert that optimization and reverify.
  Functional completion and performance/release acceptance are distinct states.
  Historical plans requiring a benchmark after every functional unit are superseded,
  not permission to restart benchmarks during functional repair.
- Keep the initial v0.6.0 release as the fixed cumulative regression baseline.
  Never reset this baseline to the preceding implementation or a newer release.
  Compare topology throughput and each scenario's mean/p95/p99 latency separately:
  throughput must remain at least 95% of v0.6.0 and latency at most 105%.
  Improvements elsewhere cannot offset a failing scenario or topology.
- Benchmark v0.6.0 and the candidate under identical actual workload, durability,
  security and resource settings, with recorded executable identities and
  separate build directories. Preserve the original published baseline evidence.
- Keep comparisons against the previous published release and pinned OpenSearch
  in release notes as well; neither replaces the fixed v0.6.0 cumulative gate.
- A regression over 5% blocks normal completion: investigate, optimize and rerun
  the full suite. Under the 2026-09-07 goal, a single implementation causing at
  least 5% degradation that cannot be resolved by optimization must be recorded
  in the core replacement exclusion ledger and excluded from the candidate.
  Do not count excluded functionality as implemented or relax safety controls.
  Retaining an over-budget implementation still needs explicit approval for a
  scoped exception. Neither exclusion nor exception resets the v0.6.0 baseline.
- Follow docs/rust-port/core-replacement-implementation-plan-2026-09-07.md for
  benchmark scope, cumulative formulas, repeated-measurement rules and evidence.

# Performance Pain-Point Discipline

- Before changing core write, refresh, replay, native query, collector, response
  materialization, or fallback code, read
  docs/rust-port/performance-pain-point-ledger-2026-09-14.md and compare the
  proposed change with its tagged patterns. Record the matching IDs, or an
  explicit no-match result and search terms, in the ledger before calling the
  change complete.
- Keep observed measurements, demonstrated causes, and hypotheses separate.
  A performance result alone does not prove a cause; do not promote a hypothesis
  to a mitigation rule without a focused measurement or a minimal reproduction.
- Each new compatibility guard must state its hot-path admission condition,
  failure-atomicity or correctness invariant, native Tantivy capability review,
  and the workload/telemetry that detects its cost. Narrow a broad guard when
  its invariant applies only to a subset of documents or queries.
- A completed optimization or functional repair must append its validation and
  v0.6.0 gate outcome to the ledger. The ledger is an audit trail, not a waiver:
  it cannot relax fixture assertions, native-first requirements, or the fixed
  cumulative performance budget.

# Agent Delegation Preference

- Use Luna or Terra for routine bounded coding, testing, and documentation tasks.
- Use Astra for difficult reasoning, performance architecture, and final integration.
- During timed benchmarks, do not run concurrent builds, tests, or diagnostics.
- Keep agent write scopes disjoint. This preference is not technically enforced
  model routing and does not change the current model globally.
