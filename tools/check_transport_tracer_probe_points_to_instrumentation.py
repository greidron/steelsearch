#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_transport_tracer_probe_points_to_instrumentation.py <probe_report.json> <transport_service.java> <transport_settings.java>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )
    stderr_text = pathlib.Path(report["artifacts"]["opensearch_stderr"]).read_text(
        encoding="utf-8", errors="replace"
    )
    transport_service_text = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
    transport_settings_text = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")

    action_literals = (
        "internal:discovery/request_peers",
        "internal:cluster/request_pre_vote",
        "internal:coordination/fault_detection/follower_check",
        "internal:cluster/coordination/start_join",
    )
    action_literal_count = sum(stdout_text.count(action) + stderr_text.count(action) for action in action_literals)

    result = {
        "work_dir": report["work_dir"],
        "selected_channel_index_count": len(re.findall(r"selected channel index \[", stdout_text)),
        "action_literal_count_across_stdout_stderr": action_literal_count,
        "source_transportservice_tracer_logger_exists": 'Loggers.getLogger(logger, ".tracer")' in transport_service_text,
        "source_should_trace_uses_simple_match": "Regex.simpleMatch(include, action)" in transport_service_text,
        "source_transport_tracer_include_setting_exists": '"transport.tracer.include"' in transport_settings_text,
        "result": "current_transport_tracer_probe_points_to_action_tagged_selected_index_instrumentation_as_the_more_direct_next_step"
        if action_literal_count == 0
        and 'Loggers.getLogger(logger, ".tracer")' in transport_service_text
        and "Regex.simpleMatch(include, action)" in transport_service_text
        and '"transport.tracer.include"' in transport_settings_text
        else "transport_tracer_path_not_yet_strong_enough_to_choose_instrumentation",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
