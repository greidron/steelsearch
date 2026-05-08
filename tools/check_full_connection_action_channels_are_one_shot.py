#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ACTIONS = {
    "internal:discovery/request_peers": "request_peers",
    "internal:coordination/fault_detection/follower_check": "follower_check",
    "internal:cluster/coordination/publish_state": "publish_state",
}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_full_connection_action_channels_are_one_shot.py <ConnectionProfile.java> <report.json>",
            file=sys.stderr,
        )
        return 2

    connection_profile = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    source_default_profile_is_multi_channel = (
        "builder.addConnections(connectionsPerNodeBulk, TransportRequestOptions.Type.BULK);" in connection_profile
        and "builder.addConnections(connectionsPerNodePing, TransportRequestOptions.Type.PING);" in connection_profile
        and "builder.addConnections(connectionsPerNodeReg, TransportRequestOptions.Type.REG);" in connection_profile
    )

    action_counts = {v: 0 for v in ACTIONS.values()}
    one_shot_counts = {v: 0 for v in ACTIONS.values()}

    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        key = ACTIONS.get(action)
        if key is None:
            continue
        action_counts[key] += 1
        if (
            row.get("first_post_response_event") == "remote_eof"
            and row.get("follow_up_frame") is None
            and row.get("post_follow_up_frame") is None
        ):
            one_shot_counts[key] += 1

    if source_default_profile_is_multi_channel and action_counts == one_shot_counts and action_counts["request_peers"] > 0:
        result = (
            "full_connection_later_action_channels_are_all_observed_as_one_shot_request_response_then_remote_eof_"
            "instead_of_retained_multi_channel_reuse"
        )
    else:
        result = "full_connection_action_channel_retention_inconclusive"

    print(
        json.dumps(
            {
                "source_default_profile_is_multi_channel": source_default_profile_is_multi_channel,
                "action_counts": action_counts,
                "one_shot_counts": one_shot_counts,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
