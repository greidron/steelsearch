#!/usr/bin/env python3
import json
import os
import re
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LIB_RS = ROOT / "crates/os-node/src/lib.rs"
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
TIMINGS_DIR = ROOT / "target/cargo-timings"
ROUNDS = 7
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


def run_timed_build() -> dict[str, float]:
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))
    os_node_lib = next(unit for unit in unit_data if unit["name"] == "os-node" and unit["target"] == "")
    duration_ms = round(os_node_lib["duration"] * 1000, 2)
    rmeta_ms = round(os_node_lib["rmeta_time"] * 1000, 2)
    return {
        "lib_duration_ms": duration_ms,
        "rmeta_ms": rmeta_ms,
        "post_rmeta_ms": round(duration_ms - rmeta_ms, 2),
    }


def repeated_pairs() -> dict[str, object]:
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    pairs = []
    lib_deltas = []
    rmeta_deltas = []
    post_rmeta_deltas = []
    for _ in range(ROUNDS):
        touch(LEAF)
        first = run_timed_build()
        touch(LEAF)
        second = run_timed_build()
        lib_delta = round(second["lib_duration_ms"] - first["lib_duration_ms"], 2)
        rmeta_delta = round(second["rmeta_ms"] - first["rmeta_ms"], 2)
        post_rmeta_delta = round(second["post_rmeta_ms"] - first["post_rmeta_ms"], 2)
        lib_deltas.append(lib_delta)
        rmeta_deltas.append(rmeta_delta)
        post_rmeta_deltas.append(post_rmeta_delta)
        pairs.append(
            {
                "first": first,
                "second": second,
                "lib_delta_ms": lib_delta,
                "rmeta_delta_ms": rmeta_delta,
                "post_rmeta_delta_ms": post_rmeta_delta,
            }
        )
    return {
        "pairs": pairs,
        "lib_delta_values_ms": lib_deltas,
        "rmeta_delta_values_ms": rmeta_deltas,
        "post_rmeta_delta_values_ms": post_rmeta_deltas,
        "lib_delta_stddev_ms": round(statistics.pstdev(lib_deltas), 2),
        "rmeta_delta_stddev_ms": round(statistics.pstdev(rmeta_deltas), 2),
        "post_rmeta_delta_stddev_ms": round(statistics.pstdev(post_rmeta_deltas), 2),
        "lib_delta_range_ms": [min(lib_deltas), max(lib_deltas)],
        "rmeta_delta_range_ms": [min(rmeta_deltas), max(rmeta_deltas)],
        "post_rmeta_delta_range_ms": [min(post_rmeta_deltas), max(post_rmeta_deltas)],
    }


def mode_profile(lib_text: str) -> dict[str, object]:
    LIB_RS.write_text(lib_text)
    return repeated_pairs()


def main() -> int:
    explicit = LIB_RS.read_text()
    star = re.sub(
        r"pub use standalone_runtime::\{.*?\n\};",
        "pub use standalone_runtime::*;",
        explicit,
        flags=re.S,
    )
    if star == explicit:
        raise SystemExit("explicit export block not found")

    try:
        explicit_mode = mode_profile(explicit)
        star_mode = mode_profile(star)
    finally:
        LIB_RS.write_text(explicit)

    result = {
        "rounds": ROUNDS,
        "explicit_mode": explicit_mode,
        "star_mode": star_mode,
        "result": "os_node_lib_variance_split_between_rmeta_and_post_rmeta_profiled",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
