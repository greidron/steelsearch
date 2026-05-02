#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${SECURITY_COMPAT_PROFILE:-single-node-secure}"
POLICY_FILE="${SECURITY_BOOTSTRAP_POLICY:-${ROOT}/tools/fixtures/security-bootstrap-policy.json}"
FIXTURE=""
REPORT_DIR=""
REPORT_PATH=""
STEELSEARCH_URL="${STEELSEARCH_URL:-}"
OPENSEARCH_URL="${OPENSEARCH_URL:-}"
USER_SET_FIXTURE=0
USER_SET_REPORT_DIR=0
USER_SET_REPORT_PATH=0

usage() {
  cat <<'USAGE'
Run the security/authz compatibility harness.

This harness is the entrypoint for secure standalone parity work. It is
intentionally strict about missing prerequisites so later tasks can plug in
fixture, certificate, and multi-node bootstrap details without changing the
command shape again.

Options:
  --profile <name>        Secure profile to run.
                          Supported today:
                            single-node-secure
                            multi-node-secure
  --policy <path>         Repo-local bootstrap policy fixture.
  --fixture <path>        Compatibility fixture path.
  --report-dir <path>     Output directory for reports.
  --report <path>         Explicit report path.
  --steelsearch-url <u>   Existing Steelsearch HTTPS/HTTP endpoint.
  --opensearch-url <u>    Existing OpenSearch HTTPS/HTTP endpoint.
  -h, --help              Show this help text.

Environment:
  SECURITY_COMPAT_PROFILE            Default profile.
  SECURITY_BOOTSTRAP_POLICY          Repo-local bootstrap policy fixture.
  SECURITY_AUTHZ_FIXTURE             Default fixture path override.
  SECURITY_COMPAT_REPORT_DIR         Default report directory override.
  SECURITY_AUTHZ_REPORT              Default report path override.
  SECURITY_SINGLE_NODE_STEELSEARCH_URL
                                     Single-node secure endpoint override.
  SECURITY_SINGLE_NODE_OPENSEARCH_URL
                                     Single-node OpenSearch secure endpoint override.
  SECURITY_MULTI_NODE_STEELSEARCH_URL
                                     Multi-node secure coordinator endpoint override.
  SECURITY_MULTI_NODE_OPENSEARCH_URL
                                     Multi-node OpenSearch secure coordinator endpoint override.
  SECURITY_MULTI_NODE_SEEDS          Comma-separated secure Steelsearch node seed list.
  STEELSEARCH_URL                    Fallback Steelsearch endpoint.
  OPENSEARCH_URL                     Fallback OpenSearch endpoint.

Current boundary:
  - bootstrap/cert generation is not wired yet
  - the canonical fixture tools/fixtures/security-authz-compat.json is not
    expected to exist until the next security/authz tasks land
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:?missing value for --profile}"
      shift 2
      ;;
    --fixture)
      FIXTURE="${2:?missing value for --fixture}"
      USER_SET_FIXTURE=1
      shift 2
      ;;
    --policy)
      POLICY_FILE="${2:?missing value for --policy}"
      shift 2
      ;;
    --report-dir)
      REPORT_DIR="${2:?missing value for --report-dir}"
      USER_SET_REPORT_DIR=1
      shift 2
      ;;
    --report)
      REPORT_PATH="${2:?missing value for --report}"
      USER_SET_REPORT_PATH=1
      shift 2
      ;;
    --steelsearch-url)
      STEELSEARCH_URL="${2:?missing value for --steelsearch-url}"
      shift 2
      ;;
    --opensearch-url)
      OPENSEARCH_URL="${2:?missing value for --opensearch-url}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

load_profile_policy() {
  if [[ ! -f "${POLICY_FILE}" ]]; then
    echo "security bootstrap policy not found: ${POLICY_FILE}" >&2
    exit 2
  fi
  eval "$(
    python3 - "${POLICY_FILE}" "${PROFILE}" <<'PY'
import json
import shlex
import sys

policy = json.load(open(sys.argv[1], encoding="utf-8"))
profile = policy.get("profiles", {}).get(sys.argv[2])
if profile is None:
    raise SystemExit(f"unsupported security profile in policy: {sys.argv[2]}")

def emit(name: str, value: str) -> None:
    print(f"{name}={shlex.quote(value)}")

emit("POLICY_FIXTURE", profile.get("fixture", ""))
emit("POLICY_REPORT_DIR", profile.get("report_dir", ""))
emit("POLICY_BOOTSTRAP_MODE", profile.get("bootstrap_mode", ""))
emit("POLICY_PKI_ROOT", policy.get("pki_root", ""))
emit("POLICY_SERVER_CERT_DIR", profile.get("server_cert_dir", ""))
emit("POLICY_STEELSEARCH_URL_ENV", profile.get("steelsearch_url_env", ""))
emit("POLICY_OPENSEARCH_URL_ENV", profile.get("opensearch_url_env", ""))
emit("POLICY_MULTI_NODE_SEEDS_ENV", profile.get("multi_node_seeds_env", ""))
for key, value in sorted((profile.get("credential_env") or {}).items()):
    shell_key = "CRED_" + key.upper()
    emit(shell_key, value)
PY
  )"
}

apply_runtime_env_defaults() {
  local pki_root="${ROOT}/${POLICY_PKI_ROOT}"
  local server_cert_dir="${ROOT}/${POLICY_SERVER_CERT_DIR}"

  export STEELSEARCH_SECURITY_ENABLED="${STEELSEARCH_SECURITY_ENABLED:-true}"
  export STEELSEARCH_HTTP_TLS_ENABLED="${STEELSEARCH_HTTP_TLS_ENABLED:-true}"
  export STEELSEARCH_TRANSPORT_TLS_ENABLED="${STEELSEARCH_TRANSPORT_TLS_ENABLED:-true}"
  export STEELSEARCH_SECURITY_BOOTSTRAP_MODE="${STEELSEARCH_SECURITY_BOOTSTRAP_MODE:-${PROFILE}}"

  export STEELSEARCH_TEST_CA_CERT="${STEELSEARCH_TEST_CA_CERT:-${pki_root}/ca/ca.crt}"
  export STEELSEARCH_TEST_CA_KEY="${STEELSEARCH_TEST_CA_KEY:-${pki_root}/ca/ca.key}"

  export STEELSEARCH_TEST_HTTP_CERT="${STEELSEARCH_TEST_HTTP_CERT:-${server_cert_dir}/http.crt}"
  export STEELSEARCH_TEST_HTTP_KEY="${STEELSEARCH_TEST_HTTP_KEY:-${server_cert_dir}/http.key}"
  export STEELSEARCH_TEST_TRANSPORT_CERT="${STEELSEARCH_TEST_TRANSPORT_CERT:-${server_cert_dir}/transport.crt}"
  export STEELSEARCH_TEST_TRANSPORT_KEY="${STEELSEARCH_TEST_TRANSPORT_KEY:-${server_cert_dir}/transport.key}"

  export STEELSEARCH_TEST_ADMIN_CERT="${STEELSEARCH_TEST_ADMIN_CERT:-${pki_root}/client/admin/client.crt}"
  export STEELSEARCH_TEST_ADMIN_KEY="${STEELSEARCH_TEST_ADMIN_KEY:-${pki_root}/client/admin/client.key}"
  export STEELSEARCH_TEST_READER_CERT="${STEELSEARCH_TEST_READER_CERT:-${pki_root}/client/reader/client.crt}"
  export STEELSEARCH_TEST_READER_KEY="${STEELSEARCH_TEST_READER_KEY:-${pki_root}/client/reader/client.key}"
  export STEELSEARCH_TEST_WRITER_CERT="${STEELSEARCH_TEST_WRITER_CERT:-${pki_root}/client/writer/client.crt}"
  export STEELSEARCH_TEST_WRITER_KEY="${STEELSEARCH_TEST_WRITER_KEY:-${pki_root}/client/writer/client.key}"
}

configure_profile() {
  case "${PROFILE}" in
    single-node-secure)
      [[ "${USER_SET_FIXTURE}" == "1" ]] || FIXTURE="${SECURITY_AUTHZ_FIXTURE:-${ROOT}/${POLICY_FIXTURE}}"
      [[ "${USER_SET_REPORT_DIR}" == "1" ]] || REPORT_DIR="${SECURITY_COMPAT_REPORT_DIR:-${ROOT}/${POLICY_REPORT_DIR}}"
      [[ "${USER_SET_REPORT_PATH}" == "1" ]] || REPORT_PATH="${SECURITY_AUTHZ_REPORT:-${REPORT_DIR}/security-authz-compat-report.json}"
      [[ -n "${STEELSEARCH_URL}" ]] || STEELSEARCH_URL="${!POLICY_STEELSEARCH_URL_ENV:-}"
      [[ -n "${OPENSEARCH_URL}" ]] || OPENSEARCH_URL="${!POLICY_OPENSEARCH_URL_ENV:-}"
      ;;
    multi-node-secure)
      [[ "${USER_SET_FIXTURE}" == "1" ]] || FIXTURE="${SECURITY_AUTHZ_FIXTURE:-${ROOT}/${POLICY_FIXTURE}}"
      [[ "${USER_SET_REPORT_DIR}" == "1" ]] || REPORT_DIR="${SECURITY_COMPAT_REPORT_DIR:-${ROOT}/${POLICY_REPORT_DIR}}"
      [[ "${USER_SET_REPORT_PATH}" == "1" ]] || REPORT_PATH="${SECURITY_AUTHZ_REPORT:-${REPORT_DIR}/security-authz-compat-report.json}"
      [[ -n "${STEELSEARCH_URL}" ]] || STEELSEARCH_URL="${!POLICY_STEELSEARCH_URL_ENV:-}"
      [[ -n "${OPENSEARCH_URL}" ]] || OPENSEARCH_URL="${!POLICY_OPENSEARCH_URL_ENV:-}"
      ;;
    *)
      echo "unsupported security profile: ${PROFILE}" >&2
      exit 2
      ;;
  esac
}

load_profile_policy
configure_profile
apply_runtime_env_defaults

if [[ ! -f "${FIXTURE}" ]]; then
  echo "security fixture not found: ${FIXTURE}" >&2
  echo "add tools/fixtures/security-authz-compat.json before running this harness" >&2
  exit 2
fi

if [[ -z "${STEELSEARCH_URL}" ]]; then
  echo "STEELSEARCH_URL or --steelsearch-url is required" >&2
  echo "bootstrap/startup wiring for secure standalone is tracked by later security tasks" >&2
  exit 2
fi

mkdir -p "${REPORT_DIR}"

cmd=(
  python3 "${ROOT}/tools/search_compat.py"
  --fixture "${FIXTURE}"
  --report "${REPORT_PATH}"
  --steelsearch-url "${STEELSEARCH_URL%/}"
)

if [[ -n "${OPENSEARCH_URL}" ]]; then
  cmd+=(--opensearch-url "${OPENSEARCH_URL%/}")
fi

echo "security compat profile: ${PROFILE}"
echo "security bootstrap policy: ${POLICY_FILE}"
echo "security bootstrap mode: ${POLICY_BOOTSTRAP_MODE}"
if [[ -n "${POLICY_PKI_ROOT:-}" ]]; then
  echo "security pki root: ${ROOT}/${POLICY_PKI_ROOT}"
fi
if [[ -n "${POLICY_SERVER_CERT_DIR:-}" ]]; then
  echo "security server cert dir: ${ROOT}/${POLICY_SERVER_CERT_DIR}"
fi
echo "security compat fixture: ${FIXTURE}"
echo "security compat report: ${REPORT_PATH}"
echo "security runtime env: STEELSEARCH_SECURITY_ENABLED=${STEELSEARCH_SECURITY_ENABLED}"
echo "security runtime env: STEELSEARCH_HTTP_TLS_ENABLED=${STEELSEARCH_HTTP_TLS_ENABLED}"
echo "security runtime env: STEELSEARCH_TRANSPORT_TLS_ENABLED=${STEELSEARCH_TRANSPORT_TLS_ENABLED}"
echo "security runtime env: STEELSEARCH_SECURITY_BOOTSTRAP_MODE=${STEELSEARCH_SECURITY_BOOTSTRAP_MODE}"
echo "security runtime env: STEELSEARCH_TEST_HTTP_CERT=${STEELSEARCH_TEST_HTTP_CERT}"
echo "security runtime env: STEELSEARCH_TEST_TRANSPORT_CERT=${STEELSEARCH_TEST_TRANSPORT_CERT}"
echo "security admin credential env: ${CRED_ADMIN_USERNAME:-<unset>} / ${CRED_ADMIN_PASSWORD:-<unset>}"
echo "security reader credential env: ${CRED_READER_USERNAME:-<unset>} / ${CRED_READER_PASSWORD:-<unset>}"
echo "security writer credential env: ${CRED_WRITER_USERNAME:-<unset>} / ${CRED_WRITER_PASSWORD:-<unset>}"
if [[ "${PROFILE}" == "multi-node-secure" ]]; then
  echo "security multi-node seeds env: ${POLICY_MULTI_NODE_SEEDS_ENV:-<unset>}"
  if [[ -n "${POLICY_MULTI_NODE_SEEDS_ENV:-}" ]]; then
    echo "security multi-node seeds: ${!POLICY_MULTI_NODE_SEEDS_ENV:-<not set>}"
  fi
fi
"${cmd[@]}"
