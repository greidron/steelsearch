#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


LINE_RE = re.compile(r"^(?P<tid>\d+)\s+\S+\s+(?P<body>.+)$")
EPOLL_RE = re.compile(r"epoll_pwait\((\d+)(?:<[^>]*>)?,")
TUPLE_RE = re.compile(
    r"fd=(?P<fd>\d+)<TCPv6:\[\[::ffff:127\.0\.0\.1\]:(?P<local>\d+)->\[::ffff:127\.0\.0\.1\]:(?P<remote>\d+)\]>"
)
TUPLE_RE_FALLBACK = re.compile(
    r"(?:read|close|ppoll)\((?P<fd>\d+)<TCPv6:\[\[::ffff:127\.0\.0\.1\]:(?P<local>\d+)->\[::ffff:127\.0\.0\.1\]:(?P<remote>\d+)\]>"
)


def main() -> int:
    if len(sys.argv) != 4:
        print(
            json.dumps(
                {
                    "error": "usage: check_late_strace_tcpv6_vs_capture.py <late-strace.log> <transport-seed-capture.json> <steelsearch-launch-env.json>"
                },
                indent=2,
            )
        )
        return 2

    strace_path = Path(sys.argv[1])
    capture_path = Path(sys.argv[2])
    env_path = Path(sys.argv[3])

    capture = json.loads(capture_path.read_text())
    launch_env = json.loads(env_path.read_text())
    steelsearch_transport_port = int(launch_env["STEELSEARCH_TRANSPORT_PORT"])

    capture_peer_ports = set()
    for row in capture:
        peer = row.get("peer_addr")
        if peer and ":" in peer:
            capture_peer_ports.add(int(peer.rsplit(":", 1)[1]))

    epoll_tids = set()
    tuple_rows = []
    tuple_tids = defaultdict(Counter)
    local_ports = set()
    remote_ports = set()

    for raw_line in strace_path.open():
        line = raw_line.rstrip("\n")
        m = LINE_RE.match(line)
        if not m:
            continue
        tid = int(m.group("tid"))
        body = m.group("body")
        if EPOLL_RE.search(body):
            epoll_tids.add(tid)

        tuple_match = TUPLE_RE.search(body) or TUPLE_RE_FALLBACK.search(body)
        if not tuple_match:
            continue
        fd = int(tuple_match.group("fd"))
        local = int(tuple_match.group("local"))
        remote = int(tuple_match.group("remote"))
        local_ports.add(local)
        remote_ports.add(remote)
        tuple_tids[tid][local] += 1
        tuple_rows.append(
            {
                "tid": tid,
                "fd": fd,
                "local_port": local,
                "remote_port": remote,
                "is_selector_thread": tid in epoll_tids,
            }
        )

    overlap_local_ports = sorted(local_ports & capture_peer_ports)
    selector_tuple_tids = sorted({row["tid"] for row in tuple_rows if row["is_selector_thread"]})
    non_selector_tuple_tids = sorted({row["tid"] for row in tuple_rows if not row["is_selector_thread"]})

    result = {
        "steelsearch_transport_port": steelsearch_transport_port,
        "strace_local_ports": sorted(local_ports),
        "strace_remote_ports": sorted(remote_ports),
        "capture_peer_ports_overlap": overlap_local_ports,
        "selector_tuple_tids": selector_tuple_tids,
        "non_selector_tuple_tids": non_selector_tuple_tids,
        "tuple_tid_details": [
            {
                "tid": tid,
                "is_selector_thread": tid in epoll_tids,
                "local_ports": [{"port": port, "count": count} for port, count in counter.most_common()],
            }
            for tid, counter in sorted(tuple_tids.items())
        ],
    }

    if (
        overlap_local_ports
        and remote_ports == {steelsearch_transport_port}
        and not selector_tuple_tids
        and non_selector_tuple_tids
    ):
        result[
            "checker_result"
        ] = "late_strace_tcpv6_fd191_path_matches_capture_socket_family_and_is_non_selector_read_only_path"
    else:
        result["checker_result"] = "late_strace_tcpv6_fd191_path_mapping_incomplete"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
