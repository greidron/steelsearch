#!/usr/bin/env python3
import re
import sys
from collections import defaultdict


ADD_RE = re.compile(
    r"steelsearch_transport_response_context=add requestId=(\d+) action=([^\s]+) node=\{([^}]*)\}"
)
PRUNE_RE = re.compile(
    r"steelsearch_transport_response_context=prune requestId=(\d+) action=([^\s]+) node=\{([^}]*)\}"
)
RECEIVED_RE = re.compile(
    r"steelsearch_transport_response_context=received requestId=(\d+) action=([^\s]+) node=\{([^}]*)\}"
)
RECEIVED_MISSING_RE = re.compile(r"steelsearch_transport_response_context=received_missing requestId=(\d+)")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_transport_response_context_for_rust_publish_state.py <opensearch-stdout.log>")
        return 2

    path = sys.argv[1]
    rust = defaultdict(lambda: {"add": 0, "prune": 0, "received": 0, "received_missing": 0})
    self_node = defaultdict(lambda: {"add": 0, "prune": 0, "received": 0, "received_missing": 0})

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = ADD_RE.search(line)
            if m:
                request_id = int(m.group(1))
                node = m.group(3)
                if node.startswith("rust-replica-1"):
                    rust[request_id]["add"] += 1
                elif node.startswith("java-primary-1"):
                    self_node[request_id]["add"] += 1
                continue

            m = PRUNE_RE.search(line)
            if m:
                request_id = int(m.group(1))
                node = m.group(3)
                if node.startswith("rust-replica-1"):
                    rust[request_id]["prune"] += 1
                elif node.startswith("java-primary-1"):
                    self_node[request_id]["prune"] += 1
                continue

            m = RECEIVED_RE.search(line)
            if m:
                request_id = int(m.group(1))
                node = m.group(3)
                if node.startswith("rust-replica-1"):
                    rust[request_id]["received"] += 1
                elif node.startswith("java-primary-1"):
                    self_node[request_id]["received"] += 1
                continue

            m = RECEIVED_MISSING_RE.search(line)
            if m:
                request_id = int(m.group(1))
                if request_id in rust:
                    rust[request_id]["received_missing"] += 1
                elif request_id in self_node:
                    self_node[request_id]["received_missing"] += 1

    rust_added = len(rust)
    rust_pruned_before_receive = sum(1 for v in rust.values() if v["add"] and v["prune"] and v["received"] == 0)
    rust_received = sum(1 for v in rust.values() if v["received"])
    rust_missing_after_add = sum(1 for v in rust.values() if v["received_missing"])
    self_received = sum(1 for v in self_node.values() if v["received"])

    print(f"rust_publish_state_added={rust_added}")
    print(f"rust_publish_state_pruned_before_receive={rust_pruned_before_receive}")
    print(f"rust_publish_state_received={rust_received}")
    print(f"rust_publish_state_received_missing_after_add={rust_missing_after_add}")
    print(f"self_publish_state_received={self_received}")

    if rust_added > 0 and rust_pruned_before_receive == rust_added and rust_received == 0:
        print("result=rust_publish_state_handler_is_pruned_before_onResponseReceived_so_disconnect_wins_before_arrival_dispatch")
        return 0
    if rust_received > 0:
        print("result=rust_publish_state_response_reaches_transport_pipeline_before_publication_callback_gap")
        return 0

    print("result=rust_publish_state_arrival_vs_dispatch_still_unresolved")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
