#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
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


def json_pointer_get(value: Any, pointer: str) -> Any:
    current = value
    for part in pointer.strip('/').split('/'):
        if part == '':
            continue
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict):
            if part == 'pit_id' and part not in current and current.get('id') is not None:
                current = current['id']
                continue
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(pointer)
    return current


def materialize(value: Any, captures: dict[str, Any]) -> Any:
    if isinstance(value, str):
        if value.startswith('${') and value.endswith('}'):
            return captures[value[2:-1]]
        return value
    if isinstance(value, list):
        return [materialize(item, captures) for item in value]
    if isinstance(value, dict):
        return {key: materialize(item, captures) for key, item in value.items()}
    return value


def materialize_case(case: dict[str, Any], captures: dict[str, Any]) -> dict[str, Any]:
    return {key: materialize(value, captures) for key, value in case.items()}


def request(base_url: str, case: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    data, content_type = encode_body(case)
    req = urllib.request.Request(base_url + case['path'], data=data, method=case['method'])
    if content_type:
        req.add_header('Content-Type', content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode('utf-8', errors='replace')
            return {'status': response.getcode(), 'body': body}
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', errors='replace')
        return {'status': error.code, 'body': body}
    except (TimeoutError, socket.timeout, urllib.error.URLError) as error:
        return {'status': 0, 'body': '', 'error': type(error).__name__}


def capture_values(case: dict[str, Any], result: dict[str, Any], captures: dict[str, Any]) -> None:
    capture_json = case.get('capture_json')
    if not isinstance(capture_json, dict):
        return
    body = json.loads(result.get('body') or 'null')
    for name, pointer in capture_json.items():
        try:
            captures[str(name)] = json_pointer_get(body, str(pointer))
        except (KeyError, IndexError, TypeError, ValueError):
            continue


def normalize_pit_report_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key == 'pit_id':
                normalized[key] = '<pit_id>'
            elif key == 'creation_time':
                normalized[key] = 0
            else:
                normalized[key] = normalize_pit_report_value(item)
        return normalized
    if isinstance(value, list):
        return [normalize_pit_report_value(item) for item in value]
    return value


def normalize_result_for_report(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    probe_surface = ' '.join(
        str(case.get(key, '')) for key in ('name', 'path', 'inventory_path')
    )
    if 'point_in_time' not in probe_surface and 'pit' not in probe_surface:
        return result
    try:
        body = json.loads(result.get('body') or 'null')
    except json.JSONDecodeError:
        return result
    return {
        **result,
        'body': json.dumps(
            normalize_pit_report_value(body),
            separators=(',', ':'),
            sort_keys=True,
        ),
    }


def classify(result: dict[str, Any]) -> str:
    if result['status'] == 0:
        return 'unreachable'
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", nargs="?", help="legacy Steelsearch base URL")
    parser.add_argument("--steelsearch-url", help="Steelsearch base URL")
    parser.add_argument("--opensearch-url", help="optional OpenSearch base URL for case-level route parity evidence")
    parser.add_argument("--fixture", default=str(FIXTURE))
    parser.add_argument("--report", "--output", dest="report", default=str(REPORT))
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--case", action="append", help="case name to run; may be repeated")
    return parser.parse_args()


def select_cases(fixture: dict[str, Any], case_names: list[str] | None) -> list[dict[str, Any]]:
    cases = list(fixture['cases'])
    if not case_names:
        return cases
    cases_by_name = {case.get('name'): case for case in cases}
    missing = sorted(set(case_names) - set(cases_by_name))
    if missing:
        raise SystemExit(f"unknown stateful route probe case(s): {', '.join(missing)}")
    return [cases_by_name[name] for name in case_names]


def main() -> int:
    args = parse_args()
    base_url = (args.steelsearch_url or args.base_url or 'http://127.0.0.1:19200').rstrip('/')
    opensearch_url = args.opensearch_url.rstrip('/') if args.opensearch_url else None
    fixture_path = Path(args.fixture)
    report_path = Path(args.report)
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    captures: dict[str, Any] = {}
    opensearch_captures: dict[str, Any] = {}
    setup_results = [
        {**step, 'result': request(base_url, materialize_case(step, captures), args.timeout)}
        for step in fixture.get('setup', [])
    ]
    for record in setup_results:
        capture_values(record, record['result'], captures)
    opensearch_setup_results = []
    if opensearch_url:
        opensearch_setup_results = [
            {
                **step,
                'result': request(
                    opensearch_url,
                    materialize_case(step, opensearch_captures),
                    args.timeout,
                ),
            }
            for step in fixture.get('setup', [])
        ]
        for record in opensearch_setup_results:
            capture_values(record, record['result'], opensearch_captures)
    cases = []
    summary = defaultdict(int)
    by_family: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    semantic_coverage: dict[str, set[str]] = defaultdict(set)
    for case in select_cases(fixture, args.case):
        case_setup_results = [
            {
                **step,
                'result': request(
                    base_url,
                    materialize_case(step, captures),
                    args.timeout,
                ),
            }
            for step in case.get('setup', [])
        ]
        for record in case_setup_results:
            capture_values(record, record['result'], captures)
        request_case = materialize_case(case, captures)
        result = request(base_url, request_case, args.timeout)
        capture_values(case, result, captures)
        report_result = normalize_result_for_report(case, result)
        runtime_status = classify(result)
        status = 'passed' if runtime_status == case['expected_runtime_status'] else 'failed'
        targets = {
            'steelsearch': {
                'runtime_status': runtime_status,
                'result': report_result,
            },
        }
        opensearch_case_setup_results = []
        if opensearch_url and case.get('opensearch_comparison') is True:
            opensearch_case_setup_results = [
                {
                    **step,
                    'result': request(
                        opensearch_url,
                        materialize_case(step, opensearch_captures),
                        args.timeout,
                    ),
                }
                for step in case.get('setup', [])
            ]
            for record in opensearch_case_setup_results:
                capture_values(record, record['result'], opensearch_captures)
            opensearch_case = materialize_case(case, opensearch_captures)
            opensearch_result = request(opensearch_url, opensearch_case, args.timeout)
            capture_values(case, opensearch_result, opensearch_captures)
            opensearch_runtime_status = classify(opensearch_result)
            opensearch_report_result = normalize_result_for_report(case, opensearch_result)
            targets['opensearch'] = {
                'runtime_status': opensearch_runtime_status,
                'result': opensearch_report_result,
            }
            if status == 'passed' and opensearch_runtime_status != runtime_status:
                status = 'failed'
        semantic_tags = infer_semantic_tags(case)
        inventory_path = case.get('inventory_path', case['path'])
        record = {
            **case,
            'inventory_path': inventory_path,
            'runtime_status': runtime_status,
            'result': report_result,
            'status': status,
            'semantic_tags': semantic_tags,
            'targets': targets,
        }
        if case_setup_results:
            record['setup_results'] = case_setup_results
        if opensearch_case_setup_results:
            record['opensearch_setup_results'] = opensearch_case_setup_results
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
        'targets': {
            'steelsearch': base_url,
            **({'opensearch': opensearch_url} if opensearch_url else {}),
        },
        'fixture': str(fixture_path),
        'setup': setup_results,
        **({'opensearch_setup': opensearch_setup_results} if opensearch_setup_results else {}),
        'cases': cases,
        'summary': dict(summary),
        'by_family': {family: dict(counts) for family, counts in sorted(by_family.items())},
        'semantic_coverage_required': list(SEMANTIC_COVERAGE_KEYS),
        'semantic_coverage_routes': semantic_routes,
        'semantic_coverage_missing': [route for route in semantic_routes if route['missing']],
        'semantic_coverage_summary': dict(semantic_summary),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        **payload['summary'],
        'semantic_complete': payload['semantic_coverage_summary'].get('complete', 0),
        'semantic_incomplete': payload['semantic_coverage_summary'].get('incomplete', 0),
    }, sort_keys=True))
    return 0 if payload['summary'].get('failed', 0) == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
