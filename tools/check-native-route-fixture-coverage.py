#!/usr/bin/env python3
"""Check that a search fixture declares cases for every native-route group."""

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


def planned_groups(plan: Any) -> set[str]:
    if not isinstance(plan, dict) or not isinstance(plan.get("case_groups"), list):
        raise SystemExit("plan.case_groups must be a list")
    return {
        group["name"]
        for group in plan["case_groups"]
        if isinstance(group, dict) and isinstance(group.get("name"), str)
    }


def fixture_cases(fixture: Any) -> list[dict[str, Any]]:
    if not isinstance(fixture, dict):
        raise SystemExit("fixture root must be an object")
    cases: list[dict[str, Any]] = []
    for key in ["cases", "requests"]:
        value = fixture.get(key)
        if isinstance(value, list):
            cases.extend(item for item in value if isinstance(item, dict))
    return cases


def fixture_indices(fixture: Any) -> set[str]:
    if not isinstance(fixture, dict) or not isinstance(fixture.get("indices"), list):
        return set()
    return {
        index["name"]
        for index in fixture["indices"]
        if isinstance(index, dict) and isinstance(index.get("name"), str)
    }


def path_search_indices(path: Any) -> list[str]:
    if not isinstance(path, str):
        return []
    clean = path.split("?", 1)[0]
    if not clean.endswith("/_search"):
        return []
    prefix = clean[: -len("/_search")].strip("/")
    if not prefix:
        return []
    return [part for part in prefix.split(",") if part and "*" not in part]


def case_groups(case: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in ["native_route_group", "native_route_groups"]:
        if key in case:
            values.append(case[key])
    metadata = case.get("metadata")
    if isinstance(metadata, dict):
        for key in ["native_route_group", "native_route_groups"]:
            if key in metadata:
                values.append(metadata[key])

    groups: list[str] = []
    for value in values:
        if isinstance(value, str):
            groups.append(value)
        elif isinstance(value, list):
            groups.extend(item for item in value if isinstance(item, str))
    return groups


def case_requests_profile(case: dict[str, Any]) -> bool:
    body = case.get("body")
    if isinstance(body, dict) and body.get("profile") is True:
        return True
    for step in case.get("steps", []) if isinstance(case.get("steps"), list) else []:
        if isinstance(step, dict) and isinstance(step.get("body"), dict) and step["body"].get("profile") is True:
            return True
    return False


def check(plan: Any, fixture: Any) -> dict[str, Any]:
    expected = planned_groups(plan)
    cases = fixture_cases(fixture)
    indices = fixture_indices(fixture)
    covered: dict[str, list[str]] = {name: [] for name in expected}
    unprofiled: list[dict[str, str]] = []
    missing_indices: list[dict[str, str]] = []
    unknown: dict[str, list[str]] = {}

    for case in cases:
        name = str(case.get("name") or "<unnamed>")
        for index in path_search_indices(case.get("path")):
            if index not in indices:
                missing_indices.append({"case": name, "index": index})
        groups = case_groups(case)
        for group in groups:
            if group in expected:
                covered[group].append(name)
                if not case_requests_profile(case):
                    unprofiled.append({"case": name, "native_route_group": group})
            else:
                unknown.setdefault(group, []).append(name)

    missing = sorted(group for group, names in covered.items() if not names)
    return {
        "schema_version": 1,
        "ok": not missing and not unknown and not unprofiled and not missing_indices,
        "summary": {
            "planned_groups": len(expected),
            "fixture_cases": len(cases),
            "fixture_indices": len(indices),
            "covered_groups": len(expected) - len(missing),
            "missing_groups": len(missing),
            "unknown_groups": len(unknown),
            "unprofiled_native_cases": len(unprofiled),
            "missing_referenced_indices": len(missing_indices),
        },
        "missing_groups": missing,
        "unknown_groups": unknown,
        "unprofiled_native_cases": unprofiled,
        "missing_referenced_indices": missing_indices,
        "covered_groups": {group: names for group, names in sorted(covered.items()) if names},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = check(load_json(args.plan), load_json(args.fixture))
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    else:
        print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
