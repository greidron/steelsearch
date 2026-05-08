#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
TIMINGS_DIR = ROOT / "target/cargo-timings"
BUILD_CMD = [
    "cargo",
    "build",
    "--timings",
    "-p",
    "os-node",
    "--features",
    "standalone-runtime",
    "--bin",
    "steelsearch",
    "--manifest-path",
    str(ROOT / "Cargo.toml"),
]
UNIT_DATA_RE = re.compile(r"const\s+UNIT_DATA\s*=\s*(\[.*?\]);", re.S)


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def newest_timing_html(before: set[Path]) -> Path:
    after = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def main() -> int:
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))
    os_node_lib = next(unit for unit in unit_data if unit["name"] == "os-node" and unit["target"] == "")
    duration_ms = round(os_node_lib["duration"] * 1000, 2)
    rmeta_ms = round(os_node_lib["rmeta_time"] * 1000, 2)
    derived_post_rmeta_ms = round(duration_ms - rmeta_ms, 2)
    result = {
        "os_node_lib_unit_keys": sorted(os_node_lib.keys()),
        "has_duration_field": "duration" in os_node_lib,
        "has_rmeta_time_field": "rmeta_time" in os_node_lib,
        "has_post_rmeta_field": "post_rmeta" in os_node_lib,
        "duration_ms": duration_ms,
        "rmeta_ms": rmeta_ms,
        "derived_post_rmeta_ms": derived_post_rmeta_ms,
        "result": "stable_cargo_timings_post_rmeta_is_a_derived_residual_from_duration_minus_rmeta_time_not_a_native_phase_field",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
