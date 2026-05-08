#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_pre_net_socket_steps_are_trivial.py <socketchannelimpl-javap.txt> <stdout.log>")
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_lock_inits = "new           #27                 // class java/util/concurrent/locks/ReentrantLock" in javap_text
    has_state_lock_init = "new           #39                 // class java/lang/Object" in javap_text
    has_require_non_null = "invokestatic  #48                 // Method java/util/Objects.requireNonNull:(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;" in javap_text
    has_family_validation = "String Protocol family not supported" in javap_text and "String IPv6 not available" in javap_text
    has_net_socket = "invokestatic  #80                 // Method sun/nio/ch/Net.socket:(Ljava/net/ProtocolFamily;Z)Ljava/io/FileDescriptor;" in javap_text

    before_open = stdout_text.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = stdout_text.count("steelsearch_netty4_open_stage=after_open_socket_channel")

    print(f"has_lock_inits={has_lock_inits}")
    print(f"has_state_lock_init={has_state_lock_init}")
    print(f"has_require_non_null={has_require_non_null}")
    print(f"has_family_validation={has_family_validation}")
    print(f"has_net_socket={has_net_socket}")
    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")

    if (
        has_lock_inits
        and has_state_lock_init
        and has_require_non_null
        and has_family_validation
        and has_net_socket
        and before_open > 0
        and after_open == 0
    ):
        print(
            "checker_result=pre_Net_socket_steps_are_trivial_so_current_stop_points_most_directly_to_Net_socket_native_creation"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
