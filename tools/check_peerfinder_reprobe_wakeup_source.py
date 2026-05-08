#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path


EVENT_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*Peer\{transportAddress=(?P<addr>[^,]+), discoveryNode=(?P<node>.+?), peersRequestInFlight=false\} (?P<event>requesting peers|attempting connection)"
)


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_peerfinder_reprobe_wakeup_source.py <peerfinder.java> <coordinator.java> <stdout.log>"
        )

    peerfinder = Path(sys.argv[1]).read_text()
    coordinator = Path(sys.argv[2]).read_text()
    lines = Path(sys.argv[3]).read_text().splitlines()

    source_has_scheduled_wakeup = (
        "scheduleUnlessShuttingDown(findPeersInterval" in peerfinder
        and "if (handleWakeUp() == false) {" in peerfinder
        and "startProbe(discoveryNodeObjectCursor.getAddress());" in peerfinder
        and "providedAddresses.forEach(this::startProbe);" in peerfinder
    )
    source_on_found_peers_updated_not_reprobe = (
        "protected void onFoundPeersUpdated()" in coordinator
        and "startElectionScheduler();" in coordinator
        and "clusterBootstrapService.onFoundPeersUpdated();" in coordinator
        and "startProbe(" not in coordinator.split("protected void onFoundPeersUpdated()", 1)[1].split("}", 1)[0]
    )

    fmt = "%Y-%m-%dT%H:%M:%S,%f"
    previous_requesting_ts = None
    deltas_ms = []
    pair_count = 0
    for line in lines:
        m = EVENT_RE.search(line)
        if not m or m.group("addr") != "127.0.0.1:57743":
            continue
        ts = datetime.strptime(m.group("ts"), fmt)
        event = m.group("event")
        node = m.group("node")
        if event == "requesting peers" and node != "null":
            previous_requesting_ts = ts
        elif event == "attempting connection" and node == "null" and previous_requesting_ts is not None:
            pair_count += 1
            deltas_ms.append(int((ts - previous_requesting_ts).total_seconds() * 1000))
            previous_requesting_ts = None

    near_one_second_count = sum(1 for d in deltas_ms if 700 <= d <= 1100)
    result = (
        "fresh_null_discovery_reprobe_is_better_explained_by_scheduled_peerfinder_handleWakeUp_than_by_direct_followers_checker_callback"
        if source_has_scheduled_wakeup
        and source_on_found_peers_updated_not_reprobe
        and pair_count > 0
        and near_one_second_count >= max(1, pair_count // 2)
        else "peerfinder_reprobe_wakeup_source_not_fully_established"
    )

    print(json.dumps({
        "source_has_scheduled_wakeup": source_has_scheduled_wakeup,
        "source_on_found_peers_updated_not_reprobe": source_on_found_peers_updated_not_reprobe,
        "requesting_to_fresh_attempt_pair_count": pair_count,
        "requesting_to_fresh_attempt_deltas_ms_last10": deltas_ms[-10:],
        "near_one_second_count": near_one_second_count,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
