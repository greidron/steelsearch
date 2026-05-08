#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: check_mixed_publish_state_socket_trigger.py <mixed_report.json>"}))
        return 1

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get("steelsearch_transport_capture") or []

    publish_entries = []
    for entry in capture:
        first = entry.get("first_frame") or {}
        follow = entry.get("follow_up_frame") or {}
        post = entry.get("post_follow_up_frame") or {}
        resp = entry.get("response_frame") or {}
        if first.get("action_hint") != "internal:cluster/coordination/publish_state":
            continue
        same_tick = entry.get("response_frame_sent_at_ms") == entry.get("connection_end_at_ms")
        publish_entries.append(
            {
                "first_frame_publish_state": True,
                "follow_up_absent": entry.get("follow_up_frame") is None,
                "post_follow_up_absent": entry.get("post_follow_up_frame") is None,
                "response_written": bool(resp),
                "connection_end": entry.get("connection_end"),
                "same_tick_remote_eof": same_tick and entry.get("connection_end") == "remote_eof",
            }
        )

    count = len(publish_entries)
    all_first_frame = count > 0 and all(e["first_frame_publish_state"] for e in publish_entries)
    all_no_followup = count > 0 and all(e["follow_up_absent"] and e["post_follow_up_absent"] for e in publish_entries)
    all_response = count > 0 and all(e["response_written"] for e in publish_entries)
    all_same_tick_eof = count > 0 and all(e["same_tick_remote_eof"] for e in publish_entries)

    if all_first_frame and all_no_followup and all_response and all_same_tick_eof:
        result = "publish_state_arrives_as_single_request_socket_and_peer_closes_same_tick_after_valid_response"
    else:
        result = "publish_state_socket_trigger_not_uniform"

    print(json.dumps({
        "publish_state_entry_count": count,
        "all_first_frame_publish_state": all_first_frame,
        "all_no_follow_up_frames": all_no_followup,
        "all_response_written": all_response,
        "all_same_tick_remote_eof": all_same_tick_eof,
        "result": result,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
