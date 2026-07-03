#!/usr/bin/env python3
"""Run every repository promotion gate checker as one fail-closed suite."""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("root-identity", ["tools/check-root-identity-promotion-gate.py"]),
    ("index-metadata", ["tools/check-index-metadata-promotion-gate.py"]),
    ("document-write", ["tools/check-document-write-promotion-gate.py"]),
    ("bulk", ["tools/check-bulk-promotion-gate.py"]),
    ("cluster-admin", ["tools/check-cluster-admin-promotion-gate.py"]),
    ("search", ["tools/check-search-promotion-gate.py"]),
    ("snapshot", ["tools/check-snapshot-promotion-gate.py"]),
    ("vector", ["tools/check-vector-promotion-gate.py"]),
    ("knn-plugin", ["tools/check-knn-plugin-promotion-gate.py"]),
    ("ml", ["tools/check-ml-promotion-gate.py"]),
    ("peer-node", ["tools/check-peer-node-promotion-gate.py"]),
    (
        "external-interop",
        [
            "tools/check-external-interop-promotion-gate.py",
            "tools/fixtures/external-interop-promotion-gate.json",
        ],
    ),
    (
        "migration",
        [
            "tools/check-migration-promotion-gate.py",
            "tools/fixtures/migration-promotion-gate.json",
        ],
    ),
    (
        "harness",
        [
            "tools/check-harness-promotion-gate.py",
            "tools/fixtures/harness-promotion-gate.json",
        ],
    ),
]


def tail(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def run_check(name: str, command: list[str]) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, *command],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result: dict[str, object] = {
        "name": name,
        "command": " ".join(command),
        "status": "ok" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
    }
    if proc.returncode != 0:
        result["stdout_tail"] = tail(proc.stdout)
        result["stderr_tail"] = tail(proc.stderr)
    return result


def main() -> int:
    results = [run_check(name, command) for name, command in CHECKS]
    failed = [result for result in results if result["status"] != "ok"]
    summary = {
        "status": "failed" if failed else "ok",
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "checks": results,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
