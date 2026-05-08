#!/usr/bin/env python3
import json
import sys


EXPECTED_WRITE_MODES = {"single-doc-crud", "bulk"}
EXPECTED_VISIBILITY = {"post-refresh", "post-recovery", "post-restart"}
EXPECTED_CHECKPOINTS = {"seq_no_drift", "global_checkpoint_drift", "local_checkpoint_drift"}
EXPECTED_FAILURES = {"decode_mismatch", "apply_mismatch", "checkpoint_mismatch"}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-java-primary-rust-replica-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "java-primary-rust-replica":
        fail("unexpected profile")
    if data.get("primary_node") != "java":
        fail("primary_node must be java")
    if data.get("replica_node") != "rust":
        fail("replica_node must be rust")

    if set(data.get("write_modes", [])) != EXPECTED_WRITE_MODES:
        fail("write_modes mismatch")
    if set(data.get("visibility_stages", [])) != EXPECTED_VISIBILITY:
        fail("visibility_stages mismatch")
    if set(data.get("checkpoint_fields", [])) != EXPECTED_CHECKPOINTS:
        fail("checkpoint_fields mismatch")
    if set(data.get("required_failure_classes", [])) != EXPECTED_FAILURES:
        fail("required_failure_classes mismatch")

    drift = data.get("checkpoint_drift", {})
    if set(drift.keys()) != EXPECTED_CHECKPOINTS:
        fail("checkpoint_drift keys mismatch")
    for key, value in drift.items():
        if value != 0:
            fail(f"{key} must be 0")

    print(json.dumps({
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
