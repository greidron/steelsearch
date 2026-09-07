# Release Notes Policy

Every new release, including release candidates, must include performance
comparisons against BOTH the immediately previous published GitHub release and
a pinned OpenSearch version. This policy starts with the next release; do not
silently rewrite historical release notes. Passing this format check does not
approve production readiness or authorize publication.

## Required Bundle

Prepare `docs/releases/<tag>/` with these files:

- `notes.md`: copy the structure in `template.md`, fill every narrative section.
- `release.json`: metadata described below.
- `current.json`: fresh benchmark matrix for the candidate release binary.
- `previous.json`: same workload rerun using the immediately previous published
  release binary, not an arbitrary earlier development build.
- `opensearch.json`: same workload against the declared OpenSearch version.

Use the benchmark matrix's `--reuse-steelsearch-binary` with an explicit
`STEELSEARCH_BINARY_PATH` for each SteelSearch binary. The runner records the
actual executable path and SHA-256 per topology and detects executable changes
during a run. Preserve build/package provenance linking each binary to its
release tag; a filename or manually asserted hash alone is not provenance.
Reports without measured executable identity cannot be used by this policy.

Use the same host, resource limits, workload, duration, concurrency, seed,
shards and replicas. Record persistence, refresh, security and deployment
settings explicitly. Never claim equal production durability merely because
the request mix matches. Rerun the previous release on the current benchmark
when the benchmark changes; do not compare incompatible historical numbers.
The current synthetic document generator includes an embedding number array
even without vector requests. Its `vector_dimension` must match across reports
because it changes source payload size; the generated notes disclose that size.
This source field does not enable a k-NN mapping or plugin support.
CPU-profiler runs are diagnostic-only and must not be used as release speed
evidence. Reports or scenarios marked `diagnostic_only` are rejected.

Required operations are `write`, `lexical`, `ranking`, `facet`, `sort_filter`,
`nested`, and `refresh`, on both single-node and three-node topologies.
The current support profile is `core-no-plugins`: vector/hybrid operations must
have zero weight. Supply, for example:

```sh
--query-mix write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,refresh=5
```

`release.json` has this structure (replace illustrative values):

```json
{
  "schema_version": 1,
  "release": "v0.5.1",
  "previous_release": "v0.5.0",
  "prerelease": false,
  "support_profile": "core-no-plugins",
  "opensearch_version": "2.19.0",
  "environment": "Describe host CPU/RAM/OS and per-node resource limits",
  "runtime_settings": "Describe each engine's persistence, refresh, security and deployment settings",
  "comparison_limits": "State comparability limits and explain observed regressions"
}
```

These tags and versions are examples, not release approval or an assertion
that a particular tag is currently the previous published release.

## Mandatory Tables

The generated performance section contains:

1. Throughput by topology: previous ops/s, current ops/s, percentage change,
   OpenSearch ops/s, current/OpenSearch ratio. Higher throughput is better.
2. All 14 operation/topology rows: previous mean ms, current mean ms,
   percentage change, OpenSearch mean ms, OpenSearch/current speedup, current
   p95 ms. Lower latency is better; positive latency change is a regression.
3. Exact release labels, OpenSearch version, executable hashes, workload,
   environment and limitations, with the raw evidence attached to the release.

Generate rather than hand-edit the tables:

```sh
python3 tools/release_notes.py docs/releases/<tag> --render
python3 tools/release_notes.py docs/releases/<tag>
```

Missing scenarios, invalid/non-finite measurements, request errors, missing
binary hashes, reference-version mismatches, different workload configurations,
identical current/previous executable hashes, and stale/edited generated tables
fail validation. Reports must contain exactly the seven core operation results.
Successful request counts, total request counts and latency sample counts must
be positive integers: each operation's latency sample count must match its
successful requests, operation successes must sum to the scenario total, and
the error-free scenario's total requests must equal its successes. Contradictory
counts cannot be used to combine throughput and latency from different runs.
Generated replica labels use the executed topology value, including the matrix
runner's three-node cap of two replicas, not an unclamped requested value.
This policy requires distinct release binaries; reusing the
same executable for a documentation-only release requires an explicitly
reviewed policy change, not silently relabelling measurements. Do not hide a regression,
omit a scenario, replace a value with N/A, or substitute a development binary
for the previous release to make a table pass.

## GitHub Publication

After release approval, use only the validated publisher:

```sh
python3 tools/publish-release.py docs/releases/<tag> \
  --repo greidron/steelsearch --tag <tag> --asset /path/to/package.tar.gz
```

This default command only validates locally and performs no remote write.
Add `--publish` only after release approval and existing release gates pass.
The publisher validates the tables before invoking GitHub, checks that the
declared previous release is still the most recently published non-draft
release (including RCs), refuses to overwrite a release, requires an existing
remote tag via `--verify-tag`, uses the checked notes verbatim, and attaches
`performance-evidence.zip`. A benchmark/format pass is NOT release approval.
Before its GitHub lookup, it copies the five bundle files to a temporary private
directory and validates that snapshot. Both the publication's notes file and
the evidence archive come from that same snapshot, so later edits to the
workspace cannot substitute unvalidated notes or reports during publication.
This protects the supported publishing path; it does not configure remote
permissions or prevent another authorized operator from publishing separately.

The `Release notes policy` CI workflow validates committed bundles on pull
requests, main/master pushes and version-tag pushes. A version tag without its bundle
fails. It never creates a release automatically.

Repository files cannot prevent a repository administrator or a token with
write permission from bypassing this publisher through GitHub UI/API. For
server-side enforcement, require the `release-notes` status check, restrict
release/tag write credentials to the approved publishing operator/automation,
and protect policy/workflow changes with review. Those remote permission
settings are NOT configured by this change. Never describe a post-publication
Actions failure as a pre-publication block. Direct `gh release create`, web UI
publication and auto-generated notes are outside the supported release process.
