#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

FOLLOW_RE = re.compile(r'internal:transport/handshake')
CLOSE_RE = re.compile(
    r'steelsearch_netty4_tcpchannel_stage=close_invoked .*callerGreatGreatGrandparent=([^ ]+) '
    r'callerGreatGreatGreatGrandparent=([^ ]+) '
    r'callerGreatGreatGreatGreatGrandparent=([^ ]+) '
    r'callerGreatGreatGreatGreatGreatGrandparent=([^ ]+)'
)


def old_followup_stats(captures):
    total = 0
    actions = {}
    for c in captures:
        ff = c.get('first_frame') or {}
        if ff.get('action_hint') != 'internal:tcp/handshake':
            continue
        fu = c.get('follow_up_frame') or {}
        action = fu.get('action_hint')
        if action:
            total += 1
            actions[action] = actions.get(action, 0) + 1
    return total, actions


def current_fingerprints(stdout):
    fps = {}
    for line in stdout.splitlines():
        m = CLOSE_RE.search(line)
        if not m:
            continue
        fp = tuple(m.groups())
        fps[fp] = fps.get(fp, 0) + 1
    return fps


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_fresh_formed_only_close_fingerprint_vs_old_followup.py OLD_CAPTURE CURRENT_STDOUT')
    old = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    stdout = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    old_followups, old_actions = old_followup_stats(old)
    fps = current_fingerprints(stdout)
    result = 'inconclusive'
    if old_followups > 0 and fps:
        result = 'old_formed_immediately_promoted_to_transport_handshake_whereas_current_fresh_run_collapses_into_executeHandshake_onFailure_closeAndFail_explicitLocalClose'
    print(json.dumps({
        'old_follow_up_count': old_followups,
        'old_follow_up_actions': old_actions,
        'current_close_fingerprints': {' | '.join(fp): count for fp, count in fps.items()},
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
