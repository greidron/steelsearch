#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: check_direct_full_connect_pre_request_peer_abort.py <report.json>"
        )

    report = load_json(sys.argv[1])
    capture = report.get("steelsearch_transport_capture") or []

    direct_full_connect = [
        entry for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    ]
    hold_open_started = [
        entry for entry in direct_full_connect
        if entry.get("hold_open_started_at_ms") is not None
    ]
    peer_remote_eof_before_post = [
        entry for entry in direct_full_connect
        if entry.get("first_post_response_event") == "remote_eof"
        and entry.get("post_follow_up_frame") is None
    ]

    abort_windows = []
    for entry in direct_full_connect:
        start = entry.get("response_frame_sent_at_ms")
        end = entry.get("connection_end_at_ms")
        if start is not None and end is not None:
            abort_windows.append(end - start)

    result = (
        "direct_full_connect_handshake_socket_enters_local_hold_open_but_peer_aborts_in_sub_second_window_before_any_post_request"
        if direct_full_connect
        and len(hold_open_started) == len(direct_full_connect)
        and len(peer_remote_eof_before_post) == len(direct_full_connect)
        and abort_windows
        else "direct_full_connect_pre_request_peer_abort_not_fully_established"
    )

    print(json.dumps({
        "direct_full_connect_count": len(direct_full_connect),
        "hold_open_started_count": len(hold_open_started),
        "peer_remote_eof_before_post_request_count": len(peer_remote_eof_before_post),
        "abort_window_min_ms": min(abort_windows) if abort_windows else None,
        "abort_window_max_ms": max(abort_windows) if abort_windows else None,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
