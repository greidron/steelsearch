#!/usr/bin/env python3
import collections
import json
import pathlib
import re
import sys


OPEN_RE = re.compile(
    r"opened transport connection \[(\d+)\] to \[(.*?)\] using channels \[\[(.*?)\]\]"
)
CLOSE_RE = re.compile(
    r"closed transport connection \[(\d+)\] to \[(.*?)\] with age \[(\d+)ms\]"
)
OBSERVED_CLOSE_RE = re.compile(
    r"node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=.*?:(\d+),"
)
LOCAL_PORT_RE = re.compile(r"localAddress=.*?:(\d+)")


def index_type(index: int) -> str:
    if 0 <= index <= 2:
        return "BULK"
    if index == 3:
        return "PING"
    if index == 4:
        return "STATE"
    if 5 <= index <= 6:
        return "RECOVERY"
    if 7 <= index <= 12:
        return "REG"
    return "UNKNOWN"


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_blind_non_handshake_connections_have_channel_index_type_signal.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = pathlib.Path(report["artifacts"]["opensearch_stdout"]).read_text(
        encoding="utf-8", errors="replace"
    )

    port_actions = collections.defaultdict(set)
    for capture in report["steelsearch_transport_capture"]:
        peer_addr = capture.get("peer_addr")
        if not peer_addr:
            continue
        port = int(peer_addr.rsplit(":", 1)[1])
        port_actions[port].add(capture["first_frame"]["action_hint"])
    handshake_ports = {port for port, actions in port_actions.items() if "internal:transport/handshake" in actions}

    open_by_id = {
        connection_id: sorted({int(port) for port in LOCAL_PORT_RE.findall(channels_text)})
        for connection_id, _, channels_text in OPEN_RE.findall(stdout_text)
    }
    close_by_id = collections.defaultdict(list)
    for connection_id, channel_index, local_port in OBSERVED_CLOSE_RE.findall(stdout_text):
        close_by_id[connection_id].append((int(channel_index), int(local_port)))

    blind_rows = []
    for connection_id, node_text, age_text in CLOSE_RE.findall(stdout_text):
        age = int(age_text)
        if "rust-replica-1" not in node_text or not (700 <= age <= 850):
            continue
        local_ports = open_by_id.get(connection_id, [])
        if set(local_ports) & handshake_ports:
            continue
        seen_actions = set()
        for port in local_ports:
            seen_actions |= port_actions.get(port, set())
        if seen_actions:
            continue
        channel_indices = sorted(index for index, _ in close_by_id.get(connection_id, []))
        type_counts = collections.Counter(index_type(index) for index in channel_indices)
        blind_rows.append(
            {
                "connection_id": int(connection_id),
                "age_ms": age,
                "observed_close_channel_count": len(channel_indices),
                "observed_close_channel_indices": channel_indices,
                "type_counts": dict(type_counts),
            }
        )

    result = {
        "blind_non_handshake_count": len(blind_rows),
        "complete_13_channel_trace_count": sum(1 for row in blind_rows if row["observed_close_channel_count"] == 13),
        "rows_with_reg_indices_7_12_count": sum(
            1 for row in blind_rows if row["type_counts"].get("REG") == 6
        ),
        "rows_with_state_index_4_count": sum(
            1 for row in blind_rows if row["type_counts"].get("STATE") == 1
        ),
        "sample_blind_rows": blind_rows[:5],
        "result": "blind_non_handshake_connections_still_have_java_only_channel_index_signal_for_type_inference"
        if blind_rows
        and all(row["observed_close_channel_count"] == 13 for row in blind_rows)
        and all(row["type_counts"].get("REG") == 6 for row in blind_rows)
        else "blind_non_handshake_channel_index_signal_not_complete_enough",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
