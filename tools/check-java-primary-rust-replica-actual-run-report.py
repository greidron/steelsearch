#!/usr/bin/env python3
import json
import sys


EXPECTED_PHASES = {"prepare", "write", "read", "recover", "restart", "check"}
EXPECTED_WRITE_MODES = {"single-doc-crud", "bulk"}
EXPECTED_VISIBILITY = {"post-refresh", "post-recovery", "post-restart"}
EXPECTED_CHECKPOINTS = {"seq_no_drift", "global_checkpoint_drift", "local_checkpoint_drift"}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-java-primary-rust-replica-actual-run-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "java-primary-rust-replica":
        fail("unexpected profile")
    if data.get("artifact_source") != "actual-phase-artifacts":
        fail("artifact_source must be actual-phase-artifacts")

    phase_artifacts = data.get("phase_artifacts", {})
    if set(phase_artifacts.keys()) != EXPECTED_PHASES:
        fail("phase_artifacts must cover all required phases")

    if set(data.get("write_modes", [])) != EXPECTED_WRITE_MODES:
        fail("write_modes mismatch")
    if set(data.get("visibility_stages", [])) != EXPECTED_VISIBILITY:
        fail("visibility_stages mismatch")

    drift = data.get("checkpoint_drift", {})
    if set(drift.keys()) != EXPECTED_CHECKPOINTS:
        fail("checkpoint_drift keys mismatch")
    for key, value in drift.items():
        if not isinstance(value, (int, float)):
            fail(f"{key} drift must be numeric")

    if data.get("divergence_classification") != "none":
        fail("divergence_classification must be none for success path")

    print(json.dumps({
        "profile": data["profile"],
        "artifact_source": data["artifact_source"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
