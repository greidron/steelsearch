#!/usr/bin/env python3
import collections
import json
import pathlib
import re
import sys


PATTERN = re.compile(
    r"action-tagged selected channel index \[(\d+)\] type \[(.*?)\] action \[(.*?)\] requestId \[(\d+)\]"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_action_tagged_selected_index_cadence.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    by_action = collections.defaultdict(collections.Counter)
    by_action_type = {}
    for index_text, type_text, action_text, _ in PATTERN.findall(stdout_text):
        by_action[action_text][int(index_text)] += 1
        by_action_type[action_text] = type_text

    result = {
        "work_dir": report["work_dir"],
        "action_index_distribution": {
            action: {
                "type": by_action_type[action],
                "index_counts": {str(index): count for index, count in sorted(counter.items())},
                "total": sum(counter.values()),
            }
            for action, counter in sorted(by_action.items())
        },
        "result": "action_tagged_selected_index_trace_splits_actual_action_cadence_by_channel_type_and_index"
        if by_action
        else "action_tagged_selected_index_trace_not_found",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
