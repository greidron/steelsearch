#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"

index_name=""
index_uuid=""
shard_id=""
target_allocation_id=""
recovery_id=""
starting_seq_no=""
primary_relocation=""

source_name=""
source_id=""
source_ephemeral_id=""
source_host=""
source_host_address=""
source_transport_address=""
source_roles=""
source_version_id=""

target_name=""
target_id=""
target_ephemeral_id=""
target_host=""
target_host_address=""
target_transport_address=""
target_roles=""
target_version_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --index-name) index_name="$2"; shift 2 ;;
    --index-uuid) index_uuid="$2"; shift 2 ;;
    --shard-id) shard_id="$2"; shift 2 ;;
    --target-allocation-id) target_allocation_id="$2"; shift 2 ;;
    --recovery-id) recovery_id="$2"; shift 2 ;;
    --starting-seq-no) starting_seq_no="$2"; shift 2 ;;
    --primary-relocation) primary_relocation="$2"; shift 2 ;;
    --source-name) source_name="$2"; shift 2 ;;
    --source-id) source_id="$2"; shift 2 ;;
    --source-ephemeral-id) source_ephemeral_id="$2"; shift 2 ;;
    --source-host) source_host="$2"; shift 2 ;;
    --source-host-address) source_host_address="$2"; shift 2 ;;
    --source-transport-address) source_transport_address="$2"; shift 2 ;;
    --source-roles) source_roles="$2"; shift 2 ;;
    --source-version-id) source_version_id="$2"; shift 2 ;;
    --target-name) target_name="$2"; shift 2 ;;
    --target-id) target_id="$2"; shift 2 ;;
    --target-ephemeral-id) target_ephemeral_id="$2"; shift 2 ;;
    --target-host) target_host="$2"; shift 2 ;;
    --target-host-address) target_host_address="$2"; shift 2 ;;
    --target-transport-address) target_transport_address="$2"; shift 2 ;;
    --target-roles) target_roles="$2"; shift 2 ;;
    --target-version-id) target_version_id="$2"; shift 2 ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-start-recovery-request"
mkdir -p "${CACHE_DIR}"
SOURCE_FILE="${CACHE_DIR}/BuildStartRecoveryRequest.java"
CLASS_FILE="${CACHE_DIR}/BuildStartRecoveryRequest.class"

cat > "${SOURCE_FILE}.tmp" <<'JAVA'
import java.net.InetAddress;
import java.util.Arrays;
import java.util.Collections;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;
import java.util.stream.Collectors;

import org.opensearch.Version;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.cluster.node.DiscoveryNodeRole;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.transport.TransportAddress;
import org.opensearch.core.index.shard.ShardId;
import org.opensearch.index.seqno.SequenceNumbers;
import org.opensearch.index.store.Store;
import org.opensearch.indices.recovery.StartRecoveryRequest;

public class BuildStartRecoveryRequest {
    private static SortedSet<DiscoveryNodeRole> parseRoles(String rolesCsv) {
        Set<String> wanted = Arrays.stream(rolesCsv.split(","))
            .map(String::trim)
            .filter(s -> s.isEmpty() == false)
            .collect(Collectors.toSet());
        return DiscoveryNodeRole.BUILT_IN_ROLES.stream()
            .filter(role -> wanted.contains(role.roleName()))
            .collect(Collectors.toCollection(TreeSet::new));
    }

    private static TransportAddress parseTransportAddress(String value) throws Exception {
        String[] parts = value.split(":");
        return new TransportAddress(InetAddress.getByName(parts[0]), Integer.parseInt(parts[1]));
    }

    private static DiscoveryNode buildNode(
        String name,
        String id,
        String ephemeralId,
        String host,
        String hostAddress,
        String transportAddress,
        String rolesCsv,
        int versionId
    ) throws Exception {
        return new DiscoveryNode(
            name,
            id,
            ephemeralId,
            host,
            hostAddress,
            parseTransportAddress(transportAddress),
            Collections.emptyMap(),
            parseRoles(rolesCsv),
            Version.fromId(versionId)
        );
    }

    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        ShardId shardId = new ShardId(args[0], args[1], Integer.parseInt(args[2]));
        String targetAllocationId = args[3];
        long recoveryId = Long.parseLong(args[4]);
        long startingSeqNo = Long.parseLong(args[5]);
        boolean primaryRelocation = Boolean.parseBoolean(args[6]);

        DiscoveryNode sourceNode = buildNode(args[7], args[8], args[9], args[10], args[11], args[12], args[13], Integer.parseInt(args[14]));
        DiscoveryNode targetNode = buildNode(args[15], args[16], args[17], args[18], args[19], args[20], args[21], Integer.parseInt(args[22]));

        Store.MetadataSnapshot metadataSnapshot = Store.MetadataSnapshot.EMPTY;
        if (startingSeqNo != SequenceNumbers.UNASSIGNED_SEQ_NO && metadataSnapshot.getHistoryUUID() == null) {
            startingSeqNo = SequenceNumbers.UNASSIGNED_SEQ_NO;
        }

        StartRecoveryRequest request = new StartRecoveryRequest(
            shardId,
            targetAllocationId,
            sourceNode,
            targetNode,
            metadataSnapshot,
            primaryRelocation,
            recoveryId,
            startingSeqNo
        );
        BytesStreamOutput out = new BytesStreamOutput();
        request.writeTo(out);
        System.out.println(hex(out.bytes().toBytesRef().bytes, 0, out.bytes().toBytesRef().length));
    }
}
JAVA

if [[ ! -f "${SOURCE_FILE}" ]] || ! cmp -s "${SOURCE_FILE}.tmp" "${SOURCE_FILE}"; then
  mv "${SOURCE_FILE}.tmp" "${SOURCE_FILE}"
  rm -f "${CLASS_FILE}"
else
  rm -f "${SOURCE_FILE}.tmp"
fi

if [[ ! -f "${CLASS_FILE}" ]] || [[ "${SOURCE_FILE}" -nt "${CLASS_FILE}" ]]; then
  javac -proc:none -cp "${LIB_CP}" -d "${CACHE_DIR}" "${SOURCE_FILE}"
fi

java -cp "${LIB_CP}:${CACHE_DIR}" BuildStartRecoveryRequest \
  "${index_name}" \
  "${index_uuid}" \
  "${shard_id}" \
  "${target_allocation_id}" \
  "${recovery_id}" \
  "${starting_seq_no}" \
  "${primary_relocation}" \
  "${source_name}" \
  "${source_id}" \
  "${source_ephemeral_id}" \
  "${source_host}" \
  "${source_host_address}" \
  "${source_transport_address}" \
  "${source_roles}" \
  "${source_version_id}" \
  "${target_name}" \
  "${target_id}" \
  "${target_ephemeral_id}" \
  "${target_host}" \
  "${target_host_address}" \
  "${target_transport_address}" \
  "${target_roles}" \
  "${target_version_id}"
