#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"

body_hex=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --body-hex) body_hex="$2"; shift 2 ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

cat > "${tmpdir}/ParsePublishWithJoinResponse.java" <<'JAVA'
import org.opensearch.cluster.coordination.PublishWithJoinResponse;
import org.opensearch.core.common.io.stream.BytesStreamInput;

public class ParsePublishWithJoinResponse {
    private static byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) Integer.parseInt(hex.substring(i, i + 2), 16);
        }
        return data;
    }

    public static void main(String[] args) throws Exception {
        byte[] body = hexToBytes(args[0]);
        int payloadOffset = 13;
        int variableHeaderSize =
            ((body[9] & 0xff) << 24)
            | ((body[10] & 0xff) << 16)
            | ((body[11] & 0xff) << 8)
            | (body[12] & 0xff);
        if (body.length >= 17) {
            variableHeaderSize =
                ((body[13] & 0xff) << 24)
                | ((body[14] & 0xff) << 16)
                | ((body[15] & 0xff) << 8)
                | (body[16] & 0xff);
            payloadOffset = 17 + variableHeaderSize;
        }
        byte[] payload = new byte[body.length - payloadOffset];
        System.arraycopy(body, payloadOffset, payload, 0, payload.length);
        PublishWithJoinResponse response = new PublishWithJoinResponse(new BytesStreamInput(payload));
        System.out.println("{"
            + "\"term\":" + response.getPublishResponse().getTerm()
            + ",\"version\":" + response.getPublishResponse().getVersion()
            + ",\"variable_header_size\":" + variableHeaderSize
            + ",\"join_present\":" + response.getJoin().isPresent()
            + (response.getJoin().isPresent()
                ? ",\"join_source\":\"" + response.getJoin().get().getSourceNode().getName() + "\""
                + ",\"join_target\":\"" + response.getJoin().get().getTargetNode().getName() + "\""
                + ",\"join_last_accepted_term\":" + response.getJoin().get().getLastAcceptedTerm()
                + ",\"join_last_accepted_version\":" + response.getJoin().get().getLastAcceptedVersion()
                : "")
            + "}");
    }
}
JAVA

javac -proc:none -cp "${LIB_CP}" "${tmpdir}/ParsePublishWithJoinResponse.java"
java -cp "${LIB_CP}:${tmpdir}" ParsePublishWithJoinResponse "${body_hex}"
