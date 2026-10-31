# ROS 2 Kubernetes Lab — industry, academia, and adoption strategy

> **Proposal — 13 October 2026.** This document is a forward-looking design, not evidence of implemented features. The current Vagrant/Kubernetes workflow is a historical Foxy/Kubernetes 1.29/Weave Net lab. The repository has a separately smoke-tested Jazzy/Noble container; **cross-worker DDS delivery, a maintained modern Kubernetes profile, and production-grade operation are not yet verified**. See [README](../README.md) and the existing [modernization roadmap](ROADMAP-2026.md).

## Decision

**Build an accessible, reproducible experimental platform for ROS 2 communication, placement, resilience, and observability across local clusters and edge/cloud environments.**

**Value to universities:** students can reproduce controlled experiments on commodity hardware, see raw data and analysis code, and extend an experiment without rebuilding infrastructure. **Value to industry:** engineers can evaluate robotics middleware, deployment policies, failures, observability, and resource/cost tradeoffs *before* production rollout. Start with a verified local lab; any industrial deployment claims require separate evidence.

**Non-goals in the near term:** a full robot fleet-management product; replacement for Nav2, Open-RMF, ROS 2, Kubernetes, or Gazebo; hard real-time or safety certification; autonomous robot control; commercial SLA claims; unverified star-growth promises.

## Baseline and release blockers

Existing software includes Vagrant VM provisioning, historical stress/HPA examples, monitoring configs, sample analysis data, Jazzy image and same-container message test, and newcomer/agent contribution guides. These are valuable assets, but current code **does not** provide a validated modern multi-worker ROS 2 demo. The old `Vagrantfile` requests approximately 30 GB VM memory and 18 vCPUs. Public About text and `CITATION.cff` describe the historical Foxy setup and require careful, truthful updates when functionality changes.

**Do these first, not in parallel with large feature expansion:**
1. [#7](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/7) supported ROS image lifecycle; [#15](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/15) maintained CNI and explicit discovery.
2. [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14) unattended talker/listener communication **between distinct workers**, with test proof; [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16) documented, measured low-resource kind/k3d entry point.
3. [#6](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/6) safety, pinning, CI; plus manifests and documentation validation.

Only publicize a one-command modern Kubernetes quickstart or publish a verified release when those tests pass. Preserve legacy material separately.

## Positioning within the ecosystem

These are *complementary projects to study and integrate*, not products to clone wholesale:

| Project / source | Overlap or lesson | Our differentiated contribution |
|---|---|---|
| [RobotKube (RWTH)](https://github.com/ika-rwth-aachen/robotkube) | Kubernetes orchestration for cooperative robotics | Reproducible, instructional baselines and transport/placement measurements, rather than copying the orchestrator |
| [FogROS2](https://github.com/BerkeleyAutomation/FogROS2) | Connecting robotics computation to cloud resources | Transparent experiments comparing local/edge/remote costs and latency, with defined failure conditions |
| [Open-RMF](https://github.com/open-rmf) | Multi-fleet coordination and interoperability | Optional example workloads and interoperability demonstrations; do not recreate fleet scheduling |
| [ROS 2 middleware documentation](https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Different-Middleware-Vendors.html) and [Fast DDS Discovery Server](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html) | Middleware and discovery configuration | A versioned, reproducible discovery/connectivity test matrix and diagnostics |
| [ros2_tracing](https://github.com/ros2/ros2_tracing) | Application tracing tools | Combine ROS traces with pod/node metrics and reproducible experimental analysis |
| [Nav2](https://docs.nav2.org/) and [Gazebo](https://gazebosim.org/docs) | Realistic application/simulation stack | Package one self-contained, observable robot scenario as an extension of the tested transport baseline |
| [Kubernetes docs](https://kubernetes.io/docs/concepts/) | Workload placement, failure recovery and observability | Measured robotics-specific behavior rather than general Kubernetes tutorials |

Revisit maintainer status, compatibility and upstream licenses at implementation time; URLs are starting points, not proof that versions interoperate today.

## Capability investments: priority and evidence gates

| Priority | Module / use case | Minimum tangible deliverable | Proof required |
|---|---|---|---|
| P0 | Reliable local cluster + ROS messaging | `make demo`, `make verify`, `make clean`; two separate worker nodes | CI job and clean-host run with logs, exact version matrix and bounds |
| P0 | DDS discovery diagnostics | Baseline explicit discovery; unicast/multicast assumptions documented | Discovery, message delivery, pod restart and network-policy failure tests |
| P1 | **Flagship: simulated mobile robot telemetry** | One simulator publishes odometry/sensor data through ROS 2 to an analysis/observer pod on another worker | Deterministic scenario checks observed topic/message rates, node placement, cleanup and recorded host requirements |
| P1 | Research benchmark harness | Fixed scenarios, CSV/JSON schema, analysis scripts, plotted results | >=3 repeated runs per configuration, raw data, version/hardware/QoS provenance; no invented performance claims |
| P1 | Observability | ROS trace + cluster resource and event dashboards | Correlation of robot-topic measurements to Kubernetes restarts/scheduling events; reproducible instructions |
| P1 | Teaching kit | 4 graded self-contained labs, instructor notes and solutions in separate paths | New student reproduces each lab in stated resource envelope |
| P2 | Edge / intermittent-connectivity resilience | One edge/cloud placement + link-loss experiment; robot-local fail-safe behavior *in simulation only* | Quantified partition/recovery times and data-loss behavior; no unsafe hardware actuation |
| P2 | Middleware alternative study | Compare selected DDS mode against rmw_zenoh or another supported RMW only if version-compatible | Same payloads/QoS/schedule, source/version declarations, fair comparisons |
| P2 | Security and supply chain | SBOM, signed images where supported, scoped RBAC/network policies | CI evidence, least-privilege tests and documented threat model |
| P3 | GPU/AI workload placement | Optional perception/inference sample with GPU and CPU fallback | Hardware/software compatibility matrix and measured latency/energy-cost limitations |
| P3 | Hardware-in-the-loop | Optional supported robot/edge device profile | Physical safety review and opt-in hardware validation; never a default |
| P3 | Multi-cluster / multi-robot federation | Separate, opt-in extension | Demand from actual adopters and repeatable integration tests |

**Crucial scope control:** do not start fleet-management UI, AI-agent autonomy, specialized hardware support, or broad multi-cloud integrations before the P0–P1 use case passes with evidence.

## Three falsifiable research questions

**RQ1 — Transport/discovery:** How do supported discovery configurations differ in cross-worker discovery success, recovery time, message loss, latency distribution, and throughput? Fix ROS distro, RMW, payload, QoS, host topology, CNI, network conditions and software versions. Record p50/p95/p99, missing messages, failures, CPU/memory, sample count and run-to-run variability. Compare only configurations tested to work with those versions.

**RQ2 — Placement:** For a simulated mobile robot's sensor/telemetry pipeline, what changes when a processing node runs on the same worker, a separate worker, or a resource-limited remote/edge node? Measure application-level end-to-end latency, message completeness, process CPU/memory and deployment/recovery time. Include accurate time synchronization or explicitly distinguish unsynchronized timing from one-way latency.

**RQ3 — Recovery:** During planned pod termination and simulated link degradation/partition, how long until publication/subscription is restored, how many samples are missed, and how does observed behavior depend on discovery mode? State what Kubernetes restarts can and cannot guarantee; never interpret application-level recovery as a hard real-time guarantee.

A research-quality dataset must include experiment ID, commit SHA, container digests, hardware specification, OS/Kubernetes/CNI, ROS/RMW/QoS, networking configuration, timestamps/time-sync method, procedure, repetitions, errors, raw measurements, scripts and explicit limitations. Keep historical datasets labeled historical. For university use, publish citable, license-compatible releases with CITATION.cff and optional archival DOI when justified.

## 90-day sequencing (planning targets, gated by proof)

**Days 1–30 — trust and access:** resolve P0 message delivery, discovery, cluster profile, CI security and accurate quickstart. Deliver one clean-host reproducibility report. If cross-node tests fail, keep scope on P0 rather than advancing the roadmap.

**Days 31–60 — flagship + measurement:** add small simulator-to-observer demo (after selecting a compatible simulator), create `experiments/` schemas/scripts for RQ1 and RQ3, and regenerate one defensible figure from new runs. Publish full limitations and benchmark methodology.

**Days 61–90 — teaching and credible adoption:** release four student exercises (middleware discovery, scheduler placement, observability, resilience) and public docs. Invite two external university educators and two industrial robotics engineers to reproduce the flagship without privileged support; capture issue-backed feedback. Once release tests pass, record short demonstration video and submit technical tutorial proposals. Scheduling targets are not guarantees.

## Education and industry adoption pathways

**University:** teaching slides/exercises, reproducible papers/data, sample assessments, semester projects and an explicit citation. Avoid requiring 30 GB host RAM for introductory labs. Gather reproducibility reports and attributable reuse evidence with contributor consent.

**Industry:** documentation for images and versions, helm/Kustomize deployment options once needed, RBAC/network policy examples, failure-mode reports, changelog, upgrade tests, and measurements meaningful to real workloads. Start with safe preproduction assessment, not production endorsement.

**Contributors:** publish role-specific issues (documentation/data analysis, ROS/QoS, Kubernetes/CI, simulation, security), bounded acceptance criteria, recorded tests, and beginner-friendly low-resource paths. Existing [AI-assisted contribution guidance](AI_ASSISTED_CONTRIBUTING.md) is optional; agents must not invent test evidence or bypass reviews.

## Measurement: value before popularity

Track **outcomes**, segmented by audience: successful installs / attempted installs; independently reproduced experiments; classes using a versioned lab; external downstream repositories; users returning with follow-up runs; CI test pass reliability; time to first ROS message; reproducible research artifacts and citations. Separately monitor unique GitHub visitors, clones, stars, forks, external PRs, issue resolution time and docs search discovery. Publicly report collection method, observation window, denominators and limitations. Do not reward fake stars, benchmark numbers, or speculative adoption claims.

## Proposed next edits and tracking

- Complete existing issues [#7](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/7), [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14), [#15](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/15), [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16), [#6](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/6) first; avoid duplicate tickets.
- Extend [benchmark #18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18) with study protocols after demo verification; coordinate docs [#19](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/19), release [#20](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/20), outreach [#21](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/21), and naming [#22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22).
- Defer branding claims of **Cloud-Native Robotics Lab** until functionality is real. Maintain the searchable proposed repository name **ROS 2 Kubernetes Lab**; broader brand is a *vision*, not a currently validated feature.
- Public documentation should include only broadly useful engineering plans and references, never private ideation, unpublished commercial discussions, credentials, personal data or partner-sensitive materials.

**Strategy-tracking issue:** [#42](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/42).
