#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Run the development replacement gate in a fixed sequence.

Usage:
  tools/run-development-replacement-gate.sh [--dry-run]

Sequence:
  1. cargo build -p os-node --features standalone-runtime --bin steelsearch
  2. cargo test --workspace --no-run
  3. tools/run-steelsearch-smoke.sh
  4. tools/run-daemon-backed-search-compat.sh
  5. tools/run-cargo-test-group.sh unit
  6. tools/run-cargo-test-group.sh daemon-integration
  7. tools/run-cargo-test-group.sh migration
  8. tools/run-cargo-test-group.sh k-nn
  9. tools/run-cargo-test-group.sh model-serving
 10. tools/run-cargo-test-group.sh multi-node
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

if [[ "$#" -ne 0 ]]; then
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

run cargo build -p os-node --features standalone-runtime --bin steelsearch
run cargo test --workspace --no-run
run tools/run-steelsearch-smoke.sh
run tools/run-daemon-backed-search-compat.sh
run tools/run-cargo-test-group.sh unit
run tools/run-cargo-test-group.sh daemon-integration
run tools/run-cargo-test-group.sh migration
run tools/run-cargo-test-group.sh k-nn
run tools/run-cargo-test-group.sh model-serving
run tools/run-cargo-test-group.sh multi-node
