#!/usr/bin/env bash
set -euo pipefail
ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
DIST="${ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_DIR="${DIST}/lib"
TMP_DIR="$(mktemp -d -t java-tcp-handshake-dump.XXXXXX)"
cat >"${TMP_DIR}/JavaTcpHandshakeFrameDump.java" <<'JAVA'
package org.opensearch.transport.nativeprotocol;

import java.lang.reflect.Constructor;
import org.opensearch.Version;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.common.settings.Settings;
import org.opensearch.common.util.concurrent.ThreadContext;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.core.common.io.stream.Writeable;

public class JavaTcpHandshakeFrameDump {
    public static void main(String[] args) throws Exception {
        Version version = Version.CURRENT.minimumCompatibilityVersion();
        Class<?> handshakeClass = Class.forName("org.opensearch.transport.TransportHandshaker$HandshakeRequest");
        Constructor<?> ctor = handshakeClass.getDeclaredConstructor(Version.class);
        ctor.setAccessible(true);
        Writeable handshake = (Writeable) ctor.newInstance(version);
        ThreadContext threadContext = new ThreadContext(Settings.EMPTY);
        NativeOutboundMessage.Request request = new NativeOutboundMessage.Request(
            threadContext,
            new String[0],
            handshake,
            version,
            "internal:tcp/handshake",
            1L,
            true,
            false
        );
        BytesStreamOutput out = new BytesStreamOutput();
        BytesReference bytes = request.serialize(out);
        byte[] raw = BytesReference.toBytes(bytes);
        StringBuilder sb = new StringBuilder();
        for (byte b : raw) {
            sb.append(String.format("%02x", b));
        }
        System.out.println(sb);
    }
}
JAVA
javac -cp "${LIB_DIR}/*" -d "${TMP_DIR}" "${TMP_DIR}/JavaTcpHandshakeFrameDump.java"
java -cp "${TMP_DIR}:${LIB_DIR}/*" org.opensearch.transport.nativeprotocol.JavaTcpHandshakeFrameDump
