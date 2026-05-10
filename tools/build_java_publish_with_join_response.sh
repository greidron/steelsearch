#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"

term=""
version=""
last_accepted_term=""
last_accepted_version=""
local_name=""
local_id=""
local_ephemeral_id=""
local_host=""
local_host_address=""
local_transport_address=""
local_roles=""
seed_name=""
seed_id=""
seed_ephemeral_id=""
seed_host=""
seed_host_address=""
seed_transport_address=""
seed_roles=""
seed_version_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --term) term="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --last-accepted-term) last_accepted_term="$2"; shift 2 ;;
    --last-accepted-version) last_accepted_version="$2"; shift 2 ;;
    --local-name) local_name="$2"; shift 2 ;;
    --local-id) local_id="$2"; shift 2 ;;
    --local-ephemeral-id) local_ephemeral_id="$2"; shift 2 ;;
    --local-host) local_host="$2"; shift 2 ;;
    --local-host-address) local_host_address="$2"; shift 2 ;;
    --local-transport-address) local_transport_address="$2"; shift 2 ;;
    --local-roles) local_roles="$2"; shift 2 ;;
    --seed-name) seed_name="$2"; shift 2 ;;
    --seed-id) seed_id="$2"; shift 2 ;;
    --seed-ephemeral-id) seed_ephemeral_id="$2"; shift 2 ;;
    --seed-host) seed_host="$2"; shift 2 ;;
    --seed-host-address) seed_host_address="$2"; shift 2 ;;
    --seed-transport-address) seed_transport_address="$2"; shift 2 ;;
    --seed-roles) seed_roles="$2"; shift 2 ;;
    --seed-version-id) seed_version_id="$2"; shift 2 ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-publish-with-join-response"
mkdir -p "${CACHE_DIR}"
SOURCE_FILE="${CACHE_DIR}/BuildPublishWithJoinResponse.java"
CLASS_FILE="${CACHE_DIR}/BuildPublishWithJoinResponse.class"

cat > "${SOURCE_FILE}.tmp" <<'JAVA'
import java.net.InetAddress;
import java.util.Arrays;
import java.util.Collections;
import java.util.Optional;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;
import java.util.stream.Collectors;

import org.opensearch.Version;
import org.opensearch.cluster.coordination.Join;
import org.opensearch.cluster.coordination.PublishResponse;
import org.opensearch.cluster.coordination.PublishWithJoinResponse;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.cluster.node.DiscoveryNodeRole;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.common.transport.TransportAddress;

public class BuildPublishWithJoinResponse {
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

    private static String hex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        long term = Long.parseLong(args[0]);
        long version = Long.parseLong(args[1]);
        long lastAcceptedTerm = Long.parseLong(args[2]);
        long lastAcceptedVersion = Long.parseLong(args[3]);

        DiscoveryNode localNode = buildNode(args[4], args[5], args[6], args[7], args[8], args[9], args[10], Integer.parseInt(args[11]));
        DiscoveryNode seedNode = buildNode(args[12], args[13], args[14], args[15], args[16], args[17], args[18], Integer.parseInt(args[19]));

        PublishWithJoinResponse response = new PublishWithJoinResponse(
            new PublishResponse(term, version),
            Optional.of(new Join(localNode, seedNode, term, lastAcceptedTerm, lastAcceptedVersion))
        );
        BytesStreamOutput out = new BytesStreamOutput();
        response.writeTo(out);
        System.out.println(hex(out.bytes().toBytesRef().bytes, 0, out.bytes().toBytesRef().length));
    }

    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
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

java -cp "${LIB_CP}:${CACHE_DIR}" BuildPublishWithJoinResponse \
  "${term}" \
  "${version}" \
  "${last_accepted_term}" \
  "${last_accepted_version}" \
  "${local_name}" \
  "${local_id}" \
  "${local_ephemeral_id}" \
  "${local_host}" \
  "${local_host_address}" \
  "${local_transport_address}" \
  "${local_roles}" \
  "137287827" \
  "${seed_name}" \
  "${seed_id}" \
  "${seed_ephemeral_id}" \
  "${seed_host}" \
  "${seed_host_address}" \
  "${seed_transport_address}" \
  "${seed_roles}" \
  "${seed_version_id}"
