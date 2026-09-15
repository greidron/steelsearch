import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import release_notes as notes

SPEC = importlib.util.spec_from_file_location("publish_release", Path(__file__).with_name("publish-release.py"))
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class ReleaseNotesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = {
            "schema_version": 1, "release": "v1.2.0", "previous_release": "v1.1.0",
            "prerelease": False, "support_profile": "core-no-plugins", "opensearch_version": "2.19.0",
            "environment": "One isolated test host", "runtime_settings": "Development persistence; not production parity",
            "comparison_limits": "Short synthetic workload; latency regressions retained",
        }
        self.write("release.json", self.manifest)
        config = {"query_mix": {key: 1 for key in notes.OPERATIONS}, "corpus_size": 5000, "vector_dimension": 384,
                  "duration_seconds": 30, "clients": 4, "number_of_shards": 3,
                  "number_of_replicas": 1, "seed": 13}
        for name, latency, throughput in (("current", 2, 200), ("previous", 1, 100), ("opensearch", 4, 50)):
            engine = "opensearch" if name == "opensearch" else "steelsearch"
            report = {"config": copy.deepcopy(config), "scenarios": {}}
            for topology in notes.TOPOLOGIES:
                report["scenarios"][f"{engine}-{topology}"] = {
                    "config": {**copy.deepcopy(config), "number_of_replicas": 0 if topology == "single-node" else 1},
                    "executable": {"path": f"/test/{name}", "sha256": ("a" if name == "current" else "b") * 64},
                    "target_identity": {"version": {"number": "2.19.0"}},
                    "summary": {"error_count": 0, "error_rate": 0, "elapsed_seconds": 30,
                                "success_count": throughput * 30, "operation_count": throughput * 30,
                                "throughput_ops_per_second": throughput},
                    "operations": {operation: {"error_count": 0,
                                                "success_count": throughput * 30 // 7 + (i < throughput * 30 % 7),
                                                "latency_ms": {"mean": latency, "p95": latency * 2,
                                                               "count": throughput * 30 // 7 + (i < throughput * 30 % 7)}}
                                   for i, operation in enumerate(notes.OPERATIONS)},
                }
            self.write(f"{name}.json", report)
        self.note_path = self.root / "notes.md"
        self.note_path.write_text(
            "# SteelSearch v1.2.0\n\n" +
            "\n\n".join(heading + "\n\nReviewed evidence recorded."
                         for heading in ("## Changes", "## Compatibility", "## Validation", "## Known Limitations")) +
            f"\n\n{notes.START}\n{notes.END}\n", encoding="utf-8"
        )

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def change_report(self, name, transform):
        value = notes.load(self.root / f"{name}.json")
        transform(value)
        self.write(f"{name}.json", value)

    def test_generated_tables_cover_both_topologies_and_seven_operations(self):
        notes.validate_notes(self.root, render=True)
        notes.validate_notes(self.root)
        content = self.note_path.read_text()
        self.assertIn("| single-node | 100.00 | 200.00 | +100.00% | 50.00 | 4.00x |", content)
        for topology in notes.TOPOLOGIES:
            for operation in notes.OPERATIONS:
                self.assertIn(f"| {topology} | {operation} | 1.00 | 2.00 | +100.00% | 4.00 | 2.00x | 4.00 |", content)

    def test_unrendered_and_edited_tables_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale or edited"):
            notes.validate_notes(self.root)
        notes.validate_notes(self.root, render=True)
        self.note_path.write_text(self.note_path.read_text().replace("200.00", "999.00"))
        with self.assertRaisesRegex(ValueError, "stale or edited"):
            notes.validate_notes(self.root)

    def test_missing_binary_identity_rejected(self):
        self.change_report("previous", lambda r: r["scenarios"]["steelsearch-three-node"].pop("executable"))
        with self.assertRaises(KeyError):
            notes.performance_section(self.root)

    def test_mixed_binary_hashes_rejected(self):
        self.change_report("previous", lambda r: r["scenarios"]["steelsearch-three-node"]["executable"].update(sha256="c" * 64))
        with self.assertRaisesRegex(ValueError, "mixed executables"):
            notes.performance_section(self.root)

    def test_missing_scenario_rejected(self):
        self.change_report("current", lambda r: r["scenarios"]["steelsearch-three-node"]["operations"].pop("write"))
        with self.assertRaisesRegex(ValueError, "operation results"):
            notes.performance_section(self.root)

    def test_same_binary_cannot_be_labelled_as_previous_release(self):
        def change(report):
            for scenario in report["scenarios"].values():
                scenario["executable"]["sha256"] = "a" * 64
        self.change_report("previous", change)
        with self.assertRaisesRegex(ValueError, "same executable"):
            notes.performance_section(self.root)

    def test_plugin_workload_rejected(self):
        self.change_report("current", lambda r: r["config"]["query_mix"].update(vector=1))
        with self.assertRaisesRegex(ValueError, "required operations"):
            notes.performance_section(self.root)

    def test_core_native_knn_profile_requires_and_renders_vector_operations(self):
        self.manifest["support_profile"] = "core-native-knn"
        self.write("release.json", self.manifest)
        operations = notes.NATIVE_KNN_OPERATIONS
        for name in ("current", "previous", "opensearch"):
            report = notes.load(self.root / f"{name}.json")
            report["config"]["query_mix"] = {operation: 1 for operation in operations}
            for scenario in report["scenarios"].values():
                scenario["config"]["query_mix"] = {operation: 1 for operation in operations}
                total = scenario["summary"]["success_count"]
                scenario["operations"] = {
                    operation: {
                        "error_count": 0,
                        "success_count": total // len(operations) + (index < total % len(operations)),
                        "latency_ms": {
                            "mean": 2,
                            "p95": 4,
                            "count": total // len(operations) + (index < total % len(operations)),
                        },
                    }
                    for index, operation in enumerate(operations)
                }
            self.write(f"{name}.json", report)
        notes.validate_notes(self.root, render=True)
        content = self.note_path.read_text()
        self.assertIn("support: `core-native-knn`", content)
        self.assertIn("vector and hybrid requests are included", content)
        for operation in ("vector", "hybrid"):
            self.assertIn(f"| single-node | {operation} |", content)

    def test_diagnostic_profile_cannot_be_promoted_to_release_evidence(self):
        original = notes.load(self.root / "current.json")
        for whole_report in (True, False):
            report = copy.deepcopy(original)
            target = report if whole_report else report["scenarios"]["steelsearch-three-node"]
            target["diagnostic_only"] = True
            self.write("current.json", report)
            with self.subTest(whole_report=whole_report), self.assertRaisesRegex(ValueError, "diagnostic profiling"):
                notes.performance_section(self.root)

    def test_mismatched_workload_rejected(self):
        def change(report):
            report["config"]["clients"] = 8
            for scenario in report["scenarios"].values():
                scenario["config"]["clients"] = 8
        self.change_report("previous", change)
        with self.assertRaisesRegex(ValueError, "configurations differ"):
            notes.performance_section(self.root)

    def test_wrong_reference_version_rejected(self):
        self.manifest["opensearch_version"] = "3.7.0"
        self.write("release.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "identity"):
            notes.performance_section(self.root)

    def test_different_source_array_dimensions_rejected_even_without_vector_queries(self):
        def change(report):
            report["config"]["vector_dimension"] = 768
            for scenario in report["scenarios"].values():
                scenario["config"]["vector_dimension"] = 768
        self.change_report("previous", change)
        with self.assertRaisesRegex(ValueError, "configurations differ"):
            notes.performance_section(self.root)

    def test_relabelled_top_level_config_cannot_hide_executed_workload(self):
        self.change_report("previous", lambda r: r["scenarios"]["steelsearch-three-node"]["config"].update(clients=8))
        with self.assertRaisesRegex(ValueError, "executed clients differs"):
            notes.performance_section(self.root)

    def test_empty_limitations_section_is_not_filled_by_generated_table(self):
        self.note_path.write_text(self.note_path.read_text().replace(
            "## Known Limitations\n\nReviewed evidence recorded.", "## Known Limitations\n"))
        with self.assertRaisesRegex(ValueError, "empty or placeholder"):
            notes.validate_notes(self.root, render=True)

    def test_nonfinite_measurements_rejected(self):
        for value in (float("nan"), float("inf"), 0, -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                notes.positive(value, "metric")

    def test_request_errors_rejected(self):
        self.change_report("current", lambda r: r["scenarios"]["steelsearch-single-node"]["summary"].update(error_count=1))
        with self.assertRaisesRegex(ValueError, "request errors"):
            notes.performance_section(self.root)

    def test_inconsistent_throughput_rejected(self):
        self.change_report("current", lambda r: r["scenarios"]["steelsearch-single-node"]["summary"].update(success_count=1))
        with self.assertRaisesRegex(ValueError, "throughput does not match"):
            notes.performance_section(self.root)

    def test_inconsistent_operation_and_latency_counts_rejected(self):
        original = notes.load(self.root / "current.json")
        def inconsistent_total(scenario):
            scenario["operations"]["write"]["success_count"] = 1
            scenario["operations"]["write"]["latency_ms"]["count"] = 1
        mutations = (
            lambda s: s["summary"].update(operation_count=s["summary"]["operation_count"] + 1),
            lambda s: s["operations"]["write"].update(success_count=1),
            lambda s: s["operations"]["write"]["latency_ms"].update(count=1),
            lambda s: s["operations"].update(vector=copy.deepcopy(s["operations"]["write"])),
            lambda s: s["operations"]["write"].update(success_count=0.5),
            lambda s: s["operations"]["write"]["latency_ms"].update(count=True),
            inconsistent_total,
        )
        for i, mutate in enumerate(mutations):
            report = copy.deepcopy(original)
            mutate(report["scenarios"]["steelsearch-single-node"])
            self.write("current.json", report)
            with self.subTest(mutation=i), self.assertRaises(ValueError):
                notes.performance_section(self.root)

    def test_publisher_rejects_inconsistent_counts_before_contacting_github(self):
        notes.validate_notes(self.root, render=True)
        self.change_report("current", lambda r: r["scenarios"]["steelsearch-single-node"]["summary"].update(operation_count=1))
        with patch.object(publisher.subprocess, "check_output") as read:
            with patch.object(publisher.subprocess, "run") as write:
                with self.assertRaisesRegex(ValueError, "total request count"):
                    publisher.publish(self.root, "owner/repo", "v1.2.0", [])
                read.assert_not_called()
                write.assert_not_called()

    def test_generated_replica_count_matches_executed_clamp(self):
        def change(report):
            report["config"]["number_of_replicas"] = 5
            for key, scenario in report["scenarios"].items():
                scenario["config"]["number_of_replicas"] = 0 if key.endswith("single-node") else 2
        for name in notes.REPORTS:
            self.change_report(name, change)
        self.assertIn("replicas: 0 on one node, 2 on three nodes", notes.performance_section(self.root))

    def test_publication_does_not_contact_github_when_notes_invalid(self):
        with patch.object(publisher.subprocess, "check_output") as read, patch.object(publisher.subprocess, "run") as write:
            with self.assertRaises(ValueError):
                publisher.publish(self.root, "owner/repo", "v1.2.0", [])
            read.assert_not_called()
            write.assert_not_called()

    def test_stale_previous_release_blocks_remote_write(self):
        notes.validate_notes(self.root, render=True)
        remote = [[{"tag_name": "v1.1.1", "draft": False, "published_at": "2026-09-06T00:00:00Z"}]]
        with patch.object(publisher.subprocess, "check_output", return_value=json.dumps(remote)):
            with patch.object(publisher.subprocess, "run") as write:
                with self.assertRaisesRegex(ValueError, "previous release changed"):
                    publisher.publish(self.root, "owner/repo", "v1.2.0", [])
                write.assert_not_called()

    def test_publisher_uses_verified_tag_exact_notes_and_evidence(self):
        notes.validate_notes(self.root, render=True)
        remote = [[{"tag_name": "v1.1.0", "draft": False, "published_at": "2026-09-06T00:00:00Z"}]]
        expected_notes = self.note_path.read_bytes()
        def inspect(command, **kwargs):
            published_notes = Path(command[command.index("--notes-file") + 1])
            self.assertEqual(published_notes.read_bytes(), expected_notes)
            archive = next(item for item in command if item.endswith("performance-evidence.zip"))
            with zipfile.ZipFile(archive) as evidence:
                self.assertEqual(evidence.read("notes.md"), expected_notes)
        with patch.object(publisher.subprocess, "check_output", return_value=json.dumps(remote)):
            with patch.object(publisher.subprocess, "run", side_effect=inspect) as write:
                publisher.publish(self.root, "owner/repo", "v1.2.0", [])
                command = write.call_args.args[0]
                self.assertIn("--verify-tag", command)
                self.assertTrue(any(item.endswith("performance-evidence.zip") for item in command))
                self.assertNotIn("--generate-notes", command)

    def test_publisher_uses_validated_snapshot_when_source_changes_during_lookup(self):
        notes.validate_notes(self.root, render=True)
        expected_notes = self.note_path.read_bytes()
        expected_report = (self.root / "current.json").read_bytes()
        remote = [[{"tag_name": "v1.1.0", "draft": False, "published_at": "2026-09-06T00:00:00Z"}]]
        def mutate(*args, **kwargs):
            self.note_path.write_text("Unvalidated replacement notes")
            self.change_report("current", lambda r: r.update(diagnostic_only=True))
            return json.dumps(remote)
        def inspect(command, **kwargs):
            path = Path(command[command.index("--notes-file") + 1])
            self.assertEqual(path.read_bytes(), expected_notes)
            archive = next(item for item in command if item.endswith("performance-evidence.zip"))
            with zipfile.ZipFile(archive) as evidence:
                self.assertEqual(evidence.read("notes.md"), expected_notes)
                self.assertEqual(evidence.read("current.json"), expected_report)
        with patch.object(publisher.subprocess, "check_output", side_effect=mutate):
            with patch.object(publisher.subprocess, "run", side_effect=inspect) as write:
                publisher.publish(self.root, "owner/repo", "v1.2.0", [])
                write.assert_called_once()

    def test_local_publisher_requires_explicit_publish_flag(self):
        notes.validate_notes(self.root, render=True)
        result = subprocess.run(["python3", str(Path(publisher.__file__)), str(self.root),
                                 "--repo", "owner/repo", "--tag", "v1.2.0"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No GitHub release created", result.stdout)


if __name__ == "__main__":
    unittest.main()
