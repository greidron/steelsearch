#!/usr/bin/env python3
import json
import sys


EXPECTED_VISIBILITY = {"pre-restart", "mid-restart", "post-restart"}
EXPECTED_ROUTING = {
    "node_assignment_changed",
    "recovery_completed",
    "write_availability_preserved",
}
EXPECTED_DURABILITY = {"accepted-write-window", "post-restart-readback"}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-java-driven-rolling-restart-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "java-driven-rolling-restart":
        fail("unexpected profile")
    if data.get("primary_node") != "java":
        fail("primary_node must be java")
    if data.get("replica_node") != "rust":
        fail("replica_node must be rust")

    if set(data.get("cluster_manager_visibility_modes", [])) != EXPECTED_VISIBILITY:
        fail("cluster_manager_visibility_modes mismatch")
    if set(data.get("shard_routing_diff_fields", [])) != EXPECTED_ROUTING:
        fail("shard_routing_diff_fields mismatch")
    if set(data.get("restart_durability_stages", [])) != EXPECTED_DURABILITY:
        fail("restart_durability_stages mismatch")
    if data.get("restart_decoder_path") != "stable":
        fail("restart_decoder_path must be stable")

    print(json.dumps({
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
