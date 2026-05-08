#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_state_hold_open_window.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
    publish_entries = [
        entry
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:cluster/coordination/publish_state")
    ]

    windows = []
    for entry in publish_entries:
        sent = entry.get("response_frame_sent_at_ms")
        end = entry.get("connection_end_at_ms")
        if isinstance(sent, int) and isinstance(end, int):
            windows.append(end - sent)

    same_tick_count = sum(1 for w in windows if w == 0)
    remote_eof_count = sum(1 for entry in publish_entries if entry.get("connection_end") == "remote_eof")
    result = {
        "report_path": str(report_path),
        "publish_state_count": len(publish_entries),
        "window_count": len(windows),
        "same_tick_count": same_tick_count,
        "remote_eof_count": remote_eof_count,
        "max_window_ms": max(windows) if windows else None,
    }

    if len(publish_entries) > 0 and remote_eof_count == len(publish_entries) and same_tick_count == len(windows):
        result["result"] = "publish_state_peer_eof_arrives_before_local_hold_open_window_matters"
    else:
        result["result"] = "publish_state_hold_open_window_probe_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
