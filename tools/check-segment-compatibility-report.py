#!/usr/bin/env python3
import json
import sys


EXPECTED_MATRIX = {
    "java-segment-to-rust-read",
    "rust-segment-to-java-read",
}
EXPECTED_METADATA = {
    "segment_file_list",
    "codec_version",
    "checksum_summary",
    "recovery_source_provenance",
}
EXPECTED_BOOTSTRAP = {
    "segment-only",
    "translog-assisted",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-segment-compatibility-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "segment-compatibility-verify":
        fail("unexpected profile")
    if data.get("primary_node") != "java":
        fail("primary_node must be java")
    if data.get("replica_node") != "rust":
        fail("replica_node must be rust")

    if set(data.get("segment_matrix", [])) != EXPECTED_MATRIX:
        fail("segment_matrix mismatch")
    if set(data.get("segment_metadata_fields", [])) != EXPECTED_METADATA:
        fail("segment_metadata_fields mismatch")
    if set(data.get("recovery_bootstrap_modes", [])) != EXPECTED_BOOTSTRAP:
        fail("recovery_bootstrap_modes mismatch")
    if data.get("recovery_bootstrap_mode") not in EXPECTED_BOOTSTRAP:
        fail("recovery_bootstrap_mode must be one of recovery_bootstrap_modes")
    if data.get("incompatibility_failure_class") != "segment_incompatibility":
        fail("incompatibility_failure_class mismatch")

    print(json.dumps({
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
