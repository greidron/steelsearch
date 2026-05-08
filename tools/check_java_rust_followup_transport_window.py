#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_rust_followup_transport_window.py <mixed-probe-report.json> <max-window-ms>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    max_window_ms = int(sys.argv[2])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []

    windows = []
    for entry in capture:
        if (entry.get("first_frame") or {}).get("action_hint") != "internal:transport/handshake":
            continue
        response_at = entry.get("response_frame_sent_at_ms")
        end_at = entry.get("connection_end_at_ms")
        if response_at is None or end_at is None:
            continue
        windows.append(end_at - response_at)

    min_window_ms = min(windows) if windows else None
    max_observed_window_ms = max(windows) if windows else None

    if windows and max_observed_window_ms <= max_window_ms:
        result = "followup_transport_channel_closes_quickly_after_identity_response"
    else:
        result = "followup_transport_window_inconclusive"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "window_count": len(windows),
                "min_window_ms": min_window_ms,
                "max_window_ms": max_observed_window_ms,
                "threshold_ms": max_window_ms,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
