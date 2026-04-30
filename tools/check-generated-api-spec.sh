#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python3 tools/generate_api_spec_docs.py

git diff --exit-code -- \
  docs/api-spec/generated/rest-routes.md \
  docs/api-spec/generated/transport-actions.md \
  docs/api-spec/generated/route-evidence-matrix.md \
  docs/api-spec/generated/openapi.json

cargo test -p os-core generated_openapi_and_route_evidence_artifacts_are_release_auditable --test generated_api_spec_artifacts -- --nocapture

echo "generated api spec artifacts are in sync"
