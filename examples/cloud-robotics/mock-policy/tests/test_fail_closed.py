"""Fail-closed behaviour, independence from model code, mock policy, fixtures."""

import ast
import json
import subprocess
import sys
import unittest
from unittest import mock

import support
from support import ContractCase, ROOT, act1, c, make_validator, now_for, obs1, obs2

import fixture_gen
import mock_policy
import validate


class FailClosedTests(ContractCase):
    def test_validator_never_raises_on_hostile_inputs(self):
        cyclic = {}
        cyclic["self"] = cyclic
        deep = cur = []
        for _ in range(5000):
            nxt = []
            cur.append(nxt)
            cur = nxt
        hostile = [
            None, True, 0, -1, 10**400, float("nan"), "", "x" * 10_000, b"bytes", [], [[]], {}, {"": ""},
            cyclic, deep, {"values": deep}, {1: 2}, {(1, 2): 3}, object(), lambda: 1,
        ]
        for h in hostile:
            with self.subTest(h=type(h).__name__):
                val = make_validator()
                self.assertFalse(val.validate_observation(h).ok)
                self.assertFalse(val.validate_action(h, 10).ok)
                self.assertFalse(val.validate_action(act1(), h).ok)

    def test_hostile_field_values_do_not_raise(self):
        for field in c.ACTION_FIELDS:
            for bad in (None, {}, [], 10**400, float("nan"), object()):
                with self.subTest(field=field, bad=type(bad).__name__):
                    a = act1()
                    a[field] = bad
                    r = make_validator().validate_action(a, now_for(act1()))
                    self.assertFalse(r.ok)

    def test_unexpected_internal_error_becomes_rejection(self):
        val = make_validator()
        with mock.patch.object(validate.ContractValidator, "_check_action", side_effect=RuntimeError("boom")):
            r = val.validate_action(act1(), 1)
        self.assertRejected(r, self.R.INTERNAL_ERROR)
        with mock.patch.object(validate.ContractValidator, "_check_observation", side_effect=ZeroDivisionError):
            r = val.validate_observation(obs1())
        self.assertRejected(r, self.R.INTERNAL_ERROR)

    def test_rejection_carries_typed_reason_and_serialises(self):
        a = act1()
        a["source_id"] = "nobody"
        r = make_validator().validate_action(a, now_for(a))
        self.assertIsInstance(r.reason, validate.RejectReason)
        d = r.as_dict()
        self.assertEqual(d["reason"], "UNAUTHORIZED_SOURCE")
        json.dumps(d)

    def test_bad_config_raises_at_construction_only(self):
        for kw in ({"max_action_age_ms": -1}, {"max_action_age_ms": True}, {"observation_registry_size": 0}):
            with self.assertRaises(ValueError):
                validate.ContractConfig(**kw)

    def test_observation_registry_is_bounded(self):
        val = make_validator(observation_registry_size=1)
        self.assertAccepted(val.validate_observation(obs1()))
        self.assertAccepted(val.validate_observation(obs2()))
        a = act1()  # refers to obs-0001, which was evicted
        self.assertRejected(val.validate_action(a, now_for(a)), self.R.UNKNOWN_OBSERVATION)


class IndependenceTests(unittest.TestCase):
    """The validator must not depend on any AI, model or ROS code."""

    FORBIDDEN = {"mock_policy", "fixture_gen", "torch", "numpy", "transformers", "huggingface_hub",
                 "rclpy", "requests", "urllib", "socket", "openai", "anthropic"}

    def test_validator_and_contract_import_only_stdlib_and_contract(self):
        for fname in ("validate.py", "contract.py"):
            tree = ast.parse((ROOT / fname).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                for n in names:
                    self.assertNotIn(n, self.FORBIDDEN, f"{fname} imports {n}")
                    if n not in sys.stdlib_module_names:
                        self.assertEqual(n, "contract", f"{fname} imports non-stdlib module {n}")

    def test_validator_works_without_mock_policy_loaded(self):
        code = (
            "import sys; sys.path.insert(0, %r); import validate; "
            "assert 'mock_policy' not in sys.modules and 'fixture_gen' not in sys.modules"
        ) % str(ROOT)
        subprocess.run([sys.executable, "-I", "-c", code], check=True)


class MockPolicyTests(ContractCase):
    def test_deterministic_for_same_seed(self):
        o = obs1()
        self.assertEqual(mock_policy.MockPolicy(seed=7).act(o), mock_policy.MockPolicy(seed=7).act(o))

    def test_different_seed_changes_output(self):
        o = obs1()
        self.assertNotEqual(mock_policy.MockPolicy(seed=7).act(o)["values"], mock_policy.MockPolicy(seed=8).act(o)["values"])

    def test_output_is_valid_and_traceable(self):
        val = make_validator()
        o = obs1()
        self.assertAccepted(val.validate_observation(o))
        a = mock_policy.MockPolicy(seed=3).act(o)
        self.assertEqual(a["observation_id"], o["observation_id"])
        self.assertEqual(a["sequence_id"], o["sequence_id"])
        self.assertAccepted(val.validate_action(a, now_for(a)))

    def test_clearly_marked_mock(self):
        a = mock_policy.MockPolicy().act(obs1())
        self.assertTrue(a["model_id"].startswith("MOCK"))
        self.assertTrue(a["source_id"].startswith("MOCK"))
        self.assertIs(a["simulated"], True)

    def test_clamps_to_limits(self):
        o = obs1()
        o["state"]["values"] = [hi for _, hi in c.JOINT_LIMITS]
        a = mock_policy.MockPolicy(seed=1).act(o)
        for v, (lo, hi) in zip(a["values"], c.JOINT_LIMITS):
            self.assertTrue(lo <= v <= hi)


class FixtureTests(unittest.TestCase):
    def test_committed_fixtures_match_generator(self):
        for name, doc in fixture_gen.build_all().items():
            text = (ROOT / "fixtures" / name).read_text(encoding="utf-8")
            self.assertEqual(text, fixture_gen.render(doc), f"{name} drifted from fixture_gen.py")

    def test_generator_is_bounded(self):
        for bad in (0, fixture_gen.MAX_FIXTURES + 1):
            with self.assertRaises(ValueError):
                fixture_gen.build_all(bad)
        with self.assertRaises(ValueError):
            fixture_gen.build_observation(0)

    def test_fixtures_are_tiny(self):
        total = sum(p.stat().st_size for p in (ROOT / "fixtures").iterdir())
        self.assertLess(total, 16 * 1024)


class SchemaSyncTests(unittest.TestCase):
    """The JSON Schemas are documentation; keep them in sync with contract.py."""

    def _schema(self, name):
        return json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))

    def test_observation_schema_matches_contract(self):
        s = self._schema("observation.v1.schema.json")
        self.assertEqual(set(s["required"]), set(c.OBSERVATION_FIELDS))
        self.assertEqual(set(s["properties"]), set(c.OBSERVATION_FIELDS))
        cam = s["properties"]["cameras"]["items"]
        self.assertEqual(set(cam["required"]), set(c.CAMERA_FIELDS))
        self.assertEqual(set(cam["properties"]["name"]["enum"]), set(c.CAMERA_KEYS))
        self.assertEqual(set(cam["properties"]["key"]["enum"]), set(c.CAMERA_KEYS.values()))
        self.assertEqual(set(cam["properties"]["encoding"]["enum"]), set(c.CAMERA_ENCODINGS))
        st = s["properties"]["state"]
        self.assertEqual(set(st["required"]), set(c.STATE_FIELDS))
        self.assertEqual(st["properties"]["names"]["const"], list(c.JOINT_NAMES))
        self.assertEqual(st["properties"]["units"]["const"], list(c.JOINT_UNITS))
        self.assertEqual(s["properties"]["contract_version"]["const"], c.CONTRACT_VERSION)

    def test_action_schema_matches_contract(self):
        s = self._schema("action.v1.schema.json")
        self.assertEqual(set(s["required"]), set(c.ACTION_FIELDS))
        self.assertEqual(set(s["properties"]), set(c.ACTION_FIELDS))
        self.assertEqual(s["properties"]["units"]["const"], list(c.JOINT_UNITS))
        self.assertEqual(s["properties"]["command"]["enum"], list(c.ALLOWED_COMMANDS))
        self.assertEqual(s["properties"]["action_space"]["const"], c.ACTION_SPACE)
        limits = [(p["minimum"], p["maximum"]) for p in s["properties"]["values"]["prefixItems"]]
        self.assertEqual(limits, list(c.JOINT_LIMITS))

    def test_fixtures_have_exactly_the_schema_fields(self):
        o = json.loads((ROOT / "fixtures" / "observation_0001.json").read_text())
        a = json.loads((ROOT / "fixtures" / "action_0001.json").read_text())
        self.assertEqual(set(o), set(c.OBSERVATION_FIELDS))
        self.assertEqual(set(a), set(c.ACTION_FIELDS))


class ExampleTests(unittest.TestCase):
    def test_example_runs_and_states_non_actuation(self):
        p = subprocess.run([sys.executable, str(ROOT / "example.py")], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("NON-ACTUATING", p.stdout)
        self.assertIn("DUPLICATE_SEQUENCE", p.stdout)


if __name__ == "__main__":
    unittest.main()
