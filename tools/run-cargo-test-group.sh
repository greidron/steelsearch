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

case "${GROUP}" in
  unit)
    run cargo test --workspace --lib --bins
    ;;
  daemon-smoke)
    run cargo test -p os-node --test dev_cluster_daemons \
      daemon_smoke_tests_core_rest_endpoints_over_real_socket
    ;;
  daemon-integration)
    run cargo test -p os-node --test dev_cluster_daemons daemon_
    ;;
  migration)
    run cargo test -p os-migration
    ;;
  k-nn)
    run cargo test -p os-plugin-knn
    run cargo test -p os-node --test dev_cluster_daemons knn
    ;;
  model-serving)
    run cargo test -p os-ml-commons
    run cargo test -p os-node --test dev_cluster_daemons model
    ;;
  multi-node)
    run cargo test -p os-node --test dev_cluster_daemons \
      three_local_daemons_form_development_cluster_and_handle_index_smoke
    ;;
  *)
    echo "unknown test group: ${GROUP}" >&2
    usage >&2
    exit 2
    ;;
esac
