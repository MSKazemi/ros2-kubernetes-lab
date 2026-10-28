# Repository audit — 28 October 2026

> **Scope and method.** Inspected repository metadata, the complete default-branch path tree, root/ROS 2/Kubernetes/monitoring/analysis/website/agent documentation, representative implementation files and CI workflows; fetched the body of **all 65 open issues** and reviewed the **11 open PRs**, their changed-file lists and GitHub mergeability metadata. **Not a code execution or end-to-end cluster audit:** the environment used for this review did not run Docker, Vagrant, the cluster, model inference or website browser checks. GitHub status is a dated snapshot; recheck before acting.
>
> **Public repository hygiene:** document public technical research only. No personal information, unpublished content, credentials or provider-sensitive data.

## Executive judgment

The strongest asset is not a single model or animated website: it is the **potential for measurable integration** of ROS 2 messaging, Kubernetes orchestration, pinned Hugging Face models/datasets, controlled network impairments, and honest reproducible benchmarks. There are **more proposals than validated experiment implementations**. The near-term risk is fragmentation, duplicated epic/issue ownership and false maturity impressions. The near-term opportunity is one reproducible CPU-first experiment and a verified kind/Jazzy ROS 2 cross-worker baseline.

**Priority order:** correct safety and baseline limitations → establish deterministic experimental contracts → integrate one pinned HF model/dataset offline → run and publish one genuine benchmark → expand into VLA/perception/remote-inference research → onboard contributors. Follow [canonical program roadmap](PROGRAM-ROADMAP-2026-2027.md) and [experiment portfolio](EXPERIMENT-PORTFOLIO.md).

## Inventory observed on default branch

| Area | Observed files / current capability | Constraint / action |
| --- | --- | --- |
| ROS 2 container | `ROS2/Dockerfile`, `ROS2/jazzy/README.md`, `scripts/test-ros2-image.sh` | Jazzy/Noble image recipe and same-container smoke test; does **not** prove multi-worker DDS |
| Legacy Kubernetes | `Vagrantfile`, `KubernetesClusterSetup/`, `Network/network_plugin.sh` | Historical Ubuntu 22.04 / Kubernetes 1.29 / Weave Net 2.8.1, heavyweight three-VM setup; isolate and label legacy |
| Original workload | `ROS2/ros_dep_1.yaml` through `ros_dep_3.yaml` | Foxy-based **stress-ng**, not self-starting ROS talker/listener |
| Monitoring | `MonitoringSystem/` with Prometheus/Grafana, Dashboard, manifests | `monitoring.sh` retrieves mutable remote manifests, grants broad permissions and uses `chmod -R 777`; `admin-user.yaml` binds `cluster-admin`; security work is prerequisite |
| Historical data | `DataAnalysis/dataset/`, notebooks, scripts, PDFs | Offline sample data are valuable teaching artifacts; historical samples are not repeatable fresh benchmark results. Pod-recovery timing requires repair |
| CI | `.github/workflows/`, `scripts/check-markdown-links.py`, `scripts/validate-site.py` | Shell, links, site metadata and image-local smoke checks exist; not yet broad manifest semantic checks or routinely verified Kubernetes E2E experiments |
| Website | `site/` with branded landing, docs, four scenario pages and results JSON | Research pages and animations are proposals; `experiments.json` deliberately has `result: null` and `run_count: 0`; **correctly not marketing fictitious accuracy** |
| AI guidance | `AGENTS.md`, `CLAUDE.md`, `docs/AI_ASSISTED_CONTRIBUTING.md` | Reuse single source, enforce one-issue-per-PR, no hidden auto-merge or false result claims |
| HF / LeRobot source | No merged, fully implemented Hugging Face policy bridge, verified LeRobot v3 conversion, remote model-server or VLA evaluation on default branch in this audit | Work exists primarily as issues and draft PRs; stage separately with pinned upstream versions and synthetic fixtures |

## Issues: every open issue classified once (65 total)

Use this as a **triage register**, not a substitute for the issue bodies or GitHub status. Issue links are `https://github.com/MSKazemi/ros2-kubernetes-lab/issues/<number>`.

| Workstream | Open issue IDs (reviewed) | Decision / triage |
| --- | --- | --- |
| A. Platform baseline, security and CI (10) | #4, #6, #7, #14, #15, #16, #29, #43, #47, #52 | Keep. Do #14/#15/#16 (PR #97 first), #6/#43 security, #29 validation. #52 observability optional after basic ROS 2 success. #7 partially delivered but still open for compatibility evidence |
| B. Docs, branding, release, community, growth (10) | #13, #17, #19, #20, #21, #22, #25, #32, #42, #44 | Keep but reconcile state. #13 is an empty legacy license issue: confirm LICENSE and close as not planned if no missing acceptance criteria. #25 appears addressed in open PR #36, **do not close until merged**. #22's original rename target already matches repo slug, leaving any expanded brand decision explicitly independent. #42 owns historical positioning, not a second current roadmap |
| C. Benchmarks, historical analytics, network and sensor fixtures (5) | #18, #45, #46, #48, #49 | Keep. Prioritize deterministic offline recovery metrics (#45/#46) and sensor fixtures (#49). #48 DDS-vs-Zenoh research only after verified baseline |
| D. HF/Physical-AI foundation and deep research (13) | #53, #54, #55, #56, #57, #58, #59, #60, #61, #62, #69, #70, #71 | **#53** is original Hugging Face strategy parent; **#54** is physical-AI context, not a separate implementation plan. #55/#58/#59/#60 are reusable gate components. #56 owns real v3 conversion, #57 compatibility, #61 upstream remote serving, #62 freshness; #69/#70/#71 advanced research, not first-run |
| E. Agent/education/ethics/external demo (9) | #64, #65, #66, #67, #68, #73, #74, #75, #77 | Keep. #73 owns Jev research, #74 PoC, #75 scientific comparison, #77 fixtures. #64 safe skills, #65 read-only RAG, #66 labs, #67 governance. #68 public Space visibility depends on results/approval |
| F. Scenario Lab and evidence (7) | #83, #84, #85, #86, #87, #88, #89 | **#83** owns website scenario presentation. #84/#85/#86/#87 are distinct educational experiments. #88 owns publication workflow, complements technical run schema #60 |
| G. HF scenarios, model catalog and mobility (11) | #92, #93, #94, #95, #96, #98, #99, #103, #104, #106, #107 | **#92** is HF scenario integration epic. #93 = student packaging/validation built on #56; #94 = comparator built on #74/#75; #95 = VLA simulation; #96 = composite remote inference scenario built on #61/#62; #98 = static Hub Space implementation; #99 = Hub research metadata complementing #58; #103 portfolio design; #104 mobility **separate extension**; #106 perception; #107 model-serving fairness **distinct from #69 robot-task assignment** |

**Total 10 + 10 + 5 + 13 + 9 + 7 + 11 = 65.** All issue categories are proposals until tested or merged. Do not bulk-close; audit checkboxes and merged commits individually.

### Duplicate/overlap resolution — clear ownership without deleting work

| Related issues | One implementation owner | Others become |
| --- | --- | --- |
| #53, #54, #92, #103 | This canonical roadmap for cross-track sequencing; #53 Hugging Face platform strategy; #92 integrated scenarios | #54 physical-AI rationale, #103 model catalog and research hypotheses |
| #56, #93 | #56 dataset conversion module; #93 validation + educational scenario | No second converter |
| #58, #99 | #58 immutable download/cache and manifest schema; #99 cards and Hub publishing | No parallel manifest format |
| #61, #62, #85, #96 | #61 server/adapter; #62 real network impairment science | #85 student simulated matrix; #96 composite HF/Jev showcase |
| #74, #75, #84, #94 | #74 one read-only triage PoC; #75 scientific benchmark | #84 casebook, #94 HF-vs-Jev comparison extension |
| #69, #87, #107 | #87 simulated task dispatch; #107 inference GPU cache/queue scheduling | #69 broader isolation/fairness research |
| #68, #98 | #98 static Space source/publication; #68 discoverability and public-results policy | One published Space, no cloned site |
| #18, #60, #88 | #18 ROS/Kubernetes measurement suite; #60 run schema, statistical contract | #88 website publication / review workflow |
| #104 and agent-mobility research | #104 bounded robotics-task continuity experiments here | Agent checkpoint/protocol primitives should remain in their own upstream research work; avoid importing unpublished/private code |

## Open pull requests: integration-first review order (11)

| PR | Observed state | Recommendation |
| --- | --- | --- |
| [#97](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/97) kind demo | Ready for review; GitHub shows mergeable clean | **Highest code review priority.** Inspect cross-worker logs, CI, resource requirements, network/security assumptions. Merge only after human approval and required checks; issue #14/#16 may remain partly open |
| [#91](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/91) stale docs | Ready/clean | Review and incorporate early; normalizes README status and gitignore. May conflict later with #72/#76/#101/#105 README hunks |
| [#36](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/36) monitoring alt text | Ready/clean | Small focused accessibility fix, verify screenshots and links |
| [#50](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/50) academic/industry strategy | Ready/clean | Preserve as reference; avoid turning into a rival roadmap |
| [#51](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/51) earlier audit | Ready/clean | Preserve dated evidence; superseded program priorities are in newer audit |
| [#72](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/72) AI/LLM/cloud robotics docs | Ready/clean | Valuable substantive research guidance; merge/rebase after doc path and cross-link checks; remove duplicate roadmap authority |
| [#76](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/76) Jev guide | **Draft**/clean | Finish fixtures and scope review; do not present Jev as live |
| [#101](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/101) HF scenario pages/Space | **Draft**/clean | Reconcile with #105 on `site/scenarios/index.html`, sitemap and Pages workflow; preserve status=null evidence contract |
| [#105](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/105) HF model explorer / RoboLattice RFC | **Draft**/clean | Reconcile model catalog with #101 and decide whether the working brand is distinct from established ROS 2 K8s Lab; no rename yet |
| [#41](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/41) community docs | Ready but GitHub reports **mergeable=false/dirty** | Rebase and resolve conflicting `SECURITY.md` / contributing edits before reconsidering; do not replace existing policy blindly |
| [#102](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/102) misleading RAG-tutor title | Ready, `unstable` checks; changed-file list shows **only `DataAnalysis/backup.py`** | **Block merge.** Does not implement issue #65 or its read-only RAG goal. Require a corrected scoped PR and verified tests; do not let `Closes #65` stand unreviewed |

PR 'clean' is only a mergeability metadata signal and does **not** establish tests, content accuracy, ethical clearance or merge approval.

## Consistency defects to correct with bounded future PRs

1. **Repo rename drift:** default repository slug is already `ros2-kubernetes-lab` but multiple Markdown links, CLI `git clone` commands, `docs/ROADMAP-2026.md`, Docker OCI metadata, and website canonical URLs still use `Vagrant-Kubernetes-ROS2-Deployment`. GitHub repository redirects may preserve some old URLs but hardcoded legacy paths are **not an intentional canonical identity**. Fix GitHub link/clone metadata separately from **live Pages domain** changes; first verify actual deployed Pages path, redirects, CNAME and search indexing before updating website canonicals/OG/sitemap.
2. **Evidence-state drift:** main README still describes website as a possible future preview, even though site source and Pages workflow are already in main and #91 checks a live URL; treat verified publication status independently of deployment CI.
3. **Agent instructions stale:** `AGENTS.md` describes issue #24 as under correction even though closed; PR #91 addresses this. Avoid a competing edit in this audit PR.
4. **Security and least privilege:** `MonitoringSystem/monitoring.sh` has `chmod -R 777` and floating remote installations; `admin-user.yaml` binds `cluster-admin`; cluster setup needs hardened defaults for new reference profiles. Keep old instructions labeled legacy, do not silently present them as safe.
5. **No authoritative implementation-vs-proposal table:** new program index and roadmap provide one; model catalog and website must use separate states `idea / synthetic demo / contract tested / container tested / cross-worker verified / reproducibly benchmarked`.
6. **No current run provenance:** `site/scenarios/data/experiments.json` retains null outcomes. Never substitute chart animation, CI green status, subjective demo, or model card claim for run artifacts.
7. **Pervasive plans vs few runnable examples:** stop multiplying roadmaps; finish one CPU no-cost experimental stack, then verified kind baseline, then optional GPU.
8. **VLA semantics:** observations, action units/order, camera resolution, FPS, latency and supported robot semantics must match a trained checkpoint; passing JSON is not equivalent to a valid policy or safe actuator.
9. **Artifact licensing:** Hub datasets/models require verified permissions, fixed commit revisions and public release review; synthetic images still require documented provenance and rights.

## Measurable 30-/60-/90-day checkpoints (proposed, not promises)

- **0–30 days:** merge/review smaller PRs and one verified kind demo; mark legacy clearly; one small deterministic offline dataset + gate + run manifest; no fake result pages.
- **31–60 days:** model/dataset revision pinning and one reproducible HF classifier OR perception workload; publish raw runs, seeds, limitations and licensing; optional Static Space of **verified** demo.
- **61–90 days:** remote inference / VLA and impairment experiments only after environment/gate tests; one independently reproducible scientific study with baselines and uncertainty; invite outside contributor replication.

## Immediate reviewer checklist

- [ ] Review #97 CI and cross-worker output; do not infer verified results from green Markdown checks.
- [ ] Reject/rework #102 mismatch with #65.
- [ ] Review/land #91, #36 and dated #50/#51 individually; rebase #41.
- [ ] Choose one main HF website track for #101/#105 and reconcile paths before merge.
- [ ] Adopt one PR for these docs, then link parent issue(s), not a new clone of an existing epic.
- [ ] Convert first small reproducibility experiment (#55 + #59 + #60) into tested code; register only measured results.
- [ ] Assign issue owners / priorities via live GitHub, and close stale #13/#25/#22 only after checking actual satisfaction.

See [PROGRAM-ROADMAP-2026-2027.md](PROGRAM-ROADMAP-2026-2027.md) for sequencing and [EXPERIMENT-PORTFOLIO.md](EXPERIMENT-PORTFOLIO.md) for scientific designs.
