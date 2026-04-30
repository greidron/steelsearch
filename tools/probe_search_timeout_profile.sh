#!/usr/bin/env bash
set -euo pipefail
IMAGE="${OPENSEARCH_TIMEOUT_PROBE_IMAGE:-opensearchproject/opensearch:2.19.0}"
CONTAINER="${OPENSEARCH_TIMEOUT_PROBE_CONTAINER:-ss-timeout-probe}"
PORT="${OPENSEARCH_TIMEOUT_PROBE_PORT:-9325}"
DOC_COUNT="${OPENSEARCH_TIMEOUT_PROBE_DOC_COUNT:-50000}"
RUNS="${OPENSEARCH_TIMEOUT_PROBE_RUNS:-5}"
OUT_DIR="${OPENSEARCH_TIMEOUT_PROBE_OUT_DIR:-target/search-timeout-probe}"
OUT_FILE="${OUT_DIR}/results.json"
PASSWORD="${OPENSEARCH_TIMEOUT_PROBE_PASSWORD:-StrongPassw0rd!}"
mkdir -p "$OUT_DIR"
cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker run -d --name "$CONTAINER" \
  -e discovery.type=single-node \
  -e plugins.security.disabled=true \
  -e OPENSEARCH_INITIAL_ADMIN_PASSWORD="$PASSWORD" \
  -p "${PORT}:9200" \
  "$IMAGE" >/dev/null

python3 - <<'PY' "$PORT" "$DOC_COUNT" "$RUNS" "$OUT_FILE" "$IMAGE"
import json, sys, time, urllib.request, urllib.error
port, doc_count, runs, out_file, image = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
base = f'http://127.0.0.1:{port}'
for _ in range(180):
    try:
        with urllib.request.urlopen(base, timeout=2) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('opensearch not ready')

def req(method, path, body=None, ctype='application/json'):
    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method, headers={'Content-Type': ctype})
    with urllib.request.urlopen(request, timeout=300) as response:
        raw = response.read()
        return json.loads(raw or b'{}')

try:
    req('DELETE', '/timeout-probe')
except Exception:
    pass
req('PUT', '/timeout-probe', {
    'settings': {'number_of_shards': 2, 'number_of_replicas': 0},
    'mappings': {'properties': {'message': {'type': 'text'}}},
})
lines = []
for i in range(doc_count):
    lines.append(json.dumps({'index': {'_index': 'timeout-probe', '_id': str(i)}}))
    lines.append(json.dumps({'message': 'alpha beta gamma delta zeta zeta zeta zeta zeta zeta zeta zeta ' + str(i)}))
req('POST', '/_bulk?refresh=true', ('\n'.join(lines) + '\n').encode(), 'application/x-ndjson')
results = []
for run in range(1, runs + 1):
    body = req('POST', '/timeout-probe/_search', {
        'query': {'match_phrase': {'message': 'alpha beta gamma delta zeta'}},
        'timeout': '1micros',
    })
    results.append({
        'run': run,
        'timed_out': body.get('timed_out'),
        'shards': body.get('_shards'),
        'total': body.get('hits', {}).get('total'),
    })
summary = {
    'image': image,
    'doc_count': doc_count,
    'runs': runs,
    'results': results,
    'timed_out_true_runs': sum(1 for r in results if r.get('timed_out') is True),
}
with open(out_file, 'w', encoding='utf-8') as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
PY
