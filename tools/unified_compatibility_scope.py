"""Explicit suite inventory for the non-plugin unified comparison profile."""

PROFILES = ("legacy-full", "core-no-plugins")
PLUGIN_SUITES = frozenset({"vector-search", "vector-search-native-surface", "knn-plugin-surface", "ml-model-surface"})
CORE_SUITES = frozenset({
    "root-cluster-node", "root-cluster-node-cat-common", "cluster-health", "allocation-explain",
    "cluster-state", "tasks", "stats", "index-lifecycle", "mapping", "settings", "alias-read",
    "template", "data-stream-rollover", "single-doc-crud", "refresh", "routing", "bulk",
    "document-write-semantic", "search-compat", "search-strict", "search-semantic",
    "runtime-stateful-probe", "admin-ops-common", "tier-read-surface", "runtime-mappings-surface",
    "snapshot-lifecycle", "alias-template-persistence", "security-authz", "multi-node-transport-admin",
    "multi-node-write-path",
})


def validate_scope(report, expected_profile):
    if expected_profile not in PROFILES:
        return ["unknown expected compatibility profile"]
    if report.get("compatibility_profile", "legacy-full") != expected_profile:
        return ["unified compatibility profile mismatch"]
    if expected_profile == "legacy-full":
        return ["legacy profile cannot contain excluded suites"] if report.get("excluded_suites") else []
    suites = report.get("suite_results")
    excluded = report.get("excluded_suites")
    if not isinstance(suites, list) or not isinstance(excluded, list):
        return ["core suite and exclusion inventories required"]
    if any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in suites + excluded):
        return ["invalid core suite inventory entry"]
    names = [row["name"] for row in suites]
    exclusions = [row["name"] for row in excluded]
    errors = []
    if set(names) != CORE_SUITES or len(names) != len(CORE_SUITES):
        errors.append("complete distinct core suite inventory required")
    if set(exclusions) != PLUGIN_SUITES or len(exclusions) != len(PLUGIN_SUITES):
        errors.append("exactly four explicit plugin suite exclusions required")
    for row in excluded:
        if (row.get("status") != "excluded" or "summary" in row or "returncode" in row
                or not isinstance(row.get("reason"), str) or not row["reason"].strip()):
            errors.append("plugin suite exclusion must not claim execution or success")
    for row in suites:
        if row["name"] != "multi-node-write-path" and row.get("required") is not True:
            errors.append(f"required core suite demoted: {row['name']}")
    return errors
