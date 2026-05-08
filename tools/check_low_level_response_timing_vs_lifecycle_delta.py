#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def classify(entries):
    tcp = []
    for e in entries:
        first = e.get("first_frame") or {}
        if first.get("action_hint") != "internal:tcp/handshake":
            continue
        tcp.append(e)
    return tcp


def summarize(entries):
    tcp = classify(entries)
    response_lags = []
    hold_open_lags = []
    lifetimes = []
    keepalives = []
    events = {}
    follow_up = 0
    post_follow_up = 0
    handled_follow_up = 0
    immediate_response = 0

    for e in tcp:
        first_at = e.get("first_frame_received_at_ms")
        resp_at = e.get("response_frame_sent_at_ms")
        hold_at = e.get("hold_open_started_at_ms")
        end_at = e.get("connection_end_at_ms")
        post = e.get("first_post_response_event")
        keepalive = e.get("proactive_keepalive_count") or 0

        if resp_at is not None and first_at is not None:
            lag = resp_at - first_at
            response_lags.append(lag)
            if lag == 0:
                immediate_response += 1
        if hold_at is not None and resp_at is not None:
            hold_open_lags.append(hold_at - resp_at)
        if end_at is not None and resp_at is not None:
            lifetimes.append(end_at - resp_at)
        keepalives.append(keepalive)
        events[post] = events.get(post, 0) + 1
        if e.get("follow_up_frame") is not None:
            follow_up += 1
        if e.get("post_follow_up_frame") is not None:
            post_follow_up += 1
        if post == "handled_follow_up_request":
            handled_follow_up += 1

    def stat(xs, fn):
        return None if not xs else fn(xs)

    return {
        "tcp_total": len(tcp),
        "response_lag_min_ms": stat(response_lags, min),
        "response_lag_median_ms": stat(response_lags, statistics.median),
        "response_lag_max_ms": stat(response_lags, max),
        "immediate_response_count": immediate_response,
        "hold_open_after_response_min_ms": stat(hold_open_lags, min),
        "hold_open_after_response_median_ms": stat(hold_open_lags, statistics.median),
        "hold_open_after_response_max_ms": stat(hold_open_lags, max),
        "lifetime_after_response_min_ms": stat(lifetimes, min),
        "lifetime_after_response_median_ms": stat(lifetimes, statistics.median),
        "lifetime_after_response_max_ms": stat(lifetimes, max),
        "first_post_response_events": events,
        "follow_up_count": follow_up,
        "post_follow_up_count": post_follow_up,
        "handled_follow_up_count": handled_follow_up,
        "proactive_keepalive_total": sum(keepalives),
        "proactive_keepalive_nonzero": sum(1 for x in keepalives if x),
    }


def main():
    if len(sys.argv) != 3:
        print(
            "usage: check_low_level_response_timing_vs_lifecycle_delta.py OLD_CAPTURE CURRENT_CAPTURE",
            file=sys.stderr,
        )
        return 2

    old_path = Path(sys.argv[1])
    current_path = Path(sys.argv[2])
    old = summarize(load_json(old_path))
    current = summarize(load_json(current_path))

    print(f"old_capture={old_path}")
    for k, v in old.items():
        print(f"old_{k}={v}")
    print(f"current_capture={current_path}")
    for k, v in current.items():
        print(f"current_{k}={v}")

    current_idle = current["first_post_response_events"].get("idle_timeout", 0)
    old_idle = old["first_post_response_events"].get("idle_timeout", 0)
    old_resp_max = old["response_lag_max_ms"]
    current_resp_max = current["response_lag_max_ms"]

    if (
        old_resp_max is not None
        and current_resp_max is not None
        and current_resp_max <= old_resp_max
        and old["follow_up_count"] > 0
        and current["follow_up_count"] == 0
        and current_idle > old_idle
        and current["proactive_keepalive_total"] > old["proactive_keepalive_total"]
    ):
        result = (
            "low_level_response_timing_did_not_regress_but_post_response_connection_lifecycle_shifted_"
            "from_followup_capable_mix_to_idle_timeout_keepalive_only"
        )
    else:
        result = "inconclusive"

    print(f"checker_result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
