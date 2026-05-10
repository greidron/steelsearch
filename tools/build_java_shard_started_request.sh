#!/usr/bin/env bash
set -euo pipefail

INDEX_NAME=""
INDEX_UUID=""
SHARD_ID=""
ALLOCATION_ID=""
PRIMARY_TERM="0"
MESSAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --index-name) INDEX_NAME="$2"; shift 2 ;;
    --index-uuid) INDEX_UUID="$2"; shift 2 ;;
    --shard-id) SHARD_ID="$2"; shift 2 ;;
    --allocation-id) ALLOCATION_ID="$2"; shift 2 ;;
    --primary-term) PRIMARY_TERM="$2"; shift 2 ;;
    --message) MESSAGE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$INDEX_NAME" && -n "$INDEX_UUID" && -n "$SHARD_ID" && -n "$ALLOCATION_ID" && -n "$MESSAGE" ]] || {
  echo "missing required args" >&2
  exit 1
}

OPEN_SEARCH_HOME="/home/ubuntu/OpenSearch/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"
CLASSPATH="$OPEN_SEARCH_HOME/lib/*:$OPEN_SEARCH_HOME/modules/*/*"
CACHE_DIR="/tmp/steelsearch-java-shard-started-request"
SRC="$CACHE_DIR/BuildShardStartedRequest.java"
mkdir -p "$CACHE_DIR"

if [[ ! -f "$CACHE_DIR/BuildShardStartedRequest.class" ]]; then
  cat >"$SRC" <<'JAVA'
import org.opensearch.cluster.action.shard.ShardStateAction.StartedShardEntry;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.core.index.Index;
import org.opensearch.core.index.shard.ShardId;

public class BuildShardStartedRequest {
  public static void main(String[] args) throws Exception {
    String indexName = null;
    String indexUuid = null;
    int shardId = -1;
    String allocationId = null;
    long primaryTerm = 0L;
    String message = null;
    for (int i = 0; i < args.length; i += 2) {
      switch (args[i]) {
        case "--index-name": indexName = args[i + 1]; break;
        case "--index-uuid": indexUuid = args[i + 1]; break;
        case "--shard-id": shardId = Integer.parseInt(args[i + 1]); break;
        case "--allocation-id": allocationId = args[i + 1]; break;
        case "--primary-term": primaryTerm = Long.parseLong(args[i + 1]); break;
        case "--message": message = args[i + 1]; break;
        default: throw new IllegalArgumentException("unknown arg " + args[i]);
      }
    }
    StartedShardEntry request = new StartedShardEntry(
      new ShardId(new Index(indexName, indexUuid), shardId),
      allocationId,
      primaryTerm,
      message
    );
    BytesStreamOutput out = new BytesStreamOutput();
    request.writeTo(out);
    byte[] bytes = out.bytes().toBytesRef().bytes;
    int offset = out.bytes().toBytesRef().offset;
    int length = out.bytes().toBytesRef().length;
    StringBuilder sb = new StringBuilder(length * 2);
    for (int i = 0; i < length; i++) {
      sb.append(String.format("%02x", bytes[offset + i] & 0xff));
    }
    System.out.print(sb.toString());
  }
}
JAVA
  javac -cp "$CLASSPATH" -d "$CACHE_DIR" "$SRC"
fi

java -cp "$CACHE_DIR:$CLASSPATH" BuildShardStartedRequest \
  --index-name "$INDEX_NAME" \
  --index-uuid "$INDEX_UUID" \
  --shard-id "$SHARD_ID" \
  --allocation-id "$ALLOCATION_ID" \
  --primary-term "$PRIMARY_TERM" \
  --message "$MESSAGE"
