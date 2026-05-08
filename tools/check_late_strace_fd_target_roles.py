#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


LINE_RE = re.compile(r"^(?P<tid>\d+)\s+\S+\s+(?P<body>.+)$")
EPOLL_RE = re.compile(r"epoll_pwait\((\d+)(?:<[^>]*>)?,")
FD_CALL_RE = re.compile(r"(?P<call>read|close)\((?P<fd>\d+)<(?P<target>[^>]*)>")


def classify_target(target: str) -> str:
    if "socket:[" in target or "TCP:[" in target or "UDP:[" in target:
        return "socket"
    if "/proc/" in target:
        return "proc"
    if "anon_inode:[eventfd]" in target:
        return "eventfd"
    if "anon_inode:[eventpoll]" in target:
        return "eventpoll"
    if target.strip() == "":
        return "unknown"
    return "other"


def top_items(counter, limit=8):
    return [{"key": k, "count": v} for k, v in counter.most_common(limit)]


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: check_late_strace_fd_target_roles.py <late-strace.log>"}, indent=2))
        return 2

    path = Path(sys.argv[1])
    epoll_tids = set()
    fd_role_counts_by_tid = defaultdict(Counter)
    fd_target_counts_by_tid = defaultdict(Counter)
    fd_role_counts_global = defaultdict(Counter)

    for raw_line in path.open():
        line = raw_line.rstrip("\n")
        m = LINE_RE.match(line)
        if not m:
            continue
        tid = int(m.group("tid"))
        body = m.group("body")
        if EPOLL_RE.search(body):
            epoll_tids.add(tid)
        fd_call = FD_CALL_RE.search(body)
        if not fd_call:
            continue
        fd = int(fd_call.group("fd"))
        if fd not in (191, 193, 194):
            continue
        target = fd_call.group("target")
        role = classify_target(target)
        fd_role_counts_by_tid[tid][f"fd={fd}:{role}"] += 1
        fd_target_counts_by_tid[tid][f"fd={fd}:{target}"] += 1
        fd_role_counts_global[fd][role] += 1

    selector_details = []
    read_only_details = []
    for tid in sorted(fd_role_counts_by_tid):
        row = {
            "tid": tid,
            "is_selector_thread": tid in epoll_tids,
            "role_counts": top_items(fd_role_counts_by_tid[tid], 12),
            "sample_targets": top_items(fd_target_counts_by_tid[tid], 6),
        }
        if tid in epoll_tids:
            selector_details.append(row)
        else:
            read_only_details.append(row)

    global_fd_roles = {
        str(fd): top_items(counter, 8) for fd, counter in sorted(fd_role_counts_global.items())
    }

    mixed_role_fds = sorted(
        fd for fd, counter in fd_role_counts_global.items() if len([r for r, c in counter.items() if c > 0]) > 1
    )

    result = {
        "selector_tids_with_fd191_193_194_activity": selector_details,
        "read_only_tids_with_fd191_193_194_activity": read_only_details,
        "global_fd_roles": global_fd_roles,
        "mixed_role_fds": mixed_role_fds,
    }

    if mixed_role_fds:
        result["checker_result"] = "late_strace_shows_fd_role_mixing_consistent_with_numeric_fd_reuse_or_noise"
    elif selector_details and read_only_details:
        result["checker_result"] = "late_strace_shows_clean_role_split_between_selector_and_read_only_threads"
    else:
        result["checker_result"] = "late_strace_fd_role_data_incomplete"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
