#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_selector_native_poll_is_practical_stop_point.py <libnio-nm.txt>",
            file=sys.stderr,
        )
        return 2

    nm_text = Path(sys.argv[1]).read_text(errors="replace")
    perf_text = Path("/tmp/perf-trace-smoke.stderr").read_text(errors="replace") if Path("/tmp/perf-trace-smoke.stderr").exists() else ""

    has_net_poll = "Java_sun_nio_ch_Net_poll" in nm_text
    has_poll_selector_impl_poll = "Java_sun_nio_ch_PollSelectorImpl_poll" in nm_text
    has_epoll_wait = "epoll_wait" in nm_text
    has_poll = " poll@" in nm_text or "\npoll@" in nm_text
    perf_missing_raw_syscalls = "events/raw_syscalls/sys_(enter|exit) not found" in perf_text

    print(f"has_net_poll={has_net_poll}")
    print(f"has_poll_selector_impl_poll={has_poll_selector_impl_poll}")
    print(f"has_epoll_wait={has_epoll_wait}")
    print(f"has_poll={has_poll}")
    print(f"perf_missing_raw_syscalls={perf_missing_raw_syscalls}")

    if has_net_poll and has_poll_selector_impl_poll and has_epoll_wait and has_poll and perf_missing_raw_syscalls:
        print(
            "checker_result="
            "selector_boundary_reaches_native_poll_epoll_symbols_and_current_session_"
            "lacks_dynamic_visibility_so_this_branch_is_a_practical_stop_point"
        )
        return 0

    print("checker_result=inconclusive_selector_native_stop_point")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
