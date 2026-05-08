#!/usr/bin/env python3
import json
import sys


EXPECTED_POINTS = {
    "before-file-copy",
    "during-file-copy",
    "during-translog-replay",
}
EXPECTED_OUTCOMES = {
    "resumed",
    "full-restart",
    "corrupted",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-peer-recovery-interruption-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "peer-recovery-interruption":
        fail("unexpected profile")
    if data.get("primary_node") != "java":
        fail("primary_node must be java")
    if data.get("replica_node") != "rust":
        fail("replica_node must be rust")

    if set(data.get("interruption_points", [])) != EXPECTED_POINTS:
        fail("interruption_points mismatch")
    if set(data.get("recovery_outcome_modes", [])) != EXPECTED_OUTCOMES:
        fail("recovery_outcome_modes mismatch")
    if data.get("recovery_outcome") not in EXPECTED_OUTCOMES:
        fail("recovery_outcome must be one of recovery_outcome_modes")
    if data.get("cleanup_failure_class") != "stale_artifact_leftover":
        fail("cleanup_failure_class mismatch")

    print(json.dumps({
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
