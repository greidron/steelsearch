#!/usr/bin/env python3
import json
import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_minimal_action_tagged_selected_index_patch_surface.py <tcp_transport.java> <connection_profile.java>",
            file=sys.stderr,
        )
        return 2

    tcp_transport_text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    connection_profile_text = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

    result = {
        "nodechannels_sendrequest_exists": "public void sendRequest(long requestId, String action, TransportRequest request, TransportRequestOptions options)"
        in tcp_transport_text,
        "nodechannels_sendrequest_has_type_selection": "TcpChannel channel = channel(options.type());" in tcp_transport_text,
        "nodechannels_has_channel_list_field": "private final List<TcpChannel> channels;" in tcp_transport_text,
        "connectionprofile_getchannel_lacks_action_context": "getChannel(List<T> channels)" in connection_profile_text,
        "result": "minimal_action_tagged_selected_index_patch_surface_is_tcptransport_nodechannels_sendrequest"
        if "public void sendRequest(long requestId, String action, TransportRequest request, TransportRequestOptions options)"
        in tcp_transport_text
        and "TcpChannel channel = channel(options.type());" in tcp_transport_text
        and "private final List<TcpChannel> channels;" in tcp_transport_text
        and "getChannel(List<T> channels)" in connection_profile_text
        else "minimal_patch_surface_not_confirmed",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
