# Mission-state handoff validator and simulator (SIMULATION, issues #104 and #110)

> **SIMULATION. SYNTHETIC. NON-ACTUATING.** A single-process, standard-library toy that validates a portable mission-state bundle (`mission-state/v1`) and replays scripted handoffs with logical ticks. It does **not** move a process, container, model or actuation right, and it opens no socket, publishes to no ROS 2 topic, drives no robot, and writes no file (except `fixture_gen.py`, which regenerates the fixtures). Its sink only appends records to an in-memory list. The SHA-256 digest is **not** a signature. Coordinator, sink and executors share one Python process, so this is **not** a trust boundary or a safety gate. No latency, success rate or other performance figure is produced; ticks are logical, not milliseconds. It says nothing about cross-worker DDS or Kubernetes behaviour.

Specification and rationale: [`docs/cloud-robotics/agent-mobility/`](../../../docs/cloud-robotics/agent-mobility/README.md).

## Files

| File | Purpose |
| --- | --- |
| [`mission_state.py`](mission_state.py) | `mission-state/v1` validator, typed `Reason` codes, canonical digest, compatibility check, `validate_for_commit` |
| [`handoff_sim.py`](handoff_sim.py) | Coordinator, epoch-fencing effect sink, executors, handoff with fault injection and rollback; runs script fixtures |
| [`validate_bundle.py`](validate_bundle.py) | CLI that checks `bundle-check` fixtures and compares each verdict to its expectation |
| [`fixture_gen.py`](fixture_gen.py) | Deterministic generator for every JSON fixture (`--check` detects drift) |
| [`fixtures/bundles/`](fixtures/bundles/) | 35 `bundle-check` fixtures: one accepted control, one per bundle rejection reason (33), and one multi-mismatch case |
| [`fixtures/scripts/`](fixtures/scripts/) | 11 `handoff-script` fixtures: happy path, stale executor, effect-gate rejections, lease, rollback, parking, abort, refusal, ping-pong |
| [`tests/`](tests/) | `unittest` suite; fails if any rejection reason lacks a fixture |

## Run (Python 3.10+, standard library only, CPU only, well under a second)

From the repository root:

```sh
python3 -m unittest discover -s examples/cloud-robotics/agent-mobility/tests -v
python3 examples/cloud-robotics/agent-mobility/validate_bundle.py          # exit 0 if every verdict matches
python3 examples/cloud-robotics/agent-mobility/handoff_sim.py              # exit 0 if every script meets its expectations
python3 examples/cloud-robotics/agent-mobility/handoff_sim.py --trace examples/cloud-robotics/agent-mobility/fixtures/scripts/rollback-ack-lost-after-effects.json
python3 examples/cloud-robotics/agent-mobility/fixture_gen.py --check      # exit 1 if committed fixtures drifted
```

Do not use `python3 -I` for the scripts: isolated mode removes the script directory from the import path.

Exit codes: `0` all expectations met, `1` an expectation failed (or fixture drift), `2` unreadable or invalid input.

## What the simulator checks

* **Epoch and fencing:** every effect carries an epoch; the sink rejects any epoch other than the one it last granted. A former owner resuming after takeover gets `STALE_EXECUTOR`.
* **Replay:** a bundle nonce is single use (`REPLAYED_NONCE`), handoff sequences must increase (`STALE_SEQUENCE`), effect IDs are single use (`REPLAYED_EFFECT`), and effect sequences are gap-free per epoch.
* **Compatibility:** frame, map revision, robot class, unit convention, capabilities, sensors (presence, type, units) and action command, space and units must match; a mismatch refuses the handoff and nothing adapts silently.
* **Staleness:** expired and future-dated bundles, bundles whose checkpoint lags the authoritative ledger, expired leases.
* **Rollback:** a committed handoff whose destination never activates is rolled back by issuing a **new, higher** epoch to the origin, which resumes from the sink ledger; or the mission is parked (no owner) when the origin is unavailable or the bundle says `park`. Aborts before commit change nothing.

## Fixture conventions

Fixtures are fictional: made-up IDs (`cloud-01`, `edge-01`, `wp-01`, ...), logical ticks, no map, robot or data. A `bundle-check` fixture holds `{expect, context, bundle}`; a `handoff-script` fixture holds `{setup, ops, expect_final}` where each op's `expect` is the verdict string (`ACCEPTED`, a reason code, an outcome such as `ROLLED_BACK`, or `REJECTED:<REASON>`). Regenerate with `python3 fixture_gen.py`; never hand-edit generated JSON.

## Limits

* Not durable: kill the process and all state is gone.
* No authentication: `executor` fields are labels; the digest is recomputable by anyone who edits the file.
* No real time, no network, no concurrency, no fault timing beyond the scripted points `destination_unreachable`, `destination_crash` and `ack_lost`.
* A passing test suite is software validation of this toy. It is not a research result and must not be entered in any results registry.
* Never wire this code to `/cmd_vel`, a motor controller or live hardware.

## Reconciliation with the E08 toy (draft PR #109)

This folder uses non-overlapping paths and does not edit or import `experiments/e08-task-handoff/`. Terminology maps as described in the [docs README](../../../docs/cloud-robotics/agent-mobility/README.md#relationship-to-the-e08-toy-and-the-seven-phase-study). The two toys intentionally have different schema identifiers (`mission-state/v1` here, `e08-synthetic-mission-v0.1` there) and are not interchangeable.
