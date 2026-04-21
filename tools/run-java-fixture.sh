#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENSEARCH_ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
OUT_DIR="${OUT_DIR:-/tmp/opensearch-fixture-classes}"
FIXTURE_CLASS="org.opensearch.transport.OpenSearchWireFixture"

cd "${OPENSEARCH_ROOT}"

CLASSPATH="$(
  ./gradlew --warning-mode none -q \
    -I "${ROOT}/tools/print-opensearch-classpath.init.gradle" \
    :server:printResolvedClasspath | tail -n 1
)"
LIB_CLASSES="$(find "${OPENSEARCH_ROOT}/libs" -path '*/build/classes/java/main' -type d | paste -sd:)"
LIB_RESOURCES="$(find "${OPENSEARCH_ROOT}/libs" -path '*/build/resources/main' -type d | paste -sd:)"
FULL_CLASSPATH="${CLASSPATH}:${LIB_CLASSES}:${LIB_RESOURCES}"

mkdir -p "${OUT_DIR}"
javac -cp "${FULL_CLASSPATH}" \
  -d "${OUT_DIR}" \
  "${ROOT}/fixtures/java/src/org/opensearch/transport/OpenSearchWireFixture.java"

java -cp "${OUT_DIR}:${FULL_CLASSPATH}" "${FIXTURE_CLASS}"
