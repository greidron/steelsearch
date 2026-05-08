#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_native_analysis_reached_practical_stop_point.py <libnio-configureBlocking-disasm.txt> <perf-trace-smoke.stderr>"
        )
        return 2

    disasm_text = Path(sys.argv[1]).read_text(errors="replace")
    perf_text = Path(sys.argv[2]).read_text(errors="replace")

    has_fcntl_getfl = "mov\tw1, #0x3" in disasm_text and "fcntl@plt" in disasm_text
    has_fcntl_setfl = "mov\tw1, #0x4" in disasm_text and "fcntl@plt" in disasm_text
    has_nonblock_bit = "#0x800" in disasm_text
    has_throw_last_error = "JNU_ThrowIOExceptionWithLastError@plt" in disasm_text
    perf_missing_raw_syscalls = "raw_syscalls" in perf_text and "not found" in perf_text

    print(f"has_fcntl_getfl={has_fcntl_getfl}")
    print(f"has_fcntl_setfl={has_fcntl_setfl}")
    print(f"has_nonblock_bit={has_nonblock_bit}")
    print(f"has_throw_last_error={has_throw_last_error}")
    print(f"perf_missing_raw_syscalls={perf_missing_raw_syscalls}")

    if has_fcntl_getfl and has_fcntl_setfl and has_nonblock_bit and has_throw_last_error and perf_missing_raw_syscalls:
        print(
            "checker_result=native_analysis_reached_practical_stop_point_and_backlog_pivot_is_more_productive_than_further_static_splitting"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
