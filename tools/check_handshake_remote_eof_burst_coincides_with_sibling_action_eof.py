#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def cluster_rows(rows, tolerance_ms):
    clusters = []
    for row in sorted(rows, key=lambda r: r["start"]):
        if not clusters or row["start"] - clusters[-1][-1]["start"] > tolerance_ms:
            clusters.append([row])
        else:
            clusters[-1].append(row)
    return clusters


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_handshake_remote_eof_burst_coincides_with_sibling_action_eof.py <report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(Path(sys.argv[1]).read_text())

    rows = []
    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        if action not in {
            "internal:transport/handshake",
            "internal:discovery/request_peers",
            "internal:coordination/fault_detection/follower_check",
        }:
            continue
        rows.append(
            {
                "action": action,
                "start": row.get("connection_started_at_ms"),
                "end": row.get("connection_end_at_ms"),
                "event": row.get("first_post_response_event"),
            }
        )

    clusters = cluster_rows([r for r in rows if r["start"] is not None], 5)
    burst_count = 0
    for cluster in clusters:
        actions = {r["action"] for r in cluster}
        if "internal:transport/handshake" not in actions:
            continue
        if "internal:discovery/request_peers" not in actions and "internal:coordination/fault_detection/follower_check" not in actions:
            continue
        if not all(r["event"] == "remote_eof" for r in cluster):
            continue
        ends = [r["end"] for r in cluster if r["end"] is not None]
        if ends and max(ends) - min(ends) <= 25:
            burst_count += 1

    if burst_count > 0:
        result = (
            "direct_full_connect_handshake_remote_eof_repeatedly_coincides_with_same_burst_sibling_action_channel_remote_eof_"
            "which_supports_whole_connection_teardown_fanout"
        )
    else:
        result = "handshake_remote_eof_burst_correlation_inconclusive"

    print(
        json.dumps(
            {
                "clustered_burst_count": burst_count,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
