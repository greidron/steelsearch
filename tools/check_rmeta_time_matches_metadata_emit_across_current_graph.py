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
    "-vv",
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
    "-vv",
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
EMIT_RE = re.compile(r"--emit=([^\s]+)")


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def newest_timing_html(before: set[Path]) -> Path:
    after = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def normalize_target(target: str) -> str:
    return target.strip()


def parse_profile(cmd: list[str]) -> dict[str, object]:
    is_check = cmd[1] == "check"
    subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    cp = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))

    emits_by_target = {}
    for line in cp.stdout.splitlines():
        if "rustc" not in line or "CARGO_PKG_NAME=os-node" not in line:
            continue
        emit_match = EMIT_RE.search(line)
        if not emit_match:
            continue
        emits = emit_match.group(1).split(",")
        if "CARGO_BIN_NAME=steelsearch" in line:
            emits_by_target['bin "steelsearch"' if not is_check else 'bin "steelsearch" (check)'] = emits
        elif "--crate-type lib" in line:
            emits_by_target["" if not is_check else "lib (check)"] = emits

    units = []
    for unit in unit_data:
        target = normalize_target(unit["target"])
        if unit["name"] != "os-node":
            continue
        emits = emits_by_target.get(target, [])
        units.append(
            {
                "target": target,
                "rmeta_time_nonnull": unit.get("rmeta_time") is not None,
                "emit": emits,
                "emit_includes_metadata": "metadata" in emits,
                "equivalent": (unit.get("rmeta_time") is not None) == ("metadata" in emits),
            }
        )
    return {"units": units}


def main() -> int:
    build_profile = parse_profile(BUILD_CMD)
    check_profile = parse_profile(CHECK_CMD)
    all_units = build_profile["units"] + check_profile["units"]
    result = {
        "build_profile": build_profile,
        "check_profile": check_profile,
        "all_units_equivalent": all(unit["equivalent"] for unit in all_units),
        "result": "rmeta_time_nonnull_vs_metadata_emit_equivalence_profiled_across_current_build_check_graph",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
