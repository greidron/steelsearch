#!/usr/bin/env python3
"""Validate required multi-node transport/admin report coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_PIT_CASES = {
    "node_a_open_pit",
    "node_b_search_node_a_pit",
    "node_b_close_node_a_pit",
    "node_b_search_node_a_pit_after_close",
    "node_a_list_pits_after_node_b_close",
}


def extract_path(value: Any, path: str) -> Any:
    current = value
    for segment in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="multi-node-transport-admin-report.json")
    parser.add_argument(
        "--require-remote-pit",
        action="store_true",
        help="require the remote REST PIT search/close transport cases to pass",
    )
    parser.add_argument(
        "--require-publication-validation-events",
        action="store_true",
        help="require coordination publication transcripts to include proposal/apply validation events",
    )
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"report not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON report {path}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"report must be a JSON object: {path}")
    return data


def case_statuses(report: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        name = case.get("name")
        status = case.get("status")
        if isinstance(name, str) and isinstance(status, str):
            statuses[name] = status
    return statuses


def cases_by_name(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        name = case.get("name")
        if isinstance(name, str):
            cases[name] = case
    return cases


def case_body(cases: dict[str, dict[str, Any]], name: str) -> Any:
    return extract_path(cases.get(name), "response.body")


def validate_remote_pit_semantics(report: dict[str, Any]) -> list[str]:
    cases = cases_by_name(report)
    errors: list[str] = []

    open_body = case_body(cases, "node_a_open_pit")
    pit_id = extract_path(open_body, "pit_id")
    if not isinstance(pit_id, str) or not pit_id:
        errors.append("node_a_open_pit did not return a non-empty pit_id")
    if extract_path(open_body, "_shards.failed") != 0:
        errors.append("node_a_open_pit did not report _shards.failed=0")

    search_body = case_body(cases, "node_b_search_node_a_pit")
    if extract_path(search_body, "hits.total.value") != 1:
        errors.append("node_b_search_node_a_pit did not return one hit")
    if extract_path(search_body, "hits.hits.0._id") != "doc-1":
        errors.append("node_b_search_node_a_pit did not return doc-1")
    if extract_path(search_body, "hits.hits.0._source.message") != "visible-through-pit":
        errors.append("node_b_search_node_a_pit did not return the PIT document source")
    if pit_id and extract_path(search_body, "pit_id") != pit_id:
        errors.append("node_b_search_node_a_pit returned a different pit_id")

    close_body = case_body(cases, "node_b_close_node_a_pit")
    if extract_path(close_body, "pits.0.successful") is not True:
        errors.append("node_b_close_node_a_pit did not close the remote PIT successfully")
    if pit_id and extract_path(close_body, "pits.0.pit_id") != pit_id:
        errors.append("node_b_close_node_a_pit closed a different pit_id")

    after_close_body = case_body(cases, "node_b_search_node_a_pit_after_close")
    if extract_path(after_close_body, "status") != 404:
        errors.append("node_b_search_node_a_pit_after_close did not return status=404")
    if extract_path(after_close_body, "error.type") != "search_phase_execution_exception":
        errors.append("node_b_search_node_a_pit_after_close did not return search_phase_execution_exception")

    list_body = case_body(cases, "node_a_list_pits_after_node_b_close")
    pits = extract_path(list_body, "pits")
    if pits != []:
        errors.append("node_a_list_pits_after_node_b_close did not return an empty pits list")

    return errors


def validation_event_key(event: Any) -> tuple[str, str, str] | None:
    if not isinstance(event, dict):
        return None
    phase = event.get("phase")
    step = event.get("step")
    status = event.get("status")
    if not all(isinstance(value, str) for value in (phase, step, status)):
        return None
    return phase, step, status


def validate_publication_validation_events(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    transcripts = extract_path(report, "coordination.publication_transport_transcripts")
    if not isinstance(transcripts, list) or not transcripts:
        return ["coordination publication transport transcripts are missing"]

    required_events = {
        ("proposal", "connect", "passed"),
        ("proposal", "action_frame", "passed"),
        ("proposal", "publication_semantics", "passed"),
        ("apply", "connect", "passed"),
        ("apply", "action_frame", "passed"),
        ("apply", "publication_semantics", "passed"),
    }
    observed_events: set[tuple[str, str, str]] = set()
    validation_event_count = 0
    for index, transcript in enumerate(transcripts):
        if not isinstance(transcript, dict):
            errors.append(f"publication transcript {index} is not an object")
            continue
        events = transcript.get("validation_events")
        if not isinstance(events, list) or not events:
            errors.append(f"publication transcript {index} has no validation_events")
            continue
        for event in events:
            key = validation_event_key(event)
            if key is None:
                errors.append(f"publication transcript {index} has malformed validation event")
                continue
            node_id = event.get("node_id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"publication transcript {index} validation event is missing node_id")
            if key[2] == "failed":
                reason = event.get("reason")
                if not isinstance(reason, str) or not reason:
                    errors.append(
                        f"publication transcript {index} failed validation event is missing reason"
                    )
            observed_events.add(key)
            validation_event_count += 1

    missing = sorted(required_events - observed_events)
    if missing:
        errors.append(f"missing publication validation event kinds: {missing}")
    if validation_event_count < len(required_events):
        errors.append("publication validation event count is too small")
    return errors


def main() -> int:
    args = parse_args()
    report = load_report(Path(args.report))
    statuses = case_statuses(report)
    errors: list[str] = []

    summary = report.get("summary", {})
    if not isinstance(summary, dict) or summary.get("failed") != 0:
        errors.append("report summary must have failed=0")

    for case in report.get("cases", []):
        if isinstance(case, dict) and case.get("status") != "passed":
            errors.append(f"case {case.get('name')!r} did not pass")

    for check in report.get("post_checks", []):
        if isinstance(check, dict) and check.get("status") != "passed":
            errors.append(f"post_check {check.get('name')!r} did not pass")

    missing_remote_pit_cases: list[str] = []
    failed_remote_pit_cases: list[str] = []
    if args.require_remote_pit:
        missing_remote_pit_cases = sorted(REQUIRED_PIT_CASES - statuses.keys())
        failed_remote_pit_cases = sorted(
            case for case in REQUIRED_PIT_CASES if statuses.get(case) != "passed"
        )
        if missing_remote_pit_cases:
            errors.append(f"missing remote PIT cases: {missing_remote_pit_cases}")
        if failed_remote_pit_cases:
            errors.append(f"remote PIT cases not passed: {failed_remote_pit_cases}")
        if not missing_remote_pit_cases and not failed_remote_pit_cases:
            errors.extend(validate_remote_pit_semantics(report))

    if args.require_publication_validation_events:
        errors.extend(validate_publication_validation_events(report))

    payload = {
        "summary": {
            "passed": not errors,
            "failed_count": len(errors),
            "remote_pit_required": bool(args.require_remote_pit),
            "publication_validation_events_required": bool(
                args.require_publication_validation_events
            ),
            "remote_pit_case_count": len(REQUIRED_PIT_CASES & statuses.keys()),
            "remote_pit_cases": sorted(REQUIRED_PIT_CASES & statuses.keys()),
        },
        "errors": errors,
        "missing_remote_pit_cases": missing_remote_pit_cases,
        "failed_remote_pit_cases": failed_remote_pit_cases,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
