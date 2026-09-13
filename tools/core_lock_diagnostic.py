"""Summarize sampled lock diagnostics, never performance acceptance evidence."""

import json

PREFIX = "STEELSEARCH_LOCK_DIAGNOSTIC "
APPEND_PREFIX = "STEELSEARCH_APPEND_DIAGNOSTIC "
SITES = {"search_snapshot", "refresh_plan", "refresh_publish", "refresh_owner", "refresh_writer"}


def parse_append(lines, allowed_pids):
    """Parse cumulative successful-append samples without estimating unsampled batches."""
    samples = []
    required_fields = {"pid", "batches", "documents", "commit_nanos"}
    for line in lines:
        if not line.startswith(APPEND_PREFIX):
            continue
        sample = json.loads(line[len(APPEND_PREFIX):])
        if type(sample) is not dict:
            raise ValueError("invalid append sample object")
        if set(sample) != required_fields:
            raise ValueError("unexpected append sample fields")
        for field in required_fields:
            if type(sample[field]) is not int or sample[field] < 0:
                raise ValueError("invalid append sample number")
        if sample["pid"] not in allowed_pids:
            raise ValueError("unexpected append sample identity")
        if sample["batches"] == 0 or (sample["batches"] - 1) % 64:
            raise ValueError("unexpected append sampling schedule")
        samples.append(sample)

    ordered_samples = sorted(samples, key=lambda sample: (sample["pid"], sample["batches"]))
    previous_by_pid = {}
    for sample in ordered_samples:
        previous = previous_by_pid.get(sample["pid"])
        if previous is not None:
            if sample["batches"] <= previous["batches"]:
                raise ValueError("append batches must strictly increase")
            if (sample["documents"] < previous["documents"]
                    or sample["commit_nanos"] < previous["commit_nanos"]):
                raise ValueError("append cumulative counters must not decrease")
        previous_by_pid[sample["pid"]] = sample
    return ordered_samples


def summarize(lines, allowed_pids):
    lines = tuple(lines)
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
    append_samples = parse_append(lines, allowed_pids)
    if not groups and not append_samples:
        raise ValueError("no lock diagnostic samples")
    result = {"diagnostic_only": True, "acceptance_established": False,
            "scope": "Sampled lock attempts across setup and mixed load; no HTTP percentile attribution. Periodic sampling and instrumentation may bias results.",
            "groups": [groups[key] for key in sorted(groups)]}
    if append_samples:
        final_by_pid = {}
        for sample in append_samples:
            final_by_pid[sample["pid"]] = sample
        result["append_groups"] = [
            {"pid": pid, "samples": sum(sample["pid"] == pid for sample in append_samples),
             "final_sample_lower_bound": {field: sample[field] for field in ("batches", "documents", "commit_nanos")}}
            for pid, sample in sorted(final_by_pid.items())
        ]
        result["append_scope"] = (
            "Sampled cumulative successful append calls only; full rebuilds and failed writes are excluded. "
            "Final samples are lower bounds, not inferred totals.")
    return result
