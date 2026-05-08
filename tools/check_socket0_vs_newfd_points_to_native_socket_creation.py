#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_socket0_vs_newfd_points_to_native_socket_creation.py <net-javap.txt> <ioutil-javap.txt> <stdout.log>"
        )
        return 2

    net_text = Path(sys.argv[1]).read_text(errors="replace")
    ioutil_text = Path(sys.argv[2]).read_text(errors="replace")
    stdout_text = Path(sys.argv[3]).read_text(errors="replace")

    has_net_wrapper = (
        "static java.io.FileDescriptor socket(java.net.ProtocolFamily, boolean) throws java.io.IOException;"
        in net_text
    )
    has_socket0_call = "Method socket0:(ZZZZ)I" in net_text
    has_newfd_call = "Method sun/nio/ch/IOUtil.newFD:(I)Ljava/io/FileDescriptor;" in net_text

    has_newfd_method = "static java.io.FileDescriptor newFD(int);" in ioutil_text
    has_fd_new = "class java/io/FileDescriptor" in ioutil_text
    has_fd_ctor = 'Method java/io/FileDescriptor."<init>":()V' in ioutil_text
    has_setfd = "Method setfdVal:(Ljava/io/FileDescriptor;I)V" in ioutil_text
    has_newfd_return = "13: aload_1" in ioutil_text and "14: areturn" in ioutil_text

    before_open = stdout_text.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = stdout_text.count("steelsearch_netty4_open_stage=after_open_socket_channel")

    print(f"has_net_wrapper={has_net_wrapper}")
    print(f"has_socket0_call={has_socket0_call}")
    print(f"has_newfd_call={has_newfd_call}")
    print(f"has_newfd_method={has_newfd_method}")
    print(f"has_fd_new={has_fd_new}")
    print(f"has_fd_ctor={has_fd_ctor}")
    print(f"has_setfd={has_setfd}")
    print(f"has_newfd_return={has_newfd_return}")
    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")

    if (
        has_net_wrapper
        and has_socket0_call
        and has_newfd_call
        and has_newfd_method
        and has_fd_new
        and has_fd_ctor
        and has_setfd
        and has_newfd_return
        and before_open > 0
        and after_open == 0
    ):
        print(
            "checker_result=IOUtil_newFD_is_a_trivial_fd_wrapper_so_current_stop_points_most_directly_to_socket0_native_socket_creation"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
