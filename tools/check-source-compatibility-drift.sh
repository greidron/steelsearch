#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

OUT_DIR="${TMP_DIR}" "${ROOT}/tools/source-compatibility-matrix.sh" >/dev/null

diff -u \
  "${ROOT}/docs/rust-port/generated/source-rest-routes.tsv" \
  "${TMP_DIR}/source-rest-routes.tsv"

diff -u \
  "${ROOT}/docs/rust-port/generated/source-transport-actions.tsv" \
  "${TMP_DIR}/source-transport-actions.tsv"

echo "source compatibility generated TSVs are up to date"
