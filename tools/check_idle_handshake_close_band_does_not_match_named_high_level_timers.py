#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        print(
            'usage: check_idle_handshake_close_band_does_not_match_named_high_level_timers.py <mixed_artifact.json> <HandshakingTransportAddressConnector.java> <PeerFinder.java> <FollowersChecker.java> <LeaderChecker.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    source_paths = [Path(p) for p in sys.argv[2:]]
    with artifact_path.open() as f:
        data = json.load(f)
    texts = [p.read_text() for p in source_paths]

    capture = data['steelsearch_transport_capture']
    gaps = [
        item['connection_end_at_ms'] - item['response_frame_sent_at_ms']
        for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]

    observed = {
        'min': min(gaps),
        'median': statistics.median(gaps),
        'max': max(gaps),
    }

    source_has_probe_handshake_1000 = 'TimeValue.timeValueMillis(1000)' in texts[0]
    source_has_probe_connect_3000 = 'TimeValue.timeValueMillis(3000)' in texts[0]
    source_has_find_peers_1000 = 'discovery.find_peers_interval' in texts[1] and 'TimeValue.timeValueMillis(1000)' in texts[1]
    source_has_request_peers_timeout_3000 = 'discovery.request_peers_timeout' in texts[1] and 'TimeValue.timeValueMillis(3000)' in texts[1]
    source_has_follower_check_interval_1000 = 'follower_check.interval' in texts[2] and 'TimeValue.timeValueMillis(1000)' in texts[2]
    source_has_leader_check_interval_1000 = 'leader_check.interval' in texts[3] and 'TimeValue.timeValueMillis(1000)' in texts[3]

    result = {
        'idle_handshake_close_gap_ms': observed,
        'source_has_probe_handshake_1000': source_has_probe_handshake_1000,
        'source_has_probe_connect_3000': source_has_probe_connect_3000,
        'source_has_find_peers_1000': source_has_find_peers_1000,
        'source_has_request_peers_timeout_3000': source_has_request_peers_timeout_3000,
        'source_has_follower_check_interval_1000': source_has_follower_check_interval_1000,
        'source_has_leader_check_interval_1000': source_has_leader_check_interval_1000,
        'result': 'idle_handshake_close_band_is_below_named_1000ms_or_3000ms_high_level_timers_and_does_not_cleanly_match_them'
        if observed['max'] < 1000 and all([
            source_has_probe_handshake_1000,
            source_has_probe_connect_3000,
            source_has_find_peers_1000,
            source_has_request_peers_timeout_3000,
            source_has_follower_check_interval_1000,
            source_has_leader_check_interval_1000,
        ])
        else 'idle_handshake_close_band_may_still_match_a_named_high_level_timer',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
