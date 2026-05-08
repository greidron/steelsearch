#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_java_tracer_vs_proxy_followup_gap.py "
            "<tracer-check.json> <proxy-check.json>",
            file=sys.stderr,
        )
        return 2

    tracer = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    proxy = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    publish_state_count = int(tracer.get("publish_state_count", 0))
    commit_state_count = int(tracer.get("commit_state_count", 0))
    proxy_publish_state_count = int(proxy.get("publish_state_count", 0))
    proxy_followup_failed = bool(proxy.get("followup_failed", False))

    result = {
        "tracer_publish_state_count": publish_state_count,
        "tracer_commit_state_count": commit_state_count,
        "proxy_publish_state_count": proxy_publish_state_count,
        "proxy_followup_failed": proxy_followup_failed,
    }

    if publish_state_count > 0 and commit_state_count > 0 and proxy_publish_state_count == 0 and proxy_followup_failed:
        result["result"] = "proxy_path_stalls_before_publish_state_while_direct_tracer_reaches_commit_state"
    else:
        result["result"] = "tracer_vs_proxy_gap_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
