# Scenario catalog: 18 experiments for students, PhD researchers and industry

> **Proposal catalog, NOT claimed implementations.** All scenarios assume synthetic, licensed or public approved data and simulated actuation. Cross-worker success, inference benchmarks and physical reliability have **not** been newly tested. See [architecture](VISION-AND-ARCHITECTURE.md) and [benchmark methodology](BENCHMARKS-AND-REPRODUCIBILITY.md).

**Difficulty tiers:** E0 = beginner laptop / schema or offline data, E1 = intermediate CPU laptop with small ROS fixture, E2 = two-worker Kubernetes experiment or optional accelerator, E3 = PhD/industry research with controlled infrastructure. These are **relative complexity levels**, not verified hardware or duration guarantees.

## Quick selection matrix

| ID | Scenario | Audience | Tier | Core question / measurable outcome | Existing/new issue |
| --- | --- | --- | --- | --- | --- |
| CR-01 | ROS nodes vs Kubernetes workers | Bachelor | E0–E1 | Can two self-starting ROS apps really communicate on different workers? | [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14), [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16) |
| CR-02 | DDS discovery and QoS failure maze | BSc/MSc | E1–E2 | How do discovery, QoS and restarts change observed delivery? | [#15](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/15), [#48](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/48) |
| CR-03 | Synthetic camera/state/action publisher | MSc | E1 | Which drops and timestamp mismatches can a test detect? | [#49](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/49), [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55) |
| CR-04 | ROS bag to LeRobotDataset v3 | MSc/PhD | E1 | Can independent people reproduce aligned multimodal episodes? | [#56](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/56) |
| CR-05 | Immutable HF Hub experiment | MSc/Platform | E0–E1 | Does the exact model/dataset revision work offline and reject drift? | [#58](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/58) |
| CR-06 | CPU mock policy + action validation | MSc/Safety | E1 | Are stale, malicious and malformed actions always blocked? | [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55), [#59](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59) |
| CR-07 | Compatible LeRobot remote inference | AI/Robotics | E2 | Do policy/server/client/simulator semantics actually match? | [#57](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57), [#61](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61) |
| CR-08 | Adaptive edge vs remote inference | PhD/Industry | E2–E3 | What network conditions increase action age and missed deadlines? | [#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62) |
| CR-09 | LLM natural language to safe simulator skill | AI/LLM MSc | E1–E2 | How often does a planner propose unauthorized or invalid calls? | [#64](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64) |
| CR-10 | RAG robotics troubleshooting tutor | Students/Operators | E0–E1 | Does retrieval reduce unsupported or misleading diagnostics? | [#65](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/65) |
| CR-11 | Fault-injection / safe failure lab | Safety/PhD | E1–E3 | Which failure modes cause delayed reject/hold and data loss? | [#59](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59) |
| CR-12 | Multi-robot inference isolation/fairness | Systems PhD | E2–E3 | Which scheduler reduces tail latency without starving clients? | [#69](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/69) |
| CR-13 | Energy/cost per valid robotic task | Systems/Sustainability | E3 | Which placement uses less metered energy for comparable quality? | [#70](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/70) |
| CR-14 | Privacy-preserving dataset audit | Ethics/Data | E0–E1 | Can license, consent, disclosure and retention constraints be verified? | [#67](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/67) |
| CR-15 | Simulated embodiment/domain shift | Embodied-AI PhD | E2–E3 | How sensitive are policy outputs to calibrated camera/dynamics changes? | [#71](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/71) |
| CR-16 | Restart and HF model-cache resilience | MLOps/Platform | E1–E2 | What share of restarts succeeds offline with pinned cached models? | [#58](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/58), [#61](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61) |
| CR-17 | Robotics telemetry and evidence replay | Observability PhD | E2 | Can a whole sensor-to-action failure be reconstructed from traces? | [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60), [#52](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/52) |
| CR-18 | Responsible AI experiment showcase | Educators/Outreach | E0–E1 | Can outsiders inspect complete provenance instead of flashy unverified charts? | [#68](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/68) |

## Detailed teaching and research briefs

### CR-01 — Discover what two kinds of "node" mean
**Starting point:** Existing legacy talker/listener explanation; future cross-worker demo blocked by #14/#15/#16. **Exercise:** Draw an ROS graph and a Kubernetes pod/node map. Predict what happens when the listener pod is moved, restarted or placed under an incompatible discovery configuration. **Evidence:** subscriber message sequence, pod name/UID, actual Kubernetes worker placement, middleware config, and a negative connection test. **Success condition:** no conclusion about cross-worker communication without proven distinct worker placement and received messages. **Deliverable:** 2-page lab report plus reproducible verification transcript with secrets redacted.

### CR-02 — Break discovery and QoS intentionally
**Baseline:** Same ROS message type, rate and payload across conditions. **Independent variables:** explicit discovery vs documented alternative, reliable vs best-effort QoS when valid, node restart, constrained network. **Metrics:** discovery elapsed time, accepted messages, gaps, retransmit interpretation, transport bytes and CPU. **Validity:** do not equate an absent callback with literal lost packets without an independent sender sequence and matched time window. **Deliverable:** controlled table + mechanism explanation + one failing configuration and fix. **Ethics:** simulation/lab networking only, no untrusted packet injection on real networks.

### CR-03 — Generate repeatable multimodal episodes
**Baseline:** deterministic image pattern, synthetic robot pose/state, action target and task text. **Variable:** FPS, resolution, injected dropped frames, out-of-order event and clock drift. **Metrics:** missing frame fraction, alignment residual and validator fail/pass. **Deliverable:** seeded fixture, schema, manifest, redacted example frame. **Important:** an Image or PointCloud2 topic alone is not an action-learning dataset.

### CR-04 — Convert and audit datasets
**Baseline:** same licensed fixture -> exported LeRobotDataset v3 -> loaded by pinned API. **Variable:** timestamp rounding, units, missing actions, episode boundaries. **Metrics:** frame alignment, schema mismatch, number of rejected episodes, checksum stability. **Deliverable:** data card, conversion code, negative tests and offline readback. **Ethics:** no identifiable people or proprietary camera imagery.

### CR-05 — Model provenance under disconnection
**Baseline:** public small model/fixture already present in an immutable cache. **Conditions:** cache hit, cold download, wrong model commit, offline no-cache, corrupted cache. **Metrics:** startup wall time, cache bytes, failure counts, traceable model identity; optionally energy when metered. **Deliverable:** revision manifest, repeatable offline test, explicitly failure-aware chart.

### CR-06 — Compare policy outputs with a deterministic gate
**Baseline:** mock policy creates valid typed action under strict schema. **Adversarial cases:** impossible unit, forbidden skill, replayed observation ID, expired TTL, out-of-bounds scalar and missed model revision. **Primary metrics:** rejection sensitivity against defined corpus, valid-action acceptance, latency to rejection, false rejections. **Requirement:** action gate, not the model, is the security boundary; no physical motor/velocity publications. **Deliverable:** positive/negative unit tests and simulated state transition logs.

### CR-07 — Test a real compatible policy, without assuming autonomy
**Baseline:** verified simulated embodiment + checkpoint + trained camera layout / state names / action dimensions. **Conditions:** local synchronous vs compatible upstream remote mode, when supported. **Metrics:** typed contract acceptance, model inference time, action age, rejections; **task success only when a runnable compatible simulator/task is validated**. **Deliverable:** documented compatibility decision record, exact LeRobot and processor/model revision, pinned image; GPU is optional and clearly priced/described. **Pitfall:** a valid prediction tensor or startup handshake is not proof of successful robot manipulation.

### CR-08 — Study cloud–edge latency and action freshness
**Hypothesis to test, not assert:** For a fixed action horizon, beyond a workload-specific RTT/jitter threshold, remote inference causes more action-staleness or starvation than local inference. **Baselines:** local; same-LAN remote; separated Kubernetes service. **Impairments:** controlled delay, jitter, bandwidth and drop, independently seeded and documented. **Measures:** source-observation-to-validated-action p50/p95/p99, timeouts, chunk age, refill/merge, queued seconds, staleness rejects, task success in compatible simulation. **Confounders:** accelerator difference, model prefetch, FPS, clock source; hold constant or report. **Deliverable:** preregistration, ≥3 independent trials/condition as a starting point with power/variance justification, negative outcomes and open analysis.

### CR-09 — Agentic task planning, not arbitrary motor output
**Goal:** Text such as "inspect station A" maps to a typed, permitted simulated skill, then to a sandboxed simulator driver. **Baselines:** deterministic keyword/finite-state rules vs small local model vs optional remote model with identical allowed tools. **Metrics:** valid skill rate, false permission grants, schema rejection count, latency/cost, task outcome and escalation-to-human rate. **Adversarial input:** prompt injection in scene descriptions and untrusted logs. **Deliverable:** typed skill library, policy validator, test corpus with ground truth and approval audit. **Rule:** No raw joint command, shell or unrestricted kubectl tool for the LLM.

### CR-10 — Read-only diagnostic AI assistant
**Problem set:** ROS_DOMAIN_ID mismatch, QoS confusion, wrong namespace, aged image, degraded node and absent metrics, plus deliberately unanswerable cases. **Experiment:** retrieval/no-retrieval; cite an approved source and version for each material claim. **Metrics:** grounding accuracy, confident hallucination, abstention calibration, resolution steps and CPU tokens/latency. **Deliverable:** reviewed evaluation dataset + scripts + example uncertainty handling. **Safety:** retrieval text is untrusted and no write tools exist.

### CR-11 — Make failures first-class experiments
**Conditions:** restart, dropped packet burst, stale timestamp, model reload, cache miss, auth denial, DNS/service failure. **Measure:** detection time, no-authorized-command interval, action-validator decision, reproducible no-actuation state, restoration time, failure count. **Deliverable:** fault matrix plus evidence for each non-passing condition. **Never label the simulated gate a certified safety stop.**

### CR-12 — Compare multi-client inference serving
**Baselines:** separate service per simulated client versus controlled queueing where supported. **Variables:** 2–3 clients, burstiness, model size, CPU/GPU allocation, quotas, fairness weights. **Metrics:** per-client throughput, p99, missed deadline, starvation, cache footprint, noisy-neighbor effect and cross-tenant leakage. **Constraint:** upstream LeRobot remote inference can bind a server instance to one active client; test/architect around this fact rather than inventing a supported multi-client mode. **Deliverable:** fairness definition and failure-inclusive per-client trace.

### CR-13 — Assess energy and cost as measured quantities
**Baseline:** identical licensed workload and quality threshold for local CPU/GPU and remote service. **Requirements:** measured watts/energy from actual tooling and clear boundary; electricity/carbon intensity assumptions separately documented; no CPU utilization -> watts fiction. **Metrics:** joules/valid inference, joules/successful task (when task exists), recovery overhead and dated euro/dollar compute rate assumptions. **Deliverable:** reproducible cost workbook/CSV, uncertainty discussion and an energy data quality rating.

### CR-14 — Privacy and participant/data governance
**Exercise:** Take an imaginary dataset card or simulated camera recording and decide if it is safe to publish; introduce private-household footage, children, person-identifying voice and restricted robot site maps as *hypothetical* prohibited releases. **Measures:** completeness of consent and licensing checklist, risk severity changes and review findings. **Deliverable:** model/dataset card plus risk register, not personal data. **For humans/physical robots:** institutional/legal/safety approval required before real-world collection.

### CR-15 — Reproduce controlled domain shift
**Baseline:** model checkpoint actually compatible with simulator robot body, camera and actions. **Perturbations:** visual changes, camera location, bounded sensor noise, dynamics, object geometry and calibration. **Metrics:** simulator task success with uncertainty, action distribution changes, invalid-output rate and sensor misalignment. **Deliverable:** randomized seeds, scene configs, model card, known failure cases and stated limitations of sim-to-real generalization. **No real robot trial in first phase.**

### CR-16 — Test Kubernetes recovery and artifact cache
**Conditions:** pod restart, rollout/rollback, offline model cache, unchanged exact weights vs updated checkpoint, access denial. **Metrics:** service ready time vs usable policy response time, content verification, stale model refusal, failure count, disk usage. **Deliverable:** bounded runner, digest-linked recovery evidence. **Beware:** readiness probe success is not proof of valid inference.

### CR-17 — Replay an evidence trail for debugging
**Goal:** Follow one synthetic episode from ROS source sequence and Kubernetes worker identity through request, policy result and gate decision. **Measures:** trace coverage, missing spans/events, correlation quality, clock uncertainty and replay artifact completeness. **Deliverable:** schema-backed public trace and a deterministic replay report, not a fabricated packet capture. Use existing [ros2_pulse community issue #52](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/52) only if instrumentation semantics are validated.

### CR-18 — Publish results responsibly
**Goal:** An accessible, read-only Hugging Face Space or docs page lets visitors inspect a benchmark method, provenance and a real downloadable run record. **Evidence:** exact environment, script, caveats, seed, failure count, reproducibility status. **Failure criterion:** any graph without a raw linked run is marked illustration, not measurement. **Deliverable:** educational static exploration, never a live remote robot control dashboard.

## Thesis/PhD directions with falsifiable questions

1. **Placement/adaptive inference:** At which measured network delay and accelerator load does *observation-to-valid-action* staleness cross a preregistered deadline for a chosen simulator? Compare fixed placements to an adaptive switcher only *after* proper baselines, and include switch overhead.
2. **Policy availability:** Under independent failures, does model-cache prewarming plus local mock/safe behavior reduce the rate of unvalidated attempted actions? Compare remote-only, cached/offline and interrupted paths; report the inability of fake policies to prove true task progress.
3. **Transport co-design:** In a valid ROS 2 workload, distinguish DDS discovery problems from LeRobot remote inference transport. Compare ROS DDS vs ROS-specific Zenoh bridge only within [#48](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/48); do not combine incompatible protocols as a single treatment.
4. **Reproducible robotic AI:** How much measured experimental variance comes from model/dataset revision drift, clock settings, action FPS or unpinned container dependencies? Include controlled perturbations and exact version evidence.
5. **Agentic planning verification:** Does typed skill validation reduce invalid/unauthorized simulated tasks across multiple LLMs without destroying legitimate task coverage? Predefine attack prompts and allowlist, not post-hoc cases.
6. **Multi-robot fairness:** Does per-client inference isolation reduce tail latency or starvation under bursty demand compared with a feasible shared pool, at matched overall GPU resources?
7. **Sustainable RobotOps:** Does a policy placement with the lowest per-inference joules also have lowest **per-successful-task** energy after retry/fallback costs? Only with actual watt/energy measurement.
8. **Domain-shift traceability:** Which camera/actuator calibration perturbations cause reproducible performance regressions, and can explicit semantic contracts flag mismatches before simulated rollout?

## Research method and admission gates

A valid scenario proposal should state (a) primary question/hypothesis, (b) prior art, (c) control and alternative, (d) simulator/fixture compatibility, (e) independent variable, (f) output metric + units, (g) expected failure mode, (h) resource/license/privacy gates, (i) repetitions/uncertainty plan, and (j) scripts and metadata an outsider will need. Use [experiment template](templates/EXPERIMENT-TEMPLATE.md) and [ethics guide](ETHICS-SAFETY-AND-GOVERNANCE.md).

**Do not promise novelty just because two technologies are combined.** Compare with FogROS2 and existing LeRobot policy-inference research, report what is different and what can be reproduced, and publish negative findings when honest.

