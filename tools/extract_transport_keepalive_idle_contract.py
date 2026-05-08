#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_transport_keepalive_idle_contract.py <TransportKeepAlive.java>",
            file=sys.stderr,
        )
        return 2

    source_path = Path(sys.argv[1])
    text = source_path.read_text(encoding="utf-8")

    result = {
        "source_path": str(source_path),
        "register_node_connection_requires_non_negative_ping_interval": "if (pingInterval.millis() < 0) {" in text,
        "scheduled_ping_runs_on_generic_threadpool": "threadPool.schedule(this, pingInterval, ThreadPool.Names.GENERIC);" in text,
        "scheduled_ping_repeats_until_shutdown": "threadPool.scheduleUnlessShuttingDown(pingInterval, ThreadPool.Names.GENERIC, this);" in text,
        "needs_keepalive_uses_last_accessed_delta": "long accessedDelta = stats.lastAccessedTime() - lastPingRelativeMillis;" in text,
        "needs_keepalive_requires_idle_window": "return accessedDelta <= 0;" in text,
        "server_echoes_keepalive_ping_only_for_server_channel": "if (channel.isServerChannel()) {" in text
        and "sendPing(channel);" in text,
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
