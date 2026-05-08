#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def count(path: Path, needle: str) -> int:
    if not path.exists():
        return 0
    return path.read_text(encoding="utf-8", errors="replace").count(needle)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_java_transport_trace_reference.py <trace-run.json>",
            file=sys.stderr,
        )
        return 2

    run = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    primary_stdout = Path(run["primary_stdout"])
    follower_stdout = Path(run["follower_stdout"])

    publish_state_count = count(primary_stdout, "internal:cluster/coordination/publish_state") + count(
        follower_stdout, "internal:cluster/coordination/publish_state"
    )
    commit_state_count = count(primary_stdout, "internal:cluster/coordination/commit_state") + count(
        follower_stdout, "internal:cluster/coordination/commit_state"
    )

    result = {
        "publish_state_count": publish_state_count,
        "commit_state_count": commit_state_count,
    }
    if publish_state_count > 0:
        result["result"] = "publish_state_observed_in_transport_trace"
    else:
        result["result"] = "transport_trace_did_not_observe_publish_state"
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
