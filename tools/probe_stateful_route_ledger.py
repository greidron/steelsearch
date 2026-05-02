#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path('/home/ubuntu/steelsearch')
FIXTURE = ROOT / 'tools/fixtures/runtime-stateful-probe.json'
REPORT = ROOT / 'docs/api-spec/generated/runtime-stateful-route-probe-report.json'
SEMANTIC_COVERAGE_KEYS = ('happy-path', 'error-path', 'idempotency-or-selector')


def encode_body(case: dict[str, Any]) -> tuple[bytes | None, str | None]:
    if 'raw_body' in case:
        return case['raw_body'].encode('utf-8'), case.get('content_type', 'application/json')
    if 'body' in case:
        return json.dumps(case['body']).encode('utf-8'), 'application/json'
    return None, None


def request(base_url: str, case: dict[str, Any]) -> dict[str, Any]:
    data, content_type = encode_body(case)
    req = urllib.request.Request(base_url + case['path'], data=data, method=case['method'])
    if content_type:
        req.add_header('Content-Type', content_type)
    try:
        with urllib.request.urlopen(req, timeout=3.0) as response:
            body = response.read().decode('utf-8', errors='replace')
            return {'status': response.getcode(), 'body': body}
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', errors='replace')
        return {'status': error.code, 'body': body}


def classify(result: dict[str, Any]) -> str:
    if result['status'] == 404 and 'no_handler_found_exception' in result.get('body', ''):
        return 'missing-route'
    return 'stateful-route-present'


def infer_semantic_tags(case: dict[str, Any]) -> list[str]:
    explicit = case.get('semantic_tags')
    if isinstance(explicit, list) and explicit:
        return [str(tag) for tag in explicit]

    name = str(case.get('name', '')).lower()
    tags: list[str] = []
    if any(token in name for token in (
        'error',
        'missing',
        'invalid',
        'unmatched',
        'unknown',
        'non_cancellable',
        'redefine',
        'conflict',
        'fail_closed',
    )):
        tags.append('error-path')
    if any(token in name for token in (
        'repeat',
        'repeated',
        'wildcard',
        'selector',
        'noop',
    )):
        tags.append('idempotency-or-selector')
    if not tags:
        tags.append('happy-path')
    return tags


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:19200').rstrip('/')
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    setup_results = [
        {**step, 'result': request(base_url, step)}
        for step in fixture.get('setup', [])
    ]
    cases = []
    summary = defaultdict(int)
    by_family: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    semantic_coverage: dict[str, set[str]] = defaultdict(set)
    for case in fixture['cases']:
        result = request(base_url, case)
        runtime_status = classify(result)
        status = 'passed' if runtime_status == case['expected_runtime_status'] else 'failed'
        semantic_tags = infer_semantic_tags(case)
        inventory_path = case.get('inventory_path', case['path'])
        record = {
            **case,
            'inventory_path': inventory_path,
            'runtime_status': runtime_status,
            'result': result,
            'status': status,
            'semantic_tags': semantic_tags,
        }
        cases.append(record)
        summary[status] += 1
        by_family[case['family']][status] += 1
        if status == 'passed':
            semantic_coverage[inventory_path].update(semantic_tags)

    semantic_routes = []
    semantic_summary = defaultdict(int)
    for inventory_path in sorted(semantic_coverage.keys()):
        present = sorted(semantic_coverage[inventory_path])
        missing = [key for key in SEMANTIC_COVERAGE_KEYS if key not in semantic_coverage[inventory_path]]
        route_record = {
            'inventory_path': inventory_path,
            'present': present,
            'missing': missing,
            'complete': not missing,
        }
        semantic_routes.append(route_record)
        semantic_summary['complete' if not missing else 'incomplete'] += 1

    payload = {
        'base_url': base_url,
        'fixture': str(FIXTURE),
        'setup': setup_results,
        'cases': cases,
        'summary': dict(summary),
        'by_family': {family: dict(counts) for family, counts in sorted(by_family.items())},
        'semantic_coverage_required': list(SEMANTIC_COVERAGE_KEYS),
        'semantic_coverage_routes': semantic_routes,
        'semantic_coverage_missing': [route for route in semantic_routes if route['missing']],
        'semantic_coverage_summary': dict(semantic_summary),
    }
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        **payload['summary'],
        'semantic_complete': payload['semantic_coverage_summary'].get('complete', 0),
        'semantic_incomplete': payload['semantic_coverage_summary'].get('incomplete', 0),
    }, sort_keys=True))
    return 0 if payload['summary'].get('failed', 0) == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
