#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_selector_branch_practical_stop_and_backlog_pivot.py <libnio-nm.txt>",
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
            "selector_branch_is_at_practical_stop_point_and_next_productive_step_is_"
            "higher_level_reproduction_or_workaround_backlog"
        )
        return 0

    print("checker_result=inconclusive_selector_branch_pivot")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
