#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_locked_configure_blocking_points_to_io_util.py <socketchannelimpl-javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_locked = "void lockedConfigureBlocking(boolean) throws java.io.IOException;" in javap_text
    has_ensure_open = "Method ensureOpen:()V" in javap_text
    has_state_lock = "Field stateLock:Ljava/lang/Object;" in javap_text
    has_forced_nonblocking = "Field forcedNonBlocking:Z" in javap_text
    has_fd_field = "Field fd:Ljava/io/FileDescriptor;" in javap_text
    has_io_util_configure = "Method sun/nio/ch/IOUtil.configureBlocking:(Ljava/io/FileDescriptor;Z)V" in javap_text
    has_closed_channel_exception = "class java/nio/channels/ClosedChannelException" in javap_text

    failed_nonblocking = stdout_text.count("Failed to enter non-blocking mode.")
    failed_close_partial = stdout_text.count("Failed to close a partially initialized socket.")

    print(f"has_locked={has_locked}")
    print(f"has_ensure_open={has_ensure_open}")
    print(f"has_state_lock={has_state_lock}")
    print(f"has_forced_nonblocking={has_forced_nonblocking}")
    print(f"has_fd_field={has_fd_field}")
    print(f"has_io_util_configure={has_io_util_configure}")
    print(f"has_closed_channel_exception={has_closed_channel_exception}")
    print(f"failed_nonblocking={failed_nonblocking}")
    print(f"failed_close_partial={failed_close_partial}")

    if (
        has_locked
        and has_ensure_open
        and has_state_lock
        and has_forced_nonblocking
        and has_fd_field
        and has_io_util_configure
        and has_closed_channel_exception
        and failed_nonblocking == 0
        and failed_close_partial == 0
    ):
        print(
            "checker_result=lockedConfigureBlocking_prelude_is_small_and_current_stop_points_most_directly_to_IOUtil_configureBlocking_or_its_native_transition"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
