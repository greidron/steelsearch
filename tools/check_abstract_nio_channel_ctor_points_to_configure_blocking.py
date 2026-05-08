#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_abstract_nio_channel_ctor_points_to_configure_blocking.py <abstract-nio-channel-javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_int_ctor = (
        "protected io.netty.channel.nio.AbstractNioChannel(io.netty.channel.Channel, java.nio.channels.SelectableChannel, int);"
        in javap_text
    )
    has_int_ctor_delegate = (
        'invokespecial #7                  // Method "<init>":(Lio/netty/channel/Channel;Ljava/nio/channels/SelectableChannel;Lio/netty/channel/nio/NioIoOps;)V'
        in javap_text
    )
    has_ops_ctor = (
        "protected io.netty.channel.nio.AbstractNioChannel(io.netty.channel.Channel, java.nio.channels.SelectableChannel, io.netty.channel.nio.NioIoOps);"
        in javap_text
    )
    has_abstract_channel_super = (
        'invokespecial #8                  // Method io/netty/channel/AbstractChannel."<init>":(Lio/netty/channel/Channel;)V'
        in javap_text
    )
    has_configure_blocking = "Method java/nio/channels/SelectableChannel.configureBlocking:(Z)Ljava/nio/channels/SelectableChannel;" in javap_text
    has_close_on_failure = "Method java/nio/channels/SelectableChannel.close:()V" in javap_text
    has_non_blocking_error = "String Failed to enter non-blocking mode." in javap_text

    before_direct = stdout_text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")
    after_direct = stdout_text.count("steelsearch_netty4_open_stage=after_direct_nio_ctor")
    after_super_parent = stdout_text.count("steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor")

    print(f"has_int_ctor={has_int_ctor}")
    print(f"has_int_ctor_delegate={has_int_ctor_delegate}")
    print(f"has_ops_ctor={has_ops_ctor}")
    print(f"has_abstract_channel_super={has_abstract_channel_super}")
    print(f"has_configure_blocking={has_configure_blocking}")
    print(f"has_close_on_failure={has_close_on_failure}")
    print(f"has_non_blocking_error={has_non_blocking_error}")
    print(f"before_direct_nio_ctor={before_direct}")
    print(f"after_direct_nio_ctor={after_direct}")
    print(f"after_super_parent_socket_ctor={after_super_parent}")

    if (
        has_int_ctor
        and has_int_ctor_delegate
        and has_ops_ctor
        and has_abstract_channel_super
        and has_configure_blocking
        and has_close_on_failure
        and has_non_blocking_error
        and before_direct > 0
        and after_direct == 0
        and after_super_parent == 0
    ):
        print(
            "checker_result=AbstractNioChannel_int_ctor_is_a_wrapper_and_current_stop_points_most_directly_to_configureBlocking_false_or_its_failure_path"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
