#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LIB_RS = ROOT / "crates/os-node/src/lib.rs"
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


def load_unit_profile(html: Path) -> dict[str, object]:
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))
    os_node_lib = next(unit for unit in unit_data if unit["name"] == "os-node" and unit["target"] == "")
    steelsearch_bin = next(
        (unit for unit in unit_data if unit["name"] == "steelsearch"),
        None,
    )
    result = {
        "os_node_lib_duration_s": os_node_lib["duration"],
        "os_node_lib_rmeta_s": os_node_lib["rmeta_time"],
        "os_node_lib_post_rmeta_s": round(os_node_lib["duration"] - os_node_lib["rmeta_time"], 3),
    }
    if steelsearch_bin is not None:
        result["steelsearch_bin_duration_s"] = steelsearch_bin["duration"]
        result["steelsearch_bin_rmeta_s"] = steelsearch_bin["rmeta_time"]
        result["steelsearch_bin_post_rmeta_s"] = round(
            steelsearch_bin["duration"] - steelsearch_bin["rmeta_time"], 3
        )
    return result


def timed_incremental_build() -> dict[str, object]:
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return load_unit_profile(newest_timing_html(before))


def mode_profile(lib_text: str) -> dict[str, object]:
    LIB_RS.write_text(lib_text)
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    first = timed_incremental_build()
    touch(LEAF)
    second = timed_incremental_build()
    return {
        "first_incremental": first,
        "second_incremental": second,
        "delta_second_minus_first_ms": {
            key.replace("_s", "_ms"): round((second[key] - first[key]) * 1000, 2)
            for key in first.keys()
            if key in second
        },
    }


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
        explicit_profile = mode_profile(explicit)
        star_profile = mode_profile(star)
    finally:
        LIB_RS.write_text(explicit)

    result = {
        "explicit_mode": explicit_profile,
        "star_mode": star_profile,
        "result": "second_run_advantage_subphase_profiled_via_stable_cargo_timings",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
