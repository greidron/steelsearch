#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:?image tag required}"
OUT="${2:?output path required}"
NAME="runtime-fields-probe-$(date +%s)-$$"
HOST="127.0.0.1"
PORT="${PROBE_PORT:-29250}"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker rm -f "$NAME" >/dev/null 2>&1 || true
CID=$(docker run -d --name "$NAME" -p "${PORT}:9200" \
  -e discovery.type=single-node \
  -e DISABLE_INSTALL_DEMO_CONFIG=true \
  -e DISABLE_SECURITY_PLUGIN=true \
  -e OPENSEARCH_JAVA_OPTS='-Xms512m -Xmx512m' \
  "$IMAGE")

BASE_URL="http://${HOST}:${PORT}"
READY=0
for _ in $(seq 1 90); do
  if curl -fsS "$BASE_URL/" >/tmp/runtime-fields-probe-root.json 2>/dev/null; then
    READY=1
    break
  fi
  sleep 2
done

if [[ "$READY" != "1" ]]; then
  jq -n \
    --arg image "$IMAGE" \
    --arg container "$CID" \
    '{image:$image, status:"startup_failed", container:$container}' > "$OUT"
  exit 0
fi

curl -fsS -XDELETE "$BASE_URL/logs-compat" >/dev/null 2>&1 || true
curl -fsS -XPUT "$BASE_URL/logs-compat" \
  -H 'Content-Type: application/json' \
  -d '{"settings":{"index":{"number_of_shards":1,"number_of_replicas":0}},"mappings":{"properties":{"message":{"type":"text"},"service":{"type":"keyword"},"level":{"type":"keyword"},"ts":{"type":"date"}}}}' >/tmp/runtime-fields-probe-create.json
curl -fsS -XPOST "$BASE_URL/logs-compat/_doc/log-2?refresh=true" \
  -H 'Content-Type: application/json' \
  -d '{"message":"checkout service payment timeout","service":"checkout","level":"warn","ts":"2026-04-22T00:01:00Z"}' >/tmp/runtime-fields-probe-doc.json
HTTP_CODE=$(curl -sS -o /tmp/runtime-fields-probe-search.json -w '%{http_code}' \
  -XPOST "$BASE_URL/logs-compat/_search" \
  -H 'Content-Type: application/json' \
  -d '{"runtime_mappings":{"computed_level":{"type":"keyword","script":{"source":"emit(doc['\''level'\''].value)"}}},"query":{"term":{"computed_level":"warn"}}}')

jq -n \
  --arg image "$IMAGE" \
  --arg base_url "$BASE_URL" \
  --argjson root "$(cat /tmp/runtime-fields-probe-root.json)" \
  --argjson response "$(cat /tmp/runtime-fields-probe-search.json)" \
  --arg http_code "$HTTP_CODE" \
  '{image:$image, base_url:$base_url, root:$root, search_status:($http_code|tonumber), search_response:$response}' > "$OUT"
