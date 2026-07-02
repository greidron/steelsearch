#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"
CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-response-cache"
CLASS_NAME="BuildClusterStatsResponse"
JAVA_FILE="${CACHE_DIR}/${CLASS_NAME}.java"
CLASS_FILE="${CACHE_DIR}/${CLASS_NAME}.class"

cluster_name=""
cluster_uuid=""
local_name=""
local_id=""
local_ephemeral_id=""
local_host=""
local_host_address=""
local_transport_address=""
local_roles=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-name) cluster_name="$2"; shift 2 ;;
    --cluster-uuid) cluster_uuid="$2"; shift 2 ;;
    --local-name) local_name="$2"; shift 2 ;;
    --local-id) local_id="$2"; shift 2 ;;
    --local-ephemeral-id) local_ephemeral_id="$2"; shift 2 ;;
    --local-host) local_host="$2"; shift 2 ;;
    --local-host-address) local_host_address="$2"; shift 2 ;;
    --local-transport-address) local_transport_address="$2"; shift 2 ;;
    --local-roles) local_roles="$2"; shift 2 ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${CACHE_DIR}"

if [[ ! -f "${CLASS_FILE}" ]]; then
cat > "${JAVA_FILE}" <<'JAVA'
import java.net.InetAddress;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;
import java.util.stream.Collectors;

import org.opensearch.Build;
import org.opensearch.Version;
import org.opensearch.action.admin.cluster.node.info.NodeInfo;
import org.opensearch.action.admin.cluster.node.stats.NodeStats;
import org.opensearch.action.admin.cluster.stats.ClusterStatsNodeResponse;
import org.opensearch.action.admin.indices.stats.ShardStats;
import org.opensearch.action.support.nodes.BaseNodeResponse;
import org.opensearch.cluster.ClusterName;
import org.opensearch.cluster.health.ClusterHealthStatus;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.cluster.node.DiscoveryNodeRole;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.core.common.io.stream.StreamOutput;
import org.opensearch.core.common.transport.TransportAddress;
import org.opensearch.monitor.fs.FsInfo;
import org.opensearch.monitor.process.ProcessInfo;
import org.opensearch.node.NodeResourceUsageStats;
import org.opensearch.node.NodesResourceUsageStats;

public class BuildClusterStatsResponse {
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

    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
    }

    private static <T extends BaseNodeResponse> void writeNodeList(StreamOutput out, List<T> nodes) throws Exception {
        out.writeVInt(nodes.size());
        for (T node : nodes) {
            node.writeTo(out);
        }
    }

    public static void main(String[] args) throws Exception {
        String clusterName = args[0];
        String clusterUuid = args[1];
        DiscoveryNode localNode = new DiscoveryNode(
            args[2],
            args[3],
            args[4],
            args[5],
            args[6],
            parseTransportAddress(args[7]),
            Collections.emptyMap(),
            parseRoles(args[8]),
            Version.CURRENT
        );
        NodeInfo nodeInfo = NodeInfo.builder(Version.CURRENT, Build.CURRENT, localNode)
            .setProcess(new ProcessInfo(1L, false, 0L))
            .build();
        FsInfo fsInfo = new FsInfo(
            System.currentTimeMillis(),
            null,
            new FsInfo.Path[] {
                new FsInfo.Path("/", "/", 1024L * 1024 * 1024, 768L * 1024 * 1024, 768L * 1024 * 1024)
            }
        );
        NodesResourceUsageStats resourceUsageStats = new NodesResourceUsageStats(
            Map.of(
                localNode.getId(),
                new NodeResourceUsageStats(
                    localNode.getId(),
                    System.currentTimeMillis(),
                    10.0d,
                    5.0d,
                    null
                )
            )
        );
        NodeStats nodeStats = new NodeStats(
            localNode,
            System.currentTimeMillis(),
            null,
            null,
            null,
            null,
            null,
            fsInfo,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            resourceUsageStats,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null
        );
        ClusterStatsNodeResponse nodeResponse = new ClusterStatsNodeResponse(
            localNode,
            ClusterHealthStatus.GREEN,
            nodeInfo,
            nodeStats,
            new ShardStats[0],
            false
        );
        BytesStreamOutput out = new BytesStreamOutput();
        new ClusterName(clusterName).writeTo(out);
        writeNodeList(out, List.of(nodeResponse));
        out.writeList(Collections.emptyList());
        out.writeVLong(System.currentTimeMillis());
        out.writeOptionalWriteable(ClusterHealthStatus.GREEN);
        out.writeOptionalString(clusterUuid);
        out.writeOptionalWriteable(null);
        out.writeOptionalWriteable(null);
        BytesReference bytesRef = out.bytes();
        var ref = bytesRef.toBytesRef();
        System.out.println(hex(ref.bytes, ref.offset, ref.length));
    }
}
JAVA

javac -proc:none -cp "${LIB_CP}" "${JAVA_FILE}"
fi

java -cp "${LIB_CP}:${CACHE_DIR}" "${CLASS_NAME}" \
  "${cluster_name}" \
  "${cluster_uuid}" \
  "${local_name}" \
  "${local_id}" \
  "${local_ephemeral_id}" \
  "${local_host}" \
  "${local_host_address}" \
  "${local_transport_address}" \
  "${local_roles}"
