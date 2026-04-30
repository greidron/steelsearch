#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path('/home/ubuntu/steelsearch')
MATRIX = ROOT / 'docs/api-spec/generated/route-evidence-matrix.md'
OUT_JSON = ROOT / 'docs/api-spec/generated/runtime-route-ledger.json'
OUT_MD = ROOT / 'docs/api-spec/generated/runtime-route-ledger.md'
SAFE_METHODS = {'GET', 'HEAD'}
UNPROBEABLE_MARKERS = (' + ', 'String.format(', 'KNNPlugin.', 'ENDPOINT', 'URL_PATH', '(dynamic)')
PLACEHOLDERS = {
    'index': 'logs-compat',
    'indices': 'logs-compat',
    'id': 'doc-1',
    'repository': 'repo-compat',
    'snapshot': 'snap-compat',
    'target_snapshot': 'snap-compat-target',
    'name': 'logs-read',
    'alias': 'logs-*',
    'nodes': 'steelsearch-dev-node',
    'nodeId': 'steelsearch-dev-node',
    'node_id': 'steelsearch-dev-node',
    'metric': 'metadata',
    'index_metric': 'docs',
    'fields': 'message',
    'task_id': '1',
    'taskId': '1',
    'scroll_id': 'scroll-1',
    'block': 'read_only',
    'new_index': 'logs-compat-next',
    'target': 'logs-compat-target',
    'thread_pool_patterns': 'search',
    'awareness_attribute_name': 'zone',
    'awareness_attribute_value': 'zone-a',
    'attribute': 'zone',
    'metrics': 'http',
    'stat': 'model_count',
    'path': 'message',
    'index_uuid': 'uuid-1',
    'targetTier': 'hot',
}


def parse_matrix() -> list[dict[str, str]]:
    rows = []
    for line in MATRIX.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| '):
            continue
        parts = [p.strip() for p in line.strip().strip('|').split('|')]
        if parts[0] in {'family', '---'}:
            continue
        family, status, method, path, profile, entry = parts
        if status not in {'planned', 'stubbed'}:
            continue
        rows.append({
            'family': family,
            'source_status': status,
            'method': method,
            'path': path.strip('`'),
            'profile': profile,
            'entrypoint': entry,
        })
    return rows


def concrete_path(path: str) -> str | None:
    if any(marker in path for marker in UNPROBEABLE_MARKERS):
        return None
    out = path
    if not out.startswith('/'):
        return None
    for key, value in PLACEHOLDERS.items():
        out = out.replace('{' + key + '}', value)
    if '{' in out or '}' in out:
        return None
    return out


def http_request(base_url: str, method: str, path: str, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(base_url + path, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            return {'status': response.getcode(), 'body': body.decode('utf-8', errors='replace')}
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', errors='replace')
        return {'status': error.code, 'body': body}


def classify_probe(result: dict[str, Any]) -> str:
    body = result.get('body', '')
    if result['status'] == 404 and 'no_handler_found_exception' in body:
        return 'missing-route'
    return 'implemented-read'


def audit(base_url: str, timeout: float) -> dict[str, Any]:
    rows = parse_matrix()
    audited = []
    summary = defaultdict(int)
    by_family: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        path = row['path']
        method = row['method']
        if method not in SAFE_METHODS:
            runtime_status = 'requires-stateful-probe'
            concrete = None
            probe = None
        else:
            concrete = concrete_path(path)
            if concrete is None:
                runtime_status = 'unprobeable-expression'
                probe = None
            else:
                probe = http_request(base_url, method, concrete, timeout)
                runtime_status = classify_probe(probe)
        audited.append({
            **row,
            'concrete_path': concrete,
            'runtime_status': runtime_status,
            'probe': probe,
        })
        summary[runtime_status] += 1
        by_family[row['family']][runtime_status] += 1
    return {
        'base_url': base_url,
        'generated_from': str(MATRIX),
        'summary': dict(sorted(summary.items())),
        'by_family': {family: dict(sorted(counts.items())) for family, counts in sorted(by_family.items())},
        'routes': audited,
    }


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        '# Runtime Route Ledger',
        '',
        'This file records runtime-backed classification for the `planned` and `stubbed` REST inventory in `route-evidence-matrix.md`.',
        '',
        f"Base URL: `{report['base_url']}`",
        '',
        '## Summary',
        '',
        '| runtime_status | count |',
        '| --- | ---: |',
    ]
    for key, count in report['summary'].items():
        lines.append(f'| {key} | {count} |')
    lines.extend(['', '## By family', '', '| family | implemented-read | missing-route | requires-stateful-probe | unprobeable-expression |', '| --- | ---: | ---: | ---: | ---: |'])
    for family, counts in report['by_family'].items():
        lines.append(
            f"| {family} | {counts.get('implemented-read',0)} | {counts.get('missing-route',0)} | {counts.get('requires-stateful-probe',0)} | {counts.get('unprobeable-expression',0)} |"
        )
    lines.extend(['', '## Missing safe read/head routes', '', '| family | method | path | concrete_path | previous_status |', '| --- | --- | --- | --- | --- |'])
    for row in report['routes']:
        if row['runtime_status'] != 'missing-route':
            continue
        lines.append(
            f"| {row['family']} | {row['method']} | `{row['path']}` | `{row['concrete_path']}` | {row['source_status']} |"
        )
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:19200'
    report = audit(base_url.rstrip('/'), 2.0)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    write_markdown(report)
    print(json.dumps(report['summary'], sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
