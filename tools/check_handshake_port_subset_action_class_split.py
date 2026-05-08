#!/usr/bin/env python3
import collections
import json
import pathlib
import re
import sys


OPEN_RE = re.compile(
    r"opened transport connection \[(\d+)\] to \[(.*?)\] using channels \[\[(.*?)\]\]"
)
CLOSE_RE = re.compile(
    r"closed transport connection \[(\d+)\] to \[(.*?)\] with age \[(\d+)ms\]"
)
LOCAL_PORT_RE = re.compile(r"localAddress=.*?:(\d+)")


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_handshake_port_subset_action_class_split.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    port_actions = collections.defaultdict(set)
    for capture in report["steelsearch_transport_capture"]:
        peer_addr = capture.get("peer_addr")
        if not peer_addr:
            continue
        port = int(peer_addr.rsplit(":", 1)[1])
        port_actions[port].add(capture["first_frame"]["action_hint"])

    handshake_ports = {port for port, actions in port_actions.items() if "internal:transport/handshake" in actions}

    open_by_id = {
        connection_id: sorted({int(port) for port in LOCAL_PORT_RE.findall(channels_text)})
        for connection_id, _, channels_text in OPEN_RE.findall(stdout_text)
    }

    subset_rows = []
    non_subset_rows = []
    for connection_id, node_text, age_text in CLOSE_RE.findall(stdout_text):
        age = int(age_text)
        if "rust-replica-1" not in node_text or not (700 <= age <= 850):
            continue
        local_ports = open_by_id.get(connection_id, [])
        seen_actions = set()
        for port in local_ports:
            seen_actions |= port_actions.get(port, set())
        row = {
            "connection_id": int(connection_id),
            "age_ms": age,
            "seen_actions": sorted(seen_actions),
        }
        if set(local_ports) & handshake_ports:
            subset_rows.append(row)
        else:
            non_subset_rows.append(row)

    result = {
        "handshake_port_subset_count": len(subset_rows),
        "handshake_port_subset_with_transport_handshake_count": sum(
            1 for row in subset_rows if "internal:transport/handshake" in row["seen_actions"]
        ),
        "handshake_port_subset_with_request_peers_count": sum(
            1 for row in subset_rows if "internal:discovery/request_peers" in row["seen_actions"]
        ),
        "handshake_port_subset_with_pre_vote_count": sum(
            1 for row in subset_rows if "internal:cluster/request_pre_vote" in row["seen_actions"]
        ),
        "handshake_port_subset_with_follower_check_count": sum(
            1 for row in subset_rows if "internal:coordination/fault_detection/follower_check" in row["seen_actions"]
        ),
        "non_handshake_port_count": len(non_subset_rows),
        "non_handshake_port_with_transport_handshake_count": sum(
            1 for row in non_subset_rows if "internal:transport/handshake" in row["seen_actions"]
        ),
        "non_handshake_port_no_seen_action_count": sum(1 for row in non_subset_rows if not row["seen_actions"]),
        "sample_non_handshake_rows": non_subset_rows[:5],
        "result": "handshake_port_subset_and_non_subset_split_by_transport_handshake_action_class_signal"
        if subset_rows
        and all("internal:transport/handshake" in row["seen_actions"] for row in subset_rows)
        and all("internal:transport/handshake" not in row["seen_actions"] for row in non_subset_rows)
        else "action_class_split_not_yet_cleanly_established",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
