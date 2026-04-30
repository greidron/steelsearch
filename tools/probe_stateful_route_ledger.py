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
    for case in fixture['cases']:
        result = request(base_url, case)
        runtime_status = classify(result)
        status = 'passed' if runtime_status == case['expected_runtime_status'] else 'failed'
        record = {
            **case,
            'inventory_path': case.get('inventory_path', case['path']),
            'runtime_status': runtime_status,
            'result': result,
            'status': status,
        }
        cases.append(record)
        summary[status] += 1
        by_family[case['family']][status] += 1
    payload = {
        'base_url': base_url,
        'fixture': str(FIXTURE),
        'setup': setup_results,
        'cases': cases,
        'summary': dict(summary),
        'by_family': {family: dict(counts) for family, counts in sorted(by_family.items())},
    }
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(payload['summary'], sort_keys=True))
    return 0 if payload['summary'].get('failed', 0) == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
