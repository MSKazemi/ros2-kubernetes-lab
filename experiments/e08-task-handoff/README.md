# E08 — synthetic embodied-agent mission handoff (offline toy)

> **State: executable educational illustration, not a robotics migration implementation or a benchmark.** This directory contains a fictional five-waypoint mission, a strict fixture validator, and a **single-process, in-memory** example of how task cursor, logical epoch and an effect-ID deduplication rule might fit together. It runs without ROS 2, Kubernetes, networks, credentials, models or external Python packages.

The **study charter and seven research phases** are in [`docs/scenario-lab/agent-mobility.md`](../../docs/scenario-lab/agent-mobility.md), tracked by [public research issue #104](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/104). This is E08 of the proposed research portfolio; it does **not** replace existing #55/#59 safety contracts or #60/#88 results schemas.

## Run (Python 3.10+)

From the repository root:

```sh
python3 experiments/e08-task-handoff/simulate.py --validate-only
python3 experiments/e08-task-handoff/simulate.py
python3 -m unittest discover -s experiments/e08-task-handoff/tests -v
```

`--validate-only` checks the sample contract without mutating state. The default command emits a deterministic JSON **synthetic example trace**: two waypoints are already completed, an illustrative epoch change occurs from the cloud-named execution to the edge-named execution, the remaining three waypoint records are accepted, and three negative probes are rejected. IDs and time *ticks* are made up; nothing connects to any ROS 2 topic or robot.

Use `--fixture PATH` with another JSON file to run the same basic contract checks. Invalid fixtures/missing input return code **2**. This directory intentionally has no install step, model weights, network calls, or cloud credentials.

## Contract / what is checked

- Top-level and nested JSON fields are allowlisted; unsupported schema versions, unknown keys, duplicate waypoint names and malformed IDs are refused.
- `checkpoint.completed` must exactly equal the prefix of mission waypoints specified by `checkpoint.cursor`; the checkpoint cannot already be finished.
- Destination execution must differ; robot ID, coordinate frame, map revision and declared capabilities are verified against the supplied **synthetic** fixture.
- The in-memory checkpoint is SHA-256 digested and a modified or previously used snapshot is refused.
- The single-process toy effect sink accepts only the next waypoint when the caller names the current execution/epoch, the synthetic observation tick is fresh, and the effect ID was not previously accepted.
- Negative unit tests cover malformed state, incompatible robot metadata, bad/future/expired observations, tampering, repeated handoff, stale origin, incorrect waypoint and CLI error behavior.

## Critical limitations and later work

These checks **do not** prove identity, signatures, authorization, destination attestation, independent action permissions, durable atomic ownership, process crash recovery, exactly-once execution, state migration across machines, DDS discovery or physical robot safety. The `sha256` field is a plain digest, **not a cryptographic signature**; a malicious caller could forge the whole JSON. The test sink shares the same Python memory and trusted fixture as the simulated coordinator. A real action gate must be isolated from the AI worker and independently verify authority before each effect.

Later experiments must introduce actual independent processes, durable fencing, a broker that is not controlled by the agent, lost-ACK reconciliation, true fault injection, equal B0/B1/B2/B3 comparison arms, and ultimately separately verified ROS 2 cross-worker experiments after infrastructure issues #14/#15/#16. Never wire this file to `/cmd_vel`, motor controllers, or live hardware. No model quality, latency, energy, completion probability or comparative migration benefit is measured here.

**Result reporting rule:** keep the website's scientific-results registry at `planned` with `null` values until independently reviewed research runs and reproducible evidence exist. Deterministic unit tests are software validation, not peer-reviewed comparative measurements.
