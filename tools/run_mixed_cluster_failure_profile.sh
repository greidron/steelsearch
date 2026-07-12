#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PHASE_C_FAILURE_WORK_DIR:-${ROOT_DIR}/target/phase-c-mixed-cluster-failure}"
mkdir -p "${WORK_DIR}"

LIVE_REPORT="${WORK_DIR}/failure-topology-probe-report.json"
LEDGER_REPORT="${WORK_DIR}/failure-ledger-report.json"
PIT_RESTART_REPORT="${WORK_DIR}/pit-restart-lifecycle-report.json"
PIT_TRANSPORT_RESTART_REPORT="${WORK_DIR}/pit-transport-restart-lifecycle-report.json"
PIT_MULTI_DAEMON_REPORT="${WORK_DIR}/pit-multi-daemon-lifecycle-report.json"
FINAL_REPORT="${WORK_DIR}/mixed-cluster-failure-report.json"
JAVA_NODE_LOSS_REPORT="${WORK_DIR}/java-node-loss-report.json"
STEEL_NODE_LOSS_PUBLICATION_REPORT="${WORK_DIR}/steelsearch-node-loss-publication-report.json"
STEEL_NODE_LOSS_RECOVERY_REPORT="${WORK_DIR}/steelsearch-node-loss-recovery-report.json"

bash "${ROOT_DIR}/tools/probe_mixed_cluster_failure_profile.sh" >"${LIVE_REPORT}"

LEDGER_STDOUT="${WORK_DIR}/failure-ledger.stdout"
LEDGER_STDERR="${WORK_DIR}/failure-ledger.stderr"
if cargo test -p os-core mixed_cluster_failure_ledger_covers_publication_mismatch_routing_hole_and_stale_replica --test mixed_cluster_failure_ledger -- --nocapture >"${LEDGER_STDOUT}" 2>"${LEDGER_STDERR}"; then
  python3 - "${LEDGER_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {"summary": {"passed": True}}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${LEDGER_STDOUT}" >&2 || true
  cat "${LEDGER_STDERR}" >&2 || true
  exit 1
fi

PIT_RESTART_STDOUT="${WORK_DIR}/pit-restart-lifecycle.stdout"
PIT_RESTART_STDERR="${WORK_DIR}/pit-restart-lifecycle.stderr"
if cargo test -p os-node --features standalone-runtime daemon_point_in_time_contexts_do_not_survive_restart --test dev_cluster_daemons -- --exact --nocapture >"${PIT_RESTART_STDOUT}" 2>"${PIT_RESTART_STDERR}"; then
  python3 - "${PIT_RESTART_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {
    "summary": {"passed": True},
    "checks": {"pit_restart_lifecycle_passed": True},
    "coverage_scope": "REST PIT restart lifecycle",
    "executed_tests": ["daemon_point_in_time_contexts_do_not_survive_restart"],
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${PIT_RESTART_STDOUT}" >&2 || true
  cat "${PIT_RESTART_STDERR}" >&2 || true
  exit 1
fi

PIT_TRANSPORT_RESTART_STDOUT="${WORK_DIR}/pit-transport-restart-lifecycle.stdout"
PIT_TRANSPORT_RESTART_STDERR="${WORK_DIR}/pit-transport-restart-lifecycle.stderr"
if cargo test -p os-node --features standalone-runtime daemon_transport_point_in_time_contexts_do_not_survive_restart --test dev_cluster_daemons -- --exact --nocapture >"${PIT_TRANSPORT_RESTART_STDOUT}" 2>"${PIT_TRANSPORT_RESTART_STDERR}"; then
  python3 - "${PIT_TRANSPORT_RESTART_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {
    "summary": {"passed": True},
    "checks": {"pit_transport_restart_lifecycle_passed": True},
    "coverage_scope": "transport PIT restart stale-context lifecycle",
    "executed_tests": ["daemon_transport_point_in_time_contexts_do_not_survive_restart"],
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${PIT_TRANSPORT_RESTART_STDOUT}" >&2 || true
  cat "${PIT_TRANSPORT_RESTART_STDERR}" >&2 || true
  exit 1
fi

PIT_MULTI_DAEMON_STDOUT="${WORK_DIR}/pit-multi-daemon-lifecycle.stdout"
PIT_MULTI_DAEMON_STDERR="${WORK_DIR}/pit-multi-daemon-lifecycle.stderr"
if cargo test -p os-node --features standalone-runtime multi_daemon_get_all_pits_fans_out_to_seed_peers --test dev_cluster_daemons -- --exact --nocapture >"${PIT_MULTI_DAEMON_STDOUT}" 2>"${PIT_MULTI_DAEMON_STDERR}"; then
  python3 - "${PIT_MULTI_DAEMON_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
report = {
    "summary": {"passed": True},
    "checks": {"pit_multi_daemon_lifecycle_passed": True},
    "coverage_scope": "multi-daemon transport PIT lifecycle",
    "executed_tests": ["multi_daemon_get_all_pits_fans_out_to_seed_peers"],
}
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
PY
else
  cat "${PIT_MULTI_DAEMON_STDOUT}" >&2 || true
  cat "${PIT_MULTI_DAEMON_STDERR}" >&2 || true
  exit 1
fi

python3 - "${LIVE_REPORT}" "${LEDGER_REPORT}" "${PIT_RESTART_REPORT}" "${PIT_TRANSPORT_RESTART_REPORT}" "${PIT_MULTI_DAEMON_REPORT}" "${JAVA_NODE_LOSS_REPORT}" "${STEEL_NODE_LOSS_PUBLICATION_REPORT}" "${STEEL_NODE_LOSS_RECOVERY_REPORT}" "${FINAL_REPORT}" <<'PY'
import json
import sys

(
    live_path,
    ledger_path,
    pit_restart_path,
    pit_transport_restart_path,
    pit_multi_daemon_path,
    java_node_loss_path,
    steel_node_loss_publication_path,
    steel_node_loss_recovery_path,
    final_path,
) = sys.argv[1:10]
with open(live_path, "r", encoding="utf-8") as fh:
    live = json.load(fh)
with open(ledger_path, "r", encoding="utf-8") as fh:
    ledger = json.load(fh)
with open(pit_restart_path, "r", encoding="utf-8") as fh:
    pit_restart = json.load(fh)
with open(pit_transport_restart_path, "r", encoding="utf-8") as fh:
    pit_transport_restart = json.load(fh)
with open(pit_multi_daemon_path, "r", encoding="utf-8") as fh:
    pit_multi_daemon = json.load(fh)
with open(java_node_loss_path, "r", encoding="utf-8") as fh:
    java_node_loss = json.load(fh)
with open(steel_node_loss_publication_path, "r", encoding="utf-8") as fh:
    steel_node_loss_publication = json.load(fh)
with open(steel_node_loss_recovery_path, "r", encoding="utf-8") as fh:
    steel_node_loss_recovery = json.load(fh)

node_loss_child_executed_tests = {
    "java_node_loss_report": sorted(set(java_node_loss.get("executed_tests", []))),
    "steelsearch_node_loss_publication_report": sorted(set(steel_node_loss_publication.get("executed_tests", []))),
    "steelsearch_node_loss_recovery_report": sorted(set(steel_node_loss_recovery.get("executed_tests", []))),
}
pit_child_executed_tests = {
    "pit_restart_lifecycle_report": sorted(set(pit_restart.get("executed_tests", []))),
    "pit_transport_restart_lifecycle_report": sorted(set(pit_transport_restart.get("executed_tests", []))),
    "pit_multi_daemon_lifecycle_report": sorted(set(pit_multi_daemon.get("executed_tests", []))),
}
report = {
    "reports": {
        "failure_topology_probe_report": live_path,
        "failure_ledger_report": ledger_path,
        "pit_restart_lifecycle_report": pit_restart_path,
        "pit_transport_restart_lifecycle_report": pit_transport_restart_path,
        "pit_multi_daemon_lifecycle_report": pit_multi_daemon_path,
        "java_node_loss_report": java_node_loss_path,
        "steelsearch_node_loss_publication_report": steel_node_loss_publication_path,
        "steelsearch_node_loss_recovery_report": steel_node_loss_recovery_path,
    },
    "child_executed_tests": {
        **pit_child_executed_tests,
        **node_loss_child_executed_tests,
    },
    "executed_tests": sorted(
        set(pit_restart.get("executed_tests", []))
        | set(pit_transport_restart.get("executed_tests", []))
        | set(pit_multi_daemon.get("executed_tests", []))
        | set(java_node_loss.get("executed_tests", []))
        | set(steel_node_loss_publication.get("executed_tests", []))
        | set(steel_node_loss_recovery.get("executed_tests", []))
    ),
    "checks": {
        "failure_topology_probe_passed": bool(live.get("summary", {}).get("passed")),
        "failure_ledger_passed": bool(ledger.get("summary", {}).get("passed")),
        "pit_restart_lifecycle_passed": bool(pit_restart.get("checks", {}).get("pit_restart_lifecycle_passed")),
        "pit_transport_restart_lifecycle_passed": bool(pit_transport_restart.get("checks", {}).get("pit_transport_restart_lifecycle_passed")),
        "pit_multi_daemon_lifecycle_passed": bool(pit_multi_daemon.get("checks", {}).get("pit_multi_daemon_lifecycle_passed")),
        "java_node_loss_passed": bool(java_node_loss.get("checks", {}).get("java_node_loss_fail_closed_passed")),
        "steelsearch_node_loss_publication_passed": bool(steel_node_loss_publication.get("checks", {}).get("steelsearch_node_loss_publication_fencing_passed")),
        "steelsearch_node_loss_recovery_passed": bool(steel_node_loss_recovery.get("checks", {}).get("steelsearch_node_loss_recovery_fencing_passed")),
    },
}
report["summary"] = {
    "passed": all(report["checks"].values())
}

with open(final_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, sort_keys=True)
print(json.dumps(report, indent=2, sort_keys=True))
PY
