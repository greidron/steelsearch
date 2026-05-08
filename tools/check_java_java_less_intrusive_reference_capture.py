#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: check_java_java_less_intrusive_reference_capture.py <tracer_check.json> <proxy_check.json>"}))
        return 1

    tracer = load(sys.argv[1])
    proxy = load(sys.argv[2])

    tracer_publish = int(tracer.get("publish_state_count", 0))
    tracer_commit = int(tracer.get("commit_state_count", 0))
    proxy_publish = int(proxy.get("publish_state_count", 0))
    proxy_followup_failed = bool(proxy.get("followup_failed"))

    if tracer_publish > 0 and tracer_commit > 0 and proxy_publish == 0 and proxy_followup_failed:
        result = "direct_tracer_is_less_intrusive_publication_observable_reference_path"
    elif tracer_publish > 0 and tracer_commit > 0:
        result = "direct_tracer_observes_publication_but_proxy_gap_not_reproduced"
    else:
        result = "direct_tracer_not_sufficient_as_reference_path"

    print(json.dumps({
        "tracer_publish_state_count": tracer_publish,
        "tracer_commit_state_count": tracer_commit,
        "proxy_publish_state_count": proxy_publish,
        "proxy_followup_failed": proxy_followup_failed,
        "result": result,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
