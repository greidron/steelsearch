#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_steelsearch_publish_state_hold_open_contract.py <main.rs>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    branch_anchor = '} else if is_request && action_hint.as_deref() == Some("internal:cluster/coordination/publish_state") {'
    start = source.find(branch_anchor)
    snippet = source[start : start + 1400] if start != -1 else ""
    result = {
        "publish_state_branch_present": start != -1,
        "publish_state_branch_writes_response": "stream.write_all(&response)?;" in snippet,
        "publish_state_branch_flushes_response": "stream.flush()?;" in snippet,
        "publish_state_branch_sets_response_timestamp": "response_frame_sent_at_ms = Some(unix_time_ms());" in snippet,
        "publish_state_branch_uses_hold_open_20s": "Duration::from_secs(20)" in snippet
        and "hold_transport_channel_open(" in snippet,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
