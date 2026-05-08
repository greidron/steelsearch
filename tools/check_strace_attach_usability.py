#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / 'strace.log'
        sleeper = subprocess.Popen(['sleep', '5'])
        time.sleep(0.5)
        trace = subprocess.run(['timeout', '2s', 'strace', '-p', str(sleeper.pid), '-o', str(log)], capture_output=True, text=True)
        try:
            sleeper.terminate()
            sleeper.wait(timeout=2)
        except Exception:
            sleeper.kill()
            sleeper.wait()
        log_text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
        result = {
            'strace_returncode': trace.returncode,
            'stderr': trace.stderr.strip(),
            'log_exists': log.exists(),
            'log_nonempty': bool(log_text.strip()),
        }
        if trace.returncode in (0, 124) and log_text.strip():
            result['checker_result'] = 'strace_attach_is_usable_in_current_session'
        else:
            result['checker_result'] = 'strace_binary_exists_but_attach_is_not_usable_in_current_session'
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
