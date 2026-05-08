#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_handshake_channel_close_fanout_candidate.py <TcpTransport.java> <report.json>",
            file=sys.stderr,
        )
        return 2

    tcp_transport = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    source_handshake_channel_is_first = "final TcpChannel handshakeChannel = channels.get(0);" in tcp_transport
    source_any_channel_close_fans_out_to_nodechannels_close = "ch.addCloseListener(ActionListener.wrap(nodeChannels::close));" in tcp_transport
    source_nodechannels_close_closes_all_channels = "CloseableChannel.closeChannels(channels, block);" in tcp_transport

    direct_full_connect_remote_eof_count = 0
    action_channel_remote_eof_count = 0

    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        if action == "internal:transport/handshake" and row.get("first_post_response_event") == "remote_eof":
            direct_full_connect_remote_eof_count += 1
        if action in {
            "internal:discovery/request_peers",
            "internal:coordination/fault_detection/follower_check",
            "internal:cluster/coordination/publish_state",
        } and row.get("first_post_response_event") == "remote_eof":
            action_channel_remote_eof_count += 1

    if (
        source_handshake_channel_is_first
        and source_any_channel_close_fans_out_to_nodechannels_close
        and source_nodechannels_close_closes_all_channels
        and direct_full_connect_remote_eof_count > 0
        and action_channel_remote_eof_count > 0
    ):
        result = (
            "tcptransport_handshake_channel_close_fanout_is_a_strong_source_runtime_candidate_for_"
            "why_full_connection_action_channels_also_die_after_first_response"
        )
    else:
        result = "handshake_channel_close_fanout_candidate_inconclusive"

    print(
        json.dumps(
            {
                "source_handshake_channel_is_first": source_handshake_channel_is_first,
                "source_any_channel_close_fans_out_to_nodechannels_close": source_any_channel_close_fans_out_to_nodechannels_close,
                "source_nodechannels_close_closes_all_channels": source_nodechannels_close_closes_all_channels,
                "direct_full_connect_remote_eof_count": direct_full_connect_remote_eof_count,
                "action_channel_remote_eof_count": action_channel_remote_eof_count,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
