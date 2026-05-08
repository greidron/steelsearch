#!/usr/bin/env python3
import json
from pathlib import Path
import re
import subprocess
import os
import time

ROOT = Path("/home/ubuntu/steelsearch")
TIMINGS_DIR = ROOT / "target/cargo-timings"
CHECK_CMD = [
    "cargo",
    "check",
    "--all-targets",
    "--timings",
    "-p",
    "os-node",
    "--features",
    "standalone-runtime",
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
    touch(ROOT / "crates/os-node/src/write_path_invariants.rs")
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    subprocess.run(CHECK_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))

    unlocked_rmeta_units = [
        {
            "name": unit["name"],
            "target": unit["target"],
            "unlocked_rmeta_units": unit.get("unlocked_rmeta_units", []),
        }
        for unit in unit_data
        if unit.get("unlocked_rmeta_units")
    ]

    result = {
        "unit_count": len(unit_data),
        "unlocked_rmeta_nonempty_count": len(unlocked_rmeta_units),
        "unlocked_rmeta_examples": unlocked_rmeta_units[:10],
        "result": "cargo_check_all_targets_graph_scanned_for_nonempty_unlocked_rmeta_units",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
