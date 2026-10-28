"""MOCK policy: a seeded, deterministic stand-in for a model. Stdlib only.

It is NOT a learned model, has no accuracy and must never be reported as a
model result. It moves each joint 10 % toward zero with tiny seeded noise and
clamps to the contract limits. It never touches a robot or ROS.

It does not validate anything: the validator (``validate.py``) is separate and
does not import this module.
"""

from __future__ import annotations

import random

import contract as c

MODEL_ID = "MOCK-policy-do-not-report-accuracy"
MODEL_REVISION = "mock-0"
DEFAULT_SOURCE_ID = "MOCK-policy-01"


class MockPolicy:
    def __init__(
        self,
        seed: int = 0,
        source_id: str = DEFAULT_SOURCE_ID,
        ttl_ms: int = 100,
        latency_ns: int = 1_000_000,
    ):
        self.seed = seed
        self.source_id = source_id
        self.ttl_ms = ttl_ms
        self.latency_ns = latency_ns

    def act(self, observation: dict) -> dict:
        """Build an action message for an (already validated) observation.

        Output depends only on ``seed`` and the observation, so it is
        reproducible. ``created_timestamp_ns`` is the observation timestamp
        plus a fixed simulated latency; no wall clock is read.
        """
        seq = observation["sequence_id"]
        rng = random.Random(f"{self.seed}:{seq}")
        values = []
        for current, (lo, hi) in zip(observation["state"]["values"], c.JOINT_LIMITS):
            noise = rng.uniform(-1.0, 1.0) * (hi - lo) * 0.005
            target = min(hi, max(lo, current * 0.9 + noise))
            values.append(round(target, 6))
        return {
            "contract_version": c.CONTRACT_VERSION,
            "simulated": True,
            "source_id": self.source_id,
            "sequence_id": seq,
            "observation_id": observation["observation_id"],
            "created_timestamp_ns": observation["source_timestamp_ns"] + self.latency_ns,
            "ttl_ms": self.ttl_ms,
            "task_id": observation["task_id"],
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "command": c.ALLOWED_COMMANDS[0],
            "action_space": c.ACTION_SPACE,
            "units": list(c.JOINT_UNITS),
            "values": values,
        }
