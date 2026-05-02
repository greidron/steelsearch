#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def find_first(text: str, marker: str) -> int:
    return text.find(marker)


def match_step(text: str, step: dict) -> tuple[bool, int, str]:
    markers = step["markers"]
    mode = step.get("match", "all")
    positions = [(marker, find_first(text, marker)) for marker in markers]
    if mode == "any":
        present = [(marker, pos) for marker, pos in positions if pos >= 0]
        if not present:
            return False, -1, f"{step['name']}: none of {markers} found"
        marker, pos = min(present, key=lambda item: item[1])
        return True, pos, f"{step['name']}: matched {marker}"
    missing = [marker for marker, pos in positions if pos < 0]
    if missing:
        return False, -1, f"{step['name']}: missing {missing}"
    pos = min(pos for _, pos in positions)
    return True, pos, f"{step['name']}: matched all"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile")
    parser.add_argument(
        "--fixture",
        default="tools/fixtures/startup-ordering-transcript.json",
    )
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text())
    text = Path(args.logfile).read_text()

    last_pos = -1
    for step in fixture.get("canonical_sequence", []):
        ok, pos, detail = match_step(text, step)
        if not ok:
            print(detail, file=sys.stderr)
            return 1
        if pos < last_pos:
            print(
                f"{step['name']}: out of order (position {pos} < {last_pos})",
                file=sys.stderr,
            )
            return 1
        last_pos = pos

    for rule in fixture.get("forbidden_orderings", []):
        earlier = find_first(text, rule["earlier"])
        later = find_first(text, rule["later"])
        if earlier >= 0 and later >= 0 and earlier < later:
            print(
                f"{rule['name']}: forbidden ordering detected: "
                f"{rule['earlier']} before {rule['later']}",
                file=sys.stderr,
            )
            return 1

    for rule in fixture.get("required_absence_after_failure", []):
        for marker in rule.get("markers", []):
            if marker in text:
                print(
                    f"{rule['name']}: forbidden success marker present: {marker}",
                    file=sys.stderr,
                )
                return 1

    print("startup ordering transcript OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
