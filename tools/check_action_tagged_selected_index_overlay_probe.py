#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_action_tagged_selected_index_overlay_probe.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    result = {
        "work_dir": report["work_dir"],
        "action_tagged_selected_index_count": len(re.findall(r"action-tagged selected channel index \[", stdout_text)),
        "selected_channel_index_count": len(re.findall(r"selected channel index \[", stdout_text)),
        "request_peers_count": len(re.findall(r"internal:discovery/request_peers", stdout_text)),
        "request_pre_vote_count": len(re.findall(r"internal:cluster/request_pre_vote", stdout_text)),
        "follower_check_count": len(re.findall(r"internal:coordination/fault_detection/follower_check", stdout_text)),
        "start_join_count": len(re.findall(r"internal:cluster/coordination/start_join", stdout_text)),
        "result": "overlay_probe_surfaces_action_tagged_selected_index_trace"
        if len(re.findall(r"action-tagged selected channel index \[", stdout_text)) > 0
        else "overlay_probe_did_not_surface_action_tagged_selected_index_trace",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
