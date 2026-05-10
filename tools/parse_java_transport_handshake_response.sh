#!/usr/bin/env bash
set -euo pipefail
ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
DIST="${ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_DIR="${DIST}/lib"

RESPONSE_HEX=""
REPORT_PATH=""
HTTP_ADDRESS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --response-hex)
      RESPONSE_HEX="$2"
      shift 2
      ;;
    --report-path)
      REPORT_PATH="$2"
      shift 2
      ;;
    --http-address)
      HTTP_ADDRESS="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${RESPONSE_HEX}" || -z "${REPORT_PATH}" ]]; then
  echo "usage: $0 --response-hex <hex> --report-path <path> [--http-address <host:port>]" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d -t java-transport-handshake-parse.XXXXXX)"
cat >"${TMP_DIR}/JavaTransportHandshakeResponseParse.java" <<'JAVA'
package org.opensearch.transport.nativeprotocol;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Collectors;
import org.opensearch.Version;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.cluster.node.DiscoveryNodeRole;
import org.opensearch.transport.TransportService;
import org.opensearch.core.common.io.stream.BytesStreamInput;

public class JavaTransportHandshakeResponseParse {
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

    public static void main(String[] args) throws IOException {
        String responseHex = args[0];
        String reportPath = args[1];
        String httpAddress = args.length > 2 ? args[2] : "";
        byte[] raw = fromHex(responseHex);

        String marker = new String(raw, 0, 2, StandardCharsets.US_ASCII);
        int messageLength = ByteBuffer.wrap(raw, 2, 4).getInt();
        long requestId = ByteBuffer.wrap(raw, 6, 8).getLong();
        int status = raw[14] & 0xFF;
        int versionId = ByteBuffer.wrap(raw, 15, 4).getInt();
        int variableHeaderSize = ByteBuffer.wrap(raw, 19, 4).getInt();
        int payloadOffset = 23 + variableHeaderSize;
        byte[] payload = new byte[raw.length - payloadOffset];
        System.arraycopy(raw, payloadOffset, payload, 0, payload.length);

        BytesStreamInput in = new BytesStreamInput(payload);
        in.setVersion(Version.fromId(versionId));
        TransportService.HandshakeResponse response = new TransportService.HandshakeResponse(in);
        DiscoveryNode node = response.getDiscoveryNode();

        String roles = node.getRoles()
            .stream()
            .map(DiscoveryNodeRole::roleName)
            .sorted()
            .map(JavaTransportHandshakeResponseParse::quote)
            .collect(Collectors.joining(","));

        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"marker_prefix\": ").append(quote(marker)).append(",\n");
        sb.append("  \"message_length\": ").append(messageLength).append(",\n");
        sb.append("  \"request_id\": ").append(requestId).append(",\n");
        sb.append("  \"status\": ").append(status).append(",\n");
        sb.append("  \"is_response\": ").append((status & 0x01) != 0).append(",\n");
        sb.append("  \"is_handshake\": ").append((status & 0x08) != 0).append(",\n");
        sb.append("  \"header_version_id\": ").append(versionId).append(",\n");
        sb.append("  \"variable_header_size\": ").append(variableHeaderSize).append(",\n");
        sb.append("  \"peer_identity_present\": ").append(node != null).append(",\n");
        sb.append("  \"cluster_name\": ").append(quote(response.getClusterName().value())).append(",\n");
        sb.append("  \"response_version_id\": ").append(response.getDiscoveryNode().getVersion().id).append(",\n");
        sb.append("  \"discovery_node\": {\n");
        sb.append("    \"name\": ").append(quote(node.getName())).append(",\n");
        sb.append("    \"id\": ").append(quote(node.getId())).append(",\n");
        sb.append("    \"ephemeral_id\": ").append(quote(node.getEphemeralId())).append(",\n");
        sb.append("    \"host_name\": ").append(quote(node.getHostName())).append(",\n");
        sb.append("    \"host_address\": ").append(quote(node.getHostAddress())).append(",\n");
        if (httpAddress.isEmpty() == false) {
            sb.append("    \"http_address\": ").append(quote(httpAddress)).append(",\n");
        }
        sb.append("    \"transport_address\": ").append(quote(node.getAddress().toString())).append(",\n");
        sb.append("    \"version_id\": ").append(node.getVersion().id).append(",\n");
        sb.append("    \"roles\": [").append(roles).append("]\n");
        sb.append("  }\n");
        sb.append("}\n");

        Files.writeString(Path.of(reportPath), sb.toString(), StandardCharsets.UTF_8);
        System.out.print(sb.toString());
    }
}
JAVA
javac -cp "${LIB_DIR}/*" -d "${TMP_DIR}" "${TMP_DIR}/JavaTransportHandshakeResponseParse.java"
java -cp "${TMP_DIR}:${LIB_DIR}/*" org.opensearch.transport.nativeprotocol.JavaTransportHandshakeResponseParse "${RESPONSE_HEX}" "${REPORT_PATH}" "${HTTP_ADDRESS}"
