#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path
import re

TS_RE = re.compile(r'^\[(?P<ts>[^\]]+)\]')


def parse_ms(line: str):
    m = TS_RE.match(line)
    if not m:
        return None
    return int(datetime.strptime(m.group('ts'), '%Y-%m-%dT%H:%M:%S,%f').timestamp() * 1000)


def main() -> int:
    if len(sys.argv) != 5:
        print(
            'usage: check_initial_close_signal_precedes_java_fault_policy.py '
            '<ClusterConnectionManager.java> <FollowersChecker.java> <Coordinator.java> <stdout.log>',
            file=sys.stderr,
        )
        return 2

    cluster_src = Path(sys.argv[1]).read_text()
    follower_src = Path(sys.argv[2]).read_text()
    coordinator_src = Path(sys.argv[3]).read_text()
    lines = Path(sys.argv[4]).read_text().splitlines()

    source_close_listener_receives_preexisting_close = (
        'conn.addCloseListener(ActionListener.wrap(() -> {' in cluster_src
        and 'connectedNodes.remove(node, finalConnection);' in cluster_src
        and 'connectionListener.onNodeDisconnected(node, conn);' in cluster_src
    )
    source_followers_checker_reacts_to_disconnect = (
        'handleDisconnectedNode(DiscoveryNode discoveryNode)' in follower_src
        and 'followerChecker.failNode("disconnected")' in follower_src
        and 'transportService.disconnectFromNode(' not in follower_src
    )
    source_coordinator_fault_path_has_no_direct_disconnect = (
        'private void removeNode(DiscoveryNode discoveryNode, String reason)' in coordinator_src
        and 'submitStateUpdateTask(' in coordinator_src
        and 'disconnectFromNode(' not in coordinator_src
    )

    cycles = 0
    unregister_before_faulty = 0
    unregister_before_activate = 0

    events = []
    for idx, line in enumerate(lines):
        ms = parse_ms(line)
        if ms is None:
            continue
        kind = None
        if 'unregistering {rust-replica-1}' in line and 'after connection close and marking as disconnected' in line:
            kind = 'unregister'
        elif 'FollowerChecker{' in line and ' marking node as faulty' in line and 'rust-replica-1' in line:
            kind = 'faulty'
        elif 'PeerFinder' in line and 'activating with nodes:' in line:
            kind = 'activate'
        if kind:
            events.append((ms, kind, idx + 1))

    for i, (ms, kind, _line) in enumerate(events):
        if kind != 'unregister':
            continue
        cycles += 1
        rest = events[i + 1 :]
        faulty = next((e for e in rest if e[1] == 'faulty' and 0 <= e[0] - ms <= 250), None)
        activate = next((e for e in rest if e[1] == 'activate' and 0 <= e[0] - ms <= 300), None)
        if faulty:
            unregister_before_faulty += 1
        if activate:
            unregister_before_activate += 1

    if (
        source_close_listener_receives_preexisting_close
        and source_followers_checker_reacts_to_disconnect
        and source_coordinator_fault_path_has_no_direct_disconnect
        and unregister_before_faulty > 0
        and unregister_before_activate > 0
    ):
        result = (
            'initial_whole_burst_close_decision_is_upstream_of_followers_checker_and_coordinator_and_is_first_observed_as_'
            'a_connection_close_signal_at_cluster_connection_manager'
        )
    else:
        result = 'initial_close_vs_java_fault_policy_inconclusive'

    print(json.dumps({
        'source_close_listener_receives_preexisting_close': source_close_listener_receives_preexisting_close,
        'source_followers_checker_reacts_to_disconnect': source_followers_checker_reacts_to_disconnect,
        'source_coordinator_fault_path_has_no_direct_disconnect': source_coordinator_fault_path_has_no_direct_disconnect,
        'cycle_count': cycles,
        'unregister_before_faulty_count': unregister_before_faulty,
        'unregister_before_activate_count': unregister_before_activate,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
