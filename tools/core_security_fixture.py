"""Project only the reviewed ML API cases out of the native security fixture."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/fixtures/security-authz-compat.json"
EXCLUDED = frozenset({"security_bad_password_ml_register_401", "security_writer_ml_connector_create_403",
                      "security_admin_ml_connector_create_success", "security_writer_ml_predict_403"})


def project(fixture):
    cases = fixture["cases"]
    names = [case["name"] for case in cases]
    if len(names) != len(set(names)) or not EXCLUDED.issubset(names):
        raise ValueError("security source case inventory drift")
    for case in cases:
        if case["name"] in EXCLUDED:
            requests = [case, *case.get("steps", [])]
            if not any(str(request.get("path", "")).startswith("/_plugins/_ml/") for request in requests):
                raise ValueError("excluded case is no longer an ML API case")
    retained = [case for case in cases if case["name"] not in EXCLUDED]
    if not retained:
        raise ValueError("security core fixture is empty")
    return {**fixture, "cases": retained}


def write_projection(path):
    source = SOURCE.read_bytes()
    projected = project(json.loads(source))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(projected, indent=2) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
    return {"source_fixture": str(SOURCE), "source_sha256": hashlib.sha256(source).hexdigest(),
            "projected_sha256": hashlib.sha256(raw).hexdigest(), "excluded_cases": sorted(EXCLUDED)}


def validate_projection(suite):
    metadata = suite.get("core_fixture_projection")
    if not isinstance(metadata, dict) or metadata.get("source_fixture") != str(SOURCE):
        return ["core security source projection evidence missing or invalid"]
    try:
        source = SOURCE.read_bytes()
        raw = Path(suite["fixture_path"]).read_bytes()
        if metadata.get("source_sha256") != hashlib.sha256(source).hexdigest():
            return ["core security source fixture changed"]
        if metadata.get("projected_sha256") != hashlib.sha256(raw).hexdigest():
            return ["core security projected fixture changed"]
        if metadata.get("excluded_cases") != sorted(EXCLUDED):
            return ["core security exclusion inventory mismatch"]
        if json.loads(raw) != project(json.loads(source)):
            return ["core security projection modified retained cases or setup"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f"invalid core security projection: {error}"]
    return []
