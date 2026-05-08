#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_socketchannelimpl_ctor_chain_points_to_two_arg_ctor.py <javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    source_has_one_arg_ctor = "sun.nio.ch.SocketChannelImpl(java.nio.channels.spi.SelectorProvider) throws java.io.IOException;" in javap_text
    source_delegates_to_two_arg_ctor = 'invokespecial #16                 // Method "<init>":(Ljava/nio/channels/spi/SelectorProvider;Ljava/net/ProtocolFamily;)V' in javap_text
    source_two_arg_ctor_has_super = 'invokespecial #22                 // Method java/nio/channels/SocketChannel."<init>":(Ljava/nio/channels/spi/SelectorProvider;)V' in javap_text
    source_two_arg_ctor_has_net_socket = "invokestatic  #80                 // Method sun/nio/ch/Net.socket:(Ljava/net/ProtocolFamily;Z)Ljava/io/FileDescriptor;" in javap_text

    after_remote = stdout_text.count("steelsearch_netty4_open_stage=after_remote_address")
    before_open = stdout_text.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = stdout_text.count("steelsearch_netty4_open_stage=after_open_socket_channel")

    print(f"source_has_one_arg_ctor={source_has_one_arg_ctor}")
    print(f"source_delegates_to_two_arg_ctor={source_delegates_to_two_arg_ctor}")
    print(f"source_two_arg_ctor_has_super={source_two_arg_ctor_has_super}")
    print(f"source_two_arg_ctor_has_net_socket={source_two_arg_ctor_has_net_socket}")
    print(f"after_remote_address={after_remote}")
    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")

    if (
        source_has_one_arg_ctor
        and source_delegates_to_two_arg_ctor
        and source_two_arg_ctor_has_super
        and source_two_arg_ctor_has_net_socket
        and after_remote > 0
        and before_open > 0
        and after_open == 0
    ):
        print(
            "checker_result=SocketChannelImpl_one_arg_ctor_delegates_to_two_arg_ctor_so_current_split_moves_inside_two_arg_ctor_between_super_and_Net_socket"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
