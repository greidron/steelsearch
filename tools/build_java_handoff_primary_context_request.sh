#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"
CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-response-cache/org/opensearch/indices/recovery"
SOURCE_FILE="${CACHE_DIR}/BuildHandoffPrimaryContextRequest.java"
CLASS_FILE="${CACHE_DIR}/BuildHandoffPrimaryContextRequest.class"

recovery_id=""
index_name=""
index_uuid=""
shard_id=""
node_id=""
allocation_id=""
cluster_state_version=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recovery-id) recovery_id="$2"; shift 2 ;;
    --index-name) index_name="$2"; shift 2 ;;
    --index-uuid) index_uuid="$2"; shift 2 ;;
    --shard-id) shard_id="$2"; shift 2 ;;
    --node-id) node_id="$2"; shift 2 ;;
    --allocation-id) allocation_id="$2"; shift 2 ;;
    --cluster-state-version) cluster_state_version="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "${recovery_id}" && -n "${index_name}" && -n "${index_uuid}" && -n "${shard_id}" && -n "${node_id}" && -n "${allocation_id}" && -n "${cluster_state_version}" ]] || {
  echo "missing required args" >&2
  exit 2
}

mkdir -p "${CACHE_DIR}"

cat > "${SOURCE_FILE}.tmp" <<'JAVA'
package org.opensearch.indices.recovery;

import java.util.HashMap;
import java.util.Map;
import org.opensearch.cluster.routing.IndexShardRoutingTable;
import org.opensearch.cluster.routing.RecoverySource;
import org.opensearch.cluster.routing.ShardRouting;
import org.opensearch.cluster.routing.UnassignedInfo;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.core.index.Index;
import org.opensearch.core.index.shard.ShardId;
import org.opensearch.index.seqno.ReplicationTracker;

public class BuildHandoffPrimaryContextRequest {
    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        long recoveryId = Long.parseLong(args[0]);
        String indexName = args[1];
        String indexUuid = args[2];
        int shardNumber = Integer.parseInt(args[3]);
        String nodeId = args[4];
        String allocationId = args[5];
        long clusterStateVersion = Long.parseLong(args[6]);

        ShardId shardId = new ShardId(new Index(indexName, indexUuid), shardNumber);
        ShardRouting primary = ShardRouting
            .newUnassigned(
                shardId,
                true,
                RecoverySource.EmptyStoreRecoverySource.INSTANCE,
                new UnassignedInfo(UnassignedInfo.Reason.INDEX_CREATED, "steelsearch fixture")
            )
            .initialize(nodeId, allocationId, 0L)
            .moveToStarted();
        IndexShardRoutingTable routingTable = new IndexShardRoutingTable.Builder(shardId)
            .addShard(primary)
            .build();

        Map<String, ReplicationTracker.CheckpointState> checkpoints = new HashMap<>();
        checkpoints.put(allocationId, new ReplicationTracker.CheckpointState(-1L, -1L, true, true, true));
        ReplicationTracker.PrimaryContext context = new ReplicationTracker.PrimaryContext(
            clusterStateVersion,
            checkpoints,
            routingTable
        );
        RecoveryHandoffPrimaryContextRequest request = new RecoveryHandoffPrimaryContextRequest(
            recoveryId,
            shardId,
            context
        );
        BytesStreamOutput out = new BytesStreamOutput();
        request.writeTo(out);
        BytesReference bytesRef = out.bytes();
        var ref = bytesRef.toBytesRef();
        System.out.println(hex(ref.bytes, ref.offset, ref.length));
    }
}
JAVA

if [[ ! -f "${SOURCE_FILE}" ]] || ! cmp -s "${SOURCE_FILE}.tmp" "${SOURCE_FILE}"; then
  mv "${SOURCE_FILE}.tmp" "${SOURCE_FILE}"
  rm -f "${CLASS_FILE}"
else
  rm -f "${SOURCE_FILE}.tmp"
fi

if [[ ! -f "${CLASS_FILE}" || "${SOURCE_FILE}" -nt "${CLASS_FILE}" ]]; then
  javac -proc:none -cp "${LIB_CP}" -d "${TMPDIR:-/tmp}/steelsearch-java-response-cache" "${SOURCE_FILE}"
fi

java -cp "${LIB_CP}:${TMPDIR:-/tmp}/steelsearch-java-response-cache" org.opensearch.indices.recovery.BuildHandoffPrimaryContextRequest \
  "${recovery_id}" \
  "${index_name}" \
  "${index_uuid}" \
  "${shard_id}" \
  "${node_id}" \
  "${allocation_id}" \
  "${cluster_state_version}"
