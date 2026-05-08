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


def profile(cmd: list[str]) -> dict[str, object]:
    subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))
    rmeta_time_present_count = sum(1 for unit in unit_data if "rmeta_time" in unit)
    rmeta_time_nonnull_count = sum(1 for unit in unit_data if unit.get("rmeta_time") is not None)
    unlocked_rmeta_nonempty_count = sum(1 for unit in unit_data if unit.get("unlocked_rmeta_units"))
    sample_without_consumers = [
        {
            "name": unit["name"],
            "target": unit["target"],
            "rmeta_time_ms": None if unit.get("rmeta_time") is None else round(unit["rmeta_time"] * 1000, 2),
            "unlocked_rmeta_units": unit.get("unlocked_rmeta_units", []),
        }
        for unit in unit_data
        if "rmeta_time" in unit and not unit.get("unlocked_rmeta_units")
    ][:5]
    return {
        "unit_count": len(unit_data),
        "rmeta_time_present_count": rmeta_time_present_count,
        "rmeta_time_nonnull_count": rmeta_time_nonnull_count,
        "unlocked_rmeta_nonempty_count": unlocked_rmeta_nonempty_count,
        "sample_rmeta_time_units_without_consumers": sample_without_consumers,
    }


def main() -> int:
    build_profile = profile(BUILD_CMD)
    check_profile = profile(CHECK_CMD)
    result = {
        "build_profile": build_profile,
        "check_profile": check_profile,
        "result": "rmeta_time_field_presence_profiled_against_unlocked_rmeta_units_for_build_and_check_graphs",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
