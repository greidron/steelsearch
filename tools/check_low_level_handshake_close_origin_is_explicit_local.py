#!/usr/bin/env python3
import re
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_low_level_handshake_close_origin_is_explicit_local.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    stdout = Path(sys.argv[1]).read_text(errors="replace")

    write_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
            r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ bytesLength=55",
            stdout,
        )
    }

    hints_by_port = {}
    for m in re.finditer(
        r"steelsearch_netty4_tcpchannel_stage=close_trace_emit "
        r"local=(/127\.0\.0\.1:(\d+)|null) remote=.*? hint=([^\s]+)",
        stdout,
    ):
        port = int(m.group(2)) if m.group(2) else None
        hint = m.group(3)
        hints_by_port.setdefault(port, []).append(hint)

    matched_ports = {port: hints_by_port[port] for port in write_ports if port in hints_by_port}
    counter = Counter()
    for hints in matched_ports.values():
        counter.update(hints)

    print(f"write_ports={len(write_ports)}")
    print(f"matched_ports={len(matched_ports)}")
    print(f"hint_counts={dict(counter)}")
    print(f"unmatched_write_ports={sorted(write_ports - matched_ports.keys())[:20]}")

    if not write_ports:
        print("checker_result=inconclusive_no_low_level_handshake_write_ports")
        return 1

    if len(matched_ports) == len(write_ports) and set(counter.keys()) == {"explicitLocalClose"}:
        print("checker_result=low_level_handshake_close_origin_is_consistently_explicitLocalClose")
        return 0

    print("checker_result=inconclusive_or_mixed_close_origin")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
