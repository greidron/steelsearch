"""Reviewed non-plugin projection of search cases and vector-only setup data."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/fixtures/search-compat.json"
EXCLUSIONS = ROOT / "tools/fixtures/release-core-plugin-exclusions.json"
VECTOR_INDICES = frozenset({"vectors-compat", "vectors-cosine-compat", "vectors-innerproduct-compat"})
PROJECTED_SUITES = frozenset({"search-compat", "tier-read-surface", "runtime-mappings-surface"})


def excluded_names():
    policy = json.loads(EXCLUSIONS.read_text())
    names = policy["excluded_cases"]
    if policy.get("profile") != "core-no-plugins" or not names or len(names) != len(set(names)):
        raise ValueError("invalid core search exclusion policy")
    return frozenset(names)


def contains_removed_reference(value):
    if isinstance(value, str):
        return any(index in value for index in VECTOR_INDICES)
    if isinstance(value, dict):
        return any(contains_removed_reference(key) or contains_removed_reference(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_removed_reference(item) for item in value)
    return False


def project(fixture):
    excluded = excluded_names()
    cases = fixture["cases"]
    by_name = {case["name"]: case for case in cases}
    if len(by_name) != len(cases) or not excluded.issubset(by_name):
        raise ValueError("search source case inventory drift")
    if any(by_name[name].get("area") not in {"knn", "ml"} for name in excluded):
        raise ValueError("cannot exclude a core search case")
    if not VECTOR_INDICES.issubset({item["name"] for item in fixture["indices"]}):
        raise ValueError("vector setup inventory drift")
    retained = [case for case in cases if case["name"] not in excluded]
    if not retained:
        raise ValueError("core search fixture is empty")
    result = {**fixture, "cases": retained,
              "indices": [item for item in fixture["indices"] if item["name"] not in VECTOR_INDICES],
              "aliases": [item for item in fixture["aliases"] if item["index"] not in VECTOR_INDICES],
              "bulk": [item for item in fixture["bulk"] if item["index"] not in VECTOR_INDICES]}
    manifest = {}
    for key, value in fixture["manifest"].items():
        if isinstance(value, list):
            value = [item for item in value if not (
                isinstance(item, str) and item in excluded or
                isinstance(item, dict) and (item.get("index") in VECTOR_INDICES or item.get("name") in excluded))]
        manifest[key] = value
    result["manifest"] = manifest
    if contains_removed_reference(result):
        raise ValueError("retained fixture references removed vector setup")
    return result


def write_projection(path):
    source = SOURCE.read_bytes()
    raw = (json.dumps(project(json.loads(source)), indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
    return {"source_fixture": str(SOURCE), "source_sha256": hashlib.sha256(source).hexdigest(),
            "projected_sha256": hashlib.sha256(raw).hexdigest(),
            "excluded_cases": sorted(excluded_names()), "excluded_indices": sorted(VECTOR_INDICES)}


def validate_projection(suite):
    metadata = suite.get("core_search_fixture_projection")
    if not isinstance(metadata, dict) or metadata.get("source_fixture") != str(SOURCE):
        return ["core search projection evidence missing or invalid"]
    try:
        source = SOURCE.read_bytes()
        raw = Path(suite["fixture_path"]).read_bytes()
        if metadata.get("source_sha256") != hashlib.sha256(source).hexdigest():
            return ["core search source fixture changed"]
        if metadata.get("projected_sha256") != hashlib.sha256(raw).hexdigest():
            return ["core search projected fixture changed"]
        if metadata.get("excluded_cases") != sorted(excluded_names()) or metadata.get("excluded_indices") != sorted(VECTOR_INDICES):
            return ["core search exclusion inventory mismatch"]
        if json.loads(raw) != project(json.loads(source)):
            return ["core search projection modified retained cases or setup"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f"invalid core search projection: {error}"]
    return []
