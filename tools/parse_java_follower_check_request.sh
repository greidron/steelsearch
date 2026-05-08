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

TMP_DIR="$(mktemp -d -t java-follower-check-parse.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

cat >"${TMP_DIR}/JavaFollowerCheckRequestParse.java" <<'JAVA'
package org.opensearch.transport.nativeprotocol;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

public class JavaFollowerCheckRequestParse {
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

    private static int[] readVInt(byte[] bytes, int offset) {
        int value = 0;
        int shift = 0;
        int index = offset;
        while (true) {
            int current = bytes[index++] & 0xFF;
            value |= (current & 0x7F) << shift;
            if ((current & 0x80) == 0) {
                return new int[] { value, index };
            }
            shift += 7;
        }
    }

    private static String[] readString(byte[] bytes, int offset) {
        int[] vint = readVInt(bytes, offset);
        int length = vint[0];
        int index = vint[1];
        String value = new String(bytes, index, length, StandardCharsets.UTF_8);
        return new String[] { value, Integer.toString(index + length) };
    }

    public static void main(String[] args) throws Exception {
        String bodyHex = args[0];
        String reportPath = args[1];
        byte[] raw = fromHex(bodyHex);

        long requestId = ByteBuffer.wrap(raw, 0, 8).getLong();
        int status = raw[8] & 0xFF;
        int versionId = ByteBuffer.wrap(raw, 9, 4).getInt();
        int variableHeaderSize = ByteBuffer.wrap(raw, 13, 4).getInt();
        int actionLength = ByteBuffer.wrap(raw, 17, 4).getInt();
        String action = new String(raw, 21, actionLength, StandardCharsets.UTF_8);
        byte[] requestPayload = Arrays.copyOfRange(raw, 17 + variableHeaderSize, raw.length);
        int offset = 0;
        String[] parentTaskNode = readString(requestPayload, offset);
        offset = Integer.parseInt(parentTaskNode[1]);
        long term = ByteBuffer.wrap(requestPayload, offset, 8).getLong();
        offset += 8;
        String[] senderName = readString(requestPayload, offset);
        offset = Integer.parseInt(senderName[1]);
        String[] senderId = readString(requestPayload, offset);
        offset = Integer.parseInt(senderId[1]);
        String[] senderEphemeralId = readString(requestPayload, offset);
        offset = Integer.parseInt(senderEphemeralId[1]);
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"request_id\": ").append(requestId).append(",\n");
        sb.append("  \"status\": ").append(status).append(",\n");
        sb.append("  \"header_version_id\": ").append(versionId).append(",\n");
        sb.append("  \"variable_header_size\": ").append(variableHeaderSize).append(",\n");
        sb.append("  \"action\": ").append(quote(action)).append(",\n");
        sb.append("  \"parent_task_node\": ").append(quote(parentTaskNode[0])).append(",\n");
        sb.append("  \"term\": ").append(term).append(",\n");
        sb.append("  \"sender\": {\n");
        sb.append("    \"name\": ").append(quote(senderName[0])).append(",\n");
        sb.append("    \"id\": ").append(quote(senderId[0])).append(",\n");
        sb.append("    \"ephemeral_id\": ").append(quote(senderEphemeralId[0])).append("\n");
        sb.append("  }\n");
        sb.append("}\n");

        Files.writeString(Path.of(reportPath), sb.toString(), StandardCharsets.UTF_8);
        System.out.print(sb.toString());
    }
}
JAVA

javac -proc:none -cp "${LIB_DIR}/*" -d "${TMP_DIR}" "${TMP_DIR}/JavaFollowerCheckRequestParse.java"
java -cp "${TMP_DIR}:${LIB_DIR}/*" org.opensearch.transport.nativeprotocol.JavaFollowerCheckRequestParse "${BODY_HEX}" "${REPORT_PATH}"
