"""Behaviour tests for scripts/ci/run-offline-checks.sh, run against a throwaway tree.

The script derives its root from its own location, so each test copies it into a
temporary fake repository containing only the pieces the test needs.
stdlib unittest, offline. Run:
    python3 -m unittest discover -s tests -p 'test_offline_checks.py'
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "ci" / "run-offline-checks.sh"

PASSING = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n"
FAILING = "import unittest\nclass T(unittest.TestCase):\n    def test_bad(self):\n        self.assertEqual(1, 2)\n"

try:
    import yaml  # noqa: F401

    HAVE_YAML = True
except ImportError:  # pragma: no cover
    HAVE_YAML = False


@unittest.skipUnless(shutil.which("bash"), "bash not available")
class OfflineChecksTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="oc-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "scripts" / "ci").mkdir(parents=True)
        shutil.copy2(SCRIPT, self.root / "scripts" / "ci" / "run-offline-checks.sh")
        self.write("scripts/ok.sh", "#!/usr/bin/env bash\necho hi\n")

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def run_script(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
        full = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.root), "LANG": "C.UTF-8"}
        full.update(env or {})
        return subprocess.run(
            ["bash", str(self.root / "scripts" / "ci" / "run-offline-checks.sh"), *args],
            cwd="/", env=full, capture_output=True, text=True, timeout=120, check=False,
        )

    def test_absent_modules_are_skipped_loudly_and_exit_zero(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for d in ("examples/ros2-sequence-probe", "experiments/model-serving-fairness"):
            self.assertIn(f"SKIP unittest:{d}: directory absent", r.stdout)
        self.assertIn("PASS bash-syntax", r.stdout)
        self.assertIn("skipped steps were NOT run", r.stdout)

    def test_passing_module_is_run(self):
        self.write("examples/ros2-sequence-probe/tests/test_a.py", PASSING)
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS unittest:examples/ros2-sequence-probe", r.stdout)
        self.assertIn("Ran 1 test", r.stdout + r.stderr)

    def test_module_without_tests_dir_uses_root_discovery(self):
        self.write("experiments/e02-dds-resilience/test_flat.py", PASSING)
        r = self.run_script()
        self.assertIn("PASS unittest:experiments/e02-dds-resilience", r.stdout)

    def test_module_with_package_tests_dir(self):
        self.write("experiments/edge-cloud-placement/tests/__init__.py", "")
        self.write("experiments/edge-cloud-placement/tests/test_p.py", PASSING)
        r = self.run_script()
        self.assertIn("PASS unittest:experiments/edge-cloud-placement", r.stdout)

    def test_failing_module_fails_run_but_other_steps_still_run(self):
        self.write("examples/lerobot-data-quality/tests/test_bad.py", FAILING)
        self.write("experiments/model-serving-fairness/tests/test_ok.py", PASSING)
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL unittest:examples/lerobot-data-quality", r.stdout)
        self.assertIn("PASS unittest:experiments/model-serving-fairness", r.stdout)
        self.assertIn("RESULT: FAIL", r.stderr)

    def test_fail_fast_stops_after_first_failure(self):
        self.write("examples/ros2-sequence-probe/tests/test_bad.py", FAILING)
        self.write("experiments/model-serving-fairness/tests/test_ok.py", PASSING)
        r = self.run_script("--fail-fast")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL unittest:examples/ros2-sequence-probe", r.stdout)
        self.assertNotIn("unittest:experiments/model-serving-fairness", r.stdout)

    def test_existing_module_with_no_tests_is_a_failure_not_a_pass(self):
        self.write("examples/cloud-robotics/agent-mobility/README.md", "x\n")
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL unittest:examples/cloud-robotics/agent-mobility", r.stdout)

    def test_bash_syntax_error_fails(self):
        self.write("scripts/broken.sh", "if then fi (\n")
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL bash-syntax", r.stdout)
        self.assertIn("syntax error: ./scripts/broken.sh", r.stderr)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_yaml_parse_error_fails_and_valid_multidoc_passes(self):
        self.write("kind/ok.yaml", "a: 1\n---\nb: 2\n")
        self.assertIn("PASS yaml-parse", self.run_script().stdout)
        self.write("kind/bad.yml", "a: [1, 2\nb: : :\n")
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL yaml-parse", r.stdout)
        self.assertIn("./kind/bad.yml", r.stderr)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_pruned_directories_are_not_scanned(self):
        self.write(".claude/plans/bad.yml", "a: [1\n")
        self.write("node_modules/x/bad.yaml", "a: [1\n")
        self.write("ok.yml", "a: 1\n")
        self.assertEqual(self.run_script().returncode, 0)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_other_git_dirs_are_pruned_but_dot_github_is_not(self):
        self.write(".git-alt/bad.yml", "a: [1\n")
        self.write("ok.yml", "a: 1\n")
        self.assertEqual(self.run_script().returncode, 0)
        self.write(".github/workflows/bad.yml", "a: [1\n")
        r = self.run_script()
        self.assertEqual(r.returncode, 1)
        self.assertIn("./.github/workflows/bad.yml", r.stderr)
        self.write(".github/scripts/broken.sh", "if then fi (\n")
        self.assertIn("./.github/scripts/broken.sh", self.run_script().stderr)

    def test_only_and_list(self):
        r = self.run_script("--only", "bash-syntax")
        self.assertEqual(r.returncode, 0)
        self.assertIn("passed=1 failed=0 skipped=0", r.stdout)
        listing = self.run_script("--list")
        self.assertEqual(listing.returncode, 0)
        self.assertIn("bash-syntax", listing.stdout)
        self.assertNotIn("PASS", listing.stdout)

    def test_unknown_step_and_bad_argument_exit_two(self):
        self.assertEqual(self.run_script("--only", "nope").returncode, 2)
        self.assertEqual(self.run_script("--bogus").returncode, 2)

    def test_repo_guard_step_is_opt_in(self):
        self.assertIn("SKIP workflow-repo-guard", self.run_script().stdout)
        r = self.run_script(env={"RRL_REQUIRE_REPO_GUARD": "1"})
        self.assertEqual(r.returncode, 1)  # guard script absent in the fake tree -> real failure
        self.assertIn("FAIL workflow-repo-guard", r.stdout)

    def test_module_needing_pyyaml_is_skipped_loudly_when_it_is_missing(self):
        self.write("experiments/e02-dds-resilience/tests/test_y.py", "import yaml\n" + PASSING)
        shim = self.root / "shim"
        shim.mkdir()
        (shim / "yaml.py").write_text("raise ImportError('simulated: no PyYAML')\n", encoding="utf-8")
        r = self.run_script(env={"PYTHONPATH": str(shim)})
        self.assertIn("SKIP unittest:experiments/e02-dds-resilience: needs PyYAML", r.stdout)
        self.assertIn("NOT tested", r.stdout)
        self.assertIn("SKIP yaml-parse", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_script_makes_no_network_or_cluster_calls(self):
        import re
        code = "\n".join(l for l in SCRIPT.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
        # executable use of a network/cluster/privileged tool (messages inside quotes are fine)
        for tool in ("curl", "wget", "docker", "kubectl", "kind", "sudo", "ssh", "vagrant"):
            self.assertIsNone(re.search(rf"(^|[;&|(]\s*|\$\(\s*){tool}\s", code, re.M), tool)
        self.assertIsNone(re.search(r"(^|[;&|(]\s*)(\"\$PY\"|python3?)\s+(-I\s+)?-m\s+pip\b", code, re.M))
        self.assertIsNone(re.search(r"(^|[;&|(]\s*)pip3?\s", code, re.M))


if __name__ == "__main__":
    unittest.main()
