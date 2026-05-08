#!/usr/bin/env python3
import json
import sys


EXPECTED_FIXTURES = {
    "java-data-node-scope-matrix.json",
    "java-mixed-cluster-binary-profiles.json",
}

EXPECTED_PROFILES = {
    "java-primary-rust-replica",
    "rust-primary-java-replica",
    "java-driven-rolling-restart",
    "peer-recovery-interruption",
    "segment-compatibility-verify",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-java-data-node-optional-gate.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("source_area") != "Java OpenSearch data-node compatibility":
        fail("unexpected source_area")
    if data.get("profile") != "optional":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "In progress":
        fail("open_search_api_compatibility must be In progress")
    if matrix.get("semantic_parity") != "N/A":
        fail("semantic_parity must be N/A")
    if matrix.get("production_readiness") != "No":
        fail("production_readiness must be No")

    if set(data.get("required_fixtures", [])) != EXPECTED_FIXTURES:
        fail("required_fixtures mismatch")
    if set(data.get("required_profiles", [])) != EXPECTED_PROFILES:
        fail("required_profiles mismatch")
    if data.get("track_status") != "optional-track":
        fail("track_status must be optional-track")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
