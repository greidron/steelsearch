#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys


def main() -> int:
    strace_path = shutil.which("strace")
    apt_get_path = shutil.which("apt-get")
    tracing_root = "/sys/kernel/tracing"
    raw_syscalls_dir = "/sys/kernel/tracing/events/raw_syscalls/sys_enter"

    perf = subprocess.run(
        ["perf", "stat", "-e", "raw_syscalls:sys_enter", "true"],
        capture_output=True,
        text=True,
    )

    result = {
        "uid": os.getuid(),
        "strace_path": strace_path,
        "apt_get_path": apt_get_path,
        "tracing_root_exists": os.path.exists(tracing_root),
        "tracing_root_writable": os.access(tracing_root, os.W_OK),
        "raw_syscalls_dir_exists": os.path.exists(raw_syscalls_dir),
        "raw_syscalls_dir_writable": os.access(raw_syscalls_dir, os.W_OK),
        "perf_raw_syscalls_available": perf.returncode == 0,
        "perf_probe_exit_code": perf.returncode,
        "perf_probe_stderr": perf.stderr.strip(),
    }

    can_self_provision = (
        strace_path is not None
        or (result["perf_raw_syscalls_available"] is True)
        or (os.getuid() == 0 and apt_get_path is not None)
        or (apt_get_path is not None and result["tracing_root_writable"])
    )

    result["checker_result"] = (
        "current_environment_can_self_provision_or_already_has_external_native_instrumentation"
        if can_self_provision
        else "current_environment_cannot_self_provision_external_native_instrumentation_for_read_starvation_branch"
    )

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
