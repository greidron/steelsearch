#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_mixed_vs_proxy_followup_gap.py "
            "<mixed-followup-remote-eof.json> <mixed-publish-state.json> <proxy-followup.json>",
            file=sys.stderr,
        )
        return 2

    mixed_followup = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    mixed_publish = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    proxy_followup = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

    result = {
        "mixed_followup_remote_eof_after_identity_count": int(mixed_followup.get("remote_eof_after_identity_count", 0)),
        "mixed_publish_state_count": int(mixed_publish.get("publish_state_count", 0)),
        "mixed_commit_state_count": int(mixed_publish.get("commit_state_count", 0)),
        "proxy_followup_failed": bool(proxy_followup.get("followup_failed", False)),
        "proxy_publish_state_count": int(proxy_followup.get("publish_state_count", 0)),
    }

    if (
        result["mixed_followup_remote_eof_after_identity_count"] > 0
        and result["mixed_publish_state_count"] > 0
        and result["proxy_followup_failed"]
        and result["proxy_publish_state_count"] == 0
    ):
        result["result"] = "proxy_reference_matches_old_mixed_followup_failure_but_differs_from_current_mixed_publish_state_progress"
    else:
        result["result"] = "mixed_vs_proxy_followup_gap_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
