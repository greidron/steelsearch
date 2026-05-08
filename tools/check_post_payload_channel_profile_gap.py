#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_post_payload_channel_profile_gap.py <ConnectionProfile.java> <report.json>"
        )

    source = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    source_has_single_channel_profile = "buildSingleChannelProfile" in source and "builder.addConnections(1, channelType);" in source
    source_has_default_multi_channel_profile = "buildDefaultConnectionProfile" in source and all(
        token in source
        for token in [
            "TransportRequestOptions.Type.BULK",
            "TransportRequestOptions.Type.PING",
            "TransportRequestOptions.Type.STATE",
            "TransportRequestOptions.Type.RECOVERY",
            "TransportRequestOptions.Type.REG",
        ]
    )

    actions = {}
    for entry in report["steelsearch_transport_capture"]:
        action = (entry.get("first_frame") or {}).get("action_hint")
        if not action:
            continue
        bucket = actions.setdefault(action, {"count": 0, "first_frame_only": 0})
        bucket["count"] += 1
        if entry.get("follow_up_frame") is None and entry.get("post_follow_up_frame") is None:
            bucket["first_frame_only"] += 1

    transport_handshake_count = actions.get("internal:transport/handshake", {}).get("count", 0)
    transport_handshake_first_frame_only = actions.get("internal:transport/handshake", {}).get("first_frame_only", 0)
    request_peers_count = actions.get("internal:discovery/request_peers", {}).get("count", 0)
    request_peers_first_frame_only = actions.get("internal:discovery/request_peers", {}).get("first_frame_only", 0)

    result = (
        "payload_corrected_but_mixed_runtime_still_looks_like_single_use_connection_profile_instead_of_default_multi_channel_profile"
        if source_has_single_channel_profile
        and source_has_default_multi_channel_profile
        and transport_handshake_count > 0
        and transport_handshake_first_frame_only == transport_handshake_count
        and request_peers_count > 0
        and request_peers_first_frame_only == request_peers_count
        else "non_payload_channel_profile_gap_not_fully_isolated"
    )

    print(
        json.dumps(
            {
                "source_has_single_channel_profile": source_has_single_channel_profile,
                "source_has_default_multi_channel_profile": source_has_default_multi_channel_profile,
                "transport_handshake_count": transport_handshake_count,
                "transport_handshake_first_frame_only": transport_handshake_first_frame_only,
                "request_peers_count": request_peers_count,
                "request_peers_first_frame_only": request_peers_first_frame_only,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
