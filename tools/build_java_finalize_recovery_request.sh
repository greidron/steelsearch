#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"
CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-response-cache/org/opensearch/indices/recovery"
SOURCE_FILE="${CACHE_DIR}/BuildFinalizeRecoveryRequest.java"
CLASS_FILE="${CACHE_DIR}/BuildFinalizeRecoveryRequest.class"

recovery_id=""
request_seq_no=""
index_name=""
index_uuid=""
shard_id=""
global_checkpoint=""
trim_above_seq_no=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recovery-id) recovery_id="$2"; shift 2 ;;
    --request-seq-no) request_seq_no="$2"; shift 2 ;;
    --index-name) index_name="$2"; shift 2 ;;
    --index-uuid) index_uuid="$2"; shift 2 ;;
    --shard-id) shard_id="$2"; shift 2 ;;
    --global-checkpoint) global_checkpoint="$2"; shift 2 ;;
    --trim-above-seq-no) trim_above_seq_no="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "${recovery_id}" && -n "${request_seq_no}" && -n "${index_name}" && -n "${index_uuid}" && -n "${shard_id}" && -n "${global_checkpoint}" && -n "${trim_above_seq_no}" ]] || {
  echo "missing required args" >&2
  exit 2
}

mkdir -p "${CACHE_DIR}"

if [[ ! -f "${CLASS_FILE}" ]]; then
cat > "${SOURCE_FILE}" <<'JAVA'
package org.opensearch.indices.recovery;

import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.core.index.Index;
import org.opensearch.core.index.shard.ShardId;

public class BuildFinalizeRecoveryRequest {
    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        long recoveryId = 0L;
        long requestSeqNo = 0L;
        String indexName = null;
        String indexUuid = null;
        int shardId = -1;
        long globalCheckpoint = 0L;
        long trimAboveSeqNo = -1L;
        for (int i = 0; i < args.length; i += 2) {
            switch (args[i]) {
                case "--recovery-id": recoveryId = Long.parseLong(args[i + 1]); break;
                case "--request-seq-no": requestSeqNo = Long.parseLong(args[i + 1]); break;
                case "--index-name": indexName = args[i + 1]; break;
                case "--index-uuid": indexUuid = args[i + 1]; break;
                case "--shard-id": shardId = Integer.parseInt(args[i + 1]); break;
                case "--global-checkpoint": globalCheckpoint = Long.parseLong(args[i + 1]); break;
                case "--trim-above-seq-no": trimAboveSeqNo = Long.parseLong(args[i + 1]); break;
                default: throw new IllegalArgumentException("unknown arg " + args[i]);
            }
        }
        RecoveryFinalizeRecoveryRequest request = new RecoveryFinalizeRecoveryRequest(
            recoveryId,
            requestSeqNo,
            new ShardId(new Index(indexName, indexUuid), shardId),
            globalCheckpoint,
            trimAboveSeqNo
        );
        BytesStreamOutput out = new BytesStreamOutput();
        request.writeTo(out);
        BytesReference bytesRef = out.bytes();
        var ref = bytesRef.toBytesRef();
        System.out.println(hex(ref.bytes, ref.offset, ref.length));
    }
}
JAVA

javac -proc:none -cp "${LIB_CP}" -d "${TMPDIR:-/tmp}/steelsearch-java-response-cache" "${SOURCE_FILE}"
fi

java -cp "${LIB_CP}:${TMPDIR:-/tmp}/steelsearch-java-response-cache" org.opensearch.indices.recovery.BuildFinalizeRecoveryRequest \
  --recovery-id "${recovery_id}" \
  --request-seq-no "${request_seq_no}" \
  --index-name "${index_name}" \
  --index-uuid "${index_uuid}" \
  --shard-id "${shard_id}" \
  --global-checkpoint "${global_checkpoint}" \
  --trim-above-seq-no "${trim_above_seq_no}"
