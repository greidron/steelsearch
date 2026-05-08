#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_connection_profile_selected_channel_trace_available.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    selected_count = len(re.findall(r"selected channel index \[", stdout_text))
    reg_count = len(re.findall(r"handle types \[REG\]", stdout_text))
    state_count = len(re.findall(r"handle types \[STATE\]", stdout_text))
    ping_count = len(re.findall(r"handle types \[PING\]", stdout_text))

    result = {
        "work_dir": report["work_dir"],
        "selected_channel_index_count": selected_count,
        "handle_types_reg_count": reg_count,
        "handle_types_state_count": state_count,
        "handle_types_ping_count": ping_count,
        "result": "connection_profile_selected_channel_trace_is_available_in_actual_probe_without_extra_patch"
        if selected_count > 0 and reg_count > 0
        else "selected_channel_trace_not_observed_in_actual_probe",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
