# Repository-wide audit and next-phase plan — 13 October 2026

> **Evidence scope:** Static review of the `main` tree at commit `7b9cb44f6ed05fd778d893470c72c5e7ea2b56cd`, primary code and Markdown documentation, GitHub issues/PRs, release records and recent GitHub Actions runs. This audit did **not** run a fresh VirtualBox/Vagrant/Kubernetes deployment or reproduce historical benchmarks. Do not treat static findings as an end-to-end runtime certification.

## Executive decision

**Direction:** Evolve the existing educational Vagrant/Kubernetes/ROS 2 experiment into a **reproducible distributed ROS 2 Kubernetes lab for education and research**. Prove cross-worker ROS messaging before expanding into advanced edge robotics or promoting it as modern supported infrastructure.

**Proposed brand**: ROS 2 Kubernetes Lab (`ros2-kubernetes-lab`), pending [#22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22) and a safe rename; repo name currently unchanged. Avoid production, hard real-time and safety-critical guarantees.

## Evidence snapshot

- [GitHub repository](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment): 6 stars, 3 forks, 18 open issues, two open PRs and no releases at audit time.
- `Vagrantfile` defines three Ubuntu 22.04 VMs: ~30 GB combined VM memory and 18 virtual CPUs, on a private network. The cluster scripts install Kubernetes **1.29** and `Network/network_plugin.sh` installs **Weave Net 2.8.1**. These are historical configurations, **not** a validated contemporary stack.
- `ROS2/Dockerfile` now builds an **amd64 ROS 2 Jazzy/Noble** image with direct apt pins and a base digest. `scripts/test-ros2-image.sh` verifies same-container talker/listener exchange. Publication was recorded in [this successful image workflow run](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/actions/runs/38228962264). This **does not** verify Kubernetes or cross-worker DDS.
- `ROS2/ros_dep_1.yaml`, `ros_dep_2.yaml` and `ros_dep_3.yaml` start **stress-ng** with HPA, not self-starting ROS talker/listener processes.
- `MonitoringSystem/monitoring.sh` downloads mutable Metrics Server manifests, deploys the old Dashboard, executes `chmod -R 777 /mnt/`, and retrieves an admin token. `MonitoringSystem/admin-user.yaml` binds `cluster-admin`. **Avoid recommending this legacy setup as secure by default**.
- The code includes substantial historical Prometheus JSON samples, notebooks and PDF plots, but not a locked/tested offline reconstruction workflow.

## Audited status by area

| Area | Present | Remaining gate |
| --- | --- | --- |
| Jazzy image | Pinned base digest, local smoke test and SHA-tag publication | True dependency snapshot, security/SBOM, supported Kubernetes integration |
| Legacy Vagrant topology | One control plane, two worker VMs and shell provisioning | Idempotence, bounded readiness, secure join command, maintained cluster stack |
| DDS networking | Historical Weave Net and docs for explicit discovery | Maintained CNI + distinct-worker discovery and restart evidence |
| ROS workloads | Historical stress-ng YAML; separate Jazzy stress example | Self-starting talker/listener with reliable remote receipt assertion |
| CI | Bash syntax and image smoke workflows | YAML validation, unit tests, CI integration and evidence-preserving release gate |
| Monitoring | Helm values, PVs, old Dashboard, Prometheus/Grafana | Least-privilege, no log tokens, tight file permissions, maintained UI |
| Research data | JSON samples and notebooks | Provenance dictionary, offline tests and rigorous benchmark protocols |
| Community/docs | README, CITATION, contributing/agent guides and roadmap | Remove drift, check links, docs site, published verified release |

### Concrete source-level defects requiring follow-up

1. **Provisioning**: `KubernetesClusterSetup/create_cluster.sh` runs `kubeadm init` unconditionally, uses `cp -i`, and writes a live join token command into `/home/vagrant/codes/join-command.sh`, i.e. the Vagrant host-shared repository directory. `Vagrantfile` relies on hardcoded `sleep 20` periods. Strict shell options are commented out in cluster scripts. [#43](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/43).
2. **Default permissions**: `MonitoringSystem/admin-user.yaml` grants `cluster-admin`; `MonitoringSystem/monitoring.sh` executes `chmod -R 777 /mnt/`. Highest-risk fixes belong in [#4](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/4) and [#6](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/6). Do not republish generated join commands, tokens or kubeconfig as audit evidence.
3. **Docs drift**: `docs/ROADMAP-2026.md` and `docs/ROS2-KUBERNETES-DDS-GUIDE.md` still claim the current `ROS2/Dockerfile` builds Foxy. Agent guides recommend now-closed [#28](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/28). The legacy `ROS2/README.md` references nonexistent `ros_dep.yaml`. Open [#44](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/44) alongside existing [#24](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/24). A missing monitoring image is already addressed in [PR #36](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/pull/36)—avoid parallel conflicting fixes.
4. **Research correctness**: `DataAnalysis/RH.py` can poll forever for a replacement pod; its pod/event selection and timestamp handling do not rigorously establish application recovery. `DataAnalysis/rehealing.py` asks for Killing/Started events on the same pod name even though replacement pods have distinct identities. Repair and test in [#45](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/45).
5. **No offline packaging**: no pinned Python environment/testable demonstration recreates a plot from committed samples. `DataAnalysis/README.md` even uses a placeholder with angle brackets as a literal Prometheus URL. [#46](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/46) complements the smaller dataset documentation [#30](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/30).
6. **Artifact security**: image publication has a digest and a successful CI test, but no evidence of recorded SBOM/vulnerability triage policy. [#47](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/47).

## Dependency-ordered development phases

### Phase 0 — First correct, secure and repeatable demonstration

1. Resolve high-risk defaults in #4/#6 and Vagrant token/provisioning reliability in #43.
2. Use the Jazzy baseline #7; implement a lightweight supported kind/k3d topology #16, and a maintained CNI + discovery #15.
3. Implement separate talker/listener deployments and test actual cross-worker message exchange #14. Require bounded timeouts, node-placement proof, recovery diagnostics and nonzero failure status.
4. Apply manifest schema validation #29 and expand CI from static checks to the lightweight integration profile. Make **passing actual integration** a release gate.

**Exit gate**: A documented clean machine can execute setup, demo, verify and cleanup; talker/listener run on different workers and pass real message assertions. Unsafe credentials do not leak into shared host directories or logs. Preserve the historical profile for reference; do not silently delete it.

### Phase 1 — Reproducibility, explanation and first credible release

5. Align all current-version claims, internal links and beginner instructions #44, #24, #17, #19. Complete separately tracked PR #36 and review open community PR #41; do not blindly merge them.
6. Repair research timing semantics #45, document historical samples #30, add offline replayable analysis #46, and implement full protocol-based benchmarking #18.
7. Add image SBOM and vulnerability triage #47, finish release checklist and community files #20. Publish a release only after Phase 0 gates are evidenced.

**Exit gate**: A new contributor follows one reproducible supported tutorial; data analysis is rerunnable without a cluster; released artifacts and supported-version claims point to exact evidence.

### Phase 2 — Research differentiator and industry/academia relevance

8. Add a hardware-free ROS 2 sensor-pipeline example #49 (actual messages across workers).
9. Design controlled DDS versus ROS 2 Zenoh bridging experiments #48, reporting raw data, topology, network conditions, sample sizes, repeats and limitations.
10. Expand later into edge/cloud placement, network partitions, multi-robot coordination, telemetry, failure recovery, and energy/performance studies only after baseline tests exist and research questions are bounded. Treat hard real-time and physical robot safety as non-goals.
11. Publish honest educational walkthroughs and research protocols through #19/#21; evaluate safe repository rename #22 after the reference path stabilizes.

## Proposed research questions (not findings)

- Under what conditions do direct DDS discovery and a ROS 2-specific Zenoh bridge differ in reachability, reliability and operational overhead? See [#48](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/48).
- How do pod placement, memory/CPU limits, controlled packet loss, QoS and forced restarts affect delivery ratio, recovery and message latency? See [#18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18).
- What are the resource/energy costs of idle versus stressed versus sensor-pipeline workloads on an identical host with fixed repeat protocols? Do not claim results until measured.
- How can users reuse deployment templates, test fixtures and metric tooling without reimplementing infrastructure? Prioritize small stable interfaces and examples over additional one-off setup scripts.

## New issue register (created from the audit)

| Priority | Issue | Scope |
| --- | --- | --- |
| P0 | [#43](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/43) | Vagrant provisioning, credential-safe node join and repeatability |
| P1 | [#44](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/44) | Documentation drift/checked internal links |
| P1 | [#45](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/45) | Correct recovery metrics and tested failure behavior |
| P1 | [#46](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/46) | Pinned, offline, reproducible analysis |
| P1 | [#47](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/47) | SBOM, vulnerability scans and artifact provenance |
| P2 | [#48](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/48) | Controlled DDS/Zenoh scientific comparison |
| P2 | [#49](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/49) | Realistic synthetic ROS sensor-pipeline tutorial |

## Important work already in the backlog

- Supported ROS image #7; multi-worker demo #14; networking #15; low-resource lab #16; CI/security #6; maintained dashboard #4.
- README and docs site #17/#19; benchmarks #18; release/community #20; outreach #21; proposed rename #22; tutorial #24; monitoring images #25; manifest lint #29; historical sample dictionary #30; metadata SEO #32.

Avoid duplicate issues and validate every PR on its actual changed code; **do not merge just because Bash syntax passes**. Existing open PRs at audit time: [#36](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/pull/36) (monitoring screenshot repairs; reported not mergeable at snapshot) and [#41](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/pull/41) (community guidance; mergeable but requires human review and appropriate checks).

## Measurements to use for next reviews

Report separately: stars/forks (weak proxies), issues closed with test evidence, unique successful clean-run installations, time-to-first-ROS-message, failed startup percentage, external contributors, first-response-to-issue, benchmark independent reproductions, number of runnable tutorials, documentation link failures, number/severity of known supply-chain findings, and supported-profile release history. Record provenance and collection date; avoid unverifiable popularity/SEO or performance claims.

## Source references

- [GitHub repository](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment)
- [Official ROS supported distributions](https://docs.ros.org/en/rolling/Releases.html)
- [Kubernetes releases and version support](https://kubernetes.io/releases/)
- [ROS 2 DDS discovery](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html)
- [Kubernetes networking model](https://kubernetes.io/docs/concepts/services-networking/)
- [kind quickstart](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [Headlamp](https://headlamp.dev/)
- [ROS 2-specific Zenoh bridge](https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds)
- [RobotKube (research context)](https://github.com/ika-rwth-aachen/robotkube)
- [ROS Kubernetes examples (ecosystem context)](https://github.com/fujitatomoya/ros_k8s)

**Accuracy note:** This report intentionally distinguishes audited source files, CI observations, planned changes, and unverified experiments. It is not a substitute for testing the environment.
