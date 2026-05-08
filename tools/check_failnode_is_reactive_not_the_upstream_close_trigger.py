#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_failnode_is_reactive_not_the_upstream_close_trigger.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    followers_checker = Path(
        "/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/FollowersChecker.java"
    ).read_text()

    has_connection_listener = "transportService.addConnectionListener" in followers_checker
    has_on_node_disconnected_callback = "public void onNodeDisconnected(DiscoveryNode node, Transport.Connection connection)" in followers_checker
    has_handle_disconnected_calls_failnode = "handleDisconnectedNode(node);" in followers_checker and 'followerChecker.failNode("disconnected");' in followers_checker
    failnode_body = followers_checker[followers_checker.find("void failNode(String reason)"):followers_checker.find("private void scheduleNextWakeUp()")]
    failnode_has_no_transport_close = "close(" not in failnode_body and "disconnectFromNode" not in failnode_body

    result = {
        "work_dir": report.get("work_dir"),
        "source_has_connection_listener": has_connection_listener,
        "source_has_on_node_disconnected_callback": has_on_node_disconnected_callback,
        "source_disconnected_callback_calls_failnode": has_handle_disconnected_calls_failnode,
        "source_failnode_has_no_transport_close": failnode_has_no_transport_close,
        "result": (
            "followers_checker_failnode_is_reactive_to_disconnect_and_not_the_upstream_transport_close_trigger"
            if has_connection_listener
            and has_on_node_disconnected_callback
            and has_handle_disconnected_calls_failnode
            and failnode_has_no_transport_close
            else "followers_checker_failnode_is_not_yet_isolated_as_reactive_only"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "followers_checker_failnode_is_reactive_to_disconnect_and_not_the_upstream_transport_close_trigger"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
