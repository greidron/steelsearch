#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
SRC = REPO / 'crates/os-node/src/standalone_runtime.rs'
text = SRC.read_text()

SYMBOLS = [
    'RestServerConfig',
    'SecurityBoundaryPolicy',
    'ReleaseReadinessChecklist',
    'SteelNode',
    'bind_rest_http_listener',
    'serve_rest_http_listener_until',
    'validate_production_mode_request',
]


def find_line(name: str) -> int:
    for i, line in enumerate(text.splitlines(), start=1):
        if re.search(r'\b' + re.escape(name) + r'\b', line):
            return i
    raise RuntimeError(f'{name} not found')


def has_signature(pattern: str) -> bool:
    return re.search(pattern, text, re.S) is not None


def main():
    lines = {name: find_line(name) for name in SYMBOLS}
    serve_uses_steelnode = 'pub fn serve_rest_http_listener_until' in text and 'node: SteelNode' in text
    handle_uses_steelnode = 'fn handle_http_connection' in text and 'node: &SteelNode' in text
    steelnode_has_rest_config = has_signature(r'pub struct SteelNode\s*\{[^}]*pub rest_config: Option<RestServerConfig>')

    phase1_thin_core = [
        'RestServerConfig',
        'SecurityBoundaryPolicy',
        'ReleaseReadinessChecklist',
        'bind_rest_http_listener',
        'validate_production_mode_request',
    ]
    phase2_coupled_adapter = [
        'SteelNode',
        'serve_rest_http_listener_until',
    ]

    result = {
        'definition_lines': lines,
        'serve_uses_steelnode': serve_uses_steelnode,
        'handle_uses_steelnode': handle_uses_steelnode,
        'steelnode_has_rest_config': steelnode_has_rest_config,
        'phase1_thin_core_candidate': phase1_thin_core,
        'phase2_coupled_adapter_candidate': phase2_coupled_adapter,
        'result': 'the_lowest_risk_patch_candidate_for_rest_bootstrap_and_policy_is_a_two_phase_split_where_five_thin_symbols_move_first_and_steelnode_plus_serve_rest_http_listener_until_follow_only_after_an_adapter_boundary_is_introduced',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
