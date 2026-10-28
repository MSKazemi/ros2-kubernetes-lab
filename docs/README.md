# Documentation map — ROS 2 Kubernetes Lab

> Maintained planning index proposed 28 October 2026. This is **documentation**, not evidence that new integrations or research experiments run. Follow [AGENTS.md](../AGENTS.md), the repository's issue and pull-request review process, and [research result publication rules](scenario-lab/RESULTS-PUBLICATION.md).

## Start here

**North star:** An open, reproducible **cloud–edge robotics AI research lab** combining ROS 2 workloads, Kubernetes execution and observability, **opt-in** Hugging Face models/datasets, safe simulation, and verifiable experimental results. It is an educational and research testbed, **not** a validated production robot controller.

| I want to… | Go to | Evidence state |
| --- | --- | --- |
| Understand the program, dependencies, owners and gates | [Integrated program roadmap](PROGRAM-ROADMAP-2026-2027.md) | Proposed |
| Select a reproducible research question and baseline | [Experiment portfolio](EXPERIMENT-PORTFOLIO.md) | Designs; no new results |
| Understand what is already in the repo and what is in a PR | [28 October repository audit](REPOSITORY-AUDIT-2026-10-28.md) | Observed GitHub snapshot |
| Build/use the current ROS 2 image | [Jazzy image guide](../ROS2/jazzy/README.md) | Container-level smoke check documented |
| Read the **historical** three-VM path | [Root README](../README.md), [cluster setup](../KubernetesClusterSetup/README.md) | Legacy Foxy / Kubernetes 1.29 / Weave Net; NOT current E2E verification |
| Learn DDS networking and current limitations | [ROS 2 / Kubernetes / DDS guide](ROS2-KUBERNETES-DDS-GUIDE.md) | Partly implemented and partly proposed |
| Work with existing Prometheus data | [Offline dataset guide](../DataAnalysis/dataset/README.md) | Historical sample; not a current benchmark |
| See conceptual research scenarios | [Scenario Lab](scenario-lab/README.md), [website source](../site/scenarios/index.html) | Animated conceptual cases, **not measurements** |
| Publish genuine evidence later | [Results and provenance contract](scenario-lab/RESULTS-PUBLICATION.md) | Schema/policy proposed |
| Contribute with Claude Code or Codex | [AI-assisted contributing](AI_ASSISTED_CONTRIBUTING.md), [agent prompts](AGENT_PROMPTS.md) | Current contributor instructions |
| Verify website work before publishing | [Static site guide](../site/README.md), [brand rules](../site/BRAND.md) | Site code in repository |

## Canonical ownership: do not create a second source of truth

1. **Program strategy and dependency order:** [PROGRAM-ROADMAP-2026-2027.md](PROGRAM-ROADMAP-2026-2027.md). The original [90-day modernization proposal](ROADMAP-2026.md) remains historical context and is **not** an up-to-date release status board.
2. **Experiment inventory:** [EXPERIMENT-PORTFOLIO.md](EXPERIMENT-PORTFOLIO.md) and the authoritative implemented-code/results status in [site/scenarios/data/experiments.json](../site/scenarios/data/experiments.json). Adding a proposal here does not turn its status into completed evidence.
3. **Runtime/API/source code:** owned by the implementation directories and pinned upstream dependencies. A website animation or issue is not proof of a deployed workload.
4. **Results:** raw data, immutable artifact manifest, analysis code and independent review, as defined in [RESULTS-PUBLICATION.md](scenario-lab/RESULTS-PUBLICATION.md); never copy example numbers as research outcomes.
5. **Issue and review state:** live [GitHub issues](https://github.com/MSKazemi/ros2-kubernetes-lab/issues) and [pull requests](https://github.com/MSKazemi/ros2-kubernetes-lab/pulls) override snapshots in planning files. Issue numbers deliberately remain stable across the repository rename.
6. **Agent conventions:** [AGENTS.md](../AGENTS.md), reused by [CLAUDE.md](../CLAUDE.md); do not duplicate agent rules in every track.

## Four coordinated workstreams

- **A — Platform foundation:** verified kind/Kubernetes/ROS 2 path, version-accurate docs, CI, security; track [#14](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/14), [#15](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/15), [#16](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/16), [#43](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/43), [#44](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/44).
- **B — Reproducible Hugging Face integration:** typed observation/action mock, Hub artifact pinning, dataset conversion, policy adapter; parent [#53](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/53) and [#92](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/92).
- **C — Research experiments and evidence:** preregistered hypotheses, fixed baselines, fault injection, safety gating, measured results; parent [#60](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/60) and [#88](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/88).
- **D — Education, website and collaboration:** student labs, accessible scenario demonstrations, result pages and Hugging Face Space **only after artifact/evidence checks**; parent [#83](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/83).

The program is **gate-driven**, not a promise that every issue will be implemented. See the [experiment portfolio](EXPERIMENT-PORTFOLIO.md) for first-run order and exclusions.

## Contribution rules for this new direction

Choose **one** child issue, check whether a PR already covers its files, state the input/output contract and deterministic offline tests, and add the necessary dataset license/model revision only when permitted. Hub tokens, unpublished robot logs, camera/person data and private infrastructure credentials must never enter this public repository. Use synthetic cases and read-only or simulated actuation by default. Human review is required before merging or publishing.
