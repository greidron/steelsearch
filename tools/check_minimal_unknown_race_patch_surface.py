#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_minimal_unknown_race_patch_surface.py <Netty4Transport.java> <Netty4TcpChannel.java> <Netty4MessageChannelHandler.java>', file=sys.stderr)
        return 2
    netty_transport = Path(sys.argv[1]).read_text()
    tcp_channel = Path(sys.argv[2]).read_text()
    message_handler = Path(sys.argv[3]).read_text()

    source_has_early_close_future_hint = 'addEarlyCloseFutureHintListener(ch);' in netty_transport
    source_has_close_hint_handler = 'ch.pipeline().addLast("close_hint", new Netty4EarlyCloseHintHandler());' in netty_transport
    source_has_channelinactive_record = 'tcpChannel.recordCloseHint("channelInactive", null);' in message_handler
    source_has_immediate_close_trace_listener = 'this.channel.closeFuture().addListener(f -> {' in tcp_channel and 'netty4 tcp channel close completed for' in tcp_channel
    source_close_trace_reads_attr_once = 'Optional.ofNullable(this.channel.attr(CLOSE_HINT_KEY).get()).orElse(closeHint)' in tcp_channel

    result = 'inconclusive'
    if all([
        source_has_early_close_future_hint,
        source_has_close_hint_handler,
        source_has_channelinactive_record,
        source_has_immediate_close_trace_listener,
        source_close_trace_reads_attr_once,
    ]):
        result = 'minimal_patch_candidate_is_to_change_netty4tcpchannel_installCloseTraceListener_order_or_deferral_not_to_add_more_close_path_markers'

    print(json.dumps({
        'source_has_early_close_future_hint': source_has_early_close_future_hint,
        'source_has_close_hint_handler': source_has_close_hint_handler,
        'source_has_channelinactive_record': source_has_channelinactive_record,
        'source_has_immediate_close_trace_listener': source_has_immediate_close_trace_listener,
        'source_close_trace_reads_attr_once': source_close_trace_reads_attr_once,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
