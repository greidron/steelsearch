#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))

def main() -> int:
    jit_stop_path, jit_stop = load(sys.argv[1])
    generic_path, generic = load(sys.argv[2])
    result = {
        'jit_stop_path': str(jit_stop_path),
        'jit_stop_result': jit_stop.get('checker_result'),
        'generic_path': str(generic_path),
        'generic_result': generic.get('checker_result'),
        'generic_payload_event_count': generic.get('generic_payload_event_count'),
        'transport_worker_payload_event_count': generic.get('transport_worker_payload_event_count'),
    }
    if (
        jit_stop.get('checker_result') == 'non_intrusive_jit_symbol_family_reached_practical_stop_without_recovering_higher_caller_frames'
        and generic.get('checker_result') == 'artifact_shows_main_same_socket_payload_reads_on_opensearch_generic_threads_but_visible_transport_source_only_exposes_generic_post_read_dispatch_not_a_direct_generic_socket_read_callsite'
        and generic.get('generic_payload_event_count', 0) > generic.get('transport_worker_payload_event_count', 0)
    ):
        result['checker_result'] = 'non_intrusive_jit_stop_is_not_a_new_branch_it_rejoins_existing_java_inbound_response_delivery_read_starvation_root_blocker'
    else:
        result['checker_result'] = 'non_intrusive_jit_stop_connection_to_read_starvation_root_remains_unclear'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
