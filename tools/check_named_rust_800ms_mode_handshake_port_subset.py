#!/usr/bin/env python3
import json
import pathlib
import re
import statistics
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
            "usage: check_named_rust_800ms_mode_handshake_port_subset.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = pathlib.Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    stdout_path = pathlib.Path(report["artifacts"]["opensearch_stdout"])
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")

    handshake_peer_ports = set()
    for capture in report["steelsearch_transport_capture"]:
        first_frame = capture.get("first_frame") or {}
        peer_addr = capture.get("peer_addr")
        if first_frame.get("action_hint") != "internal:transport/handshake" or not peer_addr:
            continue
        handshake_peer_ports.add(int(peer_addr.rsplit(":", 1)[1]))

    open_by_id = {}
    for connection_id, node_text, channels_text in OPEN_RE.findall(stdout_text):
        open_by_id[connection_id] = {
            "node_text": node_text,
            "local_ports": sorted({int(port) for port in LOCAL_PORT_RE.findall(channels_text)}),
        }

    strict_subset = []
    non_subset = []
    for connection_id, node_text, age_text in CLOSE_RE.findall(stdout_text):
        age = int(age_text)
        if "rust-replica-1" not in node_text or not (700 <= age <= 850):
            continue
        opened = open_by_id.get(connection_id)
        if opened is None:
            continue
        matched_ports = sorted(set(opened["local_ports"]) & handshake_peer_ports)
        row = {
            "connection_id": int(connection_id),
            "age_ms": age,
            "matched_handshake_peer_ports": matched_ports,
            "channel_local_port_count": len(opened["local_ports"]),
        }
        if matched_ports:
            strict_subset.append(row)
        else:
            non_subset.append(row)

    result = {
        "handshake_first_frame_peer_port_count": len(handshake_peer_ports),
        "named_rust_700_850_total_count": len(strict_subset) + len(non_subset),
        "named_rust_700_850_handshake_port_subset_count": len(strict_subset),
        "named_rust_700_850_non_handshake_port_count": len(non_subset),
        "handshake_port_subset_age_ms": {
            "min": min((row["age_ms"] for row in strict_subset), default=None),
            "median": statistics.median([row["age_ms"] for row in strict_subset])
            if strict_subset
            else None,
            "max": max((row["age_ms"] for row in strict_subset), default=None),
        },
        "sample_handshake_port_subset": strict_subset[:5],
        "sample_non_handshake_port_mode": non_subset[:5],
        "result": "named_rust_800ms_dominant_mode_can_be_split_by_same_report_handshake_peer_port_intersection"
        if strict_subset and non_subset
        else "handshake_peer_port_intersection_did_not_split_named_rust_800ms_mode_as_expected",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
