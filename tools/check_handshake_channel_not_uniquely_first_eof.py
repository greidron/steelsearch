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
        print("usage: check_handshake_channel_not_uniquely_first_eof.py <report.json>", file=sys.stderr)
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
        if row.get("first_post_response_event") != "remote_eof":
            continue
        rows.append(
            {
                "action": action,
                "start": row.get("connection_started_at_ms"),
                "end": row.get("connection_end_at_ms"),
            }
        )

    bursts = 0
    handshake_clearly_earlier = 0
    nearly_simultaneous = 0

    for cluster in cluster_rows([r for r in rows if r["start"] is not None], 5):
        actions = {r["action"] for r in cluster}
        if "internal:transport/handshake" not in actions:
            continue
        if "internal:discovery/request_peers" not in actions and "internal:coordination/fault_detection/follower_check" not in actions:
            continue
        bursts += 1
        handshake_end = min(r["end"] for r in cluster if r["action"] == "internal:transport/handshake" and r["end"] is not None)
        sibling_ends = [r["end"] for r in cluster if r["action"] != "internal:transport/handshake" and r["end"] is not None]
        if not sibling_ends:
            continue
        min_sibling_end = min(sibling_ends)
        if handshake_end + 10 < min_sibling_end:
            handshake_clearly_earlier += 1
        if abs(handshake_end - min_sibling_end) <= 10:
            nearly_simultaneous += 1

    if bursts > 0 and handshake_clearly_earlier == 0 and nearly_simultaneous > 0:
        result = (
            "current_artifact_does_not_support_handshake_channel_as_uniquely_first_eof_cause_"
            "and_is_better_read_as_near_simultaneous_peer_side_whole_burst_close"
        )
    else:
        result = "handshake_firstness_inconclusive"

    print(
        json.dumps(
            {
                "burst_count": bursts,
                "handshake_clearly_earlier_count": handshake_clearly_earlier,
                "nearly_simultaneous_count": nearly_simultaneous,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
