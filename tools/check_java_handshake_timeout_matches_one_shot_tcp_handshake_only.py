#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_handshake_timeout_matches_one_shot_tcp_handshake_only.py "
            "<transport-seed-capture.json> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    capture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

    tcp_handshake_only = 0
    tcp_handshake_with_response = 0
    tcp_handshake_without_follow_up = 0
    pre_first_frame_remote_eof = 0
    for item in capture:
        first = item.get("first_frame") or {}
        if first.get("action_hint") == "internal:tcp/handshake":
            tcp_handshake_only += 1
            if item.get("response_frame") is not None:
                tcp_handshake_with_response += 1
            if item.get("follow_up_frame") is None:
                tcp_handshake_without_follow_up += 1
        if item.get("first_post_response_event") == "remote_eof_before_first_frame":
            pre_first_frame_remote_eof += 1

    open_response = stdout.count("steelsearch_open_connection_stage=response")
    open_failure = stdout.count("steelsearch_open_connection_stage=failure")
    handshake_timeout = stdout.count("handshake_timeout[1s]")
    channels_connected_on_response = stdout.count(
        "steelsearch_tcp_open_stage=channels_connected_listener_onResponse"
    )

    print(f"tcp_handshake_only={tcp_handshake_only}")
    print(f"tcp_handshake_with_response={tcp_handshake_with_response}")
    print(f"tcp_handshake_without_follow_up={tcp_handshake_without_follow_up}")
    print(f"pre_first_frame_remote_eof={pre_first_frame_remote_eof}")
    print(f"channels_connected_on_response={channels_connected_on_response}")
    print(f"open_response={open_response}")
    print(f"open_failure={open_failure}")
    print(f"handshake_timeout={handshake_timeout}")

    if (
        tcp_handshake_only > 0
        and tcp_handshake_with_response == tcp_handshake_only
        and tcp_handshake_without_follow_up == tcp_handshake_only
        and channels_connected_on_response > 0
        and open_response == 0
        and open_failure > 0
        and handshake_timeout > 0
    ):
        print(
            "checker_result=java_handshake_timeout_matches_tcp_handshake_response_then_one_shot_remote_eof_without_followup"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
