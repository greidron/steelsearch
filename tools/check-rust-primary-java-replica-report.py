#!/usr/bin/env python3
import json
import sys


EXPECTED_WRITE_MODES = {"index", "delete", "update", "bulk-replay"}
EXPECTED_VISIBILITY = {"realtime", "read-after-refresh", "recovery-after-restart"}
EXPECTED_PROVENANCE_MODES = {"translog", "segment", "mixed"}
EXPECTED_FAILURES = {"acknowledged_but_diverged", "metadata_mismatch", "unsupported_op"}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-rust-primary-java-replica-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "rust-primary-java-replica":
        fail("unexpected profile")
    if data.get("primary_node") != "rust":
        fail("primary_node must be rust")
    if data.get("replica_node") != "java":
        fail("replica_node must be java")

    if set(data.get("write_modes", [])) != EXPECTED_WRITE_MODES:
        fail("write_modes mismatch")
    if set(data.get("visibility_stages", [])) != EXPECTED_VISIBILITY:
        fail("visibility_stages mismatch")
    if set(data.get("replica_provenance_modes", [])) != EXPECTED_PROVENANCE_MODES:
        fail("replica_provenance_modes mismatch")
    if data.get("replica_provenance") not in EXPECTED_PROVENANCE_MODES:
        fail("replica_provenance must be one of provenance modes")
    if set(data.get("required_failure_classes", [])) != EXPECTED_FAILURES:
        fail("required_failure_classes mismatch")

    print(json.dumps({
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
