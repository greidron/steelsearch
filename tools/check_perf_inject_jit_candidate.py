#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def count_metrics(path: Path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    return {
        'unknown_tmp_perf_lines': sum(1 for line in lines if '(/tmp/perf-' in line),
        'jit_lines': sum(1 for line in lines if '[JIT]' in line or ' jit ' in line.lower()),
        'read0_lines': sum(1 for line in lines if 'UnixFileDispatcherImpl_read0' in line),
    }


def main() -> int:
    perf_data = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        injected = td / 'injected.data'
        injected_script = td / 'injected.script.txt'
        inject = subprocess.run(['sudo', 'perf', 'inject', '-j', '-i', str(perf_data), '-o', str(injected)], capture_output=True, text=True)
        script = subprocess.run(['sudo', 'perf', 'script', '-i', str(injected)], capture_output=True, text=True)
        injected_script.write_text(script.stdout + script.stderr, encoding='utf-8')
        metrics = count_metrics(injected_script)
        result = {
            'perf_data': str(perf_data),
            'inject_returncode': inject.returncode,
            'script_returncode': script.returncode,
            'metrics': metrics,
        }
        if inject.returncode == 0 and script.returncode == 0 and metrics['jit_lines'] == 0 and metrics['unknown_tmp_perf_lines'] > 0:
            result['checker_result'] = 'perf_inject_jit_candidate_did_not_materialize_jit_symbols_for_higher_caller_frames'
        else:
            result['checker_result'] = 'perf_inject_jit_candidate_changed_symbolization_state'
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
