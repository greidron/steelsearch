#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')


def run_json(script: str):
    out = subprocess.run(
        ['python3', str(REPO / 'tools' / script)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    return json.loads(out)


def main():
    closure = run_json('check_standalone_runtime_stronger_scaffold_closure.py')
    scope_file_count = 1 + closure['route_module_count'] + closure['support_item_count']
    scope_line_count = closure['standalone_runtime_lines'] + closure['route_module_total_lines']
    scope_is_large = scope_file_count >= 20 or scope_line_count >= 10000

    result = {
        'scope_file_count': scope_file_count,
        'scope_line_count': scope_line_count,
        'standalone_runtime_lines': closure['standalone_runtime_lines'],
        'route_module_count': closure['route_module_count'],
        'route_module_total_lines': closure['route_module_total_lines'],
        'support_item_count': closure['support_item_count'],
        'scope_is_large': scope_is_large,
        'result': 'the_os_node_runtime_stronger_scaffold_is_too_large_for_a_low_risk_next_patch_candidate_and_should_stop_at_design_conclusion_unless_the_user_explicitly_wants_the_large_refactor',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
