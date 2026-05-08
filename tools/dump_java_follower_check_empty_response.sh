#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"

REQUEST_ID="${REQUEST_ID:-11}"
VERSION_ID="${VERSION_ID:-137287827}"

TMP_DIR="$(mktemp -d -t java-follower-empty-response.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

cat > "${TMP_DIR}/DumpFollowerCheckEmptyResponse.java" <<'JAVA'
import java.net.InetSocketAddress;
import java.util.Collections;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import org.opensearch.Version;
import org.opensearch.common.concurrent.CompletableContext;
import org.opensearch.common.settings.Settings;
import org.opensearch.common.util.BigArrays;
import org.opensearch.core.action.ActionListener;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.node.Node;
import org.opensearch.core.transport.TransportResponse;
import org.opensearch.threadpool.ThreadPool;
import org.opensearch.transport.OutboundHandler;
import org.opensearch.transport.StatsTracker;
import org.opensearch.transport.TcpChannel;
import org.opensearch.transport.nativeprotocol.NativeOutboundHandler;

public class DumpFollowerCheckEmptyResponse {
    private static class CapturingTcpChannel implements TcpChannel {
        private final ChannelStats stats = new ChannelStats();
        private final CompletableContext<Void> closeContext = new CompletableContext<>();
        private final AtomicReference<BytesReference> messageCaptor = new AtomicReference<>();
        private final InetSocketAddress localAddress = new InetSocketAddress("127.0.0.1", 9301);
        private final InetSocketAddress remoteAddress = new InetSocketAddress("127.0.0.1", 9302);

        @Override
        public boolean isServerChannel() {
            return true;
        }

        @Override
        public String getProfile() {
            return "default";
        }

        @Override
        public InetSocketAddress getLocalAddress() {
            return localAddress;
        }

        @Override
        public InetSocketAddress getRemoteAddress() {
            return remoteAddress;
        }

        @Override
        public void sendMessage(BytesReference reference, ActionListener<Void> listener) {
            messageCaptor.set(reference);
            listener.onResponse(null);
        }

        @Override
        public void addConnectListener(ActionListener<Void> listener) {
            listener.onResponse(null);
        }

        @Override
        public void close() {
            closeContext.complete(null);
        }

        @Override
        public void addCloseListener(ActionListener<Void> listener) {
            closeContext.addListener(ActionListener.toBiConsumer(listener));
        }

        @Override
        public boolean isOpen() {
            return closeContext.isDone() == false;
        }

        @Override
        public ChannelStats getChannelStats() {
            return stats;
        }

        public BytesReference getMessage() {
            return messageCaptor.get();
        }
    }

    private static String hex(BytesReference reference) {
        byte[] bytes = BytesReference.toBytes(reference);
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        long requestId = Long.parseLong(args[0]);
        int versionId = Integer.parseInt(args[1]);

        ThreadPool threadPool = new ThreadPool(Settings.builder().put(Node.NODE_NAME_SETTING.getKey(), "dump-follower-check-empty-response").build());
        try {
            StatsTracker statsTracker = new StatsTracker();
            OutboundHandler outboundHandler = new OutboundHandler(statsTracker, threadPool);
            NativeOutboundHandler nativeOutboundHandler = new NativeOutboundHandler(
                "node",
                Version.CURRENT,
                new String[0],
                statsTracker,
                threadPool,
                BigArrays.NON_RECYCLING_INSTANCE,
                outboundHandler
            );
            CapturingTcpChannel channel = new CapturingTcpChannel();
            nativeOutboundHandler.sendResponse(
                Version.fromId(versionId),
                Collections.emptySet(),
                channel,
                requestId,
                "internal:coordination/fault_detection/follower_check",
                TransportResponse.Empty.INSTANCE,
                false,
                false
            );
            System.out.println(hex(channel.getMessage()));
        } finally {
            ThreadPool.terminate(threadPool, 5, TimeUnit.SECONDS);
        }
    }
}
JAVA

javac -proc:none -cp "${LIB_CP}" "${TMP_DIR}/DumpFollowerCheckEmptyResponse.java"
java -cp "${LIB_CP}:${TMP_DIR}" DumpFollowerCheckEmptyResponse "${REQUEST_ID}" "${VERSION_ID}"
