#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

OPS = ['read(', 'close(', 'epoll_pwait(', 'ppoll(', 'futex(']


def main() -> int:
    path = Path(sys.argv[1])
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    counts = Counter()
    for line in lines:
        for op in OPS:
            if op in line:
                counts[op[:-1]] += 1
    result = {
        'path': str(path),
        'counts': dict(counts),
        'checker_result': 'late_strace_basic_mix_collected' if counts else 'late_strace_basic_mix_missing'
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
