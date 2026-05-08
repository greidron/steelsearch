#!/usr/bin/env python3
import json
import sys


EXPECTED = {
    "missing_required_suite_blocked": "security-multinode",
    "missing_redaction_smoke_blocked": "security-redaction-smoke-report.json",
    "missing_secure_durability_restart_blocked": "secure-durability-restart-report.json",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check-secure-standalone-claim-blocked-smoke.py <fixture.json>")

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    cases = data.get("cases", [])
    found = {case.get("name"): case for case in cases}
    if set(found) != set(EXPECTED):
        fail("blocked smoke cases mismatch")

    for name, missing in EXPECTED.items():
        case = found[name]
        if case.get("missing_component") != missing:
            fail(f"{name} missing_component mismatch")
        if case.get("expected_status") != "blocked":
            fail(f"{name} must expect blocked")

    print(json.dumps({
        "case_count": len(cases),
        "status": "ok"
    }))


if __name__ == "__main__":
    main()
