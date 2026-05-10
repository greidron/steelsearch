#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"
CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-response-cache/org/opensearch/indices/recovery"
SOURCE_FILE="${CACHE_DIR}/BuildRecoveryResponse.java"
CLASS_FILE="${CACHE_DIR}/BuildRecoveryResponse.class"

mkdir -p "${CACHE_DIR}"

if [[ ! -f "${CLASS_FILE}" ]]; then
cat > "${SOURCE_FILE}" <<'JAVA'
package org.opensearch.indices.recovery;

import java.util.List;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.bytes.BytesReference;

public class BuildRecoveryResponse {
    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        RecoveryResponse response = new RecoveryResponse(
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            0L,
            0L,
            0L,
            0L,
            0L,
            0,
            0L
        );
        BytesStreamOutput out = new BytesStreamOutput();
        response.writeTo(out);
        BytesReference bytesRef = out.bytes();
        var ref = bytesRef.toBytesRef();
        System.out.println(hex(ref.bytes, ref.offset, ref.length));
    }
}
JAVA

javac -proc:none -cp "${LIB_CP}" -d "${TMPDIR:-/tmp}/steelsearch-java-response-cache" "${SOURCE_FILE}"
fi

java -cp "${LIB_CP}:${TMPDIR:-/tmp}/steelsearch-java-response-cache" org.opensearch.indices.recovery.BuildRecoveryResponse
