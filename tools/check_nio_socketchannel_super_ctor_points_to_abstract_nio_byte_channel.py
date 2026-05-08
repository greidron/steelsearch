#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_nio_socketchannel_super_ctor_points_to_abstract_nio_byte_channel.py <nio-socket-channel-javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_parent_socket_ctor = (
        "public io.netty.channel.socket.nio.NioSocketChannel(io.netty.channel.Channel, java.nio.channels.SocketChannel);"
        in javap_text
    )
    has_super_call = (
        'invokespecial #23                 // Method io/netty/channel/nio/AbstractNioByteChannel."<init>":(Lio/netty/channel/Channel;Ljava/nio/channels/SelectableChannel;)V'
        in javap_text
    )
    has_config_new = "class io/netty/channel/socket/nio/NioSocketChannel$NioSocketChannelConfig" in javap_text
    has_socket_call = "Method java/nio/channels/SocketChannel.socket:()Ljava/net/Socket;" in javap_text

    before_direct = stdout_text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")
    after_direct = stdout_text.count("steelsearch_netty4_open_stage=after_direct_nio_ctor")
    after_super_parent = stdout_text.count("steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor")

    print(f"has_parent_socket_ctor={has_parent_socket_ctor}")
    print(f"has_super_call={has_super_call}")
    print(f"has_config_new={has_config_new}")
    print(f"has_socket_call={has_socket_call}")
    print(f"before_direct_nio_ctor={before_direct}")
    print(f"after_direct_nio_ctor={after_direct}")
    print(f"after_super_parent_socket_ctor={after_super_parent}")

    if (
        has_parent_socket_ctor
        and has_super_call
        and has_config_new
        and has_socket_call
        and before_direct > 0
        and after_direct == 0
        and after_super_parent == 0
    ):
        print(
            "checker_result=NioSocketChannel_parent_socket_ctor_has_not_reached_body_and_current_stop_moves_to_AbstractNioByteChannel_super_ctor"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
