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
CHECK_CMD = [
    "cargo",
    "check",
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
    subprocess.run(CHECK_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    subprocess.run(CHECK_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))
    by_id = {unit["i"]: unit for unit in unit_data}
    os_node_lib = next(
        unit
        for unit in unit_data
        if unit["name"] == "os-node" and unit["target"] == ' lib (check)'
    )

    lib_rmeta_ready_ms = round((os_node_lib["start"] + os_node_lib["rmeta_time"]) * 1000, 2)
    lib_finish_ms = round((os_node_lib["start"] + os_node_lib["duration"]) * 1000, 2)

    unlocked_rmeta = []
    for dep_id in os_node_lib.get("unlocked_rmeta_units", []):
        unit = by_id[dep_id]
        dep_start_ms = round(unit["start"] * 1000, 2)
        unlocked_rmeta.append(
            {
                "name": unit["name"],
                "target": unit["target"],
                "start_ms": dep_start_ms,
                "starts_after_rmeta_ms": round(dep_start_ms - lib_rmeta_ready_ms, 2),
                "starts_before_lib_finish": dep_start_ms <= lib_finish_ms,
            }
        )

    unlocked_units = []
    for dep_id in os_node_lib.get("unlocked_units", []):
        unit = by_id[dep_id]
        dep_start_ms = round(unit["start"] * 1000, 2)
        unlocked_units.append(
            {
                "name": unit["name"],
                "target": unit["target"],
                "start_ms": dep_start_ms,
                "starts_after_rmeta_ms": round(dep_start_ms - lib_rmeta_ready_ms, 2),
                "starts_before_lib_finish": dep_start_ms <= lib_finish_ms,
            }
        )

    result = {
        "os_node_lib_rmeta_ready_ms": lib_rmeta_ready_ms,
        "os_node_lib_finish_ms": lib_finish_ms,
        "unlocked_rmeta_units": unlocked_rmeta,
        "unlocked_units": unlocked_units,
        "unlocked_rmeta_count": len(unlocked_rmeta),
        "unlocked_rmeta_overlap_before_lib_finish_count": sum(
            1 for unit in unlocked_rmeta if unit["starts_before_lib_finish"]
        ),
        "result": "cargo_check_timing_graph_profiled_for_os_node_rmeta_unlock_dependents",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
