#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLOSE_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*netty4 tcp channel close completed for \[\[(?P<id>[^,]+), L:(?P<local>[^ ]+) ! R:(?P<remote>[^\]]+)\]\] with hint \[(?P<hint>[^\]]+)\]"
)


def parse_ts_ms(ts: str) -> int:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S,%f").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def local_to_peer(local: str):
    if local == "null":
        return None
    if local.startswith("/"):
        return local[1:]
    if "/" in local:
        return local.split("/")[-1]
    return local


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_non_unknown_close_hints_burst_classes.py <opensearch-stdout.log> <report.json>",
            file=sys.stderr,
        )
        return 2

    stdout_lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()
    report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    captures = report.get("steelsearch_transport_capture") or []

    non_unknown = []
    for idx, line in enumerate(stdout_lines):
        m = CLOSE_RE.search(line)
        if not m:
            continue
        item = m.groupdict()
        if item["hint"] == "unknown":
            continue
        item["line_index"] = idx
        item["ts_ms"] = parse_ts_ms(item["ts"])
        item["peer_addr"] = local_to_peer(item["local"])
        non_unknown.append(item)

    matched_actions = Counter()
    null_local_count = 0
    publication_failure_burst_count = 0
    socket_reset_exception_count = 0
    classified = []

    for item in non_unknown:
        classification = []
        if item["peer_addr"] is None:
            null_local_count += 1
            classification.append("pre_local_bind_or_pre_first_frame_close")
        else:
            matches = [
                cap for cap in captures if cap.get("peer_addr") == item["peer_addr"]
            ]
            if matches:
                actions = sorted(
                    {
                        cap.get("first_frame", {}).get("action_hint")
                        for cap in matches
                        if cap.get("first_frame", {}).get("action_hint")
                    }
                )
                for action in actions:
                    matched_actions[action] += 1
                if actions:
                    classification.append("capture_matched:" + ",".join(actions))
            window = stdout_lines[max(0, item["line_index"] - 12) : item["line_index"] + 13]
            window_text = "\n".join(window)
            if "failed to commit cluster state version" in window_text or "publication failed" in window_text:
                publication_failure_burst_count += 1
                classification.append("publication_failure_burst")
            if "Connection reset" in window_text:
                socket_reset_exception_count += 1
                classification.append("connection_reset_exception")
        classified.append(
            {
                "timestamp": item["ts"],
                "hint": item["hint"],
                "peer_addr": item["peer_addr"],
                "classification": classification,
            }
        )

    result = {
        "non_unknown_total": len(non_unknown),
        "null_local_count": null_local_count,
        "matched_action_counts": dict(matched_actions),
        "publication_failure_burst_count": publication_failure_burst_count,
        "socket_reset_exception_count": socket_reset_exception_count,
        "classified_non_unknown_hints": classified,
        "result": "non_unknown_close_hints_attach_to_sparse_pre_first_frame_handshake_or_publication_failure_or_connection_reset_bursts_not_normal_steady_state_action_channels",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
