# What is NOT being moved

> **SIMULATION.** The phrase "agent mobility" invites over-reading. This page fixes the meaning used in this folder so that a successful toy run is not mistaken for something larger.

**What is moved:** responsibility for *continuing a high-level mission*, expressed as a small validated bundle ([schema](MISSION-STATE-SCHEMA.md)) plus a new ownership epoch. The destination re-creates its own execution from that bundle at a safe checkpoint.

## 1. Comparison

| | Mission-state handoff (this folder) | Container or pod migration | Model relocation | Delegation (A2A style) | Transfer of actuation authority |
| --- | --- | --- | --- | --- | --- |
| What changes hands | Mission progress and the right to continue it (epoch) | A packaged process image and its runtime placement | Where inference for a policy or planner runs | A bounded subtask, origin stays owner | Permission to send commands to a body |
| Process memory / image moved | No | Yes (restart or live) | No (weights may be loaded elsewhere) | No | No |
| Model weights or hidden model state moved | No | May be inside the image | Yes (copy or remote call) | No | No |
| Mission cursor preserved | Yes, by design | Not by itself; application-level | Not applicable | Origin keeps it | Not applicable |
| Ownership generation changes | Yes (epoch + 1) | No | No | No | Should be tied to it, but is separate |
| Needs the destination to match embodiment | Yes ([matrix](COMPATIBILITY-AND-CAPABILITY-MATRIX.md)) | Only for hardware access | Only for input/output shape | Capability of the delegate | Yes, plus safety case |
| Where it is studied here | This folder (#104, #110) | Kubernetes lab (`KubernetesClusterSetup/`, manifests) | Placement experiments (#62, #85, #96), serving work | Study charter in PR #109 (arm B2) | Fail-closed action gate (#59) |

## 2. Explicit non-goals

1. **Not container migration.** No pod, container, checkpoint-restore (CRIU), live migration or image is moved or even started. A Kubernetes event (reschedule, node drain) is a *trigger a future experiment might use*, not something modelled.
2. **Not model relocation.** Weights, tokenizers, caches, hidden states and GPU memory stay where they are. Whether a destination can run the same policy is a separate compatibility question that v1 only touches through declared action-space names.
3. **Not transfer of actuation authority.** A bundle does not authorise anyone to move hardware. The simulator's sink appends records to an in-memory list. A real action gate must be isolated from the worker, independently verify authority before every command, and is issue #59's subject, not this one.
4. **Not delegation.** In delegation the origin remains the owner. Here the owner changes and the origin is fenced.
5. **Not state synchronisation or replication.** There is one authoritative ledger; there is no multi-writer merge.
6. **Not a safety mechanism.** Refusing stale or incompatible handoffs reduces a class of *software* faults in the toy. It does not make a physical robot safe.
7. **Not distributed.** One Python process, logical ticks, no sockets, no clocks, no persistence. No ROS 2 graph, DDS discovery or cross-worker delivery is involved, so nothing here supports a claim about them.
8. **Not an authentication scheme.** `integrity.digest` is a plain hash, not a signature; the executor identifiers are labels, not credentials.

## 3. Consequences for how results may be described

* A passing unit test is **software validation of a toy**, not a research result. Do not place counts from it in a results registry.
* Do not write "the agent migrated" for a toy run. Write "a simulated mission-state handoff was accepted/refused with reason X".
* Mobility can be the wrong choice. Staying put, restarting, or delegating can be better when the destination is incompatible, observations are stale or the transfer adds risk; a refusal is a valid and expected outcome, not a failure of the contract.
