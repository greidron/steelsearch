#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_socketchannel_super_chain_points_toward_net_socket.py <socketchannelimpl-javap.txt> <socketchannel-javap.txt> <abstractselectablechannel-javap.txt> <stdout.log>"
        )
        return 2

    impl = Path(sys.argv[1]).read_text(errors="replace")
    socket_channel = Path(sys.argv[2]).read_text(errors="replace")
    abstract_selectable = Path(sys.argv[3]).read_text(errors="replace")
    stdout = Path(sys.argv[4]).read_text(errors="replace")

    socket_channel_super_only = '0: aload_0' in socket_channel and '2: invokespecial #1                  // Method java/nio/channels/spi/AbstractSelectableChannel."<init>":(Ljava/nio/channels/spi/SelectorProvider;)V' in socket_channel and '5: return' in socket_channel
    abstract_selectable_has_no_io = "new           #17                 // class java/lang/Object" in abstract_selectable and "putfield      #27                 // Field provider:Ljava/nio/channels/spi/SelectorProvider;" in abstract_selectable
    impl_has_net_socket = "invokestatic  #80                 // Method sun/nio/ch/Net.socket:(Ljava/net/ProtocolFamily;Z)Ljava/io/FileDescriptor;" in impl

    before_open = stdout.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = stdout.count("steelsearch_netty4_open_stage=after_open_socket_channel")

    print(f"socket_channel_super_only={socket_channel_super_only}")
    print(f"abstract_selectable_has_no_io={abstract_selectable_has_no_io}")
    print(f"impl_has_net_socket={impl_has_net_socket}")
    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")

    if socket_channel_super_only and abstract_selectable_has_no_io and impl_has_net_socket and before_open > 0 and after_open == 0:
        print(
            "checker_result=super_constructor_chain_is_trivial_so_current_split_points_further_toward_Net_socket_or_later_two_arg_ctor_steps"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
