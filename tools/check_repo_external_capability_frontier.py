#!/usr/bin/env python3
import json
import shutil
import sys


def main() -> int:
    candidates = {
        'bpftrace': shutil.which('bpftrace'),
        'tcpdump': shutil.which('tcpdump'),
        'tshark': shutil.which('tshark'),
        'ngrep': shutil.which('ngrep'),
        'trace-cmd': shutil.which('trace-cmd'),
        'uftrace': shutil.which('uftrace'),
        'stap': shutil.which('stap'),
        'sysdig': shutil.which('sysdig'),
        'funclatency': shutil.which('funclatency'),
        'opensnoop-bpfcc': shutil.which('opensnoop-bpfcc'),
        'opensnoop': shutil.which('opensnoop'),
    }
    available = sorted([name for name, path in candidates.items() if path])
    result = {
        'candidates': candidates,
        'available_new_repo_external_planes': available,
    }
    if available:
        result['checker_result'] = 'additional_repo_external_visibility_plane_may_be_available'
    else:
        result['checker_result'] = 'no_additional_repo_external_visibility_plane_binary_is_currently_available_beyond_already_used_capabilities'
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
