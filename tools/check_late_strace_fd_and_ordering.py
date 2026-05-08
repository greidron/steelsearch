#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


LINE_RE = re.compile(r"^(?P<tid>\d+)\s+\S+\s+(?P<body>.+)$")
EPOLL_RE = re.compile(r"epoll_pwait\((\d+),")
READ_RE = re.compile(r"read\((\d+),")
CLOSE_RE = re.compile(r"close\((\d+)")


def top_counter(counter, limit=10):
    return [{"key": str(k), "count": v} for k, v in counter.most_common(limit)]


def main() -> int:
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "error": "usage: check_late_strace_fd_and_ordering.py <late-strace.log>",
                },
                indent=2,
            )
        )
        return 2

    path = Path(sys.argv[1])
    epoll_counts_by_tid = Counter()
    epfd_by_tid = Counter()
    read_counts_by_tid = Counter()
    close_counts_by_tid = Counter()
    read_fd_counts = Counter()
    close_fd_counts = Counter()
    read_fds_by_tid = defaultdict(Counter)
    close_fds_by_tid = defaultdict(Counter)

    for raw_line in path.open():
        line = raw_line.rstrip("\n")
        m = LINE_RE.match(line)
        if not m:
            continue
        tid = int(m.group("tid"))
        body = m.group("body")

        epoll_match = EPOLL_RE.search(body)
        if epoll_match:
            epfd = int(epoll_match.group(1))
            epoll_counts_by_tid[tid] += 1
            epfd_by_tid[(tid, epfd)] += 1

        read_match = READ_RE.search(body)
        if read_match:
            fd = int(read_match.group(1))
            read_counts_by_tid[tid] += 1
            read_fd_counts[fd] += 1
            read_fds_by_tid[tid][fd] += 1

        close_match = CLOSE_RE.search(body)
        if close_match:
            fd = int(close_match.group(1))
            close_counts_by_tid[tid] += 1
            close_fd_counts[fd] += 1
            close_fds_by_tid[tid][fd] += 1

    epoll_tids = set(epoll_counts_by_tid)
    read_tids = set(read_counts_by_tid)
    overlap_tids = sorted(epoll_tids & read_tids)
    read_only_tids = sorted(read_tids - epoll_tids)

    overlap_details = []
    for tid in overlap_tids:
        overlap_details.append(
            {
                "tid": tid,
                "epoll_count": epoll_counts_by_tid[tid],
                "top_read_fds": top_counter(read_fds_by_tid[tid], 5),
                "top_close_fds": top_counter(close_fds_by_tid[tid], 5),
            }
        )

    read_only_details = []
    for tid, count in read_counts_by_tid.most_common():
        if tid not in read_only_tids:
            continue
        read_only_details.append(
            {
                "tid": tid,
                "read_count": count,
                "top_read_fds": top_counter(read_fds_by_tid[tid], 5),
                "top_close_fds": top_counter(close_fds_by_tid[tid], 5),
            }
        )
        if len(read_only_details) >= 8:
            break

    selector_epfds = []
    for (tid, epfd), count in epfd_by_tid.most_common():
        selector_epfds.append({"tid": tid, "epfd": epfd, "count": count})
        if len(selector_epfds) >= 8:
            break

    result = {
        "epoll_tids": sorted(epoll_tids),
        "read_only_tids": read_only_tids,
        "overlap_tids": overlap_tids,
        "top_epoll_threads": [
            {"tid": tid, "count": count} for tid, count in epoll_counts_by_tid.most_common(8)
        ],
        "selector_epfds": selector_epfds,
        "top_read_fds": top_counter(read_fd_counts, 8),
        "top_close_fds": top_counter(close_fd_counts, 8),
        "overlap_details": overlap_details,
        "read_only_details": read_only_details,
    }

    if overlap_tids and read_only_tids:
        result[
            "checker_result"
        ] = "late_strace_shows_selector_like_epoll_threads_and_separate_read_only_fd_threads"
    elif overlap_tids:
        result["checker_result"] = "late_strace_shows_only_overlap_threads_for_read_and_epoll"
    else:
        result["checker_result"] = "late_strace_did_not_capture_epoll_read_overlap"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
