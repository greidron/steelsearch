#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_abstract_nio_byte_channel_ctor_points_to_abstract_nio_channel.py <abstract-nio-byte-channel-javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_ctor = (
        "protected io.netty.channel.nio.AbstractNioByteChannel(io.netty.channel.Channel, java.nio.channels.SelectableChannel);"
        in javap_text
    )
    has_super_call = (
        'invokespecial #5                  // Method io/netty/channel/nio/AbstractNioChannel."<init>":(Lio/netty/channel/Channel;Ljava/nio/channels/SelectableChannel;I)V'
        in javap_text
    )
    has_flush_task_init = "Field flushTask:Ljava/lang/Runnable;" in javap_text
    has_return = "19: return" in javap_text

    before_direct = stdout_text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")
    after_direct = stdout_text.count("steelsearch_netty4_open_stage=after_direct_nio_ctor")
    after_super_parent = stdout_text.count("steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor")

    print(f"has_ctor={has_ctor}")
    print(f"has_super_call={has_super_call}")
    print(f"has_flush_task_init={has_flush_task_init}")
    print(f"has_return={has_return}")
    print(f"before_direct_nio_ctor={before_direct}")
    print(f"after_direct_nio_ctor={after_direct}")
    print(f"after_super_parent_socket_ctor={after_super_parent}")

    if (
        has_ctor
        and has_super_call
        and has_flush_task_init
        and has_return
        and before_direct > 0
        and after_direct == 0
        and after_super_parent == 0
    ):
        print(
            "checker_result=AbstractNioByteChannel_ctor_is_a_thin_wrapper_so_current_stop_moves_to_AbstractNioChannel_ctor_or_configureBlocking_boundary"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
