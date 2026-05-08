#!/usr/bin/env python3
import re
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_low_level_handshake_close_caller.py <opensearch-stdout.log>", file=sys.stderr)
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

    caller_counter = Counter()
    matched_ports = set()
    pattern = re.compile(
        r"steelsearch_netty4_tcpchannel_stage=close_invoked "
        r"local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ .*?"
        r"caller=([^\s]+) callerParent=([^\s]+) callerGrandparent=([^\s]+) "
        r"callerGreatGrandparent=([^\s]+)"
    )
    for m in pattern.finditer(stdout):
        port = int(m.group(1))
        if port not in write_ports:
            continue
        matched_ports.add(port)
        caller_counter[(m.group(2), m.group(3), m.group(4), m.group(5))] += 1

    print(f"write_ports={len(write_ports)}")
    print(f"matched_ports={len(matched_ports)}")
    print(f"caller_fingerprints={len(caller_counter)}")
    for fingerprint, count in caller_counter.most_common(5):
        print(f"fingerprint_count={count} caller_chain={fingerprint}")
    print(f"unmatched_write_ports={sorted(write_ports - matched_ports)[:20]}")

    if not write_ports:
        print("checker_result=inconclusive_no_low_level_handshake_write_ports")
        return 1

    if len(matched_ports) == len(write_ports) and len(caller_counter) == 1:
        print("checker_result=low_level_handshake_close_caller_is_single_fingerprint")
        return 0

    print("checker_result=inconclusive_or_mixed_close_callers")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
