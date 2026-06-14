#!/usr/bin/env python3
"""Extract Steelsearch native-route observations from a search compat report.

The extractor is conservative. It only records observations for cases that
explicitly declare a native-route group, and it only records phase descriptions
that are present in the Steelsearch response profile section.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "tools" / "fixtures" / "native-route-coverage-plan.json"
DEFAULT_REPORT = ROOT / "target" / "opensearch-compare" / "search-compat-report.json"
DEFAULT_OUTPUT = ROOT / "target" / "opensearch-compare" / "native-route-observations.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from None


def planned_group_names(plan: Any) -> set[str]:
    if not isinstance(plan, dict) or not isinstance(plan.get("case_groups"), list):
        raise SystemExit("plan.case_groups must be a list")
    names = {
        group.get("name")
        for group in plan["case_groups"]
        if isinstance(group, dict) and isinstance(group.get("name"), str)
    }
    return {name for name in names if isinstance(name, str)}


def case_native_groups(case: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in ["native_route_group", "native_route_groups"]:
        if key in case:
            values.append(case[key])
    metadata = case.get("metadata")
    if isinstance(metadata, dict):
        for key in ["native_route_group", "native_route_groups"]:
            if key in metadata:
                values.append(metadata[key])
    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, list):
            result.extend(item for item in value if isinstance(item, str))
    return result


def steelsearch_body(case: dict[str, Any]) -> Any:
    targets = case.get("targets")
    if not isinstance(targets, dict):
        return None
    steelsearch = targets.get("steelsearch")
    if not isinstance(steelsearch, dict):
        return None
    raw = steelsearch.get("raw_response")
    if isinstance(raw, dict) and "body" in raw:
        return raw["body"]
    normalized = steelsearch.get("normalized_response")
    if isinstance(normalized, dict) and "body" in normalized:
        return normalized["body"]
    return None


def collect_descriptions(value: Any) -> list[str]:
    descriptions: list[str] = []
    if isinstance(value, dict):
        description = value.get("description")
        if isinstance(description, str):
            descriptions.append(description)
        for child in value.values():
            descriptions.extend(collect_descriptions(child))
    elif isinstance(value, list):
        for item in value:
            descriptions.extend(collect_descriptions(item))
    return descriptions


def collect_native_invariants(value: Any) -> dict[str, bool]:
    invariants: dict[str, bool] = {}
    if isinstance(value, dict):
        native_invariants = value.get("steelsearch_native_invariants")
        if isinstance(native_invariants, dict):
            for key, item in native_invariants.items():
                if isinstance(key, str) and key.startswith("requires_") and item is True:
                    invariants[key] = True
        for child in value.values():
            invariants.update(collect_native_invariants(child))
    elif isinstance(value, list):
        for item in value:
            invariants.update(collect_native_invariants(item))
    return invariants


def profile_descriptions(case: dict[str, Any]) -> list[str]:
    body = steelsearch_body(case)
    if not isinstance(body, dict):
        return []
    profile = body.get("profile")
    if profile is None:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for description in collect_descriptions(profile):
        if description not in seen:
            seen.add(description)
            result.append(description)
    return result


def profile_invariants(case: dict[str, Any]) -> dict[str, bool]:
    body = steelsearch_body(case)
    if not isinstance(body, dict):
        return {}
    profile = body.get("profile")
    if profile is None:
        return {}
    return collect_native_invariants(profile)


def extract(plan: Any, report: Any) -> dict[str, Any]:
    groups = planned_group_names(plan)
    observations = {
        name: {
            "phase_descriptions": [],
            "invariants": {},
            "source_cases": [],
            "notes": ["No matching profiled search compatibility case was observed."],
        }
        for name in sorted(groups)
    }
    unknown_groups: set[str] = set()
    cases = report.get("cases") if isinstance(report, dict) else None
    if not isinstance(cases, list):
        raise SystemExit("search compat report must contain a cases list")

    for case in cases:
        if not isinstance(case, dict):
            continue
        descriptions = profile_descriptions(case)
        invariants = profile_invariants(case)
        native_groups = case_native_groups(case)
        for group in native_groups:
            if group not in groups:
                unknown_groups.add(group)
                continue
            observation = observations[group]
            if descriptions:
                existing = set(observation["phase_descriptions"])
                for description in descriptions:
                    if description not in existing:
                        observation["phase_descriptions"].append(description)
                        existing.add(description)
                observation["notes"] = []
            if invariants:
                observation["invariants"].update(invariants)
                observation["notes"] = []
            observation["source_cases"].append(case.get("name"))

    return {
        "schema_version": 1,
        "source_report": "search-compat-report",
        "case_groups": observations,
        "unknown_native_route_groups": sorted(unknown_groups),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--search-compat-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    observations = extract(load_json(args.plan), load_json(args.search_compat_report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(observations, indent=2, sort_keys=True) + "\n")
    populated = sum(
        1
        for observation in observations["case_groups"].values()
        if observation.get("phase_descriptions")
    )
    print(f"native route observations: {args.output}")
    print(f"case_groups: {len(observations['case_groups'])}, populated: {populated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
