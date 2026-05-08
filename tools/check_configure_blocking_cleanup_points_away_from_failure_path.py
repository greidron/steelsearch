#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_configure_blocking_cleanup_points_away_from_failure_path.py <abstract-selectable-channel-javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_configure = "public final java.nio.channels.SelectableChannel configureBlocking(boolean) throws java.io.IOException;" in javap_text
    has_impl_configure = "Method implConfigureBlocking:(Z)V" in javap_text
    has_nonblocking_field = "Field nonBlocking:Z" in javap_text
    has_illegal_blocking_mode = "class java/nio/channels/IllegalBlockingModeException" in javap_text
    has_keylock = "Field keyLock:Ljava/lang/Object;" in javap_text
    has_reglock = "Field regLock:Ljava/lang/Object;" in javap_text

    failed_nonblocking = stdout_text.count("Failed to enter non-blocking mode.")
    failed_close_partial = stdout_text.count("Failed to close a partially initialized socket.")
    channel_exception = stdout_text.count("ChannelException")

    print(f"has_configure={has_configure}")
    print(f"has_impl_configure={has_impl_configure}")
    print(f"has_nonblocking_field={has_nonblocking_field}")
    print(f"has_illegal_blocking_mode={has_illegal_blocking_mode}")
    print(f"has_keylock={has_keylock}")
    print(f"has_reglock={has_reglock}")
    print(f"failed_nonblocking={failed_nonblocking}")
    print(f"failed_close_partial={failed_close_partial}")
    print(f"channel_exception={channel_exception}")

    if (
        has_configure
        and has_impl_configure
        and has_nonblocking_field
        and has_illegal_blocking_mode
        and has_keylock
        and has_reglock
        and failed_nonblocking == 0
        and failed_close_partial == 0
        and channel_exception == 0
    ):
        print(
            "checker_result=configureBlocking_contract_points_away_from_Java_cleanup_logging_and_toward_implConfigureBlocking_or_native_nonblocking_transition"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
