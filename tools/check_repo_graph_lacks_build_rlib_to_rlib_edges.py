#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
HTML_RE = re.compile(r'const UNIT_DATA = (.*?);\n', re.S)


def run(cmd):
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, check=True)


def parse_unit_data(html_path: Path):
    text = html_path.read_text()
    m = HTML_RE.search(text)
    if not m:
        raise RuntimeError(f'UNIT_DATA not found in {html_path}')
    return json.loads(m.group(1))


def latest_timing_html(target_dir: Path):
    candidates = sorted((target_dir / 'cargo-timings').glob('cargo-timing*.html'))
    if not candidates:
        raise RuntimeError('no cargo timing html found')
    return candidates[-1]


def main():
    metadata = json.loads(run(['cargo', 'metadata', '--format-version', '1']).stdout)
    workspace_members = set(metadata['workspace_members'])
    packages = {pkg['id']: pkg for pkg in metadata['packages']}
    os_node_pkg = next(pkg for pkg in metadata['packages'] if pkg['name'] == 'os-node')
    os_node_id = os_node_pkg['id']

    reverse_workspace_dependents = []
    for pkg in metadata['packages']:
        if pkg['id'] == os_node_id or pkg['id'] not in workspace_members:
            continue
        for dep in pkg.get('dependencies', []):
            if dep['name'] == 'os-node':
                reverse_workspace_dependents.append({
                    'package': pkg['name'],
                    'kind': dep.get('kind'),
                    'req': dep.get('req'),
                })

    os_node_targets = [
        {
            'name': t['name'],
            'kind': t['kind'],
            'src_path': t['src_path'].replace(str(REPO) + '/', ''),
        }
        for t in os_node_pkg['targets']
    ]

    # Force a current timing artifact for the os-node all-targets graph.
    Path(REPO / 'crates/os-node/src/write_path_invariants.rs').touch()
    run([
        'cargo', 'check', '--all-targets', '-p', 'os-node', '--features', 'standalone-runtime', '--timings'
    ])
    units = parse_unit_data(latest_timing_html(REPO / 'target'))
    os_node_units = [u for u in units if u['name'] == 'os-node']
    os_node_targets_in_graph = sorted({u['target'] for u in os_node_units})
    producer_unit = next(u for u in os_node_units if u['target'] == ' lib (check)')

    unlocked_target_names = [units[i]['target'] for i in producer_unit.get('unlocked_units', [])]
    unlocked_rmeta_target_names = [units[i]['target'] for i in producer_unit.get('unlocked_rmeta_units', [])]

    result = {
        'workspace_member_count': len(workspace_members),
        'reverse_workspace_dependents_of_os_node': reverse_workspace_dependents,
        'reverse_workspace_dependents_count': len(reverse_workspace_dependents),
        'os_node_targets': os_node_targets,
        'os_node_targets_in_all_targets_check_graph': os_node_targets_in_graph,
        'os_node_lib_check_unlocked_units': unlocked_target_names,
        'os_node_lib_check_unlocked_rmeta_units': unlocked_rmeta_target_names,
        'result': 'current_steelsearch_repo_lacks_build_mode_rlib_to_rlib_edges_for_os_node_because_no_workspace_library_depends_on_os_node_and_its_local_downstreams_are_bin_or_test_targets',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
