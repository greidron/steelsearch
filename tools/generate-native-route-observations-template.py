#!/usr/bin/env python3
"""Generate a Steelsearch native-route observations template from the plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "tools" / "fixtures" / "native-route-coverage-plan.json"
DEFAULT_OUTPUT = ROOT / "target" / "opensearch-compare" / "native-route-observations.template.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"plan file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from None


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def template_for_group(group: dict[str, Any]) -> dict[str, Any]:
    requirements = group.get("steelsearch_native_requirements")
    if not isinstance(requirements, dict):
        requirements = {}

    phase_descriptions = []
    phase_descriptions.extend(string_list(requirements.get("required_phase_descriptions")))
    phase_descriptions.extend(
        f"TODO: include phase containing substring: {item}"
        for item in string_list(requirements.get("required_phase_description_substrings"))
    )
    if not phase_descriptions:
        phase_descriptions.append("TODO: capture Steelsearch SearchPhase.description values for this group")

    invariants = {
        key: False
        for key, value in requirements.items()
        if key.startswith("requires_") and value is True
    }

    observation = {
        "status": "TODO",
        "phase_descriptions": phase_descriptions,
        "invariants": invariants,
        "source_cases": [],
        "notes": [
            "Replace TODO/false values with observed Steelsearch native route evidence.",
            "Do not mark this group complete from OpenSearch-visible parity alone.",
        ],
    }
    forbidden = string_list(requirements.get("forbidden_phase_description_substrings"))
    if forbidden:
        observation["forbidden_phase_description_substrings"] = forbidden
    return observation


def build_template(plan: dict[str, Any]) -> dict[str, Any]:
    groups = plan.get("case_groups")
    if not isinstance(groups, list):
        raise SystemExit("plan.case_groups must be a list")

    case_groups = {}
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str):
            continue
        case_groups[group["name"]] = template_for_group(group)

    return {
        "schema_version": 1,
        "plan": plan.get("name"),
        "description": "Template only. Fill with observed Steelsearch native route evidence before using as readiness input.",
        "case_groups": case_groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    plan = load_json(args.plan)
    if not isinstance(plan, dict):
        raise SystemExit("plan root must be an object")
    template = build_template(plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n")
    print(f"native route observations template: {args.output}")
    print(f"case_groups: {len(template['case_groups'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
