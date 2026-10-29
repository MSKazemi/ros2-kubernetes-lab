# Research scenario catalog — Jev in cloud–edge robotics

> **All scenarios are proposed.** They do not imply existing implementations, validated Jev scores, supported real robots, verified K8s cluster networking, or safety approval. Start with synthetic/hardware-free read-only evidence.

Jev provides **atomic, typed judgment**, not arbitrary generated code, numerical optimization or a robot trajectory. The algorithm around each judgment must perform all arithmetic, eligibility filtering, access control and safe fallback in conventional code. Reference: [TypeSafe System One concepts](https://docs.typesafe.ai/introduction) and [known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

## S1 — Explain a missing ROS 2 subscriber (P1 flagship)

- **Audience:** students, ROS 2 integrators, SREs.
- **Evidence:** synthetic event labels for a listener missing talker messages, discovery status, QoS profiles, simulated namespace/domain mismatch, network symptoms and explicitly absent metrics.
- **Question:** `Choice` among `dds_discovery`, `qos_mismatch`, `network_connectivity`, `resource_pressure`, `healthy` and `unknown`. Optional `Noul` asks whether available evidence is contradictory or insufficient.
- **Permitted result:** a read-only ranked diagnosis or a human-review flag; no automatic topic changes, kubectl or retry/actuation.
- **Baseline:** deterministic event-to-label rules and a naive most-common-class control.
- **Research metric:** macro-F1, class-specific recall, abstention coverage, false confident errors, request p95 and failure rate.
- **Prerequisites:** [#74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74). Actual cross-worker DDS claims must wait for [#14–#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14).

**Lab exercise:** present three synthetic incidents, one clearly consistent with QoS mismatch, one ambiguous discovery/network case and one deliberately malicious log string. Ask contributors to predeclare how the *deterministic* policy handles each before adding Jev.

## S2 — Review proposed LLM robot skills (P2)

- **Audience:** agentic AI, safety/security and robotics students.
- **Evidence:** a simulated operator goal, an LLM's proposed **high-level** allowlisted skill name/parameters, and a deterministic policy summary — no raw velocity commands.
- **Question:** `Choice` for apparent skill intent (`inspect_scene`, `report_status`, `navigate_to_named_waypoint_sim`, `unsupported`) or `Noul` for a suspicious mismatch.
- **Permitted result:** a **second opinion** for the reviewer. Jev is never the permission oracle: independent allowlists, parameter/schema checks and human approval are mandatory.
- **Baseline:** typed validator and policy engine **without** Jev. Jev's benefit must be measured as added screening utility, not as proof of security.
- **Research metric:** additional true-positive detection, false-negative and false-positive review rates, reviewer burden, delayed/failed API handling.
- **Prerequisites:** [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55), [#59](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59), [#64](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64). Simulator only; no real hardware.

## S3 — Where should an AI policy run? (P2)

- **Audience:** cloud/edge researchers, MLOps engineers.
- **Evidence:** precomputed, numerically validated placement candidates (`local`, `same_lan`, `kubernetes_remote`) with task compatibility, resource constraints, approved data locality and measured latency/availability as **named buckets**.
- **Question:** `Choice` for which **already eligible** placement best suits the qualitative workload constraints.
- **Permitted result:** advisory ranking to a simulation/benchmark operator. Numeric latency bounds, SLA deadlines, network partition handling and model/robot compatibility remain deterministic; never move a live motion-control loop as a result of one Jev response.
- **Baseline:** hard-constraint filtered heuristic and cost-aware deterministic policy.
- **Research metric:** placement regret vs oracle under measured workload, task success, stale-action rate, latency, availability and cost.
- **Prerequisites:** [#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62), [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60) plus verified network/inference baselines.

## S4 — Multi-robot simulated dispatch (P3)

- **Audience:** fleet scheduling and operations research groups.
- **Evidence:** small synthetic fleet with deterministic robot capability, charging, task feasibility, permissions and resource reservations.
- **Question:** `Choice` among **eligible** robot IDs for semantic task fit. Keep number of options small and log order; each candidate must pass deterministic checks first.
- **Permitted result:** recommendation for a simulation scheduler. Scheduler still enforces capacity, fairness, energy reserve and exclusivity.
- **Baseline:** round robin, greedy minimum estimated completion time and capacity/fairness-aware heuristic.
- **Research metric:** completion rate, waiting time, fairness, near-miss/invalid suggestions, abstention.
- **Prerequisites:** [#69](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/69). Do not imply physical fleet readiness.

## S5 — Route cloud-robotics observability alerts (P2)

- **Audience:** operations teams, Kubernetes monitoring practitioners.
- **Evidence:** redacted synthetic Prometheus/Loki-style alerts and a fixed mapping of system components, never unrestricted operator logs.
- **Question:** `Choice` among `network`, `ros_middleware`, `scheduler_resources`, `policy_service`, `unknown` and optionally `Score` for operational review urgency on an *ordinal* rubric.
- **Permitted result:** read-only route to a simulated incident inbox, with human review of uncertain/critical events.
- **Baseline:** alert rules using source labels, ownership map and severity annotation.
- **Research metric:** routing error, alert workload, missed critical classes, review delay. Do not represent Score as physical failure probability.

## S6 — Select compatible Hugging Face VLA experiments (P3)

- **Audience:** ML systems researchers, robotics PhD students.
- **Evidence:** **prevalidated** embodiment, action-space units, camera modalities, dataset/checkpoint licenses, device compute memory and immutable model revisions.
- **Question:** `Choice` or rubric-based `Score` about qualitative fitness among compatible, approved candidate policy experiments.
- **Permitted result:** proposed next *evaluation*, never direct model deployment on a robot.
- **Baseline:** hard compatibility matrix, documented model card and task-specific benchmark.
- **Research metric:** reviewer agreement, rejected incompatibilities, measured task performance only when a compatible simulator/checkpoint exists.
- **Prerequisites:** [#57](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57), [#58](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/58) and [#61](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61).

## S7 — Predictive maintenance advisory (P3)

- **Audience:** industrial robotics reliability researchers.
- **Evidence:** **licensed synthetic** temperature/event aggregates converted by code to descriptive buckets, labeled simulated failure scenarios and documented prevalence.
- **Question:** `Choice` among maintenance symptom classes or `Noul` asking whether the report supports *human inspection*.
- **Permitted result:** an inspection suggestion, never automatic shutdown/override or a claim of safety improvement.
- **Baseline:** thresholds and trained tabular classifier where appropriately labeled data exist.
- **Research metric:** recall at fixed false-alarm budget, calibration, precision-recall and distribution shift.
- **Prerequisites:** a separately approved, realistically labeled dataset. Synthetic anomalies alone do not validate real predictive maintenance.

## S8 — Policy-server scale-up investigation (P3)

- **Audience:** K8s platform engineers and workload schedulers.
- **Evidence:** synthetic queue length and utilization histories transformed **in code** into bounded textual status buckets; quota and pod limits separately checked.
- **Question:** `Choice` among `investigate_capacity`, `investigate_error_rate`, `investigate_network`, `no_change`, `unknown`, not a request to calculate replicas.
- **Permitted result:** annotated investigation. Kubernetes HPA, resource quotas, hard budgets and operators determine actual changes.
- **Baseline:** deterministic alert/HPA signals and no-change policy.
- **Research metric:** queue-age outcomes, cost per completed synthetic request, alert precision.
- **Prerequisites:** fixed workload generator and reproducible run manifest [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60).

## Cross-scenario research ideas for a thesis

1. **Abstention under distribution shift:** how frequently does Jev produce confidently wrong answers on unseen ROS distros, unfamiliar logging styles or new model families?
2. **Rules + Jev vs Jev alone:** does prevalidating and narrowing candidate options improve out-of-domain decision quality?
3. **Network impairment:** how does decision availability/quality change when the service is remote and encounters delay, loss or disconnections?
4. **Model and prompt drift:** do reordered Choice criteria or rephrased Noul questions change class selection? How stable are calibrated probabilities across revisions?
5. **Economic utility:** is the reduction in human triage effort worth provider cost, latency, operational effort and new privacy exposure?

Design controls and honest measurement guidance: [Benchmark protocol](BENCHMARK-PROTOCOL.md). Independent security boundaries: [Safety/privacy](SAFETY-PRIVACY.md).
