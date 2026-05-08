#!/usr/bin/env bash
set -euo pipefail
ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
DIST="${ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_DIR="${DIST}/lib"

BODY_HEX=""
REPORT_PATH=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --body-hex)
      BODY_HEX="$2"
      shift 2
      ;;
    --report-path)
      REPORT_PATH="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${BODY_HEX}" || -z "${REPORT_PATH}" ]]; then
  echo "usage: $0 --body-hex <hex> --report-path <path>" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d -t java-publish-parse.XXXXXX)"
cat >"${TMP_DIR}/JavaPublishStateRequestParse.java" <<'JAVA'
package org.opensearch.transport.nativeprotocol;

import java.io.IOException;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.opensearch.Version;
import org.opensearch.cluster.ClusterModule;
import org.opensearch.cluster.ClusterState;
import org.opensearch.cluster.coordination.CompressedStreamUtils;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.core.common.io.stream.BytesStreamInput;
import org.opensearch.core.common.io.stream.NamedWriteableRegistry;
import org.opensearch.core.common.io.stream.StreamInput;
import org.opensearch.core.common.transport.TransportAddress;
import org.opensearch.transport.BytesTransportRequest;

public class JavaPublishStateRequestParse {
    private static byte[] fromHex(String hex) {
        int len = hex.length();
        byte[] out = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            out[i / 2] = (byte) Integer.parseInt(hex.substring(i, i + 2), 16);
        }
        return out;
    }

    private static String jsonEscape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static String quote(String value) {
        return "\"" + jsonEscape(value) + "\"";
    }

    public static void main(String[] args) throws Exception {
        String bodyHex = args[0];
        String reportPath = args[1];
        byte[] raw = fromHex(bodyHex);

        long requestId = ByteBuffer.wrap(raw, 0, 8).getLong();
        int status = raw[8] & 0xFF;
        int versionId = ByteBuffer.wrap(raw, 9, 4).getInt();
        int variableHeaderSize = ByteBuffer.wrap(raw, 13, 4).getInt();
        int payloadOffset = 17 + variableHeaderSize;
        byte[] payload = new byte[raw.length - payloadOffset];
        System.arraycopy(raw, payloadOffset, payload, 0, payload.length);

        BytesStreamInput requestInput = new BytesStreamInput(payload);
        requestInput.setVersion(Version.fromId(versionId));
        BytesTransportRequest request = new BytesTransportRequest(requestInput);
        NamedWriteableRegistry registry = new NamedWriteableRegistry(ClusterModule.getNamedWriteables());

        boolean fullState;
        Long term = null;
        Long version = null;
        String clusterName = null;
        String stateUuid = null;
        try (StreamInput in = CompressedStreamUtils.decompressBytes(request, registry)) {
            fullState = in.readBoolean();
            if (fullState) {
                DiscoveryNode localNode = new DiscoveryNode(
                    "decoder-local",
                    new TransportAddress(InetAddress.getByName("127.0.0.1"), 0),
                    Version.fromId(versionId)
                );
                ClusterState state = ClusterState.readFrom(in, localNode);
                term = state.term();
                version = state.version();
                clusterName = state.getClusterName().value();
                stateUuid = state.stateUUID();
            }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"request_id\": ").append(requestId).append(",\n");
        sb.append("  \"status\": ").append(status).append(",\n");
        sb.append("  \"header_version_id\": ").append(versionId).append(",\n");
        sb.append("  \"variable_header_size\": ").append(variableHeaderSize).append(",\n");
        sb.append("  \"full_state\": ").append(fullState).append(",\n");
        sb.append("  \"term\": ").append(term == null ? "null" : term).append(",\n");
        sb.append("  \"version\": ").append(version == null ? "null" : version).append(",\n");
        sb.append("  \"cluster_name\": ").append(clusterName == null ? "null" : quote(clusterName)).append(",\n");
        sb.append("  \"state_uuid\": ").append(stateUuid == null ? "null" : quote(stateUuid)).append("\n");
        sb.append("}\n");

        Files.writeString(Path.of(reportPath), sb.toString(), StandardCharsets.UTF_8);
        System.out.print(sb.toString());
    }
}
JAVA
javac -cp "${LIB_DIR}/*" -d "${TMP_DIR}" "${TMP_DIR}/JavaPublishStateRequestParse.java"
java -cp "${TMP_DIR}:${LIB_DIR}/*" org.opensearch.transport.nativeprotocol.JavaPublishStateRequestParse "${BODY_HEX}" "${REPORT_PATH}"
