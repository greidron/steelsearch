#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_io_util_configure_native.py <ioutil-javap.txt> <stdout.log>")
        return 2

    io_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_native_method = "public static native void configureBlocking(java.io.FileDescriptor, boolean) throws java.io.IOException;" in io_text
    has_fdval = "public static native int fdVal(java.io.FileDescriptor);" in io_text

    failed_nonblocking = stdout_text.count("Failed to enter non-blocking mode.")
    failed_close_partial = stdout_text.count("Failed to close a partially initialized socket.")
    channel_exception = stdout_text.count("ChannelException")

    print(f"has_native_method={has_native_method}")
    print(f"has_fdval={has_fdval}")
    print(f"failed_nonblocking={failed_nonblocking}")
    print(f"failed_close_partial={failed_close_partial}")
    print(f"channel_exception={channel_exception}")

    if has_native_method and has_fdval and failed_nonblocking == 0 and failed_close_partial == 0 and channel_exception == 0:
        print("checker_result=IOUtil_configureBlocking_itself_is_the_native_transition_boundary")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
