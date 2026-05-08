#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_channel_instrumentation_path.py <transport_service.java> <connection_profile.java> <cluster_connection_manager.java>"
        )

    transport_service = Path(sys.argv[1]).read_text()
    connection_profile = Path(sys.argv[2]).read_text()
    cluster_conn = Path(sys.argv[3]).read_text()

    source_has_transport_tracer_action_node_only = (
        'tracerLog.trace("[{}][{}] sent to [{}] (timeout: [{}])", requestId, action, node, options.timeout());' in transport_service
        and 'tracerLog.trace("[{}][{}] received response from [{}]", requestId, holder.action(), holder.connection().getNode());' in transport_service
    )
    source_has_channel_selection_hook = (
        "ConnectionTypeHandle" in connection_profile
        and "getChannel(List<T> channels)" in connection_profile
        and "return channels.get(offset + Math.floorMod(counter.incrementAndGet(), length));" in connection_profile
    )
    source_has_connected_close_listener_hook = (
        "conn.addCloseListener(ActionListener.wrap(() -> {" in cluster_conn
        and 'logger.trace("unregistering {} after connection close and marking as disconnected", node);' in cluster_conn
        and "connectionListener.onNodeDisconnected(node, conn);" in cluster_conn
    )

    result = (
        "existing_transport_tracer_is_not_channel_class_specific_so_class_order_instrumentation_should_target_connection_type_handle_getChannel_and_connected_close_listener"
        if source_has_transport_tracer_action_node_only
        and source_has_channel_selection_hook
        and source_has_connected_close_listener_hook
        else "channel_instrumentation_path_not_fully_established"
    )

    print(json.dumps({
        "source_has_transport_tracer_action_node_only": source_has_transport_tracer_action_node_only,
        "source_has_channel_selection_hook": source_has_channel_selection_hook,
        "source_has_connected_close_listener_hook": source_has_connected_close_listener_hook,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
