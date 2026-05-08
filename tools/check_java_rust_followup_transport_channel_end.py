#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_followup_transport_channel_end.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []

    handshake_entries = []
    for entry in capture:
        first_frame = entry.get("first_frame") or {}
        if first_frame.get("action_hint") == "internal:transport/handshake":
            handshake_entries.append(entry)

    remote_eof_after_identity = 0
    timed_out_after_identity = 0
    with_follow_up_frame = 0
    for entry in handshake_entries:
        if entry.get("post_follow_up_frame") is not None:
            with_follow_up_frame += 1
        if entry.get("connection_end") == "remote_eof":
            remote_eof_after_identity += 1
        elif entry.get("connection_end") == "idle_timeout":
            timed_out_after_identity += 1

    if handshake_entries and remote_eof_after_identity == len(handshake_entries):
        result = "identity_response_followup_channel_always_remote_eof"
    elif handshake_entries and with_follow_up_frame > 0:
        result = "followup_transport_channel_progress_observed"
    else:
        result = "followup_transport_channel_end_inconclusive"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "transport_handshake_count": len(handshake_entries),
                "remote_eof_after_identity_count": remote_eof_after_identity,
                "idle_timeout_after_identity_count": timed_out_after_identity,
                "post_follow_up_frame_count": with_follow_up_frame,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
