#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_primary_rust_replica_success_path_preflight.py <membership_probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    membership_formed = bool(report.get("membership_formed"))
    observed_node_count = report.get("observed_node_count")
    blocker_class = report.get("blocker_class")
    failure_stage = report.get("failure_stage")
    markers = report.get("markers") or {}

    success_ready = membership_formed and isinstance(observed_node_count, int) and observed_node_count >= 2
    result = {
        "report_path": str(report_path),
        "failure_stage": failure_stage,
        "blocker_class": blocker_class,
        "membership_formed": membership_formed,
        "observed_node_count": observed_node_count,
        "native_transport_join_participation": markers.get(
            "steelsearch_native_transport_join_participation"
        ),
        "transport_handshake_accepted": markers.get("steelsearch_transport_handshake_accepted"),
        "transport_follow_up_observed": markers.get("steelsearch_transport_follow_up_observed"),
        "success_path_ready": success_ready,
        "result": (
            "java_primary_rust_replica_success_path_preflight_ready"
            if success_ready
            else "java_primary_rust_replica_success_path_preflight_blocked_by_membership_not_formed"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if success_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
