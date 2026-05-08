#!/usr/bin/env python3
import json
import shutil
import subprocess

result = {
    'strace_path': shutil.which('strace'),
    'perf_raw_syscalls_available': False,
    'perf_probe_exit_code': None,
    'perf_probe_stderr': None,
}
proc = subprocess.run(
    ['perf', 'stat', '-e', 'raw_syscalls:sys_enter', '--timeout', '1000', 'true'],
    capture_output=True,
    text=True,
)
result['perf_probe_exit_code'] = proc.returncode
stderr = (proc.stderr or '').strip()
result['perf_probe_stderr'] = stderr
if proc.returncode == 0:
    result['perf_raw_syscalls_available'] = True
checker_result = 'external_native_instrumentation_available'
if result['strace_path'] is None and result['perf_raw_syscalls_available'] is False:
    checker_result = 'current_environment_lacks_external_native_instrumentation_needed_to_resume_read_starvation_branch'
print(json.dumps({**result, 'checker_result': checker_result}, indent=2))
