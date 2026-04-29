# Steelsearch Development Replacement Profile

This profile defines the current supported use of `steelsearch` as a
development-time OpenSearch replacement target. It is intentionally separate
from production replacement readiness.

## Supported Profile

Steelsearch can be used as a local development daemon when the workload stays
inside the implemented Rust-native surface:

- start one or more Steelsearch daemon processes with isolated data paths;
- use the OpenSearch-shaped HTTP API for root, cluster health/state, node stats,
  index create/get/delete, document index/get, refresh, bulk, search, k-NN
  search, k-NN plugin operational routes, and ML Commons model routes that are
  implemented in the daemon;
- store data in Steelsearch-owned Tantivy/native metadata, not Java OpenSearch
  Lucene shard directories;
- migrate fixture data through mappings/settings translation plus `_bulk`
  import;
- compare supported request/response behavior with Java OpenSearch through the
  local compatibility harness when `OPENSEARCH_URL` is available.

The profile is suitable for client integration work, API-shape comparison,
fixture migration rehearsal, local search behavior checks, and development
cluster experiments.

## Explicit Non-Goals

This profile is not a production replacement claim. In development mode,
Steelsearch does not claim:

- production security parity with OpenSearch Security or any other production
  security layer;
- rolling-upgrade support;
- benchmark, load, or chaos-test readiness;
- complete OpenSearch REST/transport API coverage;
- Java OpenSearch data-node mixed-cluster membership;
- Lucene/JVM bridge compatibility or direct reuse of existing OpenSearch shard
  stores;
- full snapshot/restore parity;
- production-grade multi-tenant isolation.

## Production Gate

Production mode is fail-closed. Requesting production mode through
`--mode production` or `STEELSEARCH_MODE=production` must fail unless the
readiness gate can prove that all required security and release gates are
satisfied:

- TLS;
- authentication;
- authorization;
- index permissions;
- audit logging;
- tenant isolation;
- secure settings;
- packaging verification;
- rolling-upgrade coverage;
- Steelsearch mixed-version compatibility;
- benchmark coverage;
- load-test coverage;
- chaos-test coverage.

The development daemon also exposes `GET /_steelsearch/readiness` so callers can
inspect the current development replacement profile and blockers without
treating that result as production approval.

## Local Validation Sequence

Use this sequence before treating Steelsearch as a development replacement for
an OpenSearch-backed workflow:

1. Build the daemon and test binaries:

   ```bash
   cargo build -p os-node --bin steelsearch
   cargo test --workspace --no-run
   ```

2. Run the standalone daemon smoke check. This starts Steelsearch on free local
   HTTP and transport ports, uses an isolated data path, and tears the daemon
   down when the smoke check exits:

   ```bash
   tools/run-steelsearch-smoke.sh
   ```

3. Run the Steelsearch-only search compatibility fixture against an existing
   daemon endpoint:

   ```bash
   STEELSEARCH_URL=http://127.0.0.1:9200 \
     tools/run-search-compat.sh --report target/search-compat-steelsearch.json
   ```

4. Run the k-NN fixture path. The default search compatibility fixture includes
   k-NN mappings and vector search cases; for daemon integration coverage use
   the named cargo test group:

   ```bash
   tools/run-cargo-test-group.sh k-nn
   ```

5. Run the single documented development replacement gate when you want the
   full Steelsearch-only validation sequence in one command. This runs the
   build gate, workspace compile gate, daemon smoke check, daemon-backed
   search compatibility fixture, and the required cargo test groups in
   sequence:

   ```bash
   tools/run-development-replacement-gate.sh
   ```

6. Run Steelsearch/OpenSearch comparison only when explicitly requested. This is
   intentionally gated because it starts or targets an OpenSearch daemon and can
   take longer than the Steelsearch-only checks:

   ```bash
   RUN_OPENSEARCH_COMPARISON=1 \
     tools/run-opensearch-compare.sh
   ```

7. Run the migration rehearsal, which starts missing local daemons, loads the
   shared fixture, compares supported behavior, and writes the migration
   validation report:

   ```bash
   tools/run-migration-rehearsal.sh
   ```

Optional load validation stays behind an explicit gate:

```bash
RUN_HTTP_LOAD_TESTS=1 \
  tools/run-http-load-baseline.py --base-url http://127.0.0.1:9200 \
  --output target/http-load-baseline.json
```

## Cutover Rule

The only supported development cutover is data migration into Steelsearch-owned
indices. Existing OpenSearch clusters should remain the source of truth until a
rehearsal has:

1. started OpenSearch and Steelsearch with isolated data paths;
2. loaded equivalent fixtures into both;
3. refreshed both clusters;
4. compared supported search, bulk, k-NN, and operational responses;
5. validated counts and checksums for the migrated fixture set;
6. confirmed `/_steelsearch/readiness` still reports production blockers for any
   missing production gate.

If any unsupported API, direct shard-store reuse, Java data-node membership, or
production gate is required, the development replacement profile does not apply.
