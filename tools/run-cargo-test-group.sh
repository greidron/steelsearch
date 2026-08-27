#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Run a named Steelsearch cargo test group.

Usage:
  tools/run-cargo-test-group.sh [--dry-run] <group>

Groups:
  unit                 Workspace library and binary unit tests.
  daemon-smoke         One real-daemon socket smoke test.
  daemon-integration   Real-daemon integration tests in os-node.
  migration            Migration library tests.
  k-nn                 k-NN plugin tests plus daemon k-NN HTTP tests.
  model-serving        ML Commons tests plus daemon model-serving tests.
  multi-node           Three-daemon development cluster integration test.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

GROUP="${1:-}"
if [[ -z "${GROUP}" ]]; then
  usage >&2
  exit 2
fi

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

cd "${ROOT}"

daemon_test_env=(
  env
  -u STEELSEARCH_URL
  -u STEELSEARCH_HTTP_HOST
  -u STEELSEARCH_HTTP_PORT
  -u STEELSEARCH_TRANSPORT_HOST
  -u STEELSEARCH_TRANSPORT_PORT
  -u STEELSEARCH_WORK_DIR
)

case "${GROUP}" in
  unit)
    run cargo test --workspace --lib --bins -- --test-threads=1
    ;;
  daemon-smoke)
    run "${daemon_test_env[@]}" cargo test -p os-node --features standalone-runtime --test dev_cluster_daemons \
      daemon_smoke_tests_core_rest_endpoints_over_real_socket -- --test-threads=1
    ;;
  daemon-integration)
    run "${daemon_test_env[@]}" cargo test -p os-node --features standalone-runtime --test dev_cluster_daemons daemon_ -- --test-threads=1
    ;;
  migration)
    run cargo test -p os-migration
    ;;
  k-nn)
    run cargo test -p os-plugin-knn
    run "${daemon_test_env[@]}" cargo test -p os-node --features standalone-runtime --test dev_cluster_daemons knn -- --test-threads=1
    ;;
  model-serving)
    run cargo test -p os-ml-commons
    run "${daemon_test_env[@]}" cargo test -p os-node --features standalone-runtime --test dev_cluster_daemons model -- --test-threads=1
    ;;
  multi-node)
    run "${daemon_test_env[@]}" cargo test -p os-node --features standalone-runtime --test dev_cluster_daemons \
      three_local_daemons_form_development_cluster_and_handle_index_smoke -- --test-threads=1
    ;;
  *)
    echo "unknown test group: ${GROUP}" >&2
    usage >&2
    exit 2
    ;;
esac
