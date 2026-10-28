# Integrated cloud–edge robotics and Hugging Face program (2026–2027)

> **Status:** proposed canonical **coordination** plan as of 2026-10-28, not a release announcement. Current live issue/PR states supersede dated statements. Research must be simulation-first, read-only by default, opt-in for hosted models, and reproducible. No physical actuators are to be controlled by an unvalidated AI policy. This document coordinates existing issues rather than creating a competing epic. Reviewed in conjunction with [the repository audit](REPOSITORY-AUDIT-2026-10-28.md), [experiment portfolio](EXPERIMENT-PORTFOLIO.md), [the scenario evidence policy](scenario-lab/RESULTS-PUBLICATION.md), [AGENTS.md](../AGENTS.md).

## One-sentence north star

> **Build, observe, and scientifically benchmark distributed robotics AI across ROS 2, Kubernetes and Hugging Face, with traceable evidence and safe simulation.**

We are building a **reproducible research lab**, not a universal robotic operating system, new VLA foundation model, unreviewed robot actuator, generic ML model host, or safety-certified production system. Existing ROS 2/Kubernetes teaching paths stay available; the proposed Physical AI research direction is an **extension** with stronger scientific value.

### Target audiences and their first tangible outcome

| Audience | Need | First verified deliverable |
| --- | --- | --- |
| BSc / ROS 2 beginner | Run something without a robot or GPU | Local deterministic observation → validation → mock decision with test output (#55/#59) |
| MSc / AI systems student | Compare algorithms honestly | Family-held-out ROS 2 fault-triage benchmark: rules vs small open local HF classifier, optional Jev (#74/#75/#84/#94) |
| PhD researcher | Publish nontrivial systems research | Reproducible action-freshness/cloud–edge placement or serving-fairness study with uncertainty and replication artifacts (#62/#107) |
| ROS 2/Kubernetes engineer | Understand the operational consequences | Verified cross-worker discovery, observability, failure/restart under pinned reference versions (#14/#15/#16/#18) |
| Educator/TA | Hardware-free assignments | Six independent graded modules, fixtures and rubrics (#66) |
| Industry research team | Reproduce a performance/security claim | Pinned model, network, latency/failure conditions, raw metrics and fail-closed guard (#58/#59/#60/#88) |
| Open-source/HF community | Find projects and contribute safely | Searchable docs, research result cards, carefully licensed dataset/model cards, one static Space (#83/#98/#99) |

## Four workstreams, and exactly what each owns

**A — Modern, safe research substrate.** Owns container/K8s test profiles, CI, DDS networking, secure cluster defaults, monitoring and fixture runners. Parent issues #6, #14, #15, #16, #18, #43, #47, and PR #97. Historical Vagrant is supported as an **archived learning path** only until modernized and verified.

**B — Hugging Face/LeRobot adapter layer.** Owns typed observation/action model, immutable Hub revisions/cache, dataset conversion and offline replay, policy interface, and **upstream** remote server integration. Parent #53; implementations #55, #56, #57, #58, #59, #61; research/scenario umbrella #92. Avoid another training framework or reinvented remote inference protocol. Treat Jev as an optional external **advisor**, never the safety authority (#73/#75).

**C — Scientific experiment engine.** Owns run manifest, seeds, baselines, failure injection, statistics, raw evidence and publication process. #18 owns legacy infra metrics, #60 common schema and statistical contract, #88 review/publication registry. Research modules #62, #69/#107, #70, #71, #95, #106, #104. Never publish measured results without raw evidence.

**D — Education, discovery, collaboration.** Owns website and accessible demos (#83), HF scenario integration (#92), one static HF Space (#98), model/dataset cards (#99), learning modules (#66), student contributor instructions, issue discovery and website metadata (#19/#21/#32/#89). A scenario HTML animation is explanatory content, **not** a model benchmark.

## Architectural boundaries

```text
 [Synthetic/authorized ROS2 sensor+robot state]     [Approved HF datasets/revisions]
                 |                                             |
     ROS 2 DDS / explicit adapter                License + revision+hash manifest
                 |                                             |
       Typed obs/state contract <-------------------------------+
                 |
        [Simulated robot lifecycle / immutable mission id]
                 |
      +----------+--------------+------------------+
      |                         |                  |
 CPU/mock & rules          HF local policy    Upstream LeRobot remote
 deterministic base         pinned weights    pinned server + optional GPU
      |                         |                  |
      +-------------------------+------------------+
                                |
                   Typed policy/action proposal
                                |
                    Deterministic safety gate
                schema / bounds / TTL / provenance
                                |
                     Simulation-only action sink
                                |
               Experiment runner + trace/metrics
                                |
             Pinned run manifest + raw results + analysis
                                |
                    Reviewed result card / Space

 Optional Jev / LLM: advisory risk & triage *outside* the action safety boundary.
 Kubernetes: schedules workloads, limits resources, exposes telemetry and faults.
 DDS / Zenoh: transport and discovery are separate from model execution semantics.
```

The LeRobot remote-inference contract is **version-sensitive**: the upstream documentation currently describes a policy server/client over Zenoh with admission checks, compatible policy semantics, action chunk freshness, refill/alignment, and constrained robot support. Do not assume older APIs or generic gRPC support. [Official remote inference](https://huggingface.co/docs/lerobot/main/remote_inference).

## Delivery gates and dependency DAG (not arbitrary dates)

| Gate | Work required / owner | Minimum exit evidence | Cannot honestly claim before |
| --- | --- | --- | --- |
| **G0 — Clarity** | #44, #91; merged docs index and audit | Supported-vs-legacy matrix, canonical landing, scenario claims/status correct, no broken local references | Current compatibility, live inference, or replicated metrics |
| **G1 — Runnable ROS 2 substrate** | #14/#15/#16, PR #97, #6/#29/#43 | `make demo`/verify/clean on documented host resources, talker+listener pinned to separate workers, timed log/CI verification of deliveries and discovery, no broad privileges | Any Kubernetes cross-worker ROS 2 experiment |
| **G2 — Offline AI research contract** | #55, #59, #60, #58 (schema-only can start independently) | Fake observations + deterministic mock policy + bound/deadline guard + versioned artifact/run JSON Schema + unit/negative tests on CPU; replay gives same result | Real model/task-quality comparisons |
| **G3 — One verified HF baseline** | #56/#57 or #74/#94 or #106; #58 | Pinned HF commit(s), model/dataset licenses, golden fixture, 3+ baselines, measured latency+quality, repeatable local script, raw logs, independent review | HF runtime performance or data compatibility |
| **G4 — Distributed inference and impairment** | #61/#62/#85/#96, #59, #60 | Reproducible cluster/simulator workload, explicit workload/packet-loss/delay matrix, client/server trace, stale-action fault cases, resource telemetry | Evidence for cloud/edge robustness |
| **G5 — Extended science and publication** | #95/#104/#107/#70/#71; #88/#98/#99 | Preregistered design, independent holdout seeds, confidence intervals, controls/ablation, publicly replayable artifacts, human-approved cards and Space | Paper-grade generalization, speedup or improved safety |

**Parallelism:** G2 offline schema+gate can start **before** G1. Website and model discovery docs can progress in parallel, labeled `proposed`. G3/G4 scientific claims require earlier gates appropriate to their workloads; don't hold a CPU-only classifier behind a Kubernetes cluster requirement.

## First three releases (conditional milestones)

### M0: Foundation / first reproducible experiment (proposed weeks 1–3)

1. Human-review PR #97, #91, #36 and conflicting #41; block unrelated #102. Do not auto-merge.
2. Publish a current reference/support-state table: **Legacy Vagrant**, **Jazzy image-local**, **kind cross-worker pending verification**, **HF model inference pending**.
3. Make #55's synthetic typed observation/action contract **only for simulation**; implement #59 reject-on-expiry/out-of-bounds/replay; add #60 minimal manifest schema and deterministic test in CI.
4. Record one CPU-only offline run, from fixtures through evaluation. Publish results only if reproducible and reviewed.

**Gate:** Outside contributor can run the fixture and reproduce deterministic decisions on a CPU laptop with one documented command.

### M1: Hugging Face integration / public model-validated science (proposed weeks 4–6)

1. Complete #58 immutable Hub model/dataset revisions + offline cache + terms/license manifest; never pull unreviewed `trust_remote_code` into CI.
2. Select **one** path for first execution (not all concurrently): small local Hugging Face classifier versus rules on synthetic incidents **or** Grounding DINO/Depth Anything perception on licensed rendered images. The latter requires more CPU/GPU headroom.
3. #56/#93 can separately produce a tiny aligned camera+state+action dataset, **if** data include genuine action targets and upstream v3 APIs are pinned and round-tripped.
4. Publish inference latency, resource use, test set generation, uncertainty and raw artifacts through #60/#88. Site text must match the observed capability.

**Gate:** Fresh machine recreates the approved model snapshot by immutable commit and runs one benchmark; a human can inspect rights and results.

### M2: Cloud–edge scientific track (proposed weeks 7–12)

1. Deploy upstream LeRobot remote policy server only for a **checkpoint contract and simulator** that are actually compatible (#57/#61).
2. Compare local-vs-remote placement and simulated impairments, action TTL/starvation, bounded fallback decisions, and model cold-start effects (#62/#85/#96).
3. Run one deeper track (not all): SmolVLA+LIBERO *after compatibility verification* (#95); perception edge/cloud (#106); multi-model/GPU resource fairness (#107); mission-state handoff (#104).
4. Require external reviewer replication before marking website results as `verified`. Static HF Space #98 can showcase only public, approved synthetic demos and validated evidence.

**Gate:** One well-documented paper/research artifact, not just additional HTML pages or issue count.

### M3: Research community and medium-term extensions

Invite students to repeat the experiment on a different machine/network. Add grading rubrics (#66), model/data cards and an HF collection (#99), optional safe agent-skill evaluation (#64/#86), agent mobility (#104), and later energy/cost Pareto experiments (#70). Publish negative results and limitations.

## Technical platform profile decisions

| Profile | Purpose | Hardware/cost | State |
| --- | --- | --- | --- |
| CPU-only fixture/contract | Entry path, CI, data formats, safety, incident classifier | Ordinary Linux/macOS laptop; no GPU/robot/cloud | **To implement** (#55/#59/#60) |
| Local kind multi-worker ROS 2 | Real ROS 2 DDS/cluster verification, scheduling, fault injection | Linux host with Docker and enough cores/RAM; document measured requirements | **Open PR #97**; verify independently |
| Historical Vagrant | Reproduce archived Kubernetes/Foxy experiments if desired | ~30GB VM RAM and 18 vCPU in present configuration | **Legacy**, security caveats |
| Opt-in GPU policy/simulation | SmolVLA/remote inference/GPU scheduling | Local/workstation or separately authorized cloud GPU, explicit cost disclosure | **Research proposal** |
| Static web/HF Space | Scientific overview, approved metadata/results | No GPU needed | Site exists; HF Space **proposed** |

Choose a single primary development baseline (Jazzy on kind after tests) and make Vagrant an explicitly marked historical alternative, not a second modern installation promise.

## Model/research selection policy

- **First HF experiment:** a locally runnable classifier baseline on deterministic ROS 2 incident fixtures (#74/#94). Scientific novelty is limited; use it to validate pipeline and benchmark hygiene, not as a major paper claim.
- **First publishable distributed-systems direction:** freshness-aware cloud–edge inference under loss, jitter, queueing and model cache/cold starts (#62/#96). Measure **valid outcomes under deadlines**, not just raw speed.
- **First high-interest embodied-AI direction:** SmolVLA + simulated manipulation with a checkpoint compatible with a *specified* task/environment; LIBERO is a candidate, **not presumed plug-and-play** (#95).
- **First perception direction:** grounded detection / relative monocular depth with labeled, redistributable synthetic images (#106). Perception does not directly actuate a robot.
- **First multi-robot scheduling direction:** model-aware admission + fairness for shared inference with CPU deterministic simulator, optionally confirmed on GPU (#107). Separate task dispatch (#87).
- **Longer-term research:** safe task-state movement (#104), energy vs quality (#70), embodiment transfer (#71), comparing DDS discovery vs Zenoh bridge (#48). These should not block the initial user journey.

## Minimal experimental artifact contract — reused everywhere

Each **real run** should store:

```text
 experiment_id / hypothesis / baseline_id / scenario_id
 source_commit_sha / container_image_digest / environment lock
 ROS_distro / RMW / Kubernetes_version / network_profile
 model_repo_id / model_commit_sha / processor_config_hash / license
 dataset_repo_id / dataset_commit_sha / split_hash / license
 simulator version / observation+action schema+units / fps
 scenario seed / run seed / resource class / placement
 raw client-server traces / clock origin / failure schedule
 observed outcomes and validity flags / latency percentiles / resource metrics
 analysis script hash / timestamps / limitations / independent reviewer
```

A run with no executed model should use a distinct `mock/synthetic` variant of this schema, not fake model SHAs. Holdouts must be episode/task-family-disjoint when applicable. Use multiple seeds and confidence intervals for stochastic experiments. Include neutral/no-model baselines and explicit abstention/rejection rates; no headline speedups without matched accuracy/task success.

## Test matrix, review and scientific integrity

- **Offline CI (required):** shell/JSON schema/manifest validation, local links, HTML status integrity, mock/replay tests, expired/replayed/invalid observation failures; no tokens, GPUs or network access.
- **Kind integration CI (after G1):** built image digest, worker placement, talker/listener delivery, DDS discovery/restart, resource/timeouts, network policy, deterministic cleanup, sanitized logs.
- **HF optional smoke (opt in):** offline cache test with pinned artifacts, no `main` revision dependency; license and processor/shape checks; fixed known sample output structural assertions, **not brittle guessed quality scores**.
- **Scientific runs (separate workflow):** pre-registered matrix, repeated seeds, calibrated clocks, per-run raw data, cost/energy logging when instrumented, statistical analysis, full limitations.
- **Public publishing (human review):** rights and private data check, auth/secrets exclusion, website result card from immutable evidence only; log if a metric is not measured rather than fill a speculative number.

## Success measures (targets, not historical achievements)

| Area | Proposed target | Measurement source |
| --- | --- | --- |
| First-run reproducibility | A novice reproduces deterministic CPU experiment in <=30 minutes | User study + reproducible CI recipe |
| Cross-worker reliability | Documented independently verified two-worker message delivery in stable kind test | Actual run logs and PR checks |
| Research completeness | Each published result links to raw data, source SHA, manifest, reproducible analysis and reviewer | Results registry / #88 |
| HF reproducibility | 100% of **published model-based runs** use immutable model/dataset revisions and declared licenses | Run manifest validator |
| Safety | 100% injected invalid/stale/replayed simulation actions rejected in negative unit suite | Test report |
| Research usefulness | At least 1 high-quality comparative study with honest negative results and variance | Reproduction package |
| Community | 2 external reproductions or contributor PRs and one reusable MSc teaching lab | Repo PRs + feedback; aspirational |
| Visibility | Qualified visits to **verified** demos, paper citations and repo reuse, not only stars | Privacy-respecting analytics/links |

No target above is an achieved metric.

## GitHub coordination and implementation handoff

1. **Reuse** issue #53 (HF strategy), #92 (HF scenarios), #83 (website scenarios), #60 (run contract), #88 (results). Create **at most one new** audit/coordination ticket if the review needs status tracking; do not add a fifth HF epic with duplicate implementation tasks.
2. Ensure each child issue states: owner stream, one bounded deliverable, dependencies, inputs+outputs, CI command, limitations, and acceptance criteria; prefer links to copied prose.
3. Before coding, review overlapping open PRs #101/#105 and #72/#76; branch from latest `main` after integration. Do not cherry-pick duplicate files blindly.
4. Contribute one issue → one PR → independent diff/test review → human merge; see [AGENTS.md](../AGENTS.md).
5. **If a dataset, model or agent is not available** under an appropriate license, replace the workload with a clearly labeled synthetic/fake fixture and defer any model-performance claim.

## Official upstream starting points (recheck at implementation time)

- [LeRobot documentation](https://huggingface.co/docs/lerobot/index)
- [LeRobotDataset v3](https://huggingface.co/docs/lerobot/lerobot-dataset-v3)
- [SmolVLA](https://huggingface.co/docs/lerobot/main/smolvla)
- [LeRobot remote inference](https://huggingface.co/docs/lerobot/main/remote_inference)
- [HF Hub immutable revision downloads](https://huggingface.co/docs/huggingface_hub/guides/download)
- [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces)
- [Grounding DINO](https://huggingface.co/docs/transformers/model_doc/grounding-dino)
- [Depth Anything V2](https://huggingface.co/docs/transformers/model_doc/depth_anything_v2)

**Related program context:** [Original infrastructure roadmap](ROADMAP-2026.md) (dated proposal), [scenario website](scenario-lab/README.md), [research results](scenario-lab/RESULTS-PUBLICATION.md), [new dated audit](REPOSITORY-AUDIT-2026-10-28.md), [experiments](EXPERIMENT-PORTFOLIO.md).
