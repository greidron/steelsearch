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

python3 "${ROOT}/tools/check-source-rest-route-lines.py" \
  "${ROOT}/docs/rust-port/generated/source-rest-routes.tsv"

python3 "${ROOT}/tools/report-rest-api-coverage.py" \
  --source "${ROOT}/docs/rust-port/generated/source-rest-routes.tsv" \
  --fixtures-dir "${ROOT}/tools/fixtures" \
  --require-fixture-coverage \
  --summary-only

diff -u \
  "${ROOT}/docs/rust-port/generated/source-transport-actions.tsv" \
  "${TMP_DIR}/source-transport-actions.tsv"

python3 "${ROOT}/tools/check-source-transport-action-lines.py" \
  "${ROOT}/docs/rust-port/generated/source-transport-actions.tsv"

python3 "${ROOT}/tools/report-transport-action-coverage.py" \
  --source "${ROOT}/docs/rust-port/generated/source-transport-actions.tsv" \
  --require-release-parity \
  --summary-only

diff -u \
  "${ROOT}/docs/rust-port/generated/source-search-registrations.tsv" \
  "${TMP_DIR}/source-search-registrations.tsv"

python3 "${ROOT}/tools/check-source-search-registration-lines.py" \
  "${ROOT}/docs/rust-port/generated/source-search-registrations.tsv"

python3 "${ROOT}/tools/check-search-extension-point-contracts.py" \
  --source-search-registrations "${ROOT}/docs/rust-port/generated/source-search-registrations.tsv" \
  --runtime-source "${ROOT}/crates/os-node/src/standalone_runtime.rs"

diff -u \
  "${ROOT}/docs/rust-port/generated/source-node-runtime-components.tsv" \
  "${TMP_DIR}/source-node-runtime-components.tsv"

python3 "${ROOT}/tools/check-source-node-runtime-lines.py" \
  "${ROOT}/docs/rust-port/generated/source-node-runtime-components.tsv"

python3 "${ROOT}/tools/check-node-runtime-boundary-contracts.py" \
  --source-node-runtime "${ROOT}/docs/rust-port/generated/source-node-runtime-components.tsv" \
  --runtime-source "${ROOT}/crates/os-node/src/standalone_runtime.rs"

diff -u \
  "${ROOT}/docs/rust-port/generated/source-compatibility-matrix.tsv" \
  "${TMP_DIR}/source-compatibility-matrix.tsv"

python3 "${ROOT}/tools/check-source-compatibility-matrix-coverage.py" \
  --matrix "${ROOT}/docs/rust-port/generated/source-compatibility-matrix.tsv" \
  --generated-dir "${ROOT}/docs/rust-port/generated"

python3 "${ROOT}/tools/report-source-compatibility-gaps.py" \
  --matrix "${ROOT}/docs/rust-port/generated/source-compatibility-matrix.tsv" \
  --require-all-gaps-mapped

python3 "${ROOT}/tools/check-source-partial-promotion-readiness.py" \
  --matrix "${ROOT}/docs/rust-port/generated/source-compatibility-matrix.tsv" \
  --ledger "${ROOT}/tools/fixtures/source-partial-promotion-readiness.json"

echo "source compatibility generated TSVs are up to date"
