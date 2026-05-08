#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

def summarize(report):
    capture = report.get("steelsearch_transport_capture") or []
    tcp = [c for c in capture if (c.get("first_frame") or {}).get("action_hint") == "internal:tcp/handshake"]
    return {
        "membership_formed": report.get("membership_formed"),
        "observed_node_count": report.get("observed_node_count"),
        "failure_stage": report.get("failure_stage"),
        "tcp_total": len(tcp),
        "follow_up_count": sum(1 for c in tcp if c.get("follow_up_frame") is not None),
        "remote_eof_count": sum(1 for c in tcp if c.get("connection_end") == "remote_eof"),
        "direct_hold_open_marker": sum(1 for c in tcp if c.get("hold_open_started_at_ms") is not None),
    }

def main():
    if len(sys.argv) != 3:
        print("usage: check_direct_hold_open_after_tcp_response_candidate.py BASELINE_REPORT CANDIDATE_REPORT")
        return 2
    baseline = summarize(load(sys.argv[1]))
    candidate = summarize(load(sys.argv[2]))
    result = "direct_hold_open_after_tcp_response_candidate_does_not_restore_followup_or_formed_handoff"
    if candidate["membership_formed"]:
        result = "direct_hold_open_after_tcp_response_candidate_restored_formed_handoff"
    print(json.dumps({"baseline": baseline, "candidate": candidate, "checker_result": result}, indent=2))

if __name__ == "__main__":
    raise SystemExit(main())
