#!/usr/bin/env bash
set -euo pipefail

ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
DIST="${ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_DIR="${DIST}/lib"

MODE="plain"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "${MODE}" != "plain" && "${MODE}" != "compressed" ]]; then
  echo "--mode must be plain or compressed" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d -t java-validate-join.XXXXXX)"
cat >"${TMP_DIR}/JavaValidateJoinRequestBuild.java" <<'JAVA'
package org.opensearch.cluster.coordination;

import java.io.IOException;
import java.net.InetAddress;
import java.util.Collections;
import java.util.Set;
import org.opensearch.Version;
import org.opensearch.cluster.ClusterName;
import org.opensearch.cluster.ClusterState;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.cluster.node.DiscoveryNodeRole;
import org.opensearch.cluster.node.DiscoveryNodes;
import org.opensearch.common.settings.Settings;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.transport.TransportAddress;
import org.opensearch.transport.BytesTransportRequest;

public class JavaValidateJoinRequestBuild {
    private static String toHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b & 0xff));
        }
        return sb.toString();
    }

    private static DiscoveryNode node(String name, String id, int port) throws Exception {
        return new DiscoveryNode(
            name,
            id,
            id + "-ephemeral",
            "127.0.0.1",
            "127.0.0.1",
            new TransportAddress(InetAddress.getByName("127.0.0.1"), port),
            Collections.emptyMap(),
            Set.of(DiscoveryNodeRole.CLUSTER_MANAGER_ROLE, DiscoveryNodeRole.DATA_ROLE),
            Version.CURRENT
        );
    }

    private static ClusterState clusterState() throws Exception {
        DiscoveryNode local = node("steel-node", "steel-node-id", 9300);
        DiscoveryNodes nodes = DiscoveryNodes.builder()
            .add(local)
            .localNodeId(local.getId())
            .clusterManagerNodeId(local.getId())
            .build();
        return ClusterState.builder(new ClusterName("steelsearch-dev"))
            .version(7L)
            .stateUUID("validate-join-state")
            .nodes(nodes)
            .metadata(org.opensearch.cluster.metadata.Metadata.builder()
                .clusterUUID("steelsearch-cluster-uuid")
                .clusterUUIDCommitted(true)
                .build())
            .build();
    }

    public static void main(String[] args) throws Exception {
        String mode = args[0];
        BytesStreamOutput out = new BytesStreamOutput();
        out.setVersion(Version.CURRENT);
        if ("plain".equals(mode)) {
            new ValidateJoinRequest(clusterState()).writeTo(out);
        } else if ("compressed".equals(mode)) {
            BytesReference bytes = CompressedStreamUtils.createCompressedStream(Version.CURRENT, clusterState()::writeTo);
            new BytesTransportRequest(bytes, Version.CURRENT).writeTo(out);
        } else {
            throw new IllegalArgumentException("unknown mode " + mode);
        }
        System.out.println(toHex(BytesReference.toBytes(out.bytes())));
    }
}
JAVA

javac -cp "${LIB_DIR}/*" -d "${TMP_DIR}" "${TMP_DIR}/JavaValidateJoinRequestBuild.java"
java -cp "${TMP_DIR}:${LIB_DIR}/*" org.opensearch.cluster.coordination.JavaValidateJoinRequestBuild "${MODE}"
