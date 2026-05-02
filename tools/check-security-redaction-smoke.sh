#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <file-or-dir> [<file-or-dir> ...]" >&2
  exit 2
fi

forbidden_patterns=(
  'Authorization: Basic '
  'Authorization: Bearer '
  'SECURITY_ADMIN_PASSWORD='
  'SECURITY_READER_PASSWORD='
  'SECURITY_WRITER_PASSWORD='
  'BEGIN PRIVATE KEY'
  'BEGIN EC PRIVATE KEY'
  'BEGIN RSA PRIVATE KEY'
  'malformed-token-authz'
)

status=0

for target in "$@"; do
  if [[ ! -e "$target" ]]; then
    echo "redaction smoke target missing: $target" >&2
    status=1
    continue
  fi

  for pattern in "${forbidden_patterns[@]}"; do
    if grep -R -n -F -- "$pattern" "$target" >/tmp/security-redaction-smoke.$$ 2>/dev/null; then
      echo "forbidden security material detected: $pattern" >&2
      cat /tmp/security-redaction-smoke.$$ >&2
      status=1
    fi
  done
done

rm -f /tmp/security-redaction-smoke.$$
exit "$status"
