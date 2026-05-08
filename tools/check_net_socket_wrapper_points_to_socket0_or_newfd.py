#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_net_socket_wrapper_points_to_socket0_or_newfd.py <net-javap.txt> <stdout.log>")
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_socket_wrapper = "static java.io.FileDescriptor socket(java.net.ProtocolFamily, boolean) throws java.io.IOException;" in javap_text
    has_socket0_call = "invokestatic  #374                // Method socket0:(ZZZZ)I" in javap_text
    has_newfd_call = "invokestatic  #378                // Method sun/nio/ch/IOUtil.newFD:(I)Ljava/io/FileDescriptor;" in javap_text
    has_socket0_native = "private static native int socket0(boolean, boolean, boolean, boolean);" in javap_text

    before_open = stdout_text.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = stdout_text.count("steelsearch_netty4_open_stage=after_open_socket_channel")

    print(f"has_socket_wrapper={has_socket_wrapper}")
    print(f"has_socket0_call={has_socket0_call}")
    print(f"has_newfd_call={has_newfd_call}")
    print(f"has_socket0_native={has_socket0_native}")
    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")

    if (
        has_socket_wrapper
        and has_socket0_call
        and has_newfd_call
        and has_socket0_native
        and before_open > 0
        and after_open == 0
    ):
        print(
            "checker_result=Net_socket_is_a_thin_wrapper_so_current_split_moves_to_socket0_native_call_or_following_IOUtil_newFD"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
