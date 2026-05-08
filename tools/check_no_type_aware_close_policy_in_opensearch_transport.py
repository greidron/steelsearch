import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_no_type_aware_close_policy_in_opensearch_transport.py '
            '<tcp_transport.java> <transport_keepalive.java> <current_task_context.json>',
            file=sys.stderr,
        )
        return 1

    tcp_transport_text = Path(sys.argv[1]).read_text()
    keepalive_text = Path(sys.argv[2]).read_text()
    context = json.loads(Path(sys.argv[3]).read_text())

    source_type_used_for_send_selection = 'return connectionTypeHandle.getChannel(channels);' in tcp_transport_text
    source_close_closes_all_channels_without_type_branch = 'CloseableChannel.closeChannels(channels, block);' in tcp_transport_text
    source_keepalive_registers_all_channels_uniformly = bool(re.search(r'for \(TcpChannel channel : nodeChannels\)', keepalive_text))
    source_keepalive_has_no_type_branch = 'TransportRequestOptions.Type' not in keepalive_text

    if (
        source_type_used_for_send_selection
        and source_close_closes_all_channels_without_type_branch
        and source_keepalive_registers_all_channels_uniformly
        and source_keepalive_has_no_type_branch
        and context['no_bulk_or_recovery_actions']
        and context['later_control_traffic_present']
    ):
        result = (
            'opensearch_transport_source_has_no_type_aware_close_policy_for_bulk_recovery_vs_other_channels_so_the_close_origin_choice_is_below_this_layer'
        )
    else:
        result = 'type_aware_close_policy_presence_inconclusive'

    print(json.dumps({
        'source_type_used_for_send_selection': source_type_used_for_send_selection,
        'source_close_closes_all_channels_without_type_branch': source_close_closes_all_channels_without_type_branch,
        'source_keepalive_registers_all_channels_uniformly': source_keepalive_registers_all_channels_uniformly,
        'source_keepalive_has_no_type_branch': source_keepalive_has_no_type_branch,
        'no_bulk_or_recovery_actions': context['no_bulk_or_recovery_actions'],
        'later_control_traffic_present': context['later_control_traffic_present'],
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
