#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_open_socket_channel_points_to_socketchannelimpl_ctor.py <javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    source_has_open_socket_channel = "public java.nio.channels.SocketChannel openSocketChannel() throws java.io.IOException;" in javap_text
    source_news_socket_channel_impl = "new           #23                 // class sun/nio/ch/SocketChannelImpl" in javap_text
    source_ctor_call = "invokespecial #25                 // Method sun/nio/ch/SocketChannelImpl.\"<init>\":(Ljava/nio/channels/spi/SelectorProvider;)V" in javap_text

    after_remote = stdout_text.count("steelsearch_netty4_open_stage=after_remote_address")
    before_open = stdout_text.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = stdout_text.count("steelsearch_netty4_open_stage=after_open_socket_channel")

    print(f"source_has_open_socket_channel={source_has_open_socket_channel}")
    print(f"source_news_socket_channel_impl={source_news_socket_channel_impl}")
    print(f"source_ctor_call={source_ctor_call}")
    print(f"after_remote_address={after_remote}")
    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")

    if (
        source_has_open_socket_channel
        and source_news_socket_channel_impl
        and source_ctor_call
        and after_remote > 0
        and before_open > 0
        and after_open == 0
    ):
        print(
            "checker_result=openSocketChannel_is_a_thin_wrapper_and_current_stop_moves_to_SocketChannelImpl_constructor_boundary"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
