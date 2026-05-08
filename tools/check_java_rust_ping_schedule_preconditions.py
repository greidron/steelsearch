#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_java_rust_ping_schedule_preconditions.py "
            "<mixed-probe-report.json> <run-opensearch-dev.sh> <TransportSettings.java>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    launcher_path = Path(sys.argv[2])
    transport_settings_path = Path(sys.argv[3])

    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []
    keepalive_count = sum(1 for entry in capture if entry.get("is_keepalive_ping"))

    launcher_text = launcher_path.read_text()
    transport_settings_text = transport_settings_path.read_text()

    source_default_disabled = (
        'public static final Setting<TimeValue> PING_SCHEDULE' in transport_settings_text
        and 'TimeValue.timeValueSeconds(-1)' in transport_settings_text
    )
    launcher_overrides_ping_schedule = "transport.ping_schedule" in launcher_text

    if source_default_disabled and not launcher_overrides_ping_schedule and keepalive_count == 0:
        result = "ping_schedule_disabled_by_default_and_not_overridden"
    elif source_default_disabled and launcher_overrides_ping_schedule and keepalive_count == 0:
        result = "ping_schedule_overridden_but_keepalive_not_observed"
    elif source_default_disabled and not launcher_overrides_ping_schedule and keepalive_count > 0:
        result = "keepalive_observed_despite_default_disabled"
    else:
        result = "preconditions_do_not_explain_keepalive_state"

    payload = {
        "report_path": str(report_path),
        "source_default_disabled": source_default_disabled,
        "launcher_overrides_ping_schedule": launcher_overrides_ping_schedule,
        "keepalive_count": keepalive_count,
        "result": result,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
