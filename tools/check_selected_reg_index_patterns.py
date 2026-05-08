#!/usr/bin/env python3
import json
import pathlib
import re
import sys


PATTERN = re.compile(
    r"selected channel index \[(\d+)\] from handle types \[(.*?)\] \(offset=(\d+), length=(\d+)\)"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_selected_reg_index_patterns.py <probe_report.json>", file=sys.stderr)
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    reg_singleton = 0
    reg_multi = {index: 0 for index in range(7, 13)}
    ping = 0
    state = 0
    for index_text, types_text, offset_text, length_text in PATTERN.findall(stdout_text):
        index = int(index_text)
        offset = int(offset_text)
        length = int(length_text)
        if types_text == "REG" and offset == 0 and length == 1 and index == 0:
            reg_singleton += 1
        elif types_text == "REG" and offset == 7 and length == 6 and index in reg_multi:
            reg_multi[index] += 1
        elif types_text == "PING" and offset == 3 and length == 1 and index == 3:
            ping += 1
        elif types_text == "STATE" and offset == 4 and length == 1 and index == 4:
            state += 1

    result = {
        "reg_singleton_offset0_len1_index0_count": reg_singleton,
        "reg_multichannel_offset7_len6_counts": reg_multi,
        "ping_offset3_len1_index3_count": ping,
        "state_offset4_len1_index4_count": state,
        "result": "selected_reg_trace_splits_into_singleton_probe_index0_and_multichannel_round_robin_indices_7_12"
        if reg_singleton > 0 and all(count > 0 for count in reg_multi.values())
        else "selected_reg_trace_did_not_cleanly_split_into_expected_patterns",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
