# ROS 2 Kubernetes Lab: modernization, adoption and growth roadmap

> **Proposed expansion, not implementation (27 October 2026):** A separate [Cloud Robotics + AI/LLM Lab research program](cloud-robotics/README.md) introduces Hugging Face LeRobot, typed simulated policy integration, LLM/RAG experiments, ethics and 18 teaching/research scenarios. Its [12-month research roadmap](cloud-robotics/ROADMAP-2026-2027.md) explicitly depends on the P0 ROS/Kubernetes verification and safe-default work in this document. No AI robot execution or new cluster benchmark is claimed.
>
> **Historical 90-day modernization proposal** (11 October 2026). This document remains useful as a dated baseline, but the **current cross-project coordination plan** is [the 2026–2027 integrated roadmap](PROGRAM-ROADMAP-2026-2027.md) and [documentation index](README.md). The newer document does not mean that a model integration, current Kubernetes profile or cross-worker DDS workload is verified. For what is *actually pinned and run today*, see the [version matrix](VERSION-MATRIX.md) and the [experiment status registry](EXPERIMENT-STATUS.md); the [status snapshot](#2a-status-snapshot-2026-11-06) below maps this roadmap's items to recorded evidence.
>
> Display name: **ROS 2 Kubernetes Lab** · repository slug: `robo-resilience-lab` (renamed from `robo-resilience-lab` in commit `a88ba5c`; that name had replaced `Vagrant-Kubernetes-ROS2-Deployment` in commit `43d4690`). The audit below was written under the older names. Any broader research umbrella name remains a separate, unapproved working-name RFC in issue #22.
> Original tagline: **Deploy, scale, monitor, and benchmark distributed ROS 2 applications on Kubernetes.**
> Tracking: [GitHub issues](https://github.com/MSKazemi/robo-resilience-lab/issues).

## 1. North star and intended audience

Build a reproducible **educational and research** lab for ROS 2 applications on Kubernetes with a verified local first run, meaningful cross-node DDS behavior, optional monitoring and reproducible benchmarking. Primary audience: robotics engineers, ROS 2 educators/students, Kubernetes practitioners, and researchers investigating edge/cloud robotics. **Not intended or represented as certified production robot orchestration or hard real-time control.**

Growth target: improve usage and visibility; 600 stars would equal 100x the six-star baseline checked 10 October 2026, but it is an **aspiration, not a prediction**. Successful first runs, outside contributors, documented reuse and reproducible results are better leading indicators than stars.

## 2. Evidence-based starting point

| Observation from existing files | Consequence |
|---|---|
| `ROS2/ros_dep_1.yaml` launches `stress-ng`, not an automatic talker/listener | README's main demonstration is not a one-command success path |
| At the 2026-10-11 audit `ROS2/README.md` used a missing `ros_dep.yaml` and omitted the `ros` namespace. Corrected in issue #24 (static review only; the manual talker/listener steps were not re-run) | Fresh users encountered avoidable command errors; the manual Foxy steps remain unverified |
| At the 2026-10-11 audit, `ROS2/Dockerfile` built on ROS 2 Foxy. It now targets Jazzy / Ubuntu 24.04 (the Foxy recipe is preserved in `ROS2/legacy/foxy/Dockerfile`), but the `ROS2/ros_dep_*.yaml` manifests still use a Foxy image, cluster scripts install Kubernetes 1.29 and networking uses Weave Net 2.8.1 | Vagrant/Kubernetes stack remains `legacy`; the Jazzy image is `container tested` only (see the [support states](./ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)) |
| Three-node `Vagrantfile`: 18 vCPUs, ~30 GB VM memory | Blocks access for many laptops |
| CI builds and tests the Jazzy image ([`ros2-image-ci.yml`](../.github/workflows/ros2-image-ci.yml)) with a local talker/listener check inside one container, but does not test cluster creation or cross-worker DDS | A green image build is `container tested` at most; it does not establish `cross-worker verified` ROS messaging |
| At the 2026-10-11 audit `MonitoringSystem/monitoring.sh` used broad `chmod 777` permissions and `admin-user.yaml` bound `cluster-admin`. Today `monitoring.sh:61` uses `chmod 0775`, and `admin-user.yaml:34` **still** binds `cluster-admin`, with `admin-user-readonly.yaml` (built-in `view` role) added as an alternative | Narrower than at audit, but the default dashboard account is still broad; the Dashboard itself is still the archived `v2.7.0` manifest (`monitoring.sh:16`) |
| Root README has no central proof-of-function GIF or validated modern install profile | Limited visitor-to-user conversion |
| Repository has no GitHub release and existing code contains substantial analysis data | Reproducible release and research assets remain untapped |

This audit inspected repository contents and workflow history; **it did not execute a fresh multi-VM installation**. The table rows above were reconciled with the repository at commit `7b9cb44` on 2026-10-27 (static inspection; no Vagrant cluster was executed). Preserve historical results, but do not present old results as modern-profile benchmarks.

## 2a. Status snapshot (2026-11-06)

This table maps the P0/P1 items in section 3 to what the repository files *record*. It was assembled by reading files, not by running clusters; "recorded" means a repository document states a result, not that it was re-run for this snapshot. Pins and file references are in the [version matrix](VERSION-MATRIX.md); per-experiment status is in the [experiment status registry](EXPERIMENT-STATUS.md).

| Item | Recorded status | What is **not** established |
|---|---|---|
| #14 cross-worker talker/listener | Kind profile only: [`docs/KIND-DEMO.md`](KIND-DEMO.md) records `make demo` / `make verify` / `make verify-negative` exiting 0 on one host (2026-10-27, commit `862b026`) | The Vagrant/Weave Net cluster; other CNIs; a real multi-machine cluster. Its CI workflow had not been executed when that page was written |
| #7 ROS 2 Jazzy baseline | Image in `ROS2/Dockerfile` pins Jazzy / Ubuntu 24.04 by base-image digest; smoke test runs inside one container | Lyrical (not evaluated); arm64; hermetic rebuilds (transitive apt packages unlocked) |
| #15 maintained CNI and discovery | Default multicast discovery failed on kindnetd (both cross-worker and same-worker); a Fast DDS Discovery Server worked. The [DDS guide](ROS2-KUBERNETES-DDS-GUIDE.md) also lists single-host Docker tests of Fast DDS, Cyclone DDS and static peers | A maintained CNI on a real cluster; restart behaviour in Kubernetes; any DDS result beyond the kind profile |
| #16 lightweight kind profile | `make demo` / `make verify` / `make clean` exist; one warm run took 82 s on a 12-CPU, 31 GB host | Whether it fits an 8 to 12 GB machine (stated as untested in KIND-DEMO.md) |
| #6 CI and safe defaults | Static workflows (links, shell syntax, site, manifest schemas for Kubernetes 1.29, image smoke test) | A cluster-backed integration check proven green; `admin-user.yaml` still binds `cluster-admin` |
| #4 replace archived Dashboard | Not done: `monitoring.sh:16` still applies Dashboard `v2.7.0` | Headlamp migration |
| #18 reproducible benchmarks | Offline, **synthetic or simulated** harnesses are being added (see the registry). Historical Foxy-era data under `DataAnalysis/dataset/` is unchanged | Any measured Jazzy/Kubernetes benchmark |
| #19 versioned docs | [Version matrix](VERSION-MATRIX.md), registry and local link check (`scripts/check-markdown-links.py`) | Built or published versioned docs site |

## 3. Workstreams and ownership

Issue reference table; all numbers below are in the [current repository](https://github.com/MSKazemi/robo-resilience-lab).

| Priority | Workstream / required outcome | Issue | Completion gate |
|---|---|---|---|
| P0 | Automatic, independently tested cross-worker ROS talker/listener | [#14](https://github.com/MSKazemi/robo-resilience-lab/issues/14) | Repeatable command shows DDS messages across nodes without `kubectl exec` |
| P0 | ROS 2 Jazzy baseline; evaluate Lyrical on its **own** compatible platform | [#7](https://github.com/MSKazemi/robo-resilience-lab/issues/7) | Pinned image, verified distro and sample nodes; legacy Foxy marked EOL |
| P0 | Maintained CNI + explicit ROS DDS discovery and cross-node tests | [#15](https://github.com/MSKazemi/robo-resilience-lab/issues/15) | Cross-worker discovery, restart and debugging behavior verified |
| P0 | Lightweight kind/k3d profile with `make demo`, `make verify`, `make clean` | [#16](https://github.com/MSKazemi/robo-resilience-lab/issues/16) | Fresh test host meets documented resource/time requirements |
| P0 | Test CI, pinned dependencies, least-privilege security defaults | [#6](https://github.com/MSKazemi/robo-resilience-lab/issues/6) | PR checks + ROS integration proof, safe storage/RBAC/secrets |
| P0 | Replace archived Dashboard with maintained Headlamp and safer access | [#4](https://github.com/MSKazemi/robo-resilience-lab/issues/4) | UI smoke test, read-only default access, no exposed standing tokens |
| P1 | Visual README and accurate quickstart | [#17](https://github.com/MSKazemi/robo-resilience-lab/issues/17) | Every featured command and diagram matches checked-in/tested code |
| P1 | Reproducible DDS/HPA/monitoring benchmarks | [#18](https://github.com/MSKazemi/robo-resilience-lab/issues/18) | Runnable protocol, raw data, regenerated plots and limitations |
| P1 | Searchable versioned tutorials and troubleshooting | [#19](https://github.com/MSKazemi/robo-resilience-lab/issues/19) | Built/published docs site, verified links, honest support matrix |
| P1 | First verified release and contributor-friendly workflow | [#20](https://github.com/MSKazemi/robo-resilience-lab/issues/20) | Versioned release with integration proof and contribution guides |
| P1 | Decide brand, perform safe rename **only after confirmation** | [#22](https://github.com/MSKazemi/robo-resilience-lab/issues/22) | Old/new links, citations, badges, docs, packages audited |
| P2 | Educational demo, articles, community and conference outreach | [#21](https://github.com/MSKazemi/robo-resilience-lab/issues/21) | Useful technical content and documented engagement metrics |

## 4. Execution phases and dependency order

### Days 1–14: define supported reference path (P0)

1. Audit version support against official upstream sources; choose ROS 2 Jazzy + Ubuntu 24.04 as first proposed profile, and a currently supported Kubernetes minor after checking exact support dates. ROS 2 Lyrical belongs to an independent Ubuntu 26.04 profile, **not** the Jazzy/Noble environment.
2. Update image build for the first supported ROS 2 distribution (#7). Separate ROS workloads from stress experiments (#14).
3. Prototype DDS discovery across actual separate workers using a maintained networking stack (#15); record packet/ROS output and failures.
4. Define smoke-test exit conditions and create a compatibility matrix. Do not make feature or performance claims based solely on static YAML.

### Days 15–30: make it runnable and safe (P0)

5. Complete end-to-end ROS verification (#14), including correcting namespace, manifest naming and pod readiness checks.
6. Add a lightweight kind/k3d path (#16) while retaining a full Vagrant lab.
7. Harden CI, dependency pins, storage permissions, tokens, cluster privileges (#6); migrate Dashboard to Headlamp (#4).
8. **Gate for public modern quickstart**: a clean host successfully runs the supported installation, shows messages between different workers and passes documented verification.

### Days 31–60: package and document (P1)

9. Introduce improved landing README with architecture, real demo, accurate installation links, alternatives and caveats (#17).
10. Publish reproducible benchmarks from controlled new runs, distinguishing historical sample data (#18).
11. Build/version/publish tutorials and troubleshooting docs (#19). Create contribution guidelines and a changelog (#20).
12. Cut a first tagged release **only after** validation; document legacy Foxy migration.

### Days 61–90: grow with measured usefulness

13. Publish demonstration video + two high-quality technical posts and seek ROS/Kubernetes educator reviews (#21).
14. Triage new issues and improve installation friction using actual user reports.
15. Choose the repo rename when modern branding and canonical links are ready (#22), and verify redirects.
16. Iterate quarterly with real visitor, installation, contributor and doc-discovery data.

Phases are planning targets, **not promises**. Hold milestones rather than skipping release gates when upstream dependencies or networking validation take longer.

## 5. Release gates and definition of done

A supported-profile release is allowed only when:

- [ ] Versions (ROS distro, Ubuntu, Kubernetes, runtime, CNI, DDS) are documented, supported, and pinned where practical.
- [ ] A fresh clean-room install completes on recorded host/VM specs.
- [ ] Talker/listener launch without manual intervention, run on **different Kubernetes nodes**, and pass a scripted message-delivery check.
- [ ] Test includes restart/recovery, bounded timeouts, clear logs, and truthful exit codes.
- [ ] Default configuration does **not** expose persistent cluster-admin credentials or world-writable host storage.
- [ ] README commands, release instructions, badges, links and diagrams match verified outputs.
- [ ] Benchmark figures include method, data, repeat count and limitations.
- [ ] Old unsupported ROS Foxy steps are separated and prominently identified as historical/legacy.

A lint-only or successful Docker build is **not** a substitute for end-to-end ROS DDS verification.

## 6. Naming comparison and strategy

| Proposed slug | Pros | Caution | Decision |
|---|---|---|---|
| **robo-resilience-lab** | Explicit ROS 2 + Kubernetes keywords; future-proof across Vagrant/kind/k3d | Longer than the abbreviated alternative | **Recommended** |
| ros2-k8s-lab | Short, developer friendly | Some students search “Kubernetes” rather than “k8s” | Runner-up |
| cloud-native-ros2 | Broad cloud robotics positioning | Less precise project function | Possible umbrella descriptor |
| ros2-kube-lab | Compact | Weaker exact technical match | Alternative |
| robotics-k8s-lab | General robotics focus | ROS 2 search intent diluted | Not preferred |

Preliminary exact-name GitHub repository searches found no exact existing match for `robo-resilience-lab` at audit time. **Not a domain, trademark, social handle, or future-availability guarantee.** The rename itself was applied later, in commit `a88ba5c`; the search above predates it and says nothing about availability today.

**Proposed repository description**

> Reproducible ROS 2 on Kubernetes lab: multi-node DDS communication, local Vagrant/kind deployment, monitoring, autoscaling experiments, and benchmarks.

This text describes the *target* scope; avoid promising kind/multi-node runtime compatibility in live metadata until tests pass.

Rename checklist in [#22](https://github.com/MSKazemi/robo-resilience-lab/issues/22). Maintain repo history, issues, stars and citation continuity. Keep `CITATION.cff` and Apache-2.0 unless separate ownership/licensing review requires changes.

## 7. Measurement dashboard and goals

Baseline audited 10 October 2026: **6 stars, 2 forks, 0 releases**. GitHub stars are only an imperfect signal of active usage.

| Measure | Baseline | Review cadence | Target |
|---|---|---|---|
| Stars | 6 | Monthly | 25 / 75 / 150 / 300 / aspirational 600 |
| Successful fresh-install validations | Not measured | Per release | 1+ verified supported path before launch |
| Verified cross-node ROS messages | Not measured on current checkout | Per PR/release | Repeatable PASS on the supported profile |
| GitHub unique visitors / clones | Requires Insights access | Monthly | Record baseline, then improve |
| External contributors | Not assessed | Monthly | Record baseline and welcome first outside PR |
| Search impressions / documentation visits | No docs analytics baseline | Monthly after launch | Record and improve |
| Reproduced benchmark experiments | Historical artifacts exist; modern validated runs not assessed | Per release | 3 independently repeatable cases |

Measure feedback quality (install problems, solved issues, reproductions) alongside discovery numbers. Never artificially incentivize GitHub stars.

## 8. Initial repository/PR workflow

- Use scoped PRs: (A) ROS modernization, (B) DDS networking, (C) end-to-end demo/tests, (D) low-resource profile, (E) CI/security, (F) docs/branding, (G) benchmarks and launch.
- Require tests, updated docs and explicit risk notes for behavior-changing changes.
- Keep reviewable commits; **do not mass-merge** technical changes before cross-node validation.
- Existing related issues #4, #6 and #7 have been refreshed instead of replaced.
- This roadmap itself is a planning PR, not a modernization implementation.

## 9. Key official references

- ROS supported distribution guidance: https://docs.ros.org/en/rolling/Releases.html
- ROS Lyrical supported platforms: https://docs.ros.org/en/lyrical/Installation.html
- Kubernetes version skew and support: https://kubernetes.io/releases/
- Fast DDS Discovery Server: https://fast-dds.docs.eprosima.com/en/latest/fastdds/discovery/discovery_server.html
- Headlamp documentation: https://headlamp.dev/
- GitHub repository rename behavior: https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository
