#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_establishment_socket_fails_before_default_profile_reuse.py "
            "<handshaking_connector.java> <connection_profile.java> <report.json>"
        )

    connector = Path(sys.argv[1]).read_text()
    profile = Path(sys.argv[2]).read_text()
    report = load_json(sys.argv[3])

    source_probe_uses_single_reg_channel = (
        "ConnectionProfile.buildSingleChannelProfile(" in connector
        and "Type.REG" in connector
    )
    source_default_profile_is_multi_channel = (
        "buildDefaultConnectionProfile" in profile
        and "TransportRequestOptions.Type.BULK" in profile
        and "TransportRequestOptions.Type.PING" in profile
        and "TransportRequestOptions.Type.STATE" in profile
        and "TransportRequestOptions.Type.RECOVERY" in profile
        and "TransportRequestOptions.Type.REG" in profile
    )

    capture = report.get("steelsearch_transport_capture") or []
    direct_full_connect = [
        entry for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    ]
    establishment_socket_remote_eof = [
        entry for entry in direct_full_connect
        if entry.get("first_post_response_event") == "remote_eof"
        and entry.get("post_follow_up_frame") is None
    ]

    result = (
        "current_artifact_only_supports_that_connect_to_node_establishment_handshake_socket_fails_before_any_default_multi_channel_reuse_can_be_observed"
        if source_probe_uses_single_reg_channel
        and source_default_profile_is_multi_channel
        and direct_full_connect
        and len(establishment_socket_remote_eof) == len(direct_full_connect)
        else "establishment_socket_failure_before_default_profile_reuse_not_fully_established"
    )

    print(json.dumps({
        "source_probe_uses_single_reg_channel": source_probe_uses_single_reg_channel,
        "source_default_profile_is_multi_channel": source_default_profile_is_multi_channel,
        "direct_full_connect_count": len(direct_full_connect),
        "establishment_socket_remote_eof_count": len(establishment_socket_remote_eof),
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
