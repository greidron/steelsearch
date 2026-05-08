import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_netty4_close_hint_instrumentation_path.py '
            '<netty4_tcp_channel.java> <netty4_message_channel_handler.java> <compiled_netty4_tcp_channel.class>',
            file=sys.stderr,
        )
        return 1

    tcp_channel_text = Path(sys.argv[1]).read_text()
    handler_text = Path(sys.argv[2]).read_text()
    compiled_bytes = Path(sys.argv[3]).read_bytes()

    source_has_close_hint_fields = 'private volatile String closeHint = "unknown";' in tcp_channel_text
    source_has_close_completion_trace = 'netty4 tcp channel close completed for' in tcp_channel_text
    source_records_exception_caught_hint = 'recordCloseHint("exceptionCaught", newCause);' in handler_text
    source_records_channel_inactive_hint = 'recordCloseHint("channelInactive", null);' in handler_text
    class_has_close_hint_string = b'netty4 tcp channel close completed for' in compiled_bytes

    if (
        source_has_close_hint_fields
        and source_has_close_completion_trace
        and source_records_exception_caught_hint
        and source_records_channel_inactive_hint
        and class_has_close_hint_string
    ):
        result = 'netty4_close_hint_instrumentation_path_is_implemented'
    else:
        result = 'netty4_close_hint_instrumentation_path_incomplete'

    print(json.dumps({
        'source_has_close_hint_fields': source_has_close_hint_fields,
        'source_has_close_completion_trace': source_has_close_completion_trace,
        'source_records_exception_caught_hint': source_records_exception_caught_hint,
        'source_records_channel_inactive_hint': source_records_channel_inactive_hint,
        'class_has_close_hint_string': class_has_close_hint_string,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
