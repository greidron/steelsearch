#!/usr/bin/env python3
import json
import re
import sys
import zipfile
from pathlib import Path

JAR_LINE_RE = re.compile(r'jar1: (.+transport-netty4-client[^\n]+)\njar2: (.+lib/opensearch-[^\n]+)', re.MULTILINE)


def jar_has(path: Path, member: str) -> bool:
    with zipfile.ZipFile(path) as zf:
        return member in zf.namelist()


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: check_netty4tcpchannel_runtime_patch_path.py <run-opensearch-dev.sh> <artifact.json> <module-jar> <lib-jar>', file=sys.stderr)
        return 2
    run_script = Path(sys.argv[1]).read_text()
    artifact = json.loads(Path(sys.argv[2]).read_text())
    module_jar = Path(sys.argv[3])
    lib_jar = Path(sys.argv[4])
    member = 'org/opensearch/transport/netty4/Netty4TcpChannel.class'

    class_overlay_targets_lib = 'jar uf "${OPENSEARCH_DIST_HOME}/lib/opensearch-3.7.0-SNAPSHOT.jar"' in run_script
    extra_overlay_targets_explicit_jar = 'jar uf "${overlay_jar_path}"' in run_script
    module_has_class = jar_has(module_jar, member)
    lib_has_class = jar_has(lib_jar, member)

    stdout_text = (Path(artifact['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore')
    stderr_text = (Path(artifact['work_dir']) / 'opensearch' / 'stderr.log').read_text(errors='ignore')
    combined = stdout_text + '\n' + stderr_text
    match = JAR_LINE_RE.search(combined)
    jar_hell_pair = None
    if match:
        jar_hell_pair = [match.group(1).strip(), match.group(2).strip()]

    result = 'inconclusive'
    if class_overlay_targets_lib and extra_overlay_targets_explicit_jar and module_has_class and lib_has_class and artifact.get('blocker_class') == 'opensearch_startup_timeout' and jar_hell_pair:
        result = 'netty4tcpchannel_runtime_patch_path_is_script_level_split_target_but_current_install_tree_is_blocked_by_dual_jar_presence'

    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'class_overlay_targets_lib_opensearch_jar': class_overlay_targets_lib,
        'extra_overlay_targets_explicit_jar': extra_overlay_targets_explicit_jar,
        'module_jar_has_netty4tcpchannel': module_has_class,
        'lib_jar_has_netty4tcpchannel': lib_has_class,
        'failure_stage': artifact.get('failure_stage'),
        'blocker_class': artifact.get('blocker_class'),
        'jar_hell_pair': jar_hell_pair,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
