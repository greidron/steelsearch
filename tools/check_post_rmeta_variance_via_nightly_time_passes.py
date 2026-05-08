#!/usr/bin/env python3
import json
import os
import re
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
ROUNDS = 5
CMD = [
    "cargo",
    "+nightly",
    "rustc",
    "-p",
    "os-node",
    "--lib",
    "--features",
    "standalone-runtime",
    "--manifest-path",
    str(ROOT / "Cargo.toml"),
    "--",
    "-Z",
    "time-passes",
]
TIME_PASSES_RE = re.compile(r"time:\s+([0-9.]+);.*?\t([^\t\n]+)$")
TARGET_PHASES = [
    "codegen_to_LLVM_IR",
    "LLVM_passes",
    "codegen_crate",
    "link_rlib",
    "link_crate",
    "link_binary",
    "link",
]


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def run_time_passes() -> dict[str, float]:
    cp = subprocess.run(
        CMD,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    phases: dict[str, float] = {}
    for line in cp.stderr.splitlines():
        match = TIME_PASSES_RE.search(line.strip())
        if not match:
            continue
        phases[match.group(2)] = float(match.group(1)) * 1000
    return phases


def main() -> int:
    subprocess.run(CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    rounds = []
    for _ in range(ROUNDS):
        touch(LEAF)
        phases = run_time_passes()
        rounds.append({phase: round(phases.get(phase, 0.0), 2) for phase in TARGET_PHASES})

    summary = {}
    for phase in TARGET_PHASES:
        values = [round_data[phase] for round_data in rounds]
        if all(value == 0.0 for value in values):
            summary[phase] = {
                "present": False,
                "values_ms": values,
            }
            continue
        summary[phase] = {
            "present": True,
            "values_ms": values,
            "min_ms": min(values),
            "max_ms": max(values),
            "stddev_ms": round(statistics.pstdev(values), 2),
            "mean_ms": round(statistics.mean(values), 2),
        }

    present_stddevs = {
        phase: data["stddev_ms"]
        for phase, data in summary.items()
        if data["present"]
    }
    dominant_phase = max(present_stddevs, key=present_stddevs.get) if present_stddevs else None

    result = {
        "rounds": ROUNDS,
        "phase_summary": summary,
        "dominant_variance_phase": dominant_phase,
        "result": "post_rmeta_variance_split_across_nightly_time_passes_codegen_llvm_link_phases",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
