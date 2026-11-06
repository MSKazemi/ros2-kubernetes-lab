# Agent mobility: portable mission-state contract (simulation)

> **SIMULATION / SYNTHETIC. Documentation and an offline toy, not an implementation of robot or agent migration.** Nothing described here moves a process, container, model or actuation right between machines. Nothing was run on a robot, ROS 2 graph or Kubernetes cluster. No latency, success-rate or other performance number is claimed. The legacy Vagrant/Foxy stack is historical and a Jazzy container-only smoke test does not establish cross-worker DDS.

This folder specifies the **mission-state handoff contract** `mission-state/v1` that a *simulated* executor hands to another, and the rules that make a stale, replayed or incompatible handoff get **refused**. It addresses [issue #104](https://github.com/MSKazemi/robo-resilience-lab/issues/104) (embodied agent mobility) and [issue #110](https://github.com/MSKazemi/robo-resilience-lab/issues/110) (portable mission-state contract and compatibility validation).

## Documents

| Document | Read it to learn |
| --- | --- |
| [MISSION-STATE-SCHEMA.md](MISSION-STATE-SCHEMA.md) | Every field of the bundle, versioning, execution epoch and fencing, sequences, replay nonce, state owner, capability requirements, rollback assumptions, order of checks |
| [COMPATIBILITY-AND-CAPABILITY-MATRIX.md](COMPATIBILITY-AND-CAPABILITY-MATRIX.md) | What a destination must match (frame, map, units, sensors, action space, capabilities) and the reason code for each mismatch |
| [WHAT-IS-NOT-MOVED.md](WHAT-IS-NOT-MOVED.md) | Mission-state handoff versus container migration, model relocation, delegation and transfer of actuation authority |
| [STALE-EXECUTOR-AND-FENCING-RULES.md](STALE-EXECUTOR-AND-FENCING-RULES.md) | Normative rules for rejecting a stale executor, replayed effects and replayed bundles |
| [FAILURE-CASE-CATALOGUE.md](FAILURE-CASE-CATALOGUE.md) | Numbered failure cases, expected behaviour in the simulator, fixture names, and what the toy does *not* cover |

Code, fixtures and tests live in [`examples/cloud-robotics/agent-mobility/`](../../../examples/cloud-robotics/agent-mobility/README.md).

## One-minute picture

```text
 origin executor        coordinator (owns state_owner + epoch)         effect sink (authoritative ledger)
 ---------------        --------------------------------------         ---------------------------------
 seal bundle  ───────►  validate: shape, digest, freshness, nonce,
 (cursor = ledger)      sequence, epoch, owner, ledger, compatibility
                        COMMIT: consume nonce+sequence, epoch += 1  ──►  install grant (owner, epoch)
                        destination activates  (or ROLLBACK: epoch += 1 again, grant to origin / nobody)
 old epoch resumes  ──────────────────────────────────────────────────►  rejected: STALE_EXECUTOR
```

The unit that moves is **a small, validated, integrity-checked description of mission progress plus the ownership generation under which it may continue**. The sink, not the executor, decides whether an effect is accepted.

## Relationship to the E08 toy and the seven-phase study

A draft pull request ([#109, "E08 offline embodied-agent mobility experiment and 7-phase protocol"](https://github.com/MSKazemi/robo-resilience-lab/pull/109)) proposes a research charter (`docs/scenario-lab/agent-mobility.md`) and a five-waypoint toy (`experiments/e08-task-handoff/`). That PR is **not assumed merged**; this folder uses only non-overlapping file names and the same vocabulary, and refers to it rather than redefining it.

| E08 term (PR #109) | Term and field here | Difference |
| --- | --- | --- |
| Logical task / task ID | `mission.task_id` | Same meaning |
| Execution / `execution_id` | *executor* / `ownership.state_owner`, `handoff.from_executor`, `handoff.to_executor` | Same role, different spelling; see reconciliation note in the example README |
| Checkpoint (`cursor`, `completed`, `sha256`) | `progress` + `integrity` | Adds `committed_effect_ids` so the bundle can be checked against the authoritative ledger |
| Epoch / fencing | `ownership.epoch` doubling as fencing token | Rollback is a new higher epoch rather than a decrement |
| Effect ID | `effect_id` | Same; the sink also enforces per-epoch `effect_seq` |
| Embodiment | `requirements` (class, frame, map, units, capabilities, sensors, action) | E08 checks frame, map and capabilities only |
| Freshness (observation expiry) | `handoff.issued_tick` / `expires_tick` for the *bundle* | Observation freshness is not part of this contract; it belongs to the observation/action contract ([`mock-policy`](../../../examples/cloud-robotics/mock-policy/README.md), issue #55) |

Both artifacts share the same limits: one process, logical ticks, plain SHA-256 digest (not a signature), no independent trust boundary, no durable coordinator.

## Status

| Item | State |
| --- | --- |
| Schema spec `mission-state/v1` | Proposed, stable enough to review; no external consumers |
| Validator and handoff simulator | Implemented as an offline toy; unit-tested; **simulation only** |
| Cross-process or cross-host handoff | Not implemented |
| Durable coordinator, authenticated broker, real action gate | Not implemented (see [#59](https://github.com/MSKazemi/robo-resilience-lab/issues/59)) |
| Measurements | None. Logical ticks are not milliseconds |
