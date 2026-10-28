"""Offline negative tests for the toy handoff; no ROS 2/Kubernetes is started."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulate import FIXTURE, Rejected, ToyMission, run_demo, validate_fixture  # noqa: E402


class OfflineHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_valid_and_deterministic(self) -> None:
        self.assertEqual(validate_fixture(self.fixture), self.fixture)
        self.assertEqual(run_demo(self.fixture), run_demo(self.fixture))

    def test_handoff_resumes_only_remaining_mission(self) -> None:
        result = run_demo(self.fixture)
        self.assertEqual(result["final_execution"], "edge-planner-01")
        self.assertEqual(result["final_epoch"], 2)
        self.assertEqual(result["completed_waypoints"], self.fixture["mission"]["waypoints"])
        self.assertEqual(sum(x["type"] == "simulated_effect_accepted" for x in result["events"]), 3)
        self.assertEqual(result["rejection_checks"], {
            "stale_origin": "stale_or_unauthorized",
            "replay": "duplicate_effect",
            "expired": "stale_observation"
        })

    def test_invalid_fixtures_fail_closed(self) -> None:
        mutations = [
            (("schema_version",), "wrong"),
            (("mission", "waypoints"), ["wp-01", "wp-01", "wp-03"]),
            (("checkpoint", "cursor"), 3),
            (("checkpoint", "completed"), ["wp-02", "wp-01"]),
            (("checkpoint", "epoch"), True),
            (("checkpoint", "epoch"), 0),
            (("destination", "execution_id"), "cloud-planner-01"),
            (("destination", "frame_id"), "odom"),
            (("destination", "map_revision"), "foreign-map"),
            (("destination", "capabilities"), ["report_status"]),
            (("destination", "capabilities"), ["inspect_waypoint", "unknown_action"]),
            (("handoff_tick",), 100),
            (("observation", "ttl_ticks"), -1),
            (("observation", "captured_tick"), 10),
        ]
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                bad = copy.deepcopy(self.fixture)
                target = bad
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(Rejected):
                    validate_fixture(bad)
        bad = copy.deepcopy(self.fixture)
        bad["robot"]["unsafe_extra"] = "secret"
        with self.assertRaises(Rejected):
            validate_fixture(bad)

    def test_changed_checkpoint_digest_or_state_is_refused(self) -> None:
        toy = ToyMission(self.fixture)
        snapshot = toy.checkpoint()
        snapshot["state"]["completed"] = ["wp-01"]
        with self.assertRaisesRegex(Rejected, "digest mismatch"):
            toy.transfer(snapshot, self.fixture["handoff_tick"])
        self.assertEqual(toy.epoch, 1)
        self.assertEqual(toy.owner, "cloud-planner-01")

    def test_double_transfer_rejected(self) -> None:
        toy = ToyMission(self.fixture)
        snapshot = toy.checkpoint()
        toy.transfer(snapshot, self.fixture["handoff_tick"])
        with self.assertRaisesRegex(Rejected, "stale state"):
            toy.transfer(snapshot, self.fixture["handoff_tick"])

    def test_wrong_waypoint_and_stale_worker_are_rejected(self) -> None:
        toy = ToyMission(self.fixture)
        toy.transfer(toy.checkpoint(), self.fixture["handoff_tick"])
        self.assertEqual(toy.effect(executor="cloud-planner-01", epoch=1,
                                    effect_id="bad-cloud", waypoint="wp-03", tick=5), "stale_or_unauthorized")
        self.assertEqual(toy.effect(executor=toy.owner, epoch=toy.epoch,
                                    effect_id="bad-order", waypoint="wp-05", tick=5), "wrong_next_waypoint")
        self.assertEqual(toy.completed, ["wp-01", "wp-02"])

    def test_missing_or_malformed_fixture_returns_nonzero(self) -> None:
        proc = subprocess.run([sys.executable, str(ROOT / "simulate.py"),
                               "--fixture", str(ROOT / "fixtures" / "missing.json")],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("E08 rejected:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
