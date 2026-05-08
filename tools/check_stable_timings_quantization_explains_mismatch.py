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
ROUNDS = 5
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
    post_rmeta_ms = round(duration_ms - rmeta_ms, 2)
    return {
        "duration_ms": duration_ms,
        "rmeta_ms": rmeta_ms,
        "post_rmeta_ms": post_rmeta_ms,
    }


def is_quantized_10ms(value: float) -> bool:
    return abs(value % 10.0) < 1e-9 or abs((value % 10.0) - 10.0) < 1e-9


def profile_mode(lib_text: str) -> dict[str, object]:
    LIB_RS.write_text(lib_text)
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    samples = []
    for _ in range(ROUNDS):
        touch(LEAF)
        samples.append(run_timed_build())
    duration_values = [sample["duration_ms"] for sample in samples]
    rmeta_values = [sample["rmeta_ms"] for sample in samples]
    post_values = [sample["post_rmeta_ms"] for sample in samples]
    return {
        "samples": samples,
        "duration_values_ms": duration_values,
        "rmeta_values_ms": rmeta_values,
        "post_rmeta_values_ms": post_values,
        "duration_all_quantized_10ms": all(is_quantized_10ms(v) for v in duration_values),
        "rmeta_all_quantized_10ms": all(is_quantized_10ms(v) for v in rmeta_values),
        "post_rmeta_all_quantized_10ms": all(is_quantized_10ms(v) for v in post_values),
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
        explicit_mode = profile_mode(explicit)
        star_mode = profile_mode(star)
    finally:
        LIB_RS.write_text(explicit)

    result = {
        "rounds": ROUNDS,
        "explicit_mode": explicit_mode,
        "star_mode": star_mode,
        "result": "stable_cargo_timings_quantization_profiled_for_os_node_lib_duration_rmeta_post_rmeta",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
