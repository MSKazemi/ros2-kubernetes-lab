"""Positive and negative tests for the synthetic-episode metadata contract.

Run from the repository root (stdlib only, no network, about a second):

    python3 -m unittest discover -s examples/lerobot-data-quality/tests -t examples/lerobot-data-quality -v
"""

import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dq_contract as c  # noqa: E402
import dq_validate as v  # noqa: E402
import fixture_gen as g  # noqa: E402

FIX = os.path.join(ROOT, "fixtures")
VALID_DIR = os.path.join(FIX, "valid")
VALID_MAIN = os.path.join(VALID_DIR, "synthetic_3ep_10fps.json")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def codes(doc):
    diags, _ = v.validate_document(doc)
    return [d.code for d in diags]


def base():
    return copy.deepcopy(load(VALID_MAIN))


class ValidFixtures(unittest.TestCase):
    def test_every_valid_fixture_passes(self):
        files = sorted(f for f in os.listdir(VALID_DIR) if f.endswith(".json"))
        self.assertGreaterEqual(len(files), 2)
        for f in files:
            with self.subTest(f):
                diags, trunc = v.validate_file(os.path.join(VALID_DIR, f))
                self.assertEqual([d.as_dict() for d in diags], [])
                self.assertFalse(trunc)

    def test_tolerance_boundary(self):
        d = base()
        d["episodes"][0]["frames"][2]["timestamp"] = round(0.2 + 0.0009, 6)  # inside 1 ms
        self.assertEqual(codes(d), [])
        d["episodes"][0]["frames"][2]["timestamp"] = round(0.2 + 0.0011, 6)  # outside
        self.assertEqual(codes(d), ["TIMESTAMP_FPS_DRIFT"])


class InvalidFixtures(unittest.TestCase):
    def setUp(self):
        self.expected = load(os.path.join(FIX, "expected_diagnostics.json"))

    def test_expected_table_matches_files_on_disk(self):
        on_disk = {"invalid/" + f for f in os.listdir(os.path.join(FIX, "invalid")) if f.endswith(".json")}
        self.assertEqual(on_disk, set(self.expected))

    def test_each_invalid_fixture_yields_exactly_its_code(self):
        for rel, exp in self.expected.items():
            with self.subTest(rel):
                diags, _ = v.validate_file(os.path.join(FIX, rel))
                self.assertEqual({d.code for d in diags}, {exp["code"]})
                self.assertEqual(diags[0].path, exp["path"])
                self.assertTrue(diags[0].message and diags[0].hint)

    def test_every_required_case_is_covered_by_a_fixture(self):
        have = {e["code"] for e in self.expected.values()}
        required = {
            "DIM_MISMATCH", "UNIT_MISMATCH", "TIMESTAMP_NOT_MONOTONIC", "TIMESTAMP_FPS_DRIFT",
            "CAMERA_METADATA_MISSING", "EPISODE_EMPTY", "EPISODE_INDEX_DUPLICATE",
            "LICENSE_NOT_ALLOWED", "LICENSE_MISSING", "SCHEMA_VERSION_UNKNOWN",
        }
        self.assertLessEqual(required, have)

    def test_all_codes_used_are_documented(self):
        for e in self.expected.values():
            self.assertIn(e["code"], c.CODES)


class NamedCases(unittest.TestCase):
    """One explicit test per required invalid case, mutating the valid fixture in memory."""

    def test_dimension_mismatch_frame(self):
        d = base()
        d["episodes"][0]["frames"][0]["observation.state"].append(0.0)
        self.assertEqual(codes(d), ["DIM_MISMATCH"])

    def test_dimension_mismatch_names_and_units(self):
        d = base()
        d["features"]["action"]["names"].pop()
        d["features"]["action"]["units"].pop()
        self.assertEqual(codes(d), ["DIM_MISMATCH", "DIM_MISMATCH"])

    def test_wrong_joint_names(self):
        d = base()
        d["features"]["action"]["names"][0] = "base"
        self.assertEqual(codes(d), ["FEATURE_NAMES_MISMATCH"])

    def test_unit_mismatch(self):
        d = base()
        d["features"]["action"]["units"][0] = "deg"
        diags, _ = v.validate_document(d)
        self.assertEqual([(x.code, x.path) for x in diags], [("UNIT_MISMATCH", "/features/action/units/0")])

    def test_non_monotonic_timestamp_and_duplicate_timestamp(self):
        d = base()
        d["episodes"][1]["frames"][2]["timestamp"] = d["episodes"][1]["frames"][1]["timestamp"]  # equal
        self.assertEqual(codes(d), ["TIMESTAMP_NOT_MONOTONIC"])

    def test_fps_drift(self):
        d = base()
        d["fps"] = 20  # timestamps were generated for 10 fps; camera fps now disagrees too
        got = set(codes(d))
        self.assertIn("TIMESTAMP_FPS_DRIFT", got)
        self.assertIn("CAMERA_METADATA_INVALID", got)

    def test_missing_camera_metadata_block_and_field(self):
        d = base()
        del d["features"]["observation.images.front"]["camera"]
        self.assertEqual(codes(d), ["CAMERA_METADATA_MISSING"])
        d = base()
        del d["features"]["observation.images.wrist"]["camera"]["encoding"]
        diags, _ = v.validate_document(d)
        self.assertEqual([(x.code, x.path) for x in diags], [("CAMERA_METADATA_MISSING", "/features/observation.images.wrist/camera/encoding")])

    def test_camera_encoding_and_fps_invalid(self):
        d = base()
        d["features"]["observation.images.front"]["camera"]["encoding"] = "bayer"
        self.assertEqual(codes(d), ["CAMERA_METADATA_INVALID"])
        d = base()
        d["features"]["observation.images.front"]["camera"]["fps"] = 15
        self.assertEqual(codes(d), ["CAMERA_METADATA_INVALID"])

    def test_empty_episode(self):
        d = base()
        d["episodes"][2]["frames"] = []
        d["episodes"][2]["length"] = 0
        d["episodes"][2]["dataset_to_index"] = d["episodes"][2]["dataset_from_index"]
        self.assertEqual(codes(d), ["EPISODE_EMPTY"])

    def test_duplicate_episode_index(self):
        d = base()
        d["episodes"][2]["episode_index"] = 1
        self.assertEqual(codes(d), ["EPISODE_INDEX_DUPLICATE"])
        d = base()
        d["episodes"][1]["episode_index"] = 0  # duplicate is still reported when it also causes a gap
        self.assertIn("EPISODE_INDEX_DUPLICATE", codes(d))

    def test_bad_licence_variants(self):
        for lic, want in (("proprietary", "LICENSE_NOT_ALLOWED"), ("", "LICENSE_MISSING"), (None, "LICENSE_MISSING"), (7, "WRONG_TYPE")):
            with self.subTest(lic=lic):
                d = base()
                d["license"] = lic
                self.assertEqual(codes(d), [want])

    def test_unknown_schema_version_stops_further_checks(self):
        d = base()
        d["schema_version"] = "synthetic-episodes-meta/v2"
        d["fps"] = "garbage"  # must not be reported: layout of an unknown version is not guessed
        self.assertEqual(codes(d), ["SCHEMA_VERSION_UNKNOWN"])
        d = base()
        del d["schema_version"]
        self.assertEqual(codes(d), ["MISSING_FIELD"])

    def test_timestamps_wrong_type_and_missing(self):
        d = base()
        d["episodes"][0]["frames"][1]["timestamp"] = "0.1"
        self.assertEqual(codes(d), ["WRONG_TYPE"])
        d = base()
        del d["episodes"][0]["frames"][1]["timestamp"]
        self.assertEqual(codes(d), ["MISSING_FIELD"])

    def test_tolerance_invalid(self):
        for bad in (0, -1, 0.06, "x", True):
            with self.subTest(bad=bad):
                d = base()
                d["timestamp_tolerance_s"] = bad
                self.assertIn("TOLERANCE_INVALID", codes(d))

    def test_fps_values(self):
        for bad in (0, -5, 1.5, "10", None, True, 5000):
            with self.subTest(bad=bad):
                d = base()
                d["fps"] = bad
                self.assertIn("FPS_INVALID", codes(d))

    def test_unit_and_value_checks_on_state_limits(self):
        d = base()
        d["episodes"][0]["frames"][0]["action"][5] = -0.01
        self.assertEqual(codes(d), ["OUT_OF_LIMITS"])

    def test_no_episodes_and_missing_features(self):
        d = base()
        d["episodes"] = []
        self.assertEqual(codes(d), ["NO_EPISODES"])
        d = base()
        del d["features"]["action"]
        self.assertEqual(codes(d), ["FEATURE_MISSING"])

    def test_task_index_unknown(self):
        d = base()
        d["episodes"][1]["task_index"] = 9
        self.assertEqual(codes(d), ["TASK_MISSING"])

    def test_not_synthetic(self):
        d = base()
        del d["synthetic"]
        self.assertEqual(codes(d), ["NOT_SYNTHETIC"])


class Robustness(unittest.TestCase):
    def test_non_object_documents_never_raise(self):
        for doc in (None, [], 5, "x", True, [{"a": 1}]):
            with self.subTest(doc=doc):
                diags, _ = v.validate_document(doc)
                self.assertEqual([d.code for d in diags], ["MALFORMED_DOCUMENT"])

    def test_hostile_shapes_never_raise(self):
        d = base()
        d["features"] = {"observation.state": 1, "action": [], "observation.images.front": "x", "observation.images.wrist": None}
        d["episodes"] = [None, 3, {"frames": "no"}, {"frames": [1, None, {"timestamp": {}}]}]
        d["tasks"] = [1, {"task_index": "a"}]
        diags, _ = v.validate_document(d)
        self.assertTrue(diags)
        self.assertNotIn("INTERNAL_ERROR", [x.code for x in diags])

    def test_text_level_failures(self):
        cases = {
            "{": "MALFORMED_JSON",
            "": "MALFORMED_JSON",
            '{"fps": NaN}': "NON_FINITE_VALUE",
            '{"fps": Infinity}': "NON_FINITE_VALUE",
            "[" * 100000: "MALFORMED_JSON",
            " " * (c.MAX_FILE_BYTES + 1): "FILE_TOO_LARGE",
        }
        for text, want in cases.items():
            with self.subTest(text=text[:20]):
                diags, _ = v.validate_text(text)
                self.assertEqual([d.code for d in diags], [want])

    def test_diagnostics_are_capped(self):
        d = base()
        for ep in d["episodes"]:
            for fr in ep["frames"]:
                fr["action"] = [99.0] * 6
                fr["observation.state"] = [99.0] * 6
        diags, trunc = v.validate_document(d)
        self.assertEqual(len(diags), c.MAX_DIAGNOSTICS)
        self.assertTrue(trunc)

    def test_validator_does_not_mutate_input(self):
        d = base()
        before = json.dumps(d, sort_keys=True)
        v.validate_document(d)
        self.assertEqual(before, json.dumps(d, sort_keys=True))


class FixtureHygiene(unittest.TestCase):
    def test_fixture_generator_is_in_sync(self):
        self.assertEqual(g.main(["--check"]), 0)

    def test_fixtures_are_tiny_synthetic_and_licensed(self):
        for dirpath, _, names in os.walk(FIX):
            for n in names:
                p = os.path.join(dirpath, n)
                with self.subTest(p):
                    self.assertLess(os.path.getsize(p), 10 * 1024)
                    self.assertTrue(n.endswith((".json", ".md")), n)
        for rel in g.build_all():
            if rel.startswith(("valid/", "invalid/")):
                doc = load(os.path.join(FIX, rel))
                if doc.get("schema_version") == c.SCHEMA_VERSION:
                    self.assertIs(doc.get("synthetic"), False if "not_synthetic" in rel else True)
        self.assertTrue(os.path.isfile(os.path.join(FIX, "LICENSE-NOTE.md")))

    def test_no_image_payload_in_fixtures(self):
        for rel in g.build_all():
            text = open(os.path.join(FIX, rel), encoding="utf-8").read()
            self.assertNotIn("data_b64", text)
            self.assertNotIn("base64", text.lower())

    def test_schema_file_constants_match_contract(self):
        s = load(os.path.join(ROOT, "schema", "synthetic-episodes.v1.schema.json"))
        self.assertEqual(s["properties"]["schema_version"]["const"], c.SCHEMA_VERSION)
        self.assertEqual(tuple(s["properties"]["license"]["enum"]), c.ALLOWED_LICENSES)
        self.assertEqual(s["properties"]["fps"]["maximum"], c.MAX_FPS)
        vf = s["$defs"]["vectorFeature"]["properties"]
        self.assertEqual(tuple(vf["names"]["const"]), c.JOINT_NAMES)
        self.assertEqual(tuple(vf["units"]["const"]), c.JOINT_UNITS)
        self.assertEqual(vf["shape"]["prefixItems"][0]["const"], c.VECTOR_DIM)
        cam = s["$defs"]["cameraFeature"]["properties"]
        self.assertEqual(cam["names"]["const"], c.CAMERA_SHAPE_NAMES)
        self.assertEqual(set(cam["camera"]["properties"]["encoding"]["enum"]), set(c.CAMERA_ENCODINGS))
        self.assertEqual(set(s["properties"]["features"]["required"]), {c.STATE_KEY, c.ACTION_KEY, *c.REQUIRED_CAMERA_KEYS})

    def test_joint_layout_matches_mock_policy_contract_when_present(self):
        path = os.path.join(os.path.dirname(ROOT), "cloud-robotics", "mock-policy", "contract.py")
        if not os.path.isfile(path):
            self.skipTest("examples/cloud-robotics/mock-policy not present in this tree")
        spec = importlib.util.spec_from_file_location("mock_policy_contract", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(tuple(mod.JOINTS), c.JOINTS)
        self.assertEqual(set(mod.CAMERA_KEYS.values()), set(c.REQUIRED_CAMERA_KEYS))


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-I", os.path.join(ROOT, "dq_validate.py"), *args],
            capture_output=True, text=True, timeout=30, env=env,
        )

    def test_valid_exit_zero(self):
        r = self.run_cli(VALID_MAIN)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    def test_invalid_exit_one_with_code_path_and_hint(self):
        r = self.run_cli(os.path.join(FIX, "invalid", "unit_mismatch.json"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("[UNIT_MISMATCH] /features/observation.state/units/5", r.stdout)
        self.assertIn("hint:", r.stdout)

    def test_json_output_is_machine_readable(self):
        r = self.run_cli("--format", "json", VALID_MAIN, os.path.join(FIX, "invalid", "episode_empty.json"))
        self.assertEqual(r.returncode, 1)
        rep = json.loads(r.stdout)
        self.assertEqual(rep["report_version"], c.REPORT_VERSION)
        self.assertFalse(rep["ok"])
        self.assertTrue(rep["files"][0]["ok"])
        d = rep["files"][1]["diagnostics"][0]
        self.assertEqual(set(d), {"code", "severity", "path", "message", "hint"})
        self.assertEqual(d["code"], "EPISODE_EMPTY")

    def test_unreadable_file_exit_two(self):
        r = self.run_cli(os.path.join(FIX, "does-not-exist.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("FILE_UNREADABLE", r.stdout)

    def test_malformed_json_file_exit_one(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "bad.json")
            with open(p, "w") as fh:
                fh.write("{not json")
            r = self.run_cli(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("MALFORMED_JSON", r.stdout)

    def test_usage_errors_exit_two(self):
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("--bogus").returncode, 2)

    def test_list_codes(self):
        r = self.run_cli("--list-codes")
        self.assertEqual(r.returncode, 0)
        for code in c.CODES:
            self.assertIn(code, r.stdout)


if __name__ == "__main__":
    unittest.main()
