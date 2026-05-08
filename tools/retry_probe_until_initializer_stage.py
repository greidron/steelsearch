#!/usr/bin/env python3
import argparse
import os
import subprocess
from pathlib import Path


MARKERS = [
    "steelsearch_netty4_open_stage=before_clone",
    "steelsearch_netty4_open_stage=after_clone",
    "steelsearch_netty4_open_stage=before_get_client_initializer",
    "steelsearch_netty4_open_stage=after_get_client_initializer",
    "steelsearch_netty4_initializer_stage=method_entry",
    "steelsearch_netty4_initializer_stage=before_new_client_initializer",
    "steelsearch_netty4_initializer_stage=client_initializer_ctor_body",
    "steelsearch_netty4_initializer_stage=after_new_client_initializer",
    "steelsearch_netty4_initializer_stage=method_return",
    "steelsearch_netty4_open_stage=after_handler_setter",
    "steelsearch_netty4_open_stage=before_remote_address",
    "steelsearch_netty4_open_stage=after_remote_address",
    "steelsearch_netty4_open_stage=before_open_socket_channel",
    "steelsearch_netty4_open_stage=after_open_socket_channel",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--stop-at",
        choices=[
            "ctor_body",
            "remote_after",
            "remote_before",
            "open_after",
            "open_before",
            "formed_membership",
        ],
        default="ctor_body",
    )
    return parser.parse_args()


def marker_counts(text: str) -> dict[str, int]:
    return {marker.split("=")[-1]: text.count(marker) for marker in MARKERS}


def main() -> int:
    args = parse_args()
    effective_timeout_seconds = args.timeout_seconds
    if args.stop_at == "formed_membership":
        effective_timeout_seconds = max(effective_timeout_seconds, 420)
    env = os.environ.copy()
    env["JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED"] = "true"
    env["JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_SPLIT_BUILD_RUN"] = "1"
    env["JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS"] = "5000"
    env["JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLASS_OVERLAY_DIR"] = (
        "/home/ubuntu/OpenSearch/server/build/classes/java/main"
    )
    env["JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLASS_OVERLAY_FILES"] = (
        "org/opensearch/discovery/PeerFinder.class:"
        "org/opensearch/discovery/PeerFinder$Peer.class:"
        "org/opensearch/transport/InboundPipeline.class:"
        "org/opensearch/transport/OutboundHandler.class:"
        "org/opensearch/transport/NativeMessageHandler.class:"
        "org/opensearch/transport/TcpTransport.class:"
        "org/opensearch/transport/TcpTransport$ChannelsConnectedListener.class:"
        "org/opensearch/transport/TransportHandshaker.class:"
        "org/opensearch/transport/nativeprotocol/NativeOutboundHandler.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector$1.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector$1$1.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector$1$1$1.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector$1$1$1$1.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector$2.class:"
        "org/opensearch/discovery/HandshakingTransportAddressConnector$3.class"
    )
    env["JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_EXTRA_JAR_OVERLAY_SPECS"] = (
        "/home/ubuntu/OpenSearch/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT/modules/transport-netty4/"
        "transport-netty4-client-3.7.0-SNAPSHOT.jar"
        "|/home/ubuntu/OpenSearch/modules/transport-netty4/build/classes/java/main"
        "|org/opensearch/transport/netty4/Netty4Transport.class:"
        "org/opensearch/transport/netty4/Netty4Transport$ClientChannelInitializer.class:"
        "org/opensearch/transport/netty4/Netty4MessageChannelHandler.class:"
        "org/opensearch/transport/netty4/Netty4TcpChannel.class:"
        "org/opensearch/transport/Netty4NioSocketChannel.class"
    )

    base = Path("/tmp")
    for attempt in range(1, args.attempts + 1):
        before = {p.name for p in base.glob("java-rust-mixed-membership.*") if p.is_dir()}
        subprocess.run(
            [
                "timeout",
                f"{effective_timeout_seconds}s",
                "bash",
                "/home/ubuntu/steelsearch/tools/probe_java_rust_mixed_membership.sh",
            ],
            cwd="/home/ubuntu/steelsearch",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        created = [p for p in base.glob("java-rust-mixed-membership.*") if p.is_dir() and p.name not in before]
        newest = max(created, key=lambda p: p.stat().st_mtime) if created else None
        print(f"attempt={attempt} workdir={newest}")
        if newest is None:
            continue
        stdout = newest / "opensearch" / "stdout.log"
        text = stdout.read_text(errors="replace") if stdout.exists() else ""
        counts = marker_counts(text)
        report_path = newest / "report.json"
        report = None
        if report_path.exists():
            try:
                import json

                report = json.loads(report_path.read_text(encoding="utf-8"))
            except Exception:
                report = None
        for key, value in counts.items():
            if value:
                print(f"  {key}={value}")
        if report is not None:
            print(f"  membership_formed={report.get('membership_formed')}")
            print(f"  failure_stage={report.get('failure_stage')}")
            print(f"  observed_node_count={report.get('observed_node_count')}")
        if args.stop_at == "ctor_body":
            if counts["client_initializer_ctor_body"] > 0:
                print("result=client_initializer_ctor_body_recovered")
                return 0
            if counts["method_return"] > 0:
                print("result=method_return_without_ctor_body")
                return 10
        elif args.stop_at == "remote_after":
            if counts["after_remote_address"] > 0:
                print("result=after_remote_address_recovered")
                return 0
        elif args.stop_at == "remote_before":
            if counts["before_remote_address"] > 0 and counts["after_remote_address"] == 0:
                print("result=before_remote_without_after")
                return 0
        elif args.stop_at == "open_after":
            if counts["after_open_socket_channel"] > 0:
                print("result=after_open_socket_channel_recovered")
                return 0
        elif args.stop_at == "open_before":
            if counts["before_open_socket_channel"] > 0 and counts["after_open_socket_channel"] == 0:
                print("result=before_open_without_after")
                return 0
        elif args.stop_at == "formed_membership":
            if report is not None and report.get("membership_formed") is True:
                print("result=formed_membership_recovered")
                return 0

    print(f"result=no_useful_sample_for_{args.stop_at}")
    return 11


if __name__ == "__main__":
    raise SystemExit(main())
