"""Shared helpers for the tests (stdlib unittest only)."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import contract as c  # noqa: E402
import validate as v  # noqa: E402

ALLOWED = "MOCK-policy-01"


def load(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def obs1():
    return copy.deepcopy(load("observation_0001.json"))


def obs2():
    return copy.deepcopy(load("observation_0002.json"))


def act1():
    return copy.deepcopy(load("action_0001.json"))


def act2():
    return copy.deepcopy(load("action_0002.json"))


def now_for(action, offset_ms=10):
    return action["created_timestamp_ns"] + offset_ms * 1_000_000


def make_validator(**kw):
    kw.setdefault("allowed_sources", frozenset({ALLOWED}))
    return v.ContractValidator(v.ContractConfig(**kw))


class ContractCase(unittest.TestCase):
    R = v.RejectReason

    def assertRejected(self, result, reason, field=None):
        self.assertFalse(result.ok, f"expected rejection {reason}, got accept")
        self.assertEqual(result.reason, reason, result.as_dict())
        if field is not None:
            self.assertEqual(result.field, field, result.as_dict())

    def assertAccepted(self, result):
        self.assertTrue(result.ok, result.as_dict())
        self.assertIsNone(result.reason)
