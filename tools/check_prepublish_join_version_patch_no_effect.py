#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def publish_response_body_hex(report_path: str):
    art = json.loads(Path(report_path).read_text())
    for cap in art['steelsearch_transport_capture']:
        rf = cap.get('response_frame')
        if isinstance(rf, dict) and rf.get('action_hint') == 'internal:cluster/coordination/publish_state':
            return rf.get('body_hex')
    return None


def count(stdout: str, needle: str) -> int:
    return stdout.count(needle)


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_prepublish_join_version_patch_no_effect.py <before.json> <after.json>', file=sys.stderr)
        return 2
    before = json.loads(Path(sys.argv[1]).read_text())
    after = json.loads(Path(sys.argv[2]).read_text())
    before_stdout = (Path(before['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore')
    after_stdout = (Path(after['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore')
    before_body = publish_response_body_hex(sys.argv[1])
    after_body = publish_response_body_hex(sys.argv[2])
    result = (
        'prepublish_join_lastAcceptedVersion_patch_changes_publish_response_payload_but_does_not_open_publish_response_acceptance'
        if before_body != after_body
        and count(after_stdout, 'handlePublishResponse: accepted publish response') == 0
        and count(after_stdout, 'handlePublishResponse: value committed') == 0
        else 'inconclusive'
    )
    print({
        'before_work_dir': before['work_dir'],
        'after_work_dir': after['work_dir'],
        'before_publish_response_body_hex': before_body,
        'after_publish_response_body_hex': after_body,
        'body_changed': before_body != after_body,
        'after_accepted_publish_response_count': count(after_stdout, 'handlePublishResponse: accepted publish response'),
        'after_committed_value_count': count(after_stdout, 'handlePublishResponse: value committed'),
        'after_failed_to_commit_cluster_state_count': count(after_stdout, 'failed to commit cluster state'),
        'result': result,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
