#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TS_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]")


def parse_ms(line: str):
    m = TS_RE.match(line)
    if not m:
        return None
    return int(datetime.strptime(m.group('ts'), '%Y-%m-%dT%H:%M:%S,%f').timestamp() * 1000)


def read_text(path: str) -> str:
    return Path(path).read_text()


def main() -> int:
    if len(sys.argv) != 5:
        print(
            'usage: check_java_policy_is_reactive_not_initial_close_decider.py '
            '<ClusterConnectionManager.java> <FollowersChecker.java> <Coordinator.java> <stdout.log>',
            file=sys.stderr,
        )
        return 2

    cluster_src = read_text(sys.argv[1])
    follower_src = read_text(sys.argv[2])
    coordinator_src = read_text(sys.argv[3])
    lines = Path(sys.argv[4]).read_text().splitlines()

    source_close_listener_is_input = (
        'after connection close and marking as disconnected' in cluster_src
        and 'onNodeDisconnected(node, conn)' in cluster_src
    )
    source_followers_checker_is_reactive = (
        'handleDisconnectedNode(DiscoveryNode discoveryNode)' in follower_src
        and 'followerChecker.failNode("disconnected")' in follower_src
    )
    source_failure_callback_wires_to_remove_node = 'this::removeNode' in coordinator_src
    source_remove_node_only_when_leader = 'if (mode == Mode.LEADER)' in coordinator_src and 'private void removeNode' in coordinator_src
    source_candidate_reactivates_peerfinder = 'peerFinder.activate(coordinationState.get().getLastAcceptedState().nodes());' in coordinator_src

    events = []
    for idx, line in enumerate(lines):
        ms = parse_ms(line)
        if ms is None:
            continue
        kind = None
        if 'unregistering {rust-replica-1}' in line and 'after connection close and marking as disconnected' in line:
            kind = 'unregister'
        elif 'FollowerChecker{' in line and ' disconnected' in line and 'rust-replica-1' in line:
            kind = 'disconnected'
        elif 'FollowerChecker{' in line and ' marking node as faulty' in line and 'rust-replica-1' in line:
            kind = 'faulty'
        elif 'PeerFinder' in line and 'activating with nodes:' in line:
            kind = 'peerfinder_activate'
        elif 'PeerFinder' in line and 'probing cluster-manager nodes from cluster state:' in line:
            kind = 'peerfinder_probe_cluster_state'
        elif 'Peer{transportAddress=127.0.0.1:60591, discoveryNode=null, peersRequestInFlight=false} attempting connection' in line:
            kind = 'fresh_attempt_same_node'
        if kind:
            events.append({'ms': ms, 'kind': kind, 'line': idx + 1})

    reactive_cycle_count = 0
    activate_after_faulty_count = 0
    probe_after_faulty_count = 0
    fresh_attempt_after_faulty_count = 0

    for i, event in enumerate(events):
        if event['kind'] != 'faulty':
            continue
        base = event['ms']
        window = events[i + 1 :]
        activate = next((e for e in window if e['kind'] == 'peerfinder_activate' and 0 <= e['ms'] - base <= 100), None)
        probe = next((e for e in window if e['kind'] == 'peerfinder_probe_cluster_state' and 0 <= e['ms'] - base <= 150), None)
        fresh = next((e for e in window if e['kind'] == 'fresh_attempt_same_node' and 0 <= e['ms'] - base <= 250), None)
        if activate and probe and fresh:
            reactive_cycle_count += 1
        if activate:
            activate_after_faulty_count += 1
        if probe:
            probe_after_faulty_count += 1
        if fresh:
            fresh_attempt_after_faulty_count += 1

    if (
        source_close_listener_is_input
        and source_followers_checker_is_reactive
        and source_failure_callback_wires_to_remove_node
        and source_remove_node_only_when_leader
        and source_candidate_reactivates_peerfinder
        and reactive_cycle_count > 0
    ):
        result = (
            'java_node_level_disconnect_fault_policy_is_reactive_to_an_already_closed_connection_and_restarts_peerfinder_'
            'so_it_is_not_the_initial_close_decider'
        )
    else:
        result = 'java_policy_reactivity_vs_initial_close_inconclusive'

    print(json.dumps({
        'source_close_listener_is_input': source_close_listener_is_input,
        'source_followers_checker_is_reactive': source_followers_checker_is_reactive,
        'source_failure_callback_wires_to_remove_node': source_failure_callback_wires_to_remove_node,
        'source_remove_node_only_when_leader': source_remove_node_only_when_leader,
        'source_candidate_reactivates_peerfinder': source_candidate_reactivates_peerfinder,
        'activate_after_faulty_count': activate_after_faulty_count,
        'probe_after_faulty_count': probe_after_faulty_count,
        'fresh_attempt_after_faulty_count': fresh_attempt_after_faulty_count,
        'reactive_cycle_count': reactive_cycle_count,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
