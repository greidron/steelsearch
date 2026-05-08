#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_selected_index_trace_lacks_action_attribution.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    selected_channel_index_count = len(re.findall(r"selected channel index \[", stdout_text))
    requested_action_literal_count = sum(
        len(re.findall(pattern, stdout_text))
        for pattern in (
            r"internal:discovery/request_peers",
            r"internal:cluster/request_pre_vote",
            r"internal:coordination/fault_detection/follower_check",
            r"internal:cluster/coordination/start_join",
        )
    )

    result = {
        "work_dir": report["work_dir"],
        "selected_channel_index_count": selected_channel_index_count,
        "requested_action_literal_count": requested_action_literal_count,
        "result": "selected_channel_index_trace_is_present_but_current_transport_tracer_probe_does_not_emit_action_attribution"
        if selected_channel_index_count > 0 and requested_action_literal_count == 0
        else "action_attribution_lines_observed_or_selected_index_trace_missing",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
