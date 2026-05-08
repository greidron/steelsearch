#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: check_channel_instrumentation_exposed_in_probe.py <stdout.log>"
        )

    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")

    connection_profile_selection_count = text.count("selected channel index [")
    cluster_connection_unregister_count = text.count("unregistering ")
    connector_full_connection_count = text.count("completed full connection with [")

    result = (
        "runner_probe_path_exposes_cluster_connection_unregister_traces_but_connection_profile_getChannel_trace_is_still_missing_in_current_probe"
        if cluster_connection_unregister_count > 0
        and connector_full_connection_count > 0
        and connection_profile_selection_count == 0
        else (
            "runner_probe_path_now_exposes_connection_profile_channel_selection_and_cluster_connection_unregister_traces"
            if connection_profile_selection_count > 0
            and cluster_connection_unregister_count > 0
            and connector_full_connection_count > 0
            else "channel_instrumentation_not_yet_exposed_in_probe"
        )
    )

    print(json.dumps({
        "connection_profile_selection_count": connection_profile_selection_count,
        "cluster_connection_unregister_count": cluster_connection_unregister_count,
        "connector_full_connection_count": connector_full_connection_count,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
