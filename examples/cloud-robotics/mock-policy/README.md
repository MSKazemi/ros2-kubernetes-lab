# Simulated observation/action contract and MOCK policy (issue #55)

> **Simulated educational contract. Non-actuating.** Nothing here controls a robot, publishes to ROS 2, calls a model, uses a GPU or touches the network. The validator is **not** a safety-certified gate and `source_id` is **not** authentication. Cross-worker or Kubernetes behaviour is **not** tested here (see #14, #15, #16). The mock policy has **no task accuracy**; never report its output as a model result.

A beginner walkthrough is in [docs/OBSERVATION-ACTION-CONTRACT.md](../../../docs/OBSERVATION-ACTION-CONTRACT.md). This file is the reference.

## What is here

| File | Purpose |
| --- | --- |
| [`contract.py`](contract.py) | Constants of contract `ros2-obs-action/v1`: ordered joints with units and limits, camera name to key mapping, bounds. |
| [`schema/`](schema/) | JSON Schema (draft 2020-12) for the [observation](schema/observation.v1.schema.json) and [action](schema/action.v1.schema.json) messages. Documentation of the shape; a test keeps it in sync with `contract.py`. The Python validator is the executable authority. |
| [`validate.py`](validate.py) | Fail-closed validator. Stdlib only, imports no policy or model code. |
| [`mock_policy.py`](mock_policy.py) | Seeded, deterministic fake policy (`MOCK-policy-do-not-report-accuracy`). |
| [`fixture_gen.py`](fixture_gen.py) | Bounded deterministic generator for the committed [`fixtures/`](fixtures/) (fixed seed 42, 2x2 synthetic images, 2 sequences). |
| [`example.py`](example.py) | Traceable observation -> action -> validation -> replay-rejection run; prints JSON lines. |
| [`tests/`](tests/) | `unittest` suite with positive and negative cases. |

## Verify (one command, CPU only, about a second)

```sh
python3 -m unittest discover -s examples/cloud-robotics/mock-policy/tests -v
python3 examples/cloud-robotics/mock-policy/example.py        # optional: see a trace
python3 examples/cloud-robotics/mock-policy/fixture_gen.py --check   # fixtures not drifted
```

Needs Python 3.10 or newer (CI uses 3.12) and nothing else. No cleanup is needed: the tests write no files (only `__pycache__`, which is git-ignored) and start no processes besides short `python3` subprocesses.

## Contract v1 in short

Observation: `contract_version`, `simulated` (must be `true`), `observation_id`, `sequence_id`, `source_timestamp_ns` (monotonic source clock), `frame_name`, `task_id`, `ttl_ms`, `cameras` (each `name`, `key`, `width`, `height`, `encoding`, `data_b64`), `state` (`names`, `units`, `values` in the fixed joint order).

Action: `contract_version`, `simulated`, `source_id`, `sequence_id`, `observation_id`, `created_timestamp_ns`, `ttl_ms`, `task_id`, `model_id`, `model_revision`, `command`, `action_space`, `units`, `values`.

Camera mapping: `front_rgb` -> `observation.images.front`, `wrist_rgb` -> `observation.images.wrist`. Both are required.

Joints (name, unit, limits): `shoulder_pan` rad +-3.1416, `shoulder_lift` rad +-1.7, `elbow_flex` rad +-1.7, `wrist_flex` rad +-1.8, `wrist_roll` rad +-3.1416, `gripper` m 0..0.08. Action dimension is 6. Only the command `set_joint_targets` (action space `joint_position_target`) is allowed.

## Rejections (typed reasons)

`validate_observation(msg)` and `validate_action(msg, now_ns)` return a `ValidationResult` (`ok`, `reason`, `field`, `detail`) and never raise for bad input; an unexpected internal error becomes `INTERNAL_ERROR`. Rejected messages do not change validator state. The covered cases (each has a positive and a negative test):

| Requirement | Reasons |
| --- | --- |
| Required fields, types, malformed messages | `MISSING_FIELD`, `WRONG_TYPE`, `MALFORMED_MESSAGE`, `UNSUPPORTED_VERSION`, `NOT_SIMULATED` |
| Timestamps monotonic and bounded | `TIMESTAMP_OUT_OF_BOUNDS`, `TIMESTAMP_NOT_MONOTONIC`, `DUPLICATE_SEQUENCE`, `OUT_OF_ORDER_SEQUENCE` |
| Camera name to key mapping, shapes | `MISSING_CAMERA`, `UNKNOWN_CAMERA`, `CAMERA_KEY_MISMATCH`, `BAD_CAMERA_SHAPE`, `BAD_CAMERA_DATA` |
| State names, action dimension, units, limits | `WRONG_STATE_NAMES`, `WRONG_DIMENSION`, `WRONG_UNITS`, `OUT_OF_LIMITS` |
| NaN / infinity | `NON_FINITE_VALUE` |
| Stale or expired action | `STALE_ACTION` (age above `max_action_age_ms`, default 200), `EXPIRED_TTL`, `FUTURE_TIMESTAMP`, `STALE_OBSERVATION`, `UNKNOWN_OBSERVATION` |
| Unauthorized source or command | `UNAUTHORIZED_SOURCE` (allow-list, empty by default so all actions are rejected), `UNAUTHORIZED_COMMAND` |

Time is supplied by the caller (`now_ns`, same monotonic clock domain as the messages), so results are deterministic.

## Limits of this module

- **Not done (deferred by the issue):** the ROS 2 Jazzy adapter. It should only be added once a verified fixture/topic mapping exists. No ROS runtime was used or tested.
- `source_id` is a label compared to an allow-list. Real deployments need authenticated transport (for example SROS 2 or signed messages); not provided here.
- No fault-injection suite, safe-stop semantics or threat model: that is issue #59.
- Fixtures are synthetic (random bytes from a fixed seed, no real camera data).
