#!/usr/bin/env python3
"""Validate Steelsearch native-route observations for readiness reporting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "tools" / "fixtures" / "native-route-coverage-plan.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from None


def observations_by_group(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise SystemExit("observations root must be an object")
    if isinstance(raw.get("case_groups"), dict):
        return {
            str(name): value
            for name, value in raw["case_groups"].items()
            if isinstance(value, dict)
        }
    if isinstance(raw.get("observations"), list):
        result = {}
        for item in raw["observations"]:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("case_group")
            if isinstance(name, str):
                result[name] = item
        return result
    return {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def validate(plan: Any, raw_observations: Any) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise SystemExit("plan root must be an object")
    groups = plan.get("case_groups")
    if not isinstance(groups, list):
        raise SystemExit("plan.case_groups must be a list")
    observations = observations_by_group(raw_observations)

    cases = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str):
            continue
        name = group["name"]
        observation = observations.get(name)
        issues = []
        if observation is None:
            issues.append("missing observation")
            cases.append({"name": name, "ok": False, "issues": issues})
            continue
        phase_descriptions = string_list(observation.get("phase_descriptions"))
        if not phase_descriptions:
            issues.append("phase_descriptions must contain at least one string")
        invariants = observation.get("invariants")
        if invariants is not None and not isinstance(invariants, dict):
            issues.append("invariants must be an object when present")
        for key, value in (invariants or {}).items() if isinstance(invariants, dict) else []:
            if key.startswith("requires_") and not isinstance(value, bool):
                issues.append(f"invariant {key} must be boolean")
        cases.append({
            "name": name,
            "ok": not issues,
            "issues": issues,
            "phase_description_count": len(phase_descriptions),
            "invariant_count": len(invariants) if isinstance(invariants, dict) else 0,
        })

    known_names = {group.get("name") for group in groups if isinstance(group, dict)}
    unknown = sorted(name for name in observations if name not in known_names)
    passed = sum(1 for case in cases if case["ok"])
    failed = len(cases) - passed
    return {
        "schema_version": 1,
        "ok": failed == 0 and not unknown,
        "summary": {
            "case_groups": len(cases),
            "passed": passed,
            "failed": failed,
            "unknown_observations": len(unknown),
        },
        "cases": cases,
        "unknown_observations": unknown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate(load_json(args.plan), load_json(args.observations))
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    else:
        print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
