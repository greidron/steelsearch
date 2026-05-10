#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"
CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-response-cache/org/opensearch/indices/recovery"
SOURCE_FILE="${CACHE_DIR}/ParseStartRecoveryRequest.java"
CLASS_FILE="${CACHE_DIR}/ParseStartRecoveryRequest.class"

payload_hex=""
version_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --payload-hex) payload_hex="$2"; shift 2 ;;
    --version-id) version_id="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "${payload_hex}" && -n "${version_id}" ]] || {
  echo "usage: $0 --payload-hex <hex> --version-id <id>" >&2
  exit 2
}

mkdir -p "${CACHE_DIR}"

cat > "${SOURCE_FILE}" <<'JAVA'
package org.opensearch.indices.recovery;

import org.opensearch.Version;
import org.opensearch.core.common.io.stream.BytesStreamInput;

public class ParseStartRecoveryRequest {
    private static byte[] fromHex(String hex) {
        int len = hex.length();
        byte[] out = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            out[i / 2] = (byte) Integer.parseInt(hex.substring(i, i + 2), 16);
        }
        return out;
    }

    public static void main(String[] args) throws Exception {
        byte[] payload = fromHex(args[0]);
        int versionId = Integer.parseInt(args[1]);
        BytesStreamInput in = new BytesStreamInput(payload);
        in.setVersion(Version.fromId(versionId));
        StartRecoveryRequest request = new StartRecoveryRequest(in);
        System.out.println("{");
        System.out.println("  \"recovery_id\": " + request.recoveryId() + ",");
        System.out.println("  \"index_name\": \"" + request.shardId().getIndexName() + "\",");
        System.out.println("  \"index_uuid\": \"" + request.shardId().getIndex().getUUID() + "\",");
        System.out.println("  \"shard_id\": " + request.shardId().id() + ",");
        System.out.println("  \"starting_seq_no\": " + request.startingSeqNo() + ",");
        System.out.println("  \"target_transport_address\": \"" +
            request.targetNode().getAddress().address().getHostString() + ":" +
            request.targetNode().getAddress().address().getPort() + "\"");
        System.out.println("}");
    }
}
JAVA

if [[ ! -f "${CLASS_FILE}" || "${SOURCE_FILE}" -nt "${CLASS_FILE}" ]]; then
  javac -proc:none -cp "${LIB_CP}" -d "${TMPDIR:-/tmp}/steelsearch-java-response-cache" "${SOURCE_FILE}"
fi

java -cp "${LIB_CP}:${TMPDIR:-/tmp}/steelsearch-java-response-cache" org.opensearch.indices.recovery.ParseStartRecoveryRequest "${payload_hex}" "${version_id}"
