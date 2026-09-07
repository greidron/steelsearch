#!/usr/bin/env python3
"""The supported GitHub publishing path; validates notes before any remote write."""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from release_notes import load, require, validate_notes


def publish(directory: Path, repository: str, expected_tag: str, assets: list[Path]) -> None:
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is not None, "invalid repository")
    for asset in assets:
        require(asset.is_file(), f"missing release asset: {asset}")
        require(asset.name != "performance-evidence.zip", "reserved evidence asset name")
    with tempfile.TemporaryDirectory(prefix="steelsearch-release-") as temporary:
        snapshot = Path(temporary) / "bundle"
        snapshot.mkdir()
        filenames = ("release.json", "notes.md", "current.json", "previous.json", "opensearch.json")
        for name in filenames:
            shutil.copyfile(directory / name, snapshot / name)
        # Validate and publish the same bytes, even if the workspace changes during GitHub lookup.
        validate_notes(snapshot)
        manifest = load(snapshot / "release.json")
        require(manifest["release"] == expected_tag, "requested tag does not match release metadata")
        require(type(manifest.get("prerelease")) is bool, "prerelease must be an explicit boolean")
        response = subprocess.check_output(
            ["gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases"], text=True
        )
        releases = [release for page in json.loads(response) for release in page]
        require(not any(release["tag_name"] == expected_tag for release in releases),
                "release already exists; this publisher never overwrites a release")
        published = [release for release in releases if not release["draft"] and release.get("published_at")]
        require(bool(published), "previous published release required; no silent first-release exemption")
        previous = max(published, key=lambda release: release["published_at"])
        require(previous["tag_name"] == manifest["previous_release"],
                f"previous release changed: expected {previous['tag_name']}; renew comparison")
        archive = Path(temporary) / "performance-evidence.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name in filenames:
                bundle.write(snapshot / name, name)
        command = ["gh", "release", "create", expected_tag, str(archive),
                   *(str(asset.resolve()) for asset in assets), "--repo", repository,
                   "--verify-tag", "--title", f"SteelSearch {expected_tag}",
                   "--notes-file", str(snapshot / "notes.md")]
        if manifest["prerelease"]:
            command.extend(["--prerelease", "--latest=false"])
        subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--asset", type=Path, action="append", default=[])
    parser.add_argument("--publish", action="store_true", help="explicitly authorize GitHub publication")
    args = parser.parse_args()
    try:
        validate_notes(args.directory)
        require(load(args.directory / "release.json")["release"] == args.tag, "tag mismatch")
        if args.publish:
            publish(args.directory, args.repo, args.tag, args.asset)
        else:
            print("Local validation passed. No GitHub release created; --publish is required.")
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"release publication rejected: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
