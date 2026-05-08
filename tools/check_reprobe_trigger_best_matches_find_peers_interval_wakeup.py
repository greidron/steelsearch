#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from statistics import median
from datetime import datetime


ACTION_PATTERN = re.compile(
    r"^\[(.*?)\].*action-tagged selected channel index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\]"
)


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_reprobe_trigger_best_matches_find_peers_interval_wakeup.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    stdout_path = Path(report["artifacts"]["opensearch_stdout"])
    peerfinder_path = Path("/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java")

    fmt = "%Y-%m-%dT%H:%M:%S,%f"
    singleton_timestamps = []
    for line in stdout_path.read_text(errors="replace").splitlines():
        match = ACTION_PATTERN.search(line)
        if not match:
            continue
        ts = datetime.strptime(match.group(1), fmt)
        idx = int(match.group(2))
        req_type = match.group(3)
        action = match.group(4)
        if idx == 0 and req_type == "REG" and action == "internal:transport/handshake":
            singleton_timestamps.append(ts)

    singleton_intervals_ms = [
        int((singleton_timestamps[i] - singleton_timestamps[i - 1]).total_seconds() * 1000)
        for i in range(1, len(singleton_timestamps))
    ]

    source = peerfinder_path.read_text()
    has_find_peers_interval_1000 = '"discovery.find_peers_interval",' in source and "TimeValue.timeValueMillis(1000)" in source
    has_handle_wakeup_scheduler = "scheduleUnlessShuttingDown(findPeersInterval" in source
    has_peer_close_returns_true = 'logger.trace("{} no longer connected", this);' in source and "return true;" in source
    has_outer_wakeup_reprobe = "providedAddresses.forEach(this::startProbe);" in source and "startProbe(discoveryNodeObjectCursor.getAddress());" in source

    result = {
        "work_dir": report.get("work_dir"),
        "singleton_probe_count": len(singleton_timestamps),
        "singleton_probe_interval_ms": {
            "min": min(singleton_intervals_ms),
            "median": median(singleton_intervals_ms),
            "max": max(singleton_intervals_ms),
        },
        "source_has_find_peers_interval_default_1000ms": has_find_peers_interval_1000,
        "source_has_handle_wakeup_scheduler": has_handle_wakeup_scheduler,
        "source_peer_close_path_returns_to_outer_wakeup_without_direct_startprobe": has_peer_close_returns_true,
        "source_outer_wakeup_reprobes_cluster_state_and_configured_hosts": has_outer_wakeup_reprobe,
        "result": (
            "repeated_reprobe_best_matches_find_peers_interval_wakeup_rather_than_immediate_close_or_inbound_reflection"
            if has_find_peers_interval_1000
            and has_handle_wakeup_scheduler
            and has_peer_close_returns_true
            and has_outer_wakeup_reprobe
            and 850 <= median(singleton_intervals_ms) <= 1150
            else "repeated_reprobe_is_not_yet_best_explained_by_find_peers_interval_wakeup"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith("repeated_reprobe_best_matches_find_peers_interval_wakeup"):
        sys.exit(1)


if __name__ == "__main__":
    main()
