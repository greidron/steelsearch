#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"error": "usage: check_publication_reference_normalization.py <direct_tracer_check.json> <mixed_publish_commit_check.json> <mixed_state_close_check.json>"}))
        return 1

    tracer = load(sys.argv[1])
    mixed_pub = load(sys.argv[2])
    mixed_close = load(sys.argv[3])

    tracer_publish = int(tracer.get("publish_state_count", 0))
    tracer_commit = int(tracer.get("commit_state_count", 0))
    mixed_publish = int(mixed_pub.get("publish_state_count", 0))
    mixed_commit = int(mixed_pub.get("commit_state_count", 0))
    mixed_same_tick_close = int(mixed_close.get("same_tick_remote_eof_count", 0))

    reference = {
        "path": "direct_java_java_tracer",
        "publish_state_observed": tracer_publish > 0,
        "commit_state_observed": tracer_commit > 0,
        "publication_progress_class": "publish_and_commit_observed" if tracer_publish > 0 and tracer_commit > 0 else "insufficient_reference_progress",
        "state_channel_retention_class": "retained_through_commit" if tracer_commit > 0 else "retention_not_proven",
    }
    mixed = {
        "path": "current_java_rust_mixed",
        "publish_state_observed": mixed_publish > 0,
        "commit_state_observed": mixed_commit > 0,
        "publication_progress_class": "publish_reached_commit_blocked" if mixed_publish > 0 and mixed_commit == 0 else "other",
        "state_channel_retention_class": "same_tick_remote_eof_before_commit" if mixed_same_tick_close > 0 and mixed_commit == 0 else "other",
    }

    if reference["publication_progress_class"] == "publish_and_commit_observed" and mixed["publication_progress_class"] == "publish_reached_commit_blocked":
        result = "canonical_reference_and_mixed_publication_baselines_normalized"
    else:
        result = "normalization_incomplete"

    print(json.dumps({"reference": reference, "mixed": mixed, "result": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
