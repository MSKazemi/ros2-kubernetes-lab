# Cloud Robotics + AI/LLM teaching and contribution program

> **Course design proposal; not a released verified curriculum.** Each lab must be tested by instructors before being advertised as runnable. Existing legacy Vagrant mode needs ~30 GB RAM allocated across VMs and 18 vCPUs; the intended low-resource modern mode is still [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16).

## Who can participate and what they get

| Participant | Useful starting contribution | Outcome |
| --- | --- | --- |
| New undergraduate | Fix an incorrect command, illustrate an ROS vs Kubernetes concept, or write a schema-negative test | First PR, clear technical explanation, reproducibility discipline |
| Advanced undergraduate | Validate sensor/QoS test fixture and real error handling | ROS/K8s observability and debugging competence |
| MSc robotics student | Define camera/state/action schema and export LeRobotDataset v3 | Research-quality dataset and measurement methodology |
| MSc AI/LLM student | Compare read-only RAG and typed-skill planning baselines | Responsible agent evaluation and tool-level authorization |
| PhD distributed systems student | Preregister placement/fault study, evaluate tail latency and failure recovery | Reproducible paper or thesis experiment (publication not guaranteed) |
| PhD embodied AI student | Analyze exact model/embodiment fit and simulation domain shift | Controlled policy performance evidence |
| Professional platform engineer | Review RBAC, model cache, safe inference server, CI and provenance | Work-relevant infrastructure study |
| Instructor | Use graded six-lab sequence with TA notes and answer boundaries | Independent teaching assets and student contributions |

## Six progressive lab modules (proposed)

**Lab 1 — ROS 2 nodes vs Kubernetes nodes (beginner; no AI required)**

- **Learning objectives:** distinguish process-level ROS graph from cluster node scheduling, ROS_DOMAIN_ID, pub/sub/QoS and how pod identity changes.
- **Starting materials:** original README and DDS guide. A same-container Jazzy test exists; the actual multi-worker proof is blocked by #14/#15/#16.
- **Activity:** draw two networks, inspect the manifests, identify where stress-ng is misdescribed as talker/listener, design an integration check with timeouts.
- **Evidence:** sequence-verified subscriber output, worker placement and exact middleware only when tested.
- **Submission:** 1 architecture diagram, 1 discrepancy report, verification checklist and alternative interpretation.
- **Assessment:** conceptual correctness (30%), evidence integrity (30%), failure reasoning (25%), clarity (15%).

**Lab 2 — DDS/QoS and failure reasoning (intermediate; CPU only first)**

- **Objective:** understand that discovery and message delivery are separate from ROS application correctness.
- **Activity:** use seeded publisher/listener fixtures or a tested lab mode; compare allowed QoS profiles and controlled listener restart. Future full multi-worker experiment only after networking gate.
- **Evidence:** message sequence, expected windows, duplicates/drops, ROS/RMW/CNI configuration and failure case.
- **Submission:** small Python analysis, reproducibility manifest, limitation note.
- **Assessment:** test design (30%), collection quality (30%), analysis (25%), integrity (15%).

**Lab 3 — Robotics data as science (MSc; synthetic episode)**

- **Objective:** distinguish camera-only ROS bag from an actual policy-training episode.
- **Activity:** construct a tiny licensed synthetic camera/state/action/task episode; document units, calibration, timestamps; validate a pinned LeRobotDataset v3 readback with deliberately malformed cases.
- **Evidence:** schema, manifest and hash, feature alignment, data card and documented rejected episode.
- **Submission:** converted fixture + tests + card.
- **Assessment:** schema correctness (30%), alignments/tests (35%), provenance/privacy (25%), report (10%).
- **Gate:** wait for implementation of #56 before claiming upstream compatibility.

**Lab 4 — Model provenance and offline lab (MSc/MLOps)**

- **Objective:** reproduce a particular model/dataset revision and show missing cache fails clearly.
- **Activity:** compare immutable HF revision vs changing default, model-card review, prefetch, cache hit/miss, offline check; use a public tiny artifact only after licensing review.
- **Evidence:** exact repo commit, processor and container digest, cache verification, failure/cleanup logs without tokens.
- **Submission:** manifest + negative tests + short incident scenario.
- **Assessment:** revision integrity (35%), offline handling (30%), security (20%), explanation (15%).

**Lab 5 — Agentic AI with deterministic boundaries (AI MSc)**

- **Objective:** contrast generative language and secure authorization of simulated robot tasks.
- **Activity:** have a model propose typed skills; validator controls permissions; evaluate 10 benign and 10 adversarial sample prompts (sample minimum, not a statistical claim).
- **Evidence:** allowed vs denied calls, untrusted retrieved text, false rejects, versioned model and prompt.
- **Submission:** skill contract, attack corpus, results and safety review.
- **Assessment:** correct authorization (35%), negative tests (30%), measurement (20%), ethics (15%).
- **Rule:** no raw robot joint/velocity/shell/kubectl tools.

**Lab 6 — Reproducible cloud-robotics research (advanced MSc / PhD)**

- **Objective:** build a preregistered, failure-inclusive placement or recovery comparison.
- **Activity:** choose CR-08 or CR-16; freeze versions; repeat controlled trials, include negative cases, quantify confidence and interpret observed tail behavior.
- **Evidence:** raw results, source and artifact commits, clock assumptions, metadata/seed/conditions, regen plots and threat-to-validity discussion.
- **Submission:** paper-style 4–6-page methods/results brief, reproduction instructions and evidence status level.
- **Assessment:** hypothesis/control (25%), measurement rigor (30%), replication (25%), limitations/ethics (20%).
- **Gate:** no cluster/inference claims before modern cross-worker baseline and optional policy service are actually tested.

## Suggested 8-week teaching sequence (schedule proposal)

| Week | Theme | Output | Resource tier |
| --- | --- | --- | --- |
| 1 | Concepts and trustworthy claims | Architecture and test-plan note | Docs/CPU |
| 2 | ROS topic/message delivery | Deterministic publisher and sequence test (when available) | CPU; K8s optional |
| 3 | Data and frames/clock semantics | Synthetic episode, unit checks | CPU |
| 4 | HF Hub/model provenance | Immutable manifest and offline negative case | CPU |
| 5 | Mock inference + action validator | Logged valid/rejected candidate actions | CPU |
| 6 | LLM read-only vs allowlisted agent | Injection test with zero tool side effects | CPU optional LLM |
| 7 | Cluster/remote placement experiment | Repeated controlled results or design-only report if blocked | Optional K8s/GPU |
| 8 | Research and responsible publication | Reproducibility packet, cards and risk review | CPU |

The schedule assumes modules exist; it is **not** a guaranteed time-to-completion or evidence that lab code is implemented. Do not make course grading depend on a paid model API or physical robot.

## Student submission template

For every submission: title; scenario ID; learning objective; exact source revision; hardware/OS; ROS/K8s or N/A; data/model source and license; commands *actually run*; expected vs observed output; negative cases; manifest/raw evidence; ethics check; limitations; citations; cleanup. Public student work must not contain credentials, personal images, campus-only robot maps, internal university material or unpublished research.

### Assessment standard

Rubrics reward **correct negative outcomes** as much as success. A student who proves that an incompatible model correctly fails is more rigorous than a student who hides the failure and reports "AI robot working." Passing a unit test is not equivalent to proving deployment or safety.

## PhD incubation path: question → experiments → publication

1. Survey related work (FogROS2 and its extensions, LeRobot, ROS 2/DDS, K8s scheduling). Write the **smallest novelty statement**, not a broad marketing claim.
2. Select one falsifiable scenario from [catalog](SCENARIO-CATALOG.md); freeze task/embodiment/hardware.
3. Draft experiment registration, controls, metrics, failure conditions and statistical plan. Get supervisor/ethics approval for any human, proprietary or physical data.
4. Build a CPU mock baseline first; then add exactly one source of complexity (GPU model, network, multimachine, LLM planner) at a time.
5. Preserve every run, including timeouts and failures. Distinguish simulated success from physical task performance.
6. Reproduce independently; publish artifact/version cards and limitations; target a research workshop/paper **only after** evidence.

Potential thesis areas: edge-cloud action-age thresholds, robotic RAG grounding under domain/version drift, deterministic authorization of agentic task proposals, multi-robot policy-service fairness, energy per successful robotic task, and provenance-based reproduction of robotics-AI results.

## Contributor journey (humans, Claude Code, Codex)

Use [CONTRIBUTING.md](../../CONTRIBUTING.md), [AGENTS.md](../../AGENTS.md), [AI-assisted contributing guide](../AI_ASSISTED_CONTRIBUTING.md) and [agent prompts](../AGENT_PROMPTS.md). Either ordinary editor workflow or coding-agent assistance is welcome. Human review is responsible for tests, safety, licenses and claims.

**Beginner options:** [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55) typed CPU mock; [#65](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/65) read-only tutor evaluation fixtures; existing documentation [#24](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/24), [#29](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/29), [#30](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/30).

**Research options:** [#56](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/56), [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60), [#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62), [#69](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/69), [#70](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/70), [#71](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/71).

**Example bounded agent prompt:**

```text
Read AGENTS.md, the linked issue and the relevant files.
Explain: present behavior, smallest proposed change, exact verification, and negative cases.
Do not run Vagrant or alter robot actuation, data licenses, safety rules or secrets.
Distinguish static tests, offline fixture tests and actual cross-worker tests.
Work on a review branch, keep changes scoped, inspect the diff and produce a reviewable PR.
Never claim a benchmark or runtime behavior unless you observed and recorded it.
```

The agent should not autonomously push to main or merge its own changes. README and legal/safety disclosures should change with functionality, and PR reviewers should be able to reproduce at least the offline evidence without an external account.

## University adoption and collaboration

Offer self-contained workshops/tutorials, short videos, graded problems, reproducibility challenges and a curated first-contribution pathway. Track reproducible independent installs, external datasets/citations, independent issues/PRs, instructor reuse, research replications and reduction in setup failures. GitHub stars are a **secondary** measure; avoid spam, misleading "working robot" labels and unverified universal benchmarks.

**Course maintenance:** each published semester pins a release/tag, validates commands and dependencies, tracks deprecation of ROS/K8s/HF components, retains historical exercise references, and explicitly notes the support status of resources. Physical hardware modules are excluded until institution/site safety oversight exists.
