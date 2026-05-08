#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            'usage: check_discovery_scheduler_candidate_validation.py <scheduler_scale.json> <tick_alignment.json>'
        )

    scheduler = load(sys.argv[1])
    alignment = load(sys.argv[2])

    source_scheduler_candidate_present = (
        scheduler.get('probe_handshake_timeout_ms') == 1000
        and scheduler.get('find_peers_interval_ms') == 1000
        and scheduler.get('request_peers_timeout_ms') == 3000
    )
    artifact_rejects_uniform_1s_cadence = (
        alignment.get('result') == 'probe_retry_gaps_do_not_uniformly_align_to_1s_ticks'
    )

    result = (
        'discovery_scheduler_candidate_validated_but_uniform_1s_cadence_not_supported_by_artifact'
        if source_scheduler_candidate_present and artifact_rejects_uniform_1s_cadence
        else 'discovery_scheduler_candidate_validation_not_complete'
    )

    print(json.dumps({
        'source_scheduler_candidate_present': source_scheduler_candidate_present,
        'artifact_rejects_uniform_1s_cadence': artifact_rejects_uniform_1s_cadence,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
