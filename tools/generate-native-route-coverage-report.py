#!/usr/bin/env python3
"""Generate a Steelsearch native-route coverage report from a coverage plan.

The report intentionally fails closed. OpenSearch-visible compatibility reports
can prove response parity, but they cannot prove fallback-free native execution.
To pass a case group, callers must provide native observations containing route
evidence such as phase descriptions and Steelsearch-only invariant booleans.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "tools" / "fixtures" / "native-route-coverage-plan.json"
DEFAULT_OUTPUT = ROOT / "target" / "opensearch-compare" / "native-route-coverage-report.json"


def load_optional_json(path: Path | None) -> Any | None:
    if path is None:
        return None
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"JSON file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from None


def load_json(path: Path) -> Any:
    value = load_optional_json(path)
    if value is None:
        raise SystemExit(f"JSON file not found: {path}")
    return value


def normalize_observations(raw: Any | None) -> dict[str, dict[str, Any]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SystemExit("observations root must be an object")

    if isinstance(raw.get("case_groups"), dict):
        groups = raw["case_groups"]
        return {str(name): value for name, value in groups.items() if isinstance(value, dict)}

    observations: dict[str, dict[str, Any]] = {}
    if isinstance(raw.get("observations"), list):
        for item in raw["observations"]:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("case_group")
            if isinstance(name, str):
                observations[name] = item
    return observations


def search_report_summary(report: Any | None) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "provided": False,
            "passed": None,
            "failed": None,
            "skipped": None,
            "case_count": 0,
        }
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    cases = report.get("cases") if isinstance(report.get("cases"), list) else []
    return {
        "provided": True,
        "passed": summary.get("passed"),
        "failed": summary.get("failed"),
        "skipped": summary.get("skipped"),
        "case_count": len(cases),
    }


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def check_required_phase_descriptions(requirements: dict[str, Any], observation: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    phases = string_list(observation.get("phase_descriptions"))

    for required in string_list(requirements.get("required_phase_descriptions")):
        if required not in phases:
            issues.append(f"missing required phase description: {required}")

    for required in string_list(requirements.get("required_phase_description_substrings")):
        if not any(required in phase for phase in phases):
            issues.append(f"missing required phase description substring: {required}")

    for forbidden in string_list(requirements.get("forbidden_phase_description_substrings")):
        if any(forbidden in phase for phase in phases):
            issues.append(f"forbidden phase description substring observed: {forbidden}")

    return issues


def check_boolean_requirements(requirements: dict[str, Any], observation: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    booleans = observation.get("invariants") if isinstance(observation.get("invariants"), dict) else observation
    for key, expected in requirements.items():
        if not key.startswith("requires_") or not isinstance(expected, bool) or not expected:
            continue
        if booleans.get(key) is not True:
            issues.append(f"missing true invariant: {key}")
    return issues


def evaluate_group(group: dict[str, Any], observation: dict[str, Any] | None) -> dict[str, Any]:
    name = group.get("name")
    requirements = group.get("steelsearch_native_requirements")
    if not isinstance(requirements, dict):
        requirements = {}

    if observation is None:
        return {
            "name": name,
            "status": "failed",
            "reason": "missing_native_route_evidence",
            "failure_families": string_list(group.get("failure_families")),
            "issues": ["no native observation was provided for this case group"],
        }

    issues = []
    issues.extend(check_required_phase_descriptions(requirements, observation))
    issues.extend(check_boolean_requirements(requirements, observation))

    return {
        "name": name,
        "status": "passed" if not issues else "failed",
        "reason": None if not issues else "native_route_requirements_not_met",
        "failure_families": string_list(group.get("failure_families")),
        "issues": issues,
        "observed_phase_descriptions": string_list(observation.get("phase_descriptions")),
    }


def build_report(plan: dict[str, Any], search_report: Any | None, observations_raw: Any | None) -> dict[str, Any]:
    observations = normalize_observations(observations_raw)
    groups = plan.get("case_groups") if isinstance(plan.get("case_groups"), list) else []
    case_results = [
        evaluate_group(group, observations.get(group.get("name")))
        for group in groups
        if isinstance(group, dict)
    ]
    passed = sum(1 for case in case_results if case["status"] == "passed")
    failed = sum(1 for case in case_results if case["status"] == "failed")
    missing_evidence = sum(1 for case in case_results if case.get("reason") == "missing_native_route_evidence")

    return {
        "schema_version": 1,
        "plan": plan.get("name"),
        "ok": failed == 0 and bool(case_results),
        "summary": {
            "case_groups": len(case_results),
            "passed": passed,
            "failed": failed,
            "missing_native_route_evidence": missing_evidence,
            "search_compat_report": search_report_summary(search_report),
        },
        "cases": case_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--search-compat-report", type=Path)
    parser.add_argument("--native-observations", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    plan = load_json(args.plan)
    if not isinstance(plan, dict):
        raise SystemExit("plan root must be an object")
    search_report = load_optional_json(args.search_compat_report)
    observations = load_optional_json(args.native_observations)
    report = build_report(plan, search_report, observations)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"native route coverage report: {args.output}")
    print(f"ok: {str(report['ok']).lower()}")
    print(
        "case_groups: {case_groups}, passed: {passed}, failed: {failed}, missing_native_route_evidence: {missing}".format(
            case_groups=report["summary"]["case_groups"],
            passed=report["summary"]["passed"],
            failed=report["summary"]["failed"],
            missing=report["summary"]["missing_native_route_evidence"],
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
