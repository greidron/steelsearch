import json
import re
import sys
from pathlib import Path


def must(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.S) is not None


def main() -> int:
    if len(sys.argv) != 6:
        print(
            'usage: check_first_close_skew_is_not_action_usage.py '
            '<publication_transport_handler.java> <followers_checker.java> '
            '<peer_finder.java> <first_close_classes.json> <action_channels.json>',
            file=sys.stderr,
        )
        return 1

    publication_text = Path(sys.argv[1]).read_text()
    followers_text = Path(sys.argv[2]).read_text()
    peerfinder_text = Path(sys.argv[3]).read_text()
    first_close = json.loads(Path(sys.argv[4]).read_text())
    action_channels = json.loads(Path(sys.argv[5]).read_text())

    source_publish_state_uses_state = must(
        r'stateRequestOptions\s*=\s*TransportRequestOptions\.builder\(\).*?withType\(TransportRequestOptions\.Type\.STATE\)',
        publication_text,
    )
    source_follower_check_uses_ping = 'withType(Type.PING)' in followers_text
    source_request_peers_uses_default_reg = must(
        r'REQUEST_PEERS_ACTION_NAME,\s*new PeersRequest\(getLocalNode\(\),\s*knownNodes\),\s*TransportRequestOptions\.builder\(\)\.withTimeout\(requestPeersTimeout\)\.build\(\)',
        peerfinder_text,
    )

    first_class_counts = first_close['first_class_counts']
    action_counts = action_channels['action_counts']

    ping_state_actions_present = action_counts['follower_check'] > 0 and action_counts['publish_state'] > 0
    reg_actions_present = action_counts['request_peers'] > 0
    ping_state_never_first_close = first_class_counts['PING'] == 0 and first_class_counts['STATE'] == 0
    bulk_recovery_first_close_dominant = (
        first_class_counts['BULK'] + first_class_counts['RECOVERY']
        > first_class_counts['REG'] + first_class_counts['PING'] + first_class_counts['STATE']
    )

    if (
        source_publish_state_uses_state
        and source_follower_check_uses_ping
        and source_request_peers_uses_default_reg
        and ping_state_actions_present
        and reg_actions_present
        and ping_state_never_first_close
        and bulk_recovery_first_close_dominant
    ):
        result = (
            'first_close_class_skew_is_not_explained_by_action_channel_usage_and_is_better_explained_by_lower_transport_close_origin'
        )
    else:
        result = 'first_close_class_skew_vs_action_usage_inconclusive'

    print(json.dumps({
        'source_publish_state_uses_state': source_publish_state_uses_state,
        'source_follower_check_uses_ping': source_follower_check_uses_ping,
        'source_request_peers_uses_default_reg': source_request_peers_uses_default_reg,
        'action_counts': action_counts,
        'first_class_counts': first_class_counts,
        'ping_state_actions_present': ping_state_actions_present,
        'reg_actions_present': reg_actions_present,
        'ping_state_never_first_close': ping_state_never_first_close,
        'bulk_recovery_first_close_dominant': bulk_recovery_first_close_dominant,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
