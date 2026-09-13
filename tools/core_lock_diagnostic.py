"""Summarize sampled lock diagnostics, never performance acceptance evidence."""

import json

PREFIX = "STEELSEARCH_LOCK_DIAGNOSTIC "
SITES = {"search_snapshot", "refresh_plan", "refresh_publish", "refresh_owner"}


def summarize(lines, allowed_pids):
    groups = {}
    seen = set()
    for line in lines:
        if not line.startswith(PREFIX):
            continue
        sample = json.loads(line[len(PREFIX):])
        if sample["site"] not in SITES or sample["pid"] not in allowed_pids:
            raise ValueError("unexpected lock sample identity")
        for field in ("pid", "attempt", "sample_every", "wait_ns", "held_ns"):
            if type(sample[field]) is not int or sample[field] < 0:
                raise ValueError("invalid lock sample number")
        if sample["sample_every"] != 64 or sample["attempt"] % 64:
            raise ValueError("unexpected sampling schedule")
        identity = (sample["pid"], sample["site"], sample["attempt"])
        if identity in seen:
            raise ValueError("duplicate lock sample")
        seen.add(identity)
        group = groups.setdefault(identity[:2], {"pid": sample["pid"], "site": sample["site"],
                                                "samples": 0, "wait_ns_sum": 0, "held_ns_sum": 0,
                                                "wait_ns_max": 0, "held_ns_max": 0})
        group["samples"] += 1
        for metric in ("wait_ns", "held_ns"):
            group[f"{metric}_sum"] += sample[metric]
            group[f"{metric}_max"] = max(group[f"{metric}_max"], sample[metric])
    if not groups:
        raise ValueError("no lock diagnostic samples")
    return {"diagnostic_only": True, "acceptance_established": False,
            "scope": "Sampled lock attempts across setup and mixed load; no HTTP percentile attribution. Periodic sampling and instrumentation may bias results.",
            "groups": [groups[key] for key in sorted(groups)]}
