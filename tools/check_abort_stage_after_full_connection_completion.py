#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_abort_stage_after_full_connection_completion.py <stdout.log> <report.json>"
        )

    stdout = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    report = load_json(sys.argv[2])

    completed_full_connection_count = stdout.count("completed full connection with [")

    capture = report.get("steelsearch_transport_capture") or []
    direct_full_connect = [
        entry for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    ]
    pre_reuse_remote_eof = [
        entry for entry in direct_full_connect
        if entry.get("first_post_response_event") == "remote_eof"
        and entry.get("post_follow_up_frame") is None
    ]

    result = (
        "abort_stage_is_after_connect_to_node_completion_but_before_any_same_socket_post_handshake_reuse"
        if completed_full_connection_count > 0
        and len(direct_full_connect) > 0
        and len(pre_reuse_remote_eof) == len(direct_full_connect)
        else "abort_stage_after_full_connection_completion_not_fully_established"
    )

    print(json.dumps({
        "completed_full_connection_count": completed_full_connection_count,
        "direct_full_connect_count": len(direct_full_connect),
        "pre_reuse_remote_eof_count": len(pre_reuse_remote_eof),
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
