#!/usr/bin/env python3
import json
import sys


EXPECTED_DURABILITY = {
    "peer-recovery",
    "mixed-write-replication",
    "durability-convergence",
}

EXPECTED_DISTRIBUTED = {
    "quorum-evidence",
    "publication-ordering",
    "rolling-stability-transcript",
    "leader-failover",
    "seed-loss-recovery",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-peer-node-promotion-gate.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("source_area") != "Steelsearch multi-node runtime":
        fail("unexpected source_area")
    if data.get("profile") != "same-cluster-peer":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "Implemented":
        fail("open_search_api_compatibility must be Implemented")
    if matrix.get("semantic_parity") != "Implemented":
        fail("semantic_parity must be Implemented")
    if matrix.get("production_readiness") != "Yes":
        fail("production_readiness must be Yes")

    sections = data.get("unified_report_sections", {})
    durability = sections.get("durability_parity")
    distributed = sections.get("distributed_parity")
    if not durability or not distributed:
        fail("durability_parity and distributed_parity required")
    if durability.get("suite") != "same-cluster-peer":
        fail("durability suite mismatch")
    if distributed.get("suite") != "same-cluster-peer":
        fail("distributed suite mismatch")
    if set(durability.get("required_evidence_classes", [])) != EXPECTED_DURABILITY:
        fail("durability evidence mismatch")
    if set(distributed.get("required_evidence_classes", [])) != EXPECTED_DISTRIBUTED:
        fail("distributed evidence mismatch")

    print(json.dumps({
        "source_area": data["source_area"],
        "profile": data["profile"],
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
