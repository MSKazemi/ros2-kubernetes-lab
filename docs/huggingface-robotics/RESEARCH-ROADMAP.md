# Research implementation roadmap: ROS 2 + Hugging Face + Kubernetes

> **Plan 2026-10-28.** This does not supersede #92 or certify any real model run. Model catalog: [MODEL-CATALOG.md](MODEL-CATALOG.md); coding-agent instructions: [CLAUDE-CODE-HANDOFF.md](CLAUDE-CODE-HANDOFF.md). Proposed work should be scoped to small reviewed PRs, not an autonomous main push.

## Milestones and gates

| Milestone | Owner/action | Dependencies | Definition of done | Evidence |
| --- | --- | --- | --- | --- |
| M0: audit | Maintainer: reconcile issues and branch state (#22/#53/#54/#83/#92, merged #90, closed PR #100, open #97) | GitHub current default branch | Exact status documented; no stale deployment claims | Reviewed diff, URLs and changelog |
| M1: static discovery | HF model explorer + standalone Static Space source, model cards | This PR and #98 | SEO metadata, valid links, keyboard/readability, no token or inference | Source/validator report; no benchmark |
| M2: offline simulated contract | Implement #55 (fixed observation, action, failure modes) | ROS 2 Jazzy local image baseline | CPU-only tests, malformed action/timeout rejection, no physical robot | Unit tests, fixtures, CI summary |
| M3: reproducible HF data | #56/#93 + #58 | M2 schema and licensed fixture | v3 conversion with action, camera, timestamp, episode/task semantics and immutable commits | Dataset validation and negative fixtures |
| M4: real perception optional | New scoped issue; Grounding DINO Tiny / Depth Anything V2 Small | M1, vetted license and dataset, controlled environment | Pinned models/processors, offline fixture, p95 latency/correctness/negative cases, costs recorded; no false metric-depth claims | Reproducible run manifests and raw outputs |
| M5: VLA benchmark optional | #57/#95 | M2–M3, compatible LIBERO checkpoint, GPU approval | One seeded simulator task; exact model+processor+simulator matches; task successes and failures recorded | Raw episodes, run manifest, CI excluded GPU tests |
| M6: cloud/edge experiments | #61/#62/#96 | M5 and #59 deterministic freshness gate | Source-to-valid-action p95/p99 under jitter/loss, timeout and server failure, model cache versioning | Logs, traces, controlled network profiles |
| M7: public results + participation | #60/#88/#89/#98 | Human reviewed raw results | Clear planned/collecting/verified state, valid sitemap, optional reviewed HF Space and Collection | Hash-linked public evidence and corrected claims |

**Do not block documentation-only M1 on GPU or cross-worker DDS.** Do not claim a K8s deployed robot from a local Docker/Jazzy smoke test. A working kind test in PR #97 must be reviewed and merged before it becomes default-branch evidence.

## New research proposals not duplicates of existing issues

**P1 — Perception at the edge vs Kubernetes**: a focused Grounding DINO and Depth Anything study (independent of robot action control). Use a redistributable image fixture, test image size/compression, controlled delay/loss, precision/recall where labeled, CPU/GPU cost, image privacy and dropouts. Never call relative depth metric without calibration.

**P2 — Multi-robot model-serving fairness**: extend existing simulated fleet scheduling (#87) with GPU model-load/memory pressure and batching, pinned artifacts, budgets and fairness baselines. Start with deterministic queue simulator. Avoid equating throughput with robot task safety.

**P3 — Evidence-first contributor journey**: model explorer → issue page → local fixture → test report → reproducibility evidence. Each page links to exact issues and levels (BSc/MSc/PhD). Search indexing and traffic metrics are optional measured outcomes, not assumptions.

## Pre-registration table template

| Field | Example specification |
| --- | --- |
| Question | Does remote inference reduce p95 *valid* action age at equal task success? |
| Baseline | Local synchronous, same checkpoint and robot contract |
| Variant | Upstream supported remote LeRobot server on approved K8s profile |
| Network | Bounded, recorded RTT/jitter/drop/outage profiles with seeds |
| Primary endpoint | p95 source-image timestamp to independently valid simulated action |
| Secondary | p99, expiry fraction, task success distribution, GPU memory, energy if instrumented |
| Safety | Deterministic rejection of stale/malformed/unsupported action |
| Provenance | Immutable HF artifact commits + processor hashes, source SHA, image digest, LeRobot/sim versions |
| Replication | n episodes and seeds preregistered, raw logs+analysis published after review |
| Failure tests | Missing model, GPU OOM, delayed reply, disconnect, wrong action units/shape |

## Thesis-ready hypotheses

- **H1:** Transport-aware policy placement improves the fraction of *fresh simulated actions* versus a placement rule that ignores network variability. Compare with a preregistered deterministic baseline.
- **H2:** Perception traffic reduction (downsampling/JPEG) improves cloud turnaround while changing accuracy; estimate its Pareto frontier on a licensed annotated fixture.
- **H3:** Pinned model processor+dataset contracts reduce action-format regressions during model version rollout; inject mismatches and count correctly rejected rollouts.
- **H4:** Resource-aware fairness improves worst-client p95 and starvation frequency among simulated robots compared with FIFO at similar allocated GPU capacity.

For each: explicitly state scope, null hypothesis, methods, negative tests, reproducibility, and ethics/privacy constraints. No claim is made until observed data exists.

## Source controls

- Existing epic #92 and implementation issues #55–#62, #93–#99 are the owner-reviewed planning source.
- Upstream official LeRobot: https://huggingface.co/docs/lerobot/main
- Pinned revisions are **required before actual experiments**, and are intentionally not invented in this planning document.
- HF Static Space source here is **not a deployed Space**; manual release checklist in integrations/huggingface/spaces/robotics-model-research/README.md.
- Public source: https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment
