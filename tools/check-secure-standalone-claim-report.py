#!/usr/bin/env python3
import json
import sys


SECTIONS = [
    "route_parity",
    "semantic_parity",
    "durability_parity",
    "security_parity",
    "distributed_parity",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-secure-standalone-claim-report.py <report.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("profile") != "secure-standalone":
        fail("profile must be secure-standalone")
    status = data.get("status")
    if status not in {"blocked", "ok"}:
        fail("status must be blocked or ok")

    for section_name in SECTIONS:
        section = data.get(section_name)
        if not section:
            fail(f"missing section: {section_name}")
        if section.get("required_suites") != ["security-multinode"]:
            fail(f"{section_name} must require security-multinode")
        if not section.get("report_paths"):
            fail(f"{section_name} report_paths must be non-empty")
        if section.get("status") not in {"ok", "blocked"}:
            fail(f"{section_name} status must be ok or blocked")

    security_paths = set(data["security_parity"]["report_paths"])
    durability_paths = set(data["durability_parity"]["report_paths"])
    if "security-redaction-smoke-report.json" not in security_paths:
        fail("security parity must reference redaction smoke report")
    if "secure-durability-restart-report.json" not in durability_paths:
        fail("durability parity must reference secure durability/restart report")

    reasons = set(data.get("blocking_reasons", []))
    if status == "blocked":
        if "missing security-redaction-smoke-report.json" not in reasons:
            fail("missing redaction blocking reason")
        if "missing secure-durability-restart-report.json" not in reasons:
            fail("missing durability blocking reason")
    else:
        if reasons:
            fail("ok report must not carry blocking reasons")
        if data["security_parity"]["status"] != "ok":
            fail("security_parity must be ok when claim report is ok")
        if data["durability_parity"]["status"] != "ok":
            fail("durability_parity must be ok when claim report is ok")

    print(json.dumps({
        "profile": data["profile"],
        "status": status,
        "blocking_reasons": sorted(reasons)
    }))


if __name__ == "__main__":
    main()
