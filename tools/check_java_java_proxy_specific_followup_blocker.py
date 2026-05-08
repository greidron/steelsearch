#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_java_proxy_specific_followup_blocker.py "
            "<direct-baseline.json> <proxy-capture-check.json>",
            file=sys.stderr,
        )
        return 2

    direct = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    proxy = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    observed_node_count = int(direct.get("observed_node_count", 0))
    proxy_result = proxy.get("result")
    publish_state_count = int(proxy.get("publish_state_count", 0))
    followup_failed = bool(proxy.get("followup_failed", False))

    result = {
        "direct_observed_node_count": observed_node_count,
        "proxy_publish_state_count": publish_state_count,
        "proxy_followup_failed": followup_failed,
        "proxy_result": proxy_result,
    }

    if observed_node_count >= 2 and proxy_result == "stalled_at_followup_connection":
        result["result"] = "direct_java_java_cluster_forms_but_proxy_reference_stalls_at_followup_connection"
    else:
        result["result"] = "java_java_proxy_specific_blocker_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
