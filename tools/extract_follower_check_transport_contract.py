#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/ubuntu/OpenSearch")
    followers = root / "server/src/main/java/org/opensearch/cluster/coordination/FollowersChecker.java"
    empty_handler = root / "server/src/main/java/org/opensearch/transport/EmptyTransportResponseHandler.java"

    followers_text = followers.read_text(encoding="utf-8")
    empty_text = empty_handler.read_text(encoding="utf-8")

    action_match = re.search(r'FOLLOWER_CHECK_ACTION_NAME = "([^"]+)"', followers_text)
    timeout_match = re.search(r"withTimeout\(([^)]+)\)\.withType\(Type\.([A-Z_]+)\)", followers_text)
    read_empty = "return Empty.INSTANCE;" in followers_text
    resets_failure = "failureCountSinceLastSuccess = 0;" in followers_text
    disconnect_classification = (
        "exp instanceof ConnectTransportException || exp.getCause() instanceof ConnectTransportException"
        in followers_text
    )
    empty_same = "INSTANCE_SAME" in empty_text and "ThreadPool.Names.SAME" in empty_text

    output = {
        "followers_checker_path": str(followers),
        "empty_handler_path": str(empty_handler),
        "action_name": action_match.group(1) if action_match else None,
        "timeout_symbol": timeout_match.group(1) if timeout_match else None,
        "request_type": timeout_match.group(2) if timeout_match else None,
        "response_read_returns_empty_instance": read_empty,
        "handle_response_resets_failure_count": resets_failure,
        "connect_transport_exception_maps_to_disconnected": disconnect_classification,
        "empty_handler_instance_same_executor": empty_same,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
