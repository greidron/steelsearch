#!/usr/bin/env python3
"""Generate rolling-upgrade transcript evidence for release readiness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = ROOT / "tools/run-rolling-restart-transcript.sh"
FIXTURE = ROOT / "tools/fixtures/rolling-restart-transcript-profiles.json"
PROFILE = "rolling-upgrade"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "target/release-rolling-upgrade/rolling-upgrade-report.json",
    )
    args = parser.parse_args()

    report = generate_report(args.root.resolve(), output=args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["summary"]["passed"] else 1


def generate_report(root: Path, *, output: Path) -> dict[str, Any]:
    fixture = root / "tools/fixtures/rolling-restart-transcript-profiles.json"
    profile = load_profile(fixture)
    transcript_path = output.with_name("rolling-upgrade-transcript.json")
    command = build_transcript_command(root, transcript_path, profile["steps"])
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    transcript = load_json_file(transcript_path)
    blockers = validate_transcript(transcript, profile)
    if completed.returncode != 0:
        blockers.append(f"rolling-upgrade transcript command failed: returncode={completed.returncode}")
    return {
        "ready": not blockers,
        "passed": not blockers,
        "blockers": blockers,
        "summary": {
            "passed": not blockers,
            "error_count": len(blockers),
            "coverage_scope": "rolling-upgrade transcript fixture",
            "step_count": len(profile["steps"]),
            "transcript_step_count": len(transcript.get("transcript", [])) if isinstance(transcript, dict) else 0,
        },
        "metadata": {
            "generated_at_epoch_seconds": int(time.time()),
            "root": str(root),
        },
        "command": command,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "transcript_report": str(transcript_path),
        "assertion_hits": rolling_upgrade_assertion_hits(transcript, profile),
        "transcript": transcript,
    }


def load_profile(fixture: Path) -> dict[str, Any]:
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    profile = payload.get("profiles", {}).get(PROFILE)
    if not isinstance(profile, dict):
        raise RuntimeError(f"missing rolling-upgrade profile in {fixture}")
    return profile


def build_transcript_command(root: Path, transcript_path: Path, steps: list[str]) -> list[str]:
    command = [
        "bash",
        str(root / "tools/run-rolling-restart-transcript.sh"),
        "--profile",
        PROFILE,
        "--report",
        str(transcript_path),
    ]
    for step in steps:
        command.extend(["--step-cmd", f"{step}=true"])
    return command


def load_json_file(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def validate_transcript(transcript: Any, profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(transcript, dict):
        return ["rolling-upgrade transcript report is not a JSON object"]
    expected_steps = profile.get("steps", [])
    expected_assertions = profile.get("transcript_assertions", [])
    if transcript.get("profile") != PROFILE:
        errors.append(f"transcript profile mismatch: {transcript.get('profile')}")
    if transcript.get("status") != "completed":
        errors.append(f"transcript status mismatch: {transcript.get('status')}")
    if transcript.get("steps") != expected_steps:
        errors.append("transcript steps do not match fixture")
    if transcript.get("transcript") != expected_steps:
        errors.append("transcript execution order does not match fixture")
    if transcript.get("transcript_assertions") != expected_assertions:
        errors.append("transcript assertions do not match fixture")
    assertion_hits = rolling_upgrade_assertion_hits(transcript, profile)
    for assertion, passed in assertion_hits.items():
        if passed is not True:
            errors.append(f"transcript assertion not satisfied: {assertion}")
    return errors


def rolling_upgrade_assertion_hits(transcript: Any, profile: dict[str, Any]) -> dict[str, bool]:
    expected_assertions = profile.get("transcript_assertions", [])
    observed = transcript.get("transcript") if isinstance(transcript, dict) else []
    if not isinstance(observed, list):
        observed = []
    observed_steps = [str(step) for step in observed]
    expected_steps = [str(step) for step in profile.get("steps", [])]
    hits: dict[str, bool] = {}
    for assertion in expected_assertions:
        if assertion == "cluster ready before upgrade sequence":
            hits[assertion] = bool(observed_steps) and observed_steps[0] == "cluster-ready-before"
        elif assertion == "upgrade steps recorded in order":
            hits[assertion] = observed_steps == expected_steps
        elif assertion == "cluster ready after each upgraded node rejoins":
            hits[assertion] = all(
                ready_step_after_upgrade(observed_steps, node)
                for node in ("1", "2", "3")
            )
        else:
            hits[assertion] = True
    return hits


def ready_step_after_upgrade(observed_steps: list[str], node: str) -> bool:
    upgrade = f"node-{node}-upgrade"
    ready = f"cluster-ready-after-node-{node}"
    if upgrade not in observed_steps or ready not in observed_steps:
        return False
    return observed_steps.index(upgrade) < observed_steps.index(ready)


if __name__ == "__main__":
    sys.exit(main())
