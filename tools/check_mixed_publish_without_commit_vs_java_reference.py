#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_mixed_publish_without_commit_vs_java_reference.py <mixed_probe_report.json> <java_reference_check.json>",
            file=sys.stderr,
        )
        return 2

    mixed_path = Path(sys.argv[1])
    ref_path = Path(sys.argv[2])

    mixed = json.loads(mixed_path.read_text())
    ref = json.loads(ref_path.read_text())

    mixed_counts = collections.Counter(
        (capture.get("first_frame") or {}).get("action_hint")
        for capture in mixed.get("steelsearch_transport_capture") or []
    )

    result = {
        "mixed_report_path": str(mixed_path),
        "java_reference_path": str(ref_path),
        "mixed_publish_state_count": mixed_counts.get(
            "internal:cluster/coordination/publish_state", 0
        ),
        "mixed_commit_state_count": mixed_counts.get(
            "internal:cluster/coordination/commit_state", 0
        ),
        "java_reference_publish_state_count": ref.get("publish_state_count", 0),
        "java_reference_commit_state_count": ref.get("commit_state_count", 0),
        "result": (
            "mixed_path_reaches_publish_state_but_not_commit_state_while_java_reference_reaches_both"
            if mixed_counts.get("internal:cluster/coordination/publish_state", 0) > 0
            and mixed_counts.get("internal:cluster/coordination/commit_state", 0) == 0
            and ref.get("publish_state_count", 0) > 0
            and ref.get("commit_state_count", 0) > 0
            else "mixed_vs_java_reference_publication_gap_not_resolved"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
