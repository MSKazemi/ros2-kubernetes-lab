# ROS 2 Kubernetes Lab: modernization, adoption and growth roadmap

> Status: **Proposal** (11 October 2026). This roadmap does not indicate that new ROS distributions, Kubernetes configurations, or network modes have been validated. Current repository name is unchanged.
>
> Proposed name: **ROS 2 Kubernetes Lab** · proposed slug: `ros2-kubernetes-lab`.
> Tagline: **Deploy, scale, monitor, and benchmark distributed ROS 2 applications on Kubernetes.**
> Tracking: [GitHub issues](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues).

## 1. North star and intended audience

Build a reproducible **educational and research** lab for ROS 2 applications on Kubernetes with a verified local first run, meaningful cross-node DDS behavior, optional monitoring and reproducible benchmarking. Primary audience: robotics engineers, ROS 2 educators/students, Kubernetes practitioners, and researchers investigating edge/cloud robotics. **Not intended or represented as certified production robot orchestration or hard real-time control.**

Growth target: improve usage and visibility; 600 stars would equal 100x the six-star baseline checked 10 October 2026, but it is an **aspiration, not a prediction**. Successful first runs, outside contributors, documented reuse and reproducible results are better leading indicators than stars.

## 2. Evidence-based starting point

| Observation from existing files | Consequence |
|---|---|
| `ROS2/ros_dep_1.yaml` launches `stress-ng`, not an automatic talker/listener | README's main demonstration is not a one-command success path |
| `ROS2/README.md` uses missing `ros_dep.yaml`, and examples omit the `ros` namespace | Fresh users encounter avoidable command errors |
| At the 2026-10-11 audit, `ROS2/Dockerfile` built on ROS 2 Foxy. It now targets Jazzy / Ubuntu 24.04 (the Foxy recipe is preserved in `ROS2/legacy/foxy/Dockerfile`), but the `ROS2/ros_dep_*.yaml` manifests still use a Foxy image, cluster scripts install Kubernetes 1.29 and networking uses Weave Net 2.8.1 | Vagrant/Kubernetes stack remains `legacy`; the Jazzy image is `container tested` only (see the [support states](./ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)) |
| Three-node `Vagrantfile`: 18 vCPUs, ~30 GB VM memory | Blocks access for many laptops |
| CI builds and tests the Jazzy image ([`ros2-image-ci.yml`](../.github/workflows/ros2-image-ci.yml)) with a local talker/listener check inside one container, but does not test cluster creation or cross-worker DDS | A green image build is `container tested` at most; it does not establish `cross-worker verified` ROS messaging |
| `MonitoringSystem/monitoring.sh` includes broad `chmod 777` permissions; `admin-user.yaml` binds `cluster-admin` | Unnecessarily broad permissions for a default educational installation |
| Root README has no central proof-of-function GIF or validated modern install profile | Limited visitor-to-user conversion |
| Repository has no GitHub release and existing code contains substantial analysis data | Reproducible release and research assets remain untapped |

This audit inspected repository contents and workflow history; **it did not execute a fresh multi-VM installation**. The table rows above were reconciled with the repository at commit `7b9cb44` on 2026-10-27 (static inspection; no Vagrant cluster was executed). Preserve historical results, but do not present old results as modern-profile benchmarks.

## 3. Workstreams and ownership

Issue reference table; all numbers below are in the [current repository](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment).

| Priority | Workstream / required outcome | Issue | Completion gate |
|---|---|---|---|
| P0 | Automatic, independently tested cross-worker ROS talker/listener | [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14) | Repeatable command shows DDS messages across nodes without `kubectl exec` |
| P0 | ROS 2 Jazzy baseline; evaluate Lyrical on its **own** compatible platform | [#7](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/7) | Pinned image, verified distro and sample nodes; legacy Foxy marked EOL |
| P0 | Maintained CNI + explicit ROS DDS discovery and cross-node tests | [#15](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/15) | Cross-worker discovery, restart and debugging behavior verified |
| P0 | Lightweight kind/k3d profile with `make demo`, `make verify`, `make clean` | [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16) | Fresh test host meets documented resource/time requirements |
| P0 | Test CI, pinned dependencies, least-privilege security defaults | [#6](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/6) | PR checks + ROS integration proof, safe storage/RBAC/secrets |
| P0 | Replace archived Dashboard with maintained Headlamp and safer access | [#4](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/4) | UI smoke test, read-only default access, no exposed standing tokens |
| P1 | Visual README and accurate quickstart | [#17](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/17) | Every featured command and diagram matches checked-in/tested code |
| P1 | Reproducible DDS/HPA/monitoring benchmarks | [#18](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/18) | Runnable protocol, raw data, regenerated plots and limitations |
| P1 | Searchable versioned tutorials and troubleshooting | [#19](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/19) | Built/published docs site, verified links, honest support matrix |
| P1 | First verified release and contributor-friendly workflow | [#20](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/20) | Versioned release with integration proof and contribution guides |
| P1 | Decide brand, perform safe rename **only after confirmation** | [#22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22) | Old/new links, citations, badges, docs, packages audited |
| P2 | Educational demo, articles, community and conference outreach | [#21](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/21) | Useful technical content and documented engagement metrics |

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
| **ros2-kubernetes-lab** | Explicit ROS 2 + Kubernetes keywords; future-proof across Vagrant/kind/k3d | Longer than the abbreviated alternative | **Recommended** |
| ros2-k8s-lab | Short, developer friendly | Some students search “Kubernetes” rather than “k8s” | Runner-up |
| cloud-native-ros2 | Broad cloud robotics positioning | Less precise project function | Possible umbrella descriptor |
| ros2-kube-lab | Compact | Weaker exact technical match | Alternative |
| robotics-k8s-lab | General robotics focus | ROS 2 search intent diluted | Not preferred |

Preliminary exact-name GitHub repository searches found no exact existing match for `ros2-kubernetes-lab` at audit time. **Not a domain, trademark, social handle, or future-availability guarantee.** No repository rename performed.

**Proposed repository description**

> Reproducible ROS 2 on Kubernetes lab: multi-node DDS communication, local Vagrant/kind deployment, monitoring, autoscaling experiments, and benchmarks.

This text describes the *target* scope; avoid promising kind/multi-node runtime compatibility in live metadata until tests pass.

Rename checklist in [#22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22). Maintain repo history, issues, stars and citation continuity. Keep `CITATION.cff` and Apache-2.0 unless separate ownership/licensing review requires changes.

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
