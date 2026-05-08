#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path


PATTERN = re.compile(
    r"action-tagged selected channel index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\] requestId \[(\d+)\].* for \[(.*)\]$"
)


def load_rows(log_path: Path):
    rows = []
    for line in log_path.read_text(errors="replace").splitlines():
        match = PATTERN.search(line)
        if not match:
            continue
        rows.append(
            {
                "ts": line[1:24],
                "idx": int(match.group(1)),
                "type": match.group(2),
                "action": match.group(3),
                "request_id": int(match.group(4)),
                "node": match.group(5),
            }
        )
    return rows


def split_cycles(rows):
    cycles = []
    current = []
    for row in rows:
        if row["action"] == "internal:transport/handshake" and row["idx"] == 0:
            if current:
                cycles.append(current)
            current = [row]
        elif current:
            current.append(row)
    if current:
        cycles.append(current)
    return cycles


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_reg_round_robin_skew_explained_by_variable_request_peers.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    stdout_path = Path(report["artifacts"]["opensearch_stdout"])
    rows = load_rows(stdout_path)
    cycles = split_cycles(rows)

    request_peers_multiplicity = Counter()
    named_reg_actions_per_cycle = Counter()
    transition_matches = 0
    transition_total = 0

    for index, cycle in enumerate(cycles):
        named_reg = [
            row
            for row in cycle
            if "rust-replica-1" in row["node"] and row["type"] == "REG"
        ]
        if not named_reg:
            continue

        request_peers_count = sum(
            1 for row in named_reg if row["action"] == "internal:discovery/request_peers"
        )
        request_peers_multiplicity[request_peers_count] += 1
        named_reg_actions_per_cycle[len(named_reg)] += 1

        if index + 1 >= len(cycles):
            continue

        next_named_handshake = [
            row
            for row in cycles[index + 1]
            if "rust-replica-1" in row["node"]
            and row["type"] == "REG"
            and row["action"] == "internal:transport/handshake"
        ]
        if not next_named_handshake:
            continue

        current_handshake_idx = named_reg[0]["idx"]
        current_reg_count = len(named_reg)
        expected_next_idx = 7 + ((current_handshake_idx - 7 + current_reg_count) % 6)
        actual_next_idx = next_named_handshake[0]["idx"]
        transition_total += 1
        if expected_next_idx == actual_next_idx:
            transition_matches += 1

    result = {
        "work_dir": report.get("work_dir"),
        "cycle_count": len(cycles),
        "request_peers_multiplicity_per_cycle": dict(sorted(request_peers_multiplicity.items())),
        "named_reg_actions_per_cycle": dict(sorted(named_reg_actions_per_cycle.items())),
        "transition_matches": transition_matches,
        "transition_total": transition_total,
        "result": (
            "reg_7_12_skew_is_explained_by_a_persistent_round_robin_counter_plus_variable_request_peers_multiplicity"
            if transition_matches == transition_total and transition_total > 0
            else "reg_7_12_skew_is_not_fully_explained_by_the_persistent_round_robin_counter_hypothesis"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if transition_matches != transition_total or transition_total == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
