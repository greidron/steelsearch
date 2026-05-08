#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_followers_checker_split_points_to_remote_eof_not_retry_timeout.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    stdout_text = Path(report["artifacts"]["opensearch_stdout"]).read_text(errors="replace")
    followers_checker_source = Path(
        "/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/FollowersChecker.java"
    ).read_text()

    disconnected_count = stdout_text.count("FollowersChecker")
    failed_too_many_count = stdout_text.count("failed too many times")
    failed_retrying_count = stdout_text.count("failed, retrying")
    health_check_failed_count = stdout_text.count("health check failed")

    has_timeout_10000 = '"cluster.fault_detection.follower_check.timeout",' in followers_checker_source and "TimeValue.timeValueMillis(10000)" in followers_checker_source
    has_retry_count_3 = '"cluster.fault_detection.follower_check.retry_count",' in followers_checker_source and "3," in followers_checker_source
    has_disconnected_connect_transport_branch = "ConnectTransportException" in followers_checker_source and 'reason = NODE_LEFT_REASON_DISCONNECTED;' in followers_checker_source
    has_failed_too_many_branch = "failed too many times" in followers_checker_source

    result = {
        "work_dir": report.get("work_dir"),
        "followers_checker_log_counts": {
            "disconnected": disconnected_count,
            "failed_too_many_times": failed_too_many_count,
            "failed_retrying": failed_retrying_count,
            "health_check_failed": health_check_failed_count,
        },
        "source_has_timeout_10000ms": has_timeout_10000,
        "source_has_retry_count_3": has_retry_count_3,
        "source_has_disconnected_connect_transport_branch": has_disconnected_connect_transport_branch,
        "source_has_failed_too_many_branch": has_failed_too_many_branch,
        "result": (
            "followers_checker_split_points_to_remote_eof_disconnect_arrival_not_retry_or_timeout_internal_path"
            if disconnected_count > 0
            and failed_too_many_count == 0
            and failed_retrying_count == 0
            and health_check_failed_count == 0
            and has_timeout_10000
            and has_retry_count_3
            and has_disconnected_connect_transport_branch
            and has_failed_too_many_branch
            else "followers_checker_split_is_not_yet_resolved_as_remote_eof_disconnect_arrival"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "followers_checker_split_points_to_remote_eof_disconnect_arrival_not_retry_or_timeout_internal_path"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
