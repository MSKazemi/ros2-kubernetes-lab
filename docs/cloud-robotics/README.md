# Cloud Robotics + AI/LLM Lab

> **Research and education proposal | 27 October 2026 | NOT a verified implementation.** This program extends the existing [ROS 2 on Kubernetes lab](../../README.md); it does not replace it or claim a working AI robot fleet. The original Vagrant/Foxy/Kubernetes 1.29/Weave Net configuration is historical. A separate Jazzy/Noble container has a **same-container** talker/listener smoke test, but cross-worker DDS communication and a modern low-resource cluster are **not yet verified**.

**Vision:** A reproducible, safe-by-default open laboratory for learning how to **deploy, test, observe, benchmark and responsibly operate robotics AI** across ROS 2, edge systems and Kubernetes, with Hugging Face LeRobot and optional LLM/VLA models.

**Proposed program name:** *Cloud Robotics + AI Lab* (also "RobotOps Lab" as the experimental operations track). The repository renaming discussion [#22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22) is separate: **do not rename or announce a new production brand without review**.

**One-sentence promise:** *From a simulated robot observation to a validated AI response, with measurable latency, data/model provenance, safe fallbacks and independently reproducible results.*

## What exists, versus what is proposed

| Dimension | Existing on main | Intended research extension | Release gate |
| --- | --- | --- | --- |
| Local cluster | Historical three-VM Vagrant lab | Supported kind/k3d profile with bounded resources | [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16), [#43](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/43) |
| ROS 2 | Jazzy/Noble container-only message test; historical stress manifests | Cross-worker self-starting talker/listener + typed simulated sensor/actions | [#7](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/7), [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14), [#15](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/15) |
| Observability | Prometheus/Grafana configs; old collected metrics | Action-aware traces and reproducible fault/placement experiments | [#18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18), [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60) |
| Hugging Face | No verified integration | LeRobotDataset v3 conversion, exact Hub revisions, optional remote policy server | [#56](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/56), [#58](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/58), [#61](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61) |
| AI/LLM | No verified ROS runtime planner | Read-only diagnostic RAG; bounded, typed simulated skills | [#64](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64), [#65](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/65) |
| Responsible robotics | Safety and security notes | Risk register, model/data governance, typed fail-closed simulated action gate | [#59](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59), [#67](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/67) |

**The first outcome is deliberately modest:** CPU-only mock policy + simulator-only action validation + a transparent run record. No GPU, expensive cloud service or physical robot is necessary for that *proposed* MVP. Do not describe future commands as executable until code and CI prove them.

## Choose your track

| Audience | Start here | What you will learn or produce |
| --- | --- | --- |
| Beginner / bachelor student | [Educational labs](EDUCATION-AND-CONTRIBUTING.md), scenarios CR-01/02 | ROS vs K8s nodes, messages, QoS, reproducible CLI labs |
| MSc / robotics engineer | [Scenario catalog](SCENARIO-CATALOG.md), CR-03/04/05 | Simulation recordings, dataset alignment, typed policy and monitoring |
| PhD / systems researcher | [Benchmark protocol](BENCHMARKS-AND-REPRODUCIBILITY.md), CR-06/08/12 | Publishable placement, reliability, scheduling and energy experiments |
| AI/VLA researcher | [Hugging Face integration](HUGGINGFACE-INTEGRATION.md), CR-04/07 | Compatible LeRobot observation/action semantics, model provenance |
| LLM/agent researcher | [Agentic AI design](AGENTIC-LLM-RESEARCH.md), CR-09/10 | Typed skill planning, RAG, prompt-injection rejection |
| Industrial evaluator | [Architecture](VISION-AND-ARCHITECTURE.md), [ethics](ETHICS-SAFETY-AND-GOVERNANCE.md) | Resource and failure analysis with explicit **non-production** limits |
| Instructor / mentor | [Teaching kit](EDUCATION-AND-CONTRIBUTING.md) | Six reusable graded modules, rubric and hardware tiers |

## Documentation map

1. [Vision, architecture and trust boundaries](VISION-AND-ARCHITECTURE.md)
2. [18 hands-on student, engineering and PhD scenarios](SCENARIO-CATALOG.md)
3. [Hugging Face Hub, LeRobot, SmolVLA and policy serving](HUGGINGFACE-INTEGRATION.md)
4. [LLM/agentic robotics and RAG studies](AGENTIC-LLM-RESEARCH.md)
5. [Benchmarks, metrics, reproducibility and protocol](BENCHMARKS-AND-REPRODUCIBILITY.md)
6. [Ethics, security, safety, privacy and legal-review triggers](ETHICS-SAFETY-AND-GOVERNANCE.md)
7. [Course modules and contributor pathways](EDUCATION-AND-CONTRIBUTING.md)
8. [12-month phased roadmap with linked issues](ROADMAP-2026-2027.md)
9. [Experiment record / preregistration template](templates/EXPERIMENT-TEMPLATE.md)
10. [Dataset, model and risk templates](templates/DATASET-CARD-TEMPLATE.md), [model](templates/MODEL-CARD-TEMPLATE.md), [risk register](templates/RISK-REGISTER-TEMPLATE.md)
11. [Primary sources and related work](REFERENCES.md)

## Flagship demonstration: ROS 2 observations to AI policy to simulated action

The planned hardware-free demo has four separate proofs, **not one misleading success checkbox**:

1. **Data proof:** A licensed deterministic synthetic camera/state/action episode has explicit units, calibration, task identity, episode boundaries and valid LeRobot dataset conversion.
2. **Contract proof:** A deterministic mock policy receives a *versioned* observation, responds with schema-valid action candidate, and is blocked if stale/malformed/unapproved.
3. **Deployment proof:** Only after [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14), [#15](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/15) and [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16), prove ROS messages on different Kubernetes workers; later use a pinned upstream LeRobot policy server as an **optional** profile.
4. **Research proof:** Preserve full run metadata, raw failures, clock assumptions and offline-regenerable plots. API success alone is not evidence of task success or physical safety.

A simulator is still a model of reality, not a physical-safety test. LLMs **never** directly drive actuators in this proposal.

## Open workstreams and reading

- [Umbrella Hugging Face/RobotOps design #53](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/53); [Physical AI/LLM proposal #54](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/54)
- [Existing infrastructure roadmap](../ROADMAP-2026.md), [research strategy issue #42](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/42), [proposed PR #50](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/pull/50)
- New scoped tasks: [#55–#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55) and [#64–#71](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64). See [roadmap for exact mapping](ROADMAP-2026-2027.md).

## Explicit non-goals

No production SLAs, fleet management suite, replacement for ROS 2/LeRobot/FogROS2/Open-RMF/Nav2, hard-real-time motion guarantee, physical autonomy, self-issued safety certification, autonomous public-cloud robot actuation, secret-bearing public datasets or claims that SmolVLA is drop-in compatible with arbitrary ROS topics.

**Documentation maturity:** The pages in this folder describe *proposals, experiment specifications and templates*. This work has not installed a fresh supported cluster, evaluated an AI model, or measured a real robot. Keep this warning when sharing screenshots, blog posts, papers or conference submissions.

