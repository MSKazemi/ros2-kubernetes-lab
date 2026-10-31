# Embodied agent mobility: seven-phase cloud–edge robotics research plan

> **Status: study proposal v0.1, 2026-10-28.** An **offline, single-process synthetic illustration** is implemented in [`experiments/e08-task-handoff/`](../../experiments/e08-task-handoff/). It is not real AI-agent migration, a robot controller, independent security enforcement, Kubernetes handoff, cross-worker ROS 2 messaging, an experiment comparing baselines, or a peer-reviewed result. The legacy Vagrant/Foxy/Kubernetes stack remains historical; a Jazzy container-only smoke test does not validate current cross-worker DDS.
>
> Tracking: [embodied mobility research issue #104](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/104). Related proposed experiment **E08** in the [integrated program roadmap PR #108](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/108); that PR is not assumed merged.

## Purpose and falsifiable question

**Under which task, network, robot-compatibility and fault conditions can a high-level AI mission resume on a different executor while preserving the correct mission cursor and refusing stale, repeated or incompatible *simulated* effects, compared with staying, restarting or delegating?**

Movement means **transfer of execution responsibility at a safe checkpoint**; a robot or Kubernetes pod moving between hosts, an A2A delegation, a remote model inference call, and physical task reassignment are distinct experiments. A process image, GPU memory, hidden model state, ROS 2 DDS participant, safety-critical control loop or real motor command is **not** migrated by this project.

The robot/simulator-side action policy must be independently enforced in a later distributed implementation. The present in-memory toy checks only a few semantic invariants and provides **no trust/security boundary**, durability, remote attestation, cancellation of physical movement or global containment guarantee.

### Definitions and research invariants

| Term | Intended meaning | Bounded claim to test |
| --- | --- | --- |
| Logical task | Stable mission goal and unique task ID | Task identity stays stable across handoff |
| Execution | One worker incarnation and execution ID | Each moved execution has a new identity |
| Checkpoint | Versioned, integrity-checked committed mission state | Receiver resumes at exact completed-waypoint prefix |
| Epoch / fencing | Coordinator-controlled ownership generation | An old executor cannot have a *covered* effect accepted after transfer |
| Effect ID | Stable ID for one simulated mission-side effect | Replays are rejected by a trusted future broker |
| Embodiment | Robot class, frame, map revision, skills and resource limits | Incompatible destinations refuse rather than silently adapt |
| Freshness | Observation time, expiry and clock assumptions | Stale data cannot authorize a new simulated effect |

**H1 continuity:** a correctly implemented checkpoint relocation may preserve completed steps better than naive restart after a crash. **H2 bounded authority:** after the owner epoch changes, a stale origin cannot commit *through the tested action gateway*. **H3 compatibility:** incompatible frame/map/capability/observation must block handoff. **H4 decision quality:** migration is sometimes worse than staying/delegating when transfer costs, uncertainty or network partitions dominate. These are hypotheses, **not results**. A sound study must include counterexamples and negative findings.

## Seven phase research and implementation gates

| Phase | Research question | Deliverable and evidence required | State |
| --- | --- | --- | --- |
| **1. Foundations** | What exactly counts as moving an agent? | Taxonomy, boundaries, H1–H4, risks, baselines and falsifiable preregistration | Proposed here; preregistration not completed |
| **2. Robotics substrate** | Can we replay a synthetic mission/fault schedule without hardware? | Offline fixture, validator, deterministic toy trace and negative unit tests; *later* proven ROS 2 cross-worker environment | Small single-process toy available; ROS/K8s not tested here |
| **3. Portable state** | Which high-level state is transferable, and which permissions remain site-bound? | Versioned schema, state compatibility engine, immutable checkpoint transfer and validation across processes | Toy subset only; full transfer planned |
| **4. Secure handoff** | Can a stale execution or duplicate request cause a protected action? | Independent broker, coordinator-owned durable epochs, consent/revocation, uncertain-effect reconciliation, fault tests | Toy epoch/replay checks only; no security guarantee |
| **5. Cloud–edge integration** | Can task execution survive a real host boundary or partition? | Two verified Kubernetes workers, real inter-node transport, ROS 2 message evidence, container revisions and failure traces | Planned; depends on #14/#15/#16 and review of PR #97 |
| **6. Comparative evaluation** | When is mobility preferable to stay/restart/delegate? | Frozen cases, equal fault schedules, B0–B3 implementation, all failures, uncertainty intervals and reproducible plots | Planned; no benchmark numbers |
| **7. Heterogeneous AI and robots** | When can a mission move across different robots, models or runtimes? | Embodiment and policy compatibility tests, optional pinned HF artifacts, multi-robot evidence and publication package | Planned; physical trials out of scope |

Do not interpret a successful unit test in Phase 2 as completing Phases 3–7. In particular, the current toy is **one process, one memory ledger and synthetic logical ticks**; it has no independent robot-side authority or distributed effect commit.

## First executable slice: fictional five-waypoint inspection

Fixture: [`inspection-v0.1.json`](../../experiments/e08-task-handoff/fixtures/inspection-v0.1.json). The example starts with two waypoints already completed by a cloud-named logical execution, produces a canonical SHA-256 snapshot of the declared state, updates a local owner epoch, and completes remaining waypoint *records* under an edge-named logical execution. It checks three explicit rejected probes: stale origin, effect-ID replay, and expired observation. It also rejects malformed fixture fields, incompatible destination frame/map/capabilities, tampered snapshot digest and reuse of a stale pre-transfer snapshot.

The SHA-256 digest detects accidental content modification **in the toy**; it is not a signature, authentication, MAC, or independently trusted provenance. The in-memory epoch is not a durable fencing token. No messages move between OS processes and no ROS 2 command is emitted.

Run from the repository root (Python 3.10+ standard library):

```sh
python3 experiments/e08-task-handoff/simulate.py --validate-only
python3 experiments/e08-task-handoff/simulate.py
python3 -m unittest discover -s experiments/e08-task-handoff/tests -v
```

The CLI prints deterministic **synthetic illustration traces**, not field measurements. See the [E08 runner README](../../experiments/e08-task-handoff/README.md) for exact guarantees and limitations. A real implementation must replace these toy checks with independently verified and durable enforcement; it must **not** reuse the toy as a safety gateway.

## Later R1 scientific comparison (not yet implemented)

Keep the same mission, observation sequence, fault seeds, executor constraints and time measurement methodology for each arm:

| Arm | Ownership semantics | What to report |
| --- | --- | --- |
| **B0 stay** | Original task/executor does not transfer ownership | Timeouts, incomplete mission, valid actions, downtime |
| **B1 restart** | New executor restarts without portable checkpoint | Repeated/lost steps and whether independent effect gate blocks repeats |
| **B2 delegate** | Origin retains ownership and requests a bounded remote subtask | Cancellation and origin-dependency under partitions |
| **B3 relocate** | Destination receives validated checkpoint and new epoch | Resume correctness, refused transfers, downtime, transfer bytes |

Predeclare fault injections at **before prepare**, **after snapshot**, **after fencing**, **before destination activation**, **after simulated effect commit but before acknowledgement**, **during partition**, and **when stale origin recovers**. A lost ACK with uncertain external side effect must be *parked/reconciled*, not silently replayed. Include invalid robot map frame, missing capability, incompatible schema, observation expiry, grant revocation, and refused destinations. Do not choose fault timing after seeing outcome.

**Primary outcome (proposed):** fraction of runs that complete the mission *correctly* without unauthorized or duplicate **accepted covered simulated effects**. Report numerator, denominator and failure cases. Secondary outcomes: lost/repeated completed steps, p50/p95/p99 time to first next valid action, downtime, transfer bytes, rejected/unknown effects, compatibility refusals, cost/energy where actually metered, recovery rate, and intervention burden. Use monotonic clocks or explicitly documented cross-host synchronization; the toy's ticks are not milliseconds.

Before any statistical comparison: freeze fixtures, measure and document fault delivery, record source SHA/OCI digests, ROS/Kubernetes/RMW/discovery versions, independent seeds, task/robot revisions, resources and uncertainty plan. Reuse [result publication contract](RESULTS-PUBLICATION.md), [#60 run manifest](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/60) and [#88 evidence registry](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/88); **do not put toy counts or imaginary runtime performance into the public result registry**.

## Dependencies and division of responsibility

- **Platform prerequisite:** #14 cross-worker ROS 2 talker/listener, #15 maintained DDS discovery, #16 kind/k3d validation, #7 supported image baseline. PR #97 requires independent review before claiming this gate.
- **Independent simulator action permissions:** #55 typed observation/action contract and #59 fail-closed action gate. Keep execution privilege decisions outside untrusted model output; never send arbitrary shell commands, `/cmd_vel` or motor commands.
- **Existing neighboring work:** #62/#85/#96 evaluate **inference placement/freshness**, not state relocation; #69/#87 study fair scheduling, not mission-state authority; #83 owns site gallery; #60/#88 own results metadata.
- **External models:** Hugging Face assets are optional and require exact compatible model/processor revisions, licenses, data rights and reproducible embedding/action semantics. Jev-like recommendations may rank **prequalified placements**, not enforce permissions or safety.
- **Privacy/security:** use synthetic fixtures and local isolated nonprivileged execution. Never commit tokens, private sensors/maps, secrets, real robot endpoints or personal data. No physical deployment or paid cloud call is authorized by this document.

## Next scoped tasks for a Claude Code / Codex contributor

1. Read root `AGENTS.md`, `SAFETY.md`, issue #104 and this study. Run the offline toy tests and confirm they do **not** cover real transport or independent enforcement.
2. Design a **new** cross-process contract with coordinator-owned durability and a separately provisioned action broker; do not treat shared SQLite on arbitrary network filesystems as a secure distributed authority.
3. Build explicit fault-state fixtures for crash-before-fence, after-fence, after-effect-before-ack, partition and stale origin; require failed/uncertain outcomes to appear in evidence.
4. Before any ROS network benchmark, verify the actual cluster, middleware/discovery and pod-to-worker mapping. Keep the original Foxy/Vagrant historical configuration separate.
5. Submit one focused PR with exact commands, observed evidence, limitations and no automatic main-branch merge.

**A valid scientific negative result is valuable:** an agent should stay put when the destination is incompatible, the network is unsafe, observations are stale or moving would add risk without improving useful work.
