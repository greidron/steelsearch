#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys

candidates = {
    'strace': shutil.which('strace'),
    'bpftrace': shutil.which('bpftrace'),
    'async_profiler': shutil.which('async-profiler'),
    'perf': shutil.which('perf'),
}

probe = subprocess.run(['perf', 'inject', '-h'], capture_output=True, text=True)
perf_inject_jit_available = '--jit' in (probe.stdout + probe.stderr)

result = {
    'candidates': candidates,
    'perf_inject_jit_available': perf_inject_jit_available,
}

new_capability = bool(candidates['strace'] or candidates['bpftrace'] or candidates['async_profiler'])
if not new_capability and perf_inject_jit_available:
    result['checker_result'] = 'no_materially_different_external_capability_or_new_root_blocker_relief_candidate_is_currently_available'
else:
    result['checker_result'] = 'a_materially_different_capability_or_new_relief_candidate_may_be_available'

json.dump(result, sys.stdout, indent=2)
sys.stdout.write('\n')
