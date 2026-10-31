"""Traceable request -> response example. Simulated only; NON-ACTUATING.

Reads the committed observation fixture, validates it, asks the MOCK policy
for an action, validates the action, and prints one JSON line per step. The
"dispatch" step only prints a message: nothing is sent to ROS or to a robot.

    python3 example.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mock_policy
import validate

HERE = Path(__file__).resolve().parent
NOW_OFFSET_NS = 10_000_000  # simulated receive time: 10 ms after the action


def main() -> int:
    obs = json.loads((HERE / "fixtures" / "observation_0001.json").read_text(encoding="utf-8"))
    validator = validate.ContractValidator(
        validate.ContractConfig(allowed_sources=frozenset({mock_policy.DEFAULT_SOURCE_ID}))
    )
    steps = []

    r_obs = validator.validate_observation(obs)
    steps.append({"step": "observation", "observation_id": obs["observation_id"], **r_obs.as_dict()})
    action = mock_policy.MockPolicy(seed=42).act(obs)
    now_ns = action["created_timestamp_ns"] + NOW_OFFSET_NS
    r_act = validator.validate_action(action, now_ns)
    steps.append(
        {"step": "action", "observation_id": action["observation_id"], "model_id": action["model_id"], **r_act.as_dict()}
    )
    # Replaying the same action must be rejected (duplicate sequence).
    r_replay = validator.validate_action(action, now_ns)
    steps.append({"step": "action_replay", "observation_id": action["observation_id"], **r_replay.as_dict()})

    for s in steps:
        print(json.dumps(s, sort_keys=True))
    accepted = r_obs.ok and r_act.ok and not r_replay.ok
    print(
        "NON-ACTUATING: simulated example only; no ROS, no robot and no dispatch happened. "
        "MOCK policy output has no task accuracy."
    )
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
