#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_io_util_configure_disassembly_points_to_fcntl.py <libnio-configureBlocking-disasm.txt> <stdout.log>"
        )
        return 2

    disasm_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_symbol = "<Java_sun_nio_ch_IOUtil_configureBlocking>:" in disasm_text
    has_fcntl_getfl = "mov\tw1, #0x3" in disasm_text and "bl\t6640 <fcntl@plt>" in disasm_text
    has_nonblock_clear = "and\tw1, w0, #0xfffff7ff" in disasm_text
    has_nonblock_set = "orr\tw2, w0, #0x800" in disasm_text
    has_fcntl_setfl = "mov\tw1, #0x4" in disasm_text
    has_throw_last_error = "JNU_ThrowIOExceptionWithLastError@plt" in disasm_text

    failed_nonblocking = stdout_text.count("Failed to enter non-blocking mode.")
    failed_close_partial = stdout_text.count("Failed to close a partially initialized socket.")
    channel_exception = stdout_text.count("ChannelException")

    print(f"has_symbol={has_symbol}")
    print(f"has_fcntl_getfl={has_fcntl_getfl}")
    print(f"has_nonblock_clear={has_nonblock_clear}")
    print(f"has_nonblock_set={has_nonblock_set}")
    print(f"has_fcntl_setfl={has_fcntl_setfl}")
    print(f"has_throw_last_error={has_throw_last_error}")
    print(f"failed_nonblocking={failed_nonblocking}")
    print(f"failed_close_partial={failed_close_partial}")
    print(f"channel_exception={channel_exception}")

    if (
        has_symbol
        and has_fcntl_getfl
        and has_nonblock_clear
        and has_nonblock_set
        and has_fcntl_setfl
        and has_throw_last_error
        and failed_nonblocking == 0
        and failed_close_partial == 0
        and channel_exception == 0
    ):
        print(
            "checker_result=IOUtil_configureBlocking_native_path_reaches_fcntl_getfl_setfl_and_current_stop_is_at_syscall_level_nonblocking_flag_transition"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
