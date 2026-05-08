#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_impl_configure_blocking_points_to_locked_or_io_util.py <socketchannelimpl-javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_impl = "protected void implConfigureBlocking(boolean) throws java.io.IOException;" in javap_text
    has_read_lock = "Field readLock:Ljava/util/concurrent/locks/ReentrantLock;" in javap_text
    has_write_lock = "Field writeLock:Ljava/util/concurrent/locks/ReentrantLock;" in javap_text
    has_locked_call = "Method lockedConfigureBlocking:(Z)V" in javap_text
    has_locked_method = "void lockedConfigureBlocking(boolean) throws java.io.IOException;" in javap_text
    has_io_util_configure = "Method sun/nio/ch/IOUtil.configureBlocking:(Ljava/io/FileDescriptor;Z)V" in javap_text

    failed_nonblocking = stdout_text.count("Failed to enter non-blocking mode.")
    failed_close_partial = stdout_text.count("Failed to close a partially initialized socket.")

    print(f"has_impl={has_impl}")
    print(f"has_read_lock={has_read_lock}")
    print(f"has_write_lock={has_write_lock}")
    print(f"has_locked_call={has_locked_call}")
    print(f"has_locked_method={has_locked_method}")
    print(f"has_io_util_configure={has_io_util_configure}")
    print(f"failed_nonblocking={failed_nonblocking}")
    print(f"failed_close_partial={failed_close_partial}")

    if (
        has_impl
        and has_read_lock
        and has_write_lock
        and has_locked_call
        and has_locked_method
        and has_io_util_configure
        and failed_nonblocking == 0
        and failed_close_partial == 0
    ):
        print(
            "checker_result=implConfigureBlocking_is_a_lock_wrapper_so_current_stop_moves_to_lockedConfigureBlocking_or_IOUtil_configureBlocking"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
