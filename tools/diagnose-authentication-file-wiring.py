#!/usr/bin/env python3
"""Compare daemon and legacy authentication-file settings over real loopback HTTP."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def probe(url, credentials=None):
    headers = {}
    if credentials:
        headers["Authorization"] = "Basic " + base64.b64encode(credentials.encode()).decode()
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    results = []
    for setting in ("STEELSEARCH_AUTHENTICATION_USERS_FILE", "SECURITY_AUTHENTICATION_USERS_FILE",
                    "--security.authentication_users_file"):
        with tempfile.TemporaryDirectory(prefix="steelsearch-auth-wiring-") as work:
            root = Path(work)
            users = root / "users.json"
            users.write_text(json.dumps({"users": [{"username": "wiring-admin",
                "password": "local-diagnostic-only", "roles": ["admin"]}],
                "service_accounts": [{"name": "wiring-service", "token": "local-service-only",
                                      "roles": ["writer"]}]}))
            users.chmod(0o600)
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("STEELSEARCH_", "SECURITY_"))}
            env["STEELSEARCH_SECURITY_ENABLED"] = "true"
            if not setting.startswith("--"):
                env[setting] = str(users)
            port = free_port()
            transport = free_port()
            while transport == port:
                transport = free_port()
            command = [str(binary), "--mode", "development", "--http.host", "127.0.0.1",
                       "--http.port", str(port), "--transport.host", "127.0.0.1",
                       "--transport.port", str(transport), "--path.data", str(root / "data")]
            if setting.startswith("--"):
                # CLI must override the official environment setting, even if that file is absent.
                env["STEELSEARCH_AUTHENTICATION_USERS_FILE"] = str(root / "missing-env.json")
                command.extend([setting, str(users)])
            if setting != "SECURITY_AUTHENTICATION_USERS_FILE":
                env["SECURITY_AUTHENTICATION_USERS_FILE"] = str(root / "missing-legacy.json")
            with (args.output_dir / (setting + ".log")).open("w") as log:
                process = subprocess.Popen(command, env=env, stdout=log, stderr=log,
                                           start_new_session=True)
                try:
                    url = f"http://127.0.0.1:{port}/"
                    deadline = time.monotonic() + 30
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError(f"daemon exited: {process.returncode}")
                        try:
                            anonymous = probe(url)
                            break
                        except (urllib.error.URLError, TimeoutError, ConnectionError):
                            if time.monotonic() >= deadline:
                                raise RuntimeError("daemon startup timed out")
                            time.sleep(0.1)
                    results.append({"setting": setting, "anonymous_status": anonymous,
                                    "valid_status": probe(url, "wiring-admin:local-diagnostic-only"),
                                    "invalid_status": probe(url, "wiring-admin:wrong"),
                                    "admin_health_status": probe(url + "_cluster/health", "wiring-admin:local-diagnostic-only"),
                                    "service_status": probe(url, "wiring-service:local-service-only"),
                                    "invalid_service_status": probe(url, "wiring-service:wrong"),
                                    "service_health_status": probe(url + "_cluster/health", "wiring-service:local-service-only")})
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
    if hashlib.sha256(binary.read_bytes()).hexdigest() != digest:
        raise RuntimeError("binary changed during diagnostic")
    report = {"diagnostic": True, "acceptance": False, "mode": "development",
              "tls_tested": False, "binary_sha256": digest, "results": results}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if all(row["anonymous_status"] == 401 and row["valid_status"] == 200
                    and row["invalid_status"] == 401 and row["admin_health_status"] == 200
                    and row["service_status"] == 200 and row["invalid_service_status"] == 401
                    and row["service_health_status"] == 403 for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
