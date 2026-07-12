#!/usr/bin/env python3
"""Generate release packaging evidence for Steelsearch."""

from __future__ import annotations

import argparse
import json
import platform
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback is not expected here.
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
BUILD_COMMAND = (
    "cargo",
    "build",
    "--release",
    "-p",
    "os-node",
    "--features",
    "standalone-runtime",
    "--bin",
    "steelsearch",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "target/release-packaging/packaging-report.json")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    report = generate_report(args.root.resolve(), skip_build=args.skip_build)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["summary"]["error_count"] == 0 else 1


def generate_report(root: Path, *, skip_build: bool) -> dict[str, Any]:
    blockers: list[str] = []
    started_at = int(time.time())
    build = run_build(root, skip_build=skip_build)
    if build["returncode"] != 0:
        blockers.append(f"release build failed: returncode={build['returncode']}")

    cargo = inspect_cargo_package(root)
    blockers.extend(cargo["blockers"])
    dockerfile = inspect_dockerfile(root)
    blockers.extend(dockerfile["blockers"])
    binary = inspect_binary(root / "target/release/steelsearch")
    blockers.extend(binary["blockers"])

    return {
        "ready": not blockers,
        "passed": not blockers,
        "blockers": blockers,
        "summary": {
            "passed": not blockers,
            "error_count": len(blockers),
            "build_returncode": build["returncode"],
            "binary_present": binary["present"],
            "binary_executable": binary["executable"],
            "binary_size_bytes": binary["size_bytes"],
        },
        "metadata": {
            "generated_at_epoch_seconds": started_at,
            "host_os": platform.system().lower(),
            "host_machine": platform.machine(),
            "root": str(root),
        },
        "build": build,
        "cargo_package": cargo,
        "dockerfile": dockerfile,
        "binary": binary,
    }


def run_build(root: Path, *, skip_build: bool) -> dict[str, Any]:
    command = list(BUILD_COMMAND)
    if skip_build:
        return {"command": command, "skipped": True, "returncode": 0, "stderr_tail": ""}
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": command,
        "skipped": False,
        "returncode": completed.returncode,
        "stderr_tail": completed.stderr[-4000:],
    }


def inspect_cargo_package(root: Path) -> dict[str, Any]:
    path = root / "crates/os-node/Cargo.toml"
    blockers: list[str] = []
    payload, parse_error = load_toml(path)
    if parse_error:
        return {"path": str(path), "blockers": [parse_error]}

    package = payload.get("package", {})
    features = payload.get("features", {})
    bins = payload.get("bin", [])
    if package.get("name") != "os-node":
        blockers.append("os-node package name mismatch")
    package_version = package.get("version")
    if not isinstance(package_version, str) or not package_version.strip():
        blockers.append("os-node package version is missing")
        package_version = None
    workspace_versions = inspect_workspace_package_versions(root, package_version)
    blockers.extend(workspace_versions["blockers"])
    if "standalone-runtime" not in features:
        blockers.append("standalone-runtime feature is missing")
    steelsearch_bins = [item for item in bins if isinstance(item, dict) and item.get("name") == "steelsearch"]
    if not steelsearch_bins:
        blockers.append("steelsearch bin target is missing")
    elif "standalone-runtime" not in steelsearch_bins[0].get("required-features", []):
        blockers.append("steelsearch bin does not require standalone-runtime")
    return {
        "path": str(path),
        "package_name": package.get("name"),
        "package_version": package_version,
        "workspace_package_versions": workspace_versions,
        "has_standalone_runtime_feature": "standalone-runtime" in features,
        "has_steelsearch_bin": bool(steelsearch_bins),
        "blockers": blockers,
    }


def load_toml(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, f"{path} is missing"
    try:
        if tomllib is None:
            raise RuntimeError("tomllib is unavailable")
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - evidence report records blocker
        return {}, f"{path} parse failed: {error}"
    if not isinstance(payload, dict):
        return {}, f"{path} payload is not a TOML table"
    return payload, None


def inspect_workspace_package_versions(root: Path, expected_version: str | None) -> dict[str, Any]:
    crates_dir = root / "crates"
    blockers: list[str] = []
    versions: dict[str, str | None] = {}
    if not crates_dir.is_dir():
        return {
            "expected_version": expected_version,
            "versions": versions,
            "blockers": ["crates directory is missing"],
        }
    for manifest in sorted(crates_dir.glob("*/Cargo.toml")):
        payload, parse_error = load_toml(manifest)
        crate_name = manifest.parent.name
        if parse_error:
            blockers.append(parse_error)
            versions[crate_name] = None
            continue
        package = payload.get("package")
        version = package.get("version") if isinstance(package, dict) else None
        versions[crate_name] = version if isinstance(version, str) else None
        if expected_version and version != expected_version:
            blockers.append(
                f"{manifest.relative_to(root)} package version mismatch: {version}"
            )
    return {
        "expected_version": expected_version,
        "versions": versions,
        "blockers": blockers,
    }


def inspect_dockerfile(root: Path) -> dict[str, Any]:
    path = root / "Dockerfile"
    blockers: list[str] = []
    if not path.is_file():
        return {"path": str(path), "blockers": ["Dockerfile is missing"]}
    text = path.read_text(encoding="utf-8")
    required_snippets = (
        "cargo build --release",
        "--features standalone-runtime",
        "--bin steelsearch",
        "/workspace/target/release/steelsearch",
        "/usr/local/bin/steelsearch",
        "USER steelsearch",
        "EXPOSE 9200 9300",
    )
    for snippet in required_snippets:
        if snippet not in text:
            blockers.append(f"Dockerfile is missing snippet: {snippet}")
    return {
        "path": str(path),
        "required_snippets": list(required_snippets),
        "blockers": blockers,
    }


def inspect_binary(path: Path) -> dict[str, Any]:
    blockers: list[str] = []
    if not path.is_file():
        return {
            "path": str(path),
            "present": False,
            "executable": False,
            "size_bytes": 0,
            "blockers": ["release steelsearch binary is missing"],
        }
    mode = path.stat().st_mode
    executable = bool(mode & stat.S_IXUSR)
    size = path.stat().st_size
    if not executable:
        blockers.append("release steelsearch binary is not executable")
    if size <= 0:
        blockers.append("release steelsearch binary is empty")
    return {
        "path": str(path),
        "present": True,
        "executable": executable,
        "size_bytes": size,
        "mtime_epoch_seconds": path.stat().st_mtime,
        "blockers": blockers,
    }


if __name__ == "__main__":
    sys.exit(main())
