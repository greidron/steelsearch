#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict, OrderedDict
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
TASKS = ROOT / 'tasks.md'
MATRIX = ROOT / 'docs/api-spec/generated/route-evidence-matrix.md'
LEDGER = ROOT / 'docs/api-spec/generated/runtime-route-ledger.json'
PROBE_REPORT = ROOT / 'docs/api-spec/generated/runtime-stateful-route-probe-report.json'
OUT_JSON = ROOT / 'docs/api-spec/generated/runtime-missing-route-priority.json'
OUT_MD = ROOT / 'docs/api-spec/generated/runtime-missing-route-priority.md'
ANCHOR_TEXT = 'Swagger/runtime route parity backlog (generated from `docs/api-spec/generated/route-evidence-matrix.md` planned+stubbed inventory)'

FAMILY_TITLES = {
    'root-cluster-node':'root/cluster/node runtime route parity',
    'index-and-metadata':'index/metadata runtime route parity',
    'document-and-bulk':'document/bulk runtime route parity',
    'search':'search runtime route parity',
    'snapshot-migration-interop':'snapshot/migration helper runtime route parity',
    'vector-and-ml':'vector/ML runtime route parity',
    'misc':'misc runtime route parity',
}
FAMILY_PLANS = {
    'root-cluster-node':('`standalone_runtime.rs` unit tests로 exact route dispatch, path parameter, error envelope를 고정','`tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node` 또는 dedicated root compat fixture로 OpenSearch compare 추가'),
    'index-and-metadata':('index/template/alias/data-stream state mutation과 readback을 unit test로 고정','`tools/run-phase-a-acceptance-harness.sh --scope index-metadata` fixture에 OpenSearch compare와 setup/teardown 추가'),
    'document-and-bulk':('single-doc, bulk, refresh, by-query family의 happy-path/error-path를 unit test로 고정','`tools/run-phase-a-acceptance-harness.sh --scope document-write-path`와 stateful compare fixture로 OpenSearch parity 검증'),
    'search':('query/session/template/scroll/PIT/count/explain route dispatch와 validation을 unit test로 고정','`tools/run-phase-a-acceptance-harness.sh --scope search` 및 `--scope search-execution` fixture에 OpenSearch compare 추가'),
    'snapshot-migration-interop':('ingest/painless helper route의 request validation과 transcript shape를 unit test로 고정','`tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration` fixture에 OpenSearch compare 추가'),
    'vector-and-ml':('plugin route path normalization과 request validation을 unit test로 고정','`tools/run-phase-a-acceptance-harness.sh --scope vector-ml` 또는 dedicated plugin compare runner로 OpenSearch surface compare 추가'),
    'misc':('misc route의 path normalization, method matrix, fail-closed behavior를 unit test로 고정','family별 dedicated smoke/integration runner를 추가하고 가능한 surface는 OpenSearch compare, 불가능한 것은 explicit out-of-scope/defer로 분류'),
}
FAMILY_ORDER = ['root-cluster-node','index-and-metadata','document-and-bulk','search','snapshot-migration-interop','vector-and-ml','misc']
RUNTIME_STATUS_ORDER = {'missing-route':0,'requires-stateful-probe':1,'unprobeable-expression':2,'implemented-read':3,'implemented-stateful':4,'unknown':5}
PATH_NORMALIZATION = {
    '/ + ENDPOINT': '/_rank_eval',
    '/{index}/ + ENDPOINT': '/{index}/_rank_eval',
    '"/" + ENDPOINT': '/_rank_eval',
    '"/{index}/" + ENDPOINT': '/{index}/_rank_eval',
    'String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, CLEAR_CACHE, INDEX)': '/_plugins/_knn/clear_cache/{index}',
    'String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)': '/_plugins/_knn/models/{model_id}',
    'String.format(Locale.ROOT, "%s/%s/{%s}/_train", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)': '/_plugins/_knn/models/{model_id}/_train',
    'String.format(Locale.ROOT, "%s/%s/_train", KNNPlugin.KNN_BASE_URI, MODELS)': '/_plugins/_knn/models/_train',
    'String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)': '/_plugins/_knn/models/_search',
    'KNNPlugin.KNN_BASE_URI + "/stats/"': '/_plugins/_knn/stats',
    'KNNPlugin.KNN_BASE_URI + "/stats/{stat}"': '/_plugins/_knn/stats/{stat}',
    'KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/"': '/_plugins/_knn/{nodeId}/stats',
    'KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/{stat}"': '/_plugins/_knn/{nodeId}/stats/{stat}',
    'KNNPlugin.KNN_BASE_URI + URL_PATH': '/_plugins/_knn/warmup',
    '_wlm/workload_group/': '/_wlm/workload_group',
    '_wlm/workload_group/{name}': '/_wlm/workload_group/{name}',
    '_wlm/stats': '/_wlm/stats',
    '_wlm/{nodeId}/stats': '/_wlm/{nodeId}/stats',
    '_wlm/stats/{workloadGroupId}': '/_wlm/stats/{workloadGroupId}',
    '_wlm/{nodeId}/stats/{workloadGroupId}': '/_wlm/{nodeId}/stats/{workloadGroupId}',
    '_list/wlm_stats': '/_list/wlm_stats',
    '_list/wlm_stats/{nodeId}/stats': '/_list/wlm_stats/{nodeId}/stats',
    '_list/wlm_stats/stats/{workloadGroupId}': '/_list/wlm_stats/stats/{workloadGroupId}',
    '_list/wlm_stats/{nodeId}/stats/{workloadGroupId}': '/_list/wlm_stats/{nodeId}/stats/{workloadGroupId}',
    '/{index}/_tier/ + targetTier': '/{index}/_tier/{targetTier}',
}


def normalize_path(path: str) -> str:
    normalized = PATH_NORMALIZATION.get(path, path)
    normalized = normalized.rstrip('/') or '/'
    if not normalized.startswith('/'):
        normalized = '/' + normalized
    return normalized


def parse_matrix():
    rows=[]
    for line in MATRIX.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| '):
            continue
        parts=[p.strip() for p in line.strip().strip('|').split('|')]
        if parts[0] in {'family','---'}:
            continue
        family,status,method,path,profile,entry=parts
        if status not in {'planned','stubbed','implemented-read'}:
            continue
        if "/_opensearch_dashboards" in path and "route.getPath(" in path:
            continue
        rows.append({'family':family,'source_status':status,'method':method,'path':path.strip('`')})
    return rows


def load_ledger():
    data=json.loads(LEDGER.read_text(encoding='utf-8'))
    mapping = {}
    for route in data['routes']:
        method = route['method']
        path = route['path']
        runtime_status = route['runtime_status']
        mapping[(method, path)] = runtime_status
        mapping[(method, normalize_path(path))] = runtime_status
    return mapping, data['summary'], data['by_family']


def load_stateful_probe():
    if not PROBE_REPORT.exists():
        return {}
    data=json.loads(PROBE_REPORT.read_text(encoding='utf-8'))
    result={}
    for case in data.get('cases', []):
        if case.get('runtime_status') != 'stateful-route-present':
            continue
        inventory_path = case.get('inventory_path')
        method = case.get('method')
        if inventory_path and method:
            result[(method, inventory_path)] = 'implemented-stateful'
    return result


def priority_score(path: str) -> int:
    if path.startswith('/_cat/'):
        return 0
    if path.startswith('/_cluster/') or path.startswith('/_nodes/') or path.startswith('/_tasks'):
        return 10
    if '/_search/template' in path or '/_render/template' in path or '/_msearch/template' in path:
        return 20
    if path.startswith('/_search') or '/_search' in path or '/_count' in path or '/_validate/query' in path:
        return 30
    if '/_mapping' in path or '/_settings' in path or '/_stats' in path or '/_segments' in path or '/_recovery' in path:
        return 40
    if '/_ingest' in path or '/_scripts' in path:
        return 50
    return 60


def render_priority(rows):
    grouped=defaultdict(list)
    for row in rows:
        if row['runtime_status']!='missing-route':
            continue
        grouped[row['family']].append(row)
    for fam in grouped:
        grouped[fam].sort(key=lambda row:(priority_score(row['path']), row['path'], row['method']))
    payload={fam:[{'method':r['method'],'path':r['path']} for r in grouped[fam]] for fam in FAMILY_ORDER if grouped.get(fam)}
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    lines=['# Runtime Missing Route Priority','','This file lists safe read/head routes that currently probe as `missing-route`, ordered by family and implementation priority.','']
    for fam in FAMILY_ORDER:
        items=grouped.get(fam)
        if not items:
            continue
        lines.extend([f'## {fam}',''])
        for row in items:
            lines.append(f"- `{row['path']}` ({row['method']})")
        lines.append('')
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')


def rewrite_tasks(rows, summary, by_family):
    grouped=defaultdict(list)
    for row in rows:
        grouped[row['family']].append(row)
    lines=[]
    all_complete = all(
        row['runtime_status'] in {'implemented-read', 'implemented-stateful'}
        for row in rows
    )
    lines.append(f"- [{'x' if all_complete else ' '}] {ANCHOR_TEXT}")
    lines.append(f"  - [x] canonical planned/stubbed inventory를 runtime-backed route ledger로 재분류 (`docs/api-spec/generated/runtime-route-ledger.{ '{json,md}' }` 생성)")
    lines.append('  - [x] runtime-backed ledger의 `implemented-read` 항목을 `route-evidence-matrix`/Swagger 상태와 동기화')
    lines.append('  - [x] runtime-backed ledger의 `missing-route` 항목을 family별 구현 우선순위로 재정렬하고 false positive를 제거 (`docs/api-spec/generated/runtime-missing-route-priority.{json,md}` 생성, implemented-read 항목은 `[x]`로 재분류)')
    lines.append('  - [x] runtime-backed ledger의 `requires-stateful-probe` 항목에 대해 stateful fixture/probe runner를 추가')
    for fam in FAMILY_ORDER:
        items=grouped.get(fam)
        if not items:
            continue
        title=FAMILY_TITLES[fam]
        unit, integ = FAMILY_PLANS[fam]
        family_complete = all(
            row['runtime_status'] in {'implemented-read', 'implemented-stateful'}
            for row in items
        )
        lines.append(f"  - [{'x' if family_complete else ' '}] {title}")
        lines.append(f'    - [x] unit test plan: {unit}')
        lines.append(f'    - [x] integration/OpenSearch compare plan: {integ}')
        lines.append(f"    - [x] runtime-backed summary: implemented-read={by_family.get(fam,{}).get('implemented-read',0)}, missing-route={by_family.get(fam,{}).get('missing-route',0)}, requires-stateful-probe={by_family.get(fam,{}).get('requires-stateful-probe',0)}, unprobeable-expression={by_family.get(fam,{}).get('unprobeable-expression',0)}")
        agg=OrderedDict()
        for row in sorted(items, key=lambda r:(RUNTIME_STATUS_ORDER.get(r['runtime_status'],4), priority_score(r['path']), r['path'], r['method'])):
            agg.setdefault(row['path'], []).append((row['method'], row['runtime_status']))
        for path, methods in agg.items():
            status = sorted([s for _,s in methods], key=lambda s:RUNTIME_STATUS_ORDER.get(s,4))[0]
            mark = 'x' if status in {'implemented-read', 'implemented-stateful'} else ' '
            method_text=', '.join(sorted(m for m,_ in methods))
            lines.append(f'    - [{mark}] `{path}` ({method_text}) [{status}]')
    text = TASKS.read_text(encoding='utf-8')
    idx = text.index(ANCHOR_TEXT) - 6
    TASKS.write_text(text[:idx] + '\n'.join(lines) + '\n', encoding='utf-8')


def main():
    matrix_rows=parse_matrix()
    ledger_map, summary, by_family = load_ledger()
    stateful_probe_map = load_stateful_probe()
    rows=[]
    for row in matrix_rows:
        normalized_path = normalize_path(row['path'])
        runtime_status = stateful_probe_map.get((row['method'], row['path']))
        if runtime_status is None:
            runtime_status = stateful_probe_map.get((row['method'], normalized_path))
        if runtime_status is None:
            runtime_status = ledger_map.get((row['method'], row['path']))
        if runtime_status is None:
            runtime_status = ledger_map.get((row['method'], normalized_path), 'unknown')
        row = {**row, 'path': normalized_path, 'runtime_status': runtime_status}
        rows.append(row)
    render_priority(rows)
    rewrite_tasks(rows, summary, by_family)
    print(json.dumps(summary, sort_keys=True))

if __name__ == '__main__':
    main()
