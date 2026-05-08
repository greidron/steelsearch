#!/usr/bin/env python3
import json
import sys
import zipfile
from pathlib import Path


TRACE_BYTES = b"selected channel index"
INNER_CLASS_ENTRY = "org/opensearch/transport/ConnectionProfile$ConnectionTypeHandle.class"


def file_contains_bytes(path: Path, needle: bytes) -> bool:
    return path.exists() and needle in path.read_bytes()


def jar_entry_contains_bytes(path: Path, entry: str, needle: bytes) -> bool:
    if not path.exists():
        return False
    with zipfile.ZipFile(path) as zf:
        try:
            return needle in zf.read(entry)
        except KeyError:
            return False


def runner_prefers_distribution_bin(run_script: Path) -> bool:
    text = run_script.read_text()
    return (
        'DEFAULT_DIST_HOME="${OPENSEARCH_ROOT}/distribution/archives/linux-arm64-tar/build/install/opensearch-3.7.0-SNAPSHOT"' in text
        and 'if [[ -x "${OPENSEARCH_DIST_HOME}/bin/opensearch" ]]; then' in text
        and 'OPENSEARCH_BIN="${OPENSEARCH_BIN:-${OPENSEARCH_DIST_HOME}/bin/opensearch}"' in text
    )


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_connection_profile_trace_not_built_into_runtime.py "
        "<run-opensearch-dev.sh> <ConnectionProfile.java> <ConnectionProfile$ConnectionTypeHandle.class> <dist opensearch jar>",
            file=sys.stderr,
        )
        return 2

    run_script = Path(sys.argv[1])
    source_java = Path(sys.argv[2])
    build_class = Path(sys.argv[3])
    dist_jar = Path(sys.argv[4])

    source_has_trace = file_contains_bytes(source_java, TRACE_BYTES)
    build_class_has_trace = file_contains_bytes(build_class, TRACE_BYTES)
    dist_jar_has_trace = jar_entry_contains_bytes(dist_jar, INNER_CLASS_ENTRY, TRACE_BYTES)
    prefers_dist_bin = runner_prefers_distribution_bin(run_script)

    if source_has_trace and build_class_has_trace and dist_jar_has_trace and prefers_dist_bin:
        result = (
            "connection_profile_trace_is_already_present_in_build_and_distribution_artifacts_"
            "so_missing_runtime_logs_point_to_runtime_send_path_or_log_reachability_not_artifact_mismatch"
        )
    elif source_has_trace and not build_class_has_trace and not dist_jar_has_trace and prefers_dist_bin:
        result = (
            "connection_profile_trace_is_missing_because_source_patch_is_not_built_into_runtime_artifacts_"
            "and_runner_prefers_prebuilt_distribution_bin"
        )
    elif source_has_trace and build_class_has_trace and not dist_jar_has_trace and prefers_dist_bin:
        result = (
            "connection_profile_trace_is_built_in_server_classes_but_not_in_distribution_jar_"
            "and_runner_still_prefers_distribution_bin"
        )
    elif source_has_trace and dist_jar_has_trace:
        result = "connection_profile_trace_is_present_in_runtime_distribution_artifact"
    else:
        result = "connection_profile_trace_build_state_is_inconclusive"

    print(
        json.dumps(
            {
                "source_java_has_trace_string": source_has_trace,
                "build_inner_class_has_trace_string": build_class_has_trace,
                "distribution_jar_has_trace_string": dist_jar_has_trace,
                "runner_prefers_distribution_bin": prefers_dist_bin,
                "distribution_jar": str(dist_jar),
                "distribution_jar_entry": INNER_CLASS_ENTRY,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
