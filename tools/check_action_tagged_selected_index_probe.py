#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_action_tagged_selected_index_probe.py <probe_report.json>", file=sys.stderr)
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    result = {
        "work_dir": report["work_dir"],
        "action_tagged_selected_index_count": len(re.findall(r"action-tagged selected channel index \[", stdout_text)),
        "selected_channel_index_count": len(re.findall(r"selected channel index \[", stdout_text)),
        "result": "patched_action_tagged_selected_index_line_not_observed_in_current_force_gradle_probe"
        if len(re.findall(r"action-tagged selected channel index \[", stdout_text)) == 0
        else "patched_action_tagged_selected_index_line_observed",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
