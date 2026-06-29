#!/usr/bin/env bash
set -euo pipefail

OPENSEARCH_ROOT=${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}
DISTRO_ROOT="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
LIB_CP="${DISTRO_ROOT}/lib/*"
CACHE_DIR="${TMPDIR:-/tmp}/steelsearch-java-response-cache"
CLASS_NAME="BuildQueryPhaseResultV2"
JAVA_FILE="${CACHE_DIR}/${CLASS_NAME}.java"
CLASS_FILE="${CACHE_DIR}/${CLASS_NAME}.class"

local_node_id=""
index_name=""
index_uuid=""
shard_id=""
total_hits=""
context_session_id="steelsearch-phase-query"
context_id="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local-node-id) local_node_id="$2"; shift 2 ;;
    --index-name) index_name="$2"; shift 2 ;;
    --index-uuid) index_uuid="$2"; shift 2 ;;
    --shard-id) shard_id="$2"; shift 2 ;;
    --total-hits) total_hits="$2"; shift 2 ;;
    --context-session-id) context_session_id="$2"; shift 2 ;;
    --context-id) context_id="$2"; shift 2 ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "${local_node_id}" && -n "${index_name}" && -n "${index_uuid}" && -n "${shard_id}" && -n "${total_hits}" ]] || {
  echo "missing required args" >&2
  exit 2
}

mkdir -p "${CACHE_DIR}"

if [[ ! -f "${CLASS_FILE}" ]]; then
cat > "${JAVA_FILE}" <<'JAVA'
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.TotalHits;
import org.opensearch.action.OriginalIndices;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.common.lucene.search.TopDocsAndMaxScore;
import org.opensearch.search.DocValueFormat;
import org.opensearch.search.SearchShardTarget;
import org.opensearch.search.internal.ShardSearchContextId;
import org.opensearch.search.query.QuerySearchResult;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.core.index.Index;
import org.opensearch.core.index.shard.ShardId;

public class BuildQueryPhaseResultV2 {
    private static String hex(byte[] bytes, int offset, int length) {
        StringBuilder sb = new StringBuilder(length * 2);
        for (int i = offset; i < offset + length; i++) {
            sb.append(String.format("%02x", bytes[i]));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        String localNodeId = null;
        String indexName = null;
        String indexUuid = null;
        int shardId = -1;
        long totalHits = 0L;
        for (int i = 0; i < args.length; i += 2) {
            switch (args[i]) {
                case "--local-node-id": localNodeId = args[i + 1]; break;
                case "--index-name": indexName = args[i + 1]; break;
                case "--index-uuid": indexUuid = args[i + 1]; break;
                case "--shard-id": shardId = Integer.parseInt(args[i + 1]); break;
                case "--total-hits": totalHits = Long.parseLong(args[i + 1]); break;
                case "--context-session-id": break;
                case "--context-id": break;
                default: throw new IllegalArgumentException("unknown arg " + args[i]);
            }
        }

        String contextSessionId = "steelsearch-phase-query";
        long contextId = 1L;
        for (int i = 0; i < args.length; i += 2) {
            switch (args[i]) {
                case "--context-session-id": contextSessionId = args[i + 1]; break;
                case "--context-id": contextId = Long.parseLong(args[i + 1]); break;
                default: break;
            }
        }

        QuerySearchResult querySearchResult = new QuerySearchResult(
            new ShardSearchContextId(contextSessionId, contextId),
            new SearchShardTarget(localNodeId, new ShardId(new Index(indexName, indexUuid), shardId), null, OriginalIndices.NONE),
            null
        );
        TopDocs topDocs = new TopDocs(new TotalHits(totalHits, TotalHits.Relation.EQUAL_TO), new ScoreDoc[0]);
        querySearchResult.topDocs(new TopDocsAndMaxScore(topDocs, Float.NaN), new DocValueFormat[0]);
        querySearchResult.setShardIndex(shardId);

        BytesStreamOutput out = new BytesStreamOutput();
        querySearchResult.writeTo(out);
        BytesReference bytesRef = out.bytes();
        var ref = bytesRef.toBytesRef();
        System.out.println(hex(ref.bytes, ref.offset, ref.length));
    }
}
JAVA

javac -proc:none -cp "${LIB_CP}" "${JAVA_FILE}"
fi

java -cp "${LIB_CP}:${CACHE_DIR}" "${CLASS_NAME}" \
  --local-node-id "${local_node_id}" \
  --index-name "${index_name}" \
  --index-uuid "${index_uuid}" \
  --shard-id "${shard_id}" \
  --total-hits "${total_hits}" \
  --context-session-id "${context_session_id}" \
  --context-id "${context_id}"
