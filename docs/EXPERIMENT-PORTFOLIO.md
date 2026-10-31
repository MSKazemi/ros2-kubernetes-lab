# Reproducible robotics AI experiment portfolio

> **Status:** proposed, simulation-first research designs as of 2026-10-28. **No runs or performance numbers are claimed by this document.** Each experiment needs a real implementation PR and evidence reviewed under [the results contract](scenario-lab/RESULTS-PUBLICATION.md). Do not run unsupported policy commands against real robots. Canonical [program gates](PROGRAM-ROADMAP-2026-2027.md) and [audit](REPOSITORY-AUDIT-2026-10-28.md).

## Portfolio — choose one experiment, not all at once

| ID / first-run tier | Falsifiable question | Systems / HF component | Measured outcomes | Issues and prerequisite |
| --- | --- | --- | --- | --- |
| **E00 — CPU, first** | Can the same synthetic observation yield a typed, bounded, deterministic and rejectable action? | Fake ROS 2 adapter, mock policy, fail-closed gate | Schema pass/fail, replay equality, rejected stale/replay/out-of-range fraction | #55 #59 #60; no cluster needed |
| **E01 — CPU, first HF science** | When does a pinned local open classifier improve incident triage over deterministic rules, without increasing dangerous errors? | Local HF classification model vs rules; optional hosted Jev only with consent | Macro-F1, per-class error, abstention/coverage, selective risk, end-to-end p50/p95, cost | #74 #75 #84 #94; E00 + #58 |
| **E02 — CI/kind** | Which discovery configuration delivers messages across Kubernetes workers, on restart? | ROS 2 Jazzy, DDS discovery and optional bridge | Discovery completion, delivered/expected messages, p95 age, restart recovery | #14 #15 #16 #18, PR #97; G1 |
| **E03 — CPU, data** | Can synthetic ROS 2 action episodes be faithfully round-tripped into LeRobotDataset v3? | LeRobot v3 packaging, Hub metadata | Episode/frame/action counts, timestamps, modality alignment, round-trip equality, storage | #56 #93 #58 #99; E00 |
| **E04 — CPU/GPU, perception** | How do grounded detection and relative depth quality/latency change with placement, resolution and network faults? | Grounding DINO, Depth Anything V2 (pinned models) | Detection mAP/recall, depth scale-invariant error, p95 latency, bytes, throughput | #106 #58 #60 #88; labeled licensed images |
| **E05 — network, core PhD** | At what jitter/delay/loss do cloud-provided action chunks become stale enough that local or guarded execution is preferable? | LeRobot compatible remote server, optional GPU, simulated policy and action gate | Fresh accepted actions, deadline misses, action age, task completion, tail latency, fallback | #61 #62 #85 #96, plus #55 #57 #58 #59 #60 and G1 |
| **E06 — GPU/simulator, embodied AI** | Does a pinned SmolVLA checkpoint maintain manipulation success under controlled visual/network shifts? | SmolVLA/LeRobot, compatible simulator task (LIBERO candidate only after validation) | Task success, intervention/invalid rate, action latency, seed variance, GPU resource | #95 #57 #58 #60; compatible checkpoint/simulator and licensed tasks |
| **E07 — CPU then GPU, systems** | Does model-aware scheduling improve deadline-success fairness for multiple simulated robot clients compared to FIFO? | Multi-model inference, Kubernetes scheduling, cached model revisions | Jain's index, worst-client deadline success, p95 wait, GPU residency/evictions, throughput | #107 #69 #87 #58 #60; do not confuse task dispatch and model serving |
| **E08 — CPU/simulator, mobility** | Can a mission task change workers exactly once without unauthorized duplicate actions after crash/restart? | Portable task checkpoint, lease/fencing, provenance, simulator sink | Lost/duplicate tasks, time to resume, unauthorized action count, evidence coverage | #104 #59 #60; no physical actuation |
| **E09 — advanced systems** | Which local/remote policy configuration yields the best task-quality/energy/cost Pareto frontier? | Kubernetes telemetry, model serving, power meters when available | Valid outcomes per joule/euro, p95 action age, energy, model quality | #70 #62 #107, after E05/E07; measured power not CPU proxy |

**Recommended first public experiment:** E00 (make the harness real), followed by **E01** (first HF comparison) and **E02** (infrastructure). E03 and E04 can develop in parallel in separate PRs. **First high-value PhD paper direction:** E05; E07 and E08 are differentiated follow-up research directions.

## Shared experiment runner and artifact structure (proposed, not yet on main)

```text
experiments/
  README.md                        # actual supported commands/status
  common/
    schemas/observation.schema.json
    schemas/action.schema.json
    schemas/run-manifest.schema.json
    validators/                    # stdlib-first, offline-safe
    metrics/                       # quality, latency, risk, fairness
  e00-mock-contract/
    fixtures/ tests/ README.md
  e01-incident-triage/
    fixtures/ baselines/ splits/ tests/ README.md
  e02-dds-kind/
    scenarios/ collector/ tests/ README.md
  e03-lerobot-v3/
    fixtures/ tests/ README.md
  e04-perception/
    fixtures/ annotations/ tests/ README.md
  e05-action-freshness/
    network-profiles/ scenarios/ analysis/ tests/ README.md
  e06-vla-simulation/
    compatibility/ scenarios/ tests/ README.md
  e07-model-serving-fairness/
    simulator/ policies/ tests/ README.md
  e08-task-handoff/
    coordinator/ simulator/ tests/ README.md
results/
  README.md                        # public reviewed registry ONLY
  <experiment-id>/<run-id>/
    manifest.json                  # pinned and signed/hashed inputs
    raw/                           # anonymized, permitted and minimal
    analysis/                       # source SHA/command/environment
    summary.json                   # actual measured outcomes, no placeholders
```

This is a **suggested future layout**. Do **not** create all folders or empty modules now; implement one experiment at a time. Retain existing `DataAnalysis/`, `site/scenarios/data/experiments.json`, `scripts/` and `integrations/huggingface/` changes when reviewed; avoid duplicating the dataset registry or source-of-truth schema.

### Proposed operator command contract (for implementation PRs; THESE COMMANDS ARE NOT AVAILABLE YET)

```bash
# After E00 implementation, expected example interface:
python3 -m experiments.e00_mock_contract --seed 2026 --out results/local/e00
python3 -m experiments.common.validate results/local/e00/manifest.json

# After G1 / PR #97 review, expected kind interface:
make demo
make verify
make clean

# After E01 implementation AND an explicitly approved, pinned artifact cache:
python3 -m experiments.e01_incident_triage --offline --config configs/synthetic.yaml
```

No command in this block should be added to README as a real command until implemented and tested. Names above are API proposals, not promises.

## E00 — deterministic offline contract and safe failure (MVP)

**Research engineering question:** Does the typed contract preserve data/clock semantics and fail closed under faults?

1. Define `observation` with: scenario_id, monotonic capture/receive times, immutable episode_id, robot_model_id, seq_no, camera image shape+dtype, state vector component names/units, and task id. Synthetic PNG or inline fixtures are **not real camera readings**.
2. Define `action_proposal` with: model/algorithm id, source seq_no, action names+units, finite numeric values, limits, not_after deadline, and optional abstention. Avoid shells, topic wildcard writes, raw motor commands or executable code.
3. Implement deterministic rules/mock-policy baseline with fixed seeds and no network. Action goes to **simulated sink only**.
4. Validation gate rejects malformed, NaN/inf, unit mismatch, unauthorized, expired, duplicate or sequence-regressing proposals. Record rejection reasons and whether fallback is no-op/hold in **simulation**.
5. Test negative cases, zero network access, reproducible summary bytes, and explicit nulls where model id not relevant.

**Acceptance:** One nonprivileged laptop reproduces both accepted and rejected examples; CI tests every negative category; published sample has a manifest with no fabricated measured model metrics. **Owners:** #55, #59, #60.

## E01 — first Hugging Face comparison, ROS 2 fault triage

**Hypothesis (to test, not assert):** On held-out incident families, a pinned small local HF classifier can improve macro-F1 over rules, but may worsen inference latency and selective risk on ambiguous cases.

**Dataset:** Synthetic/human-reviewed, consent-safe incident casebook with DDS discovery failure, QoS incompatibility, ROS domain mismatch, missing endpoints, pod CrashLoopBackOff, image pull error, insufficient CPU, RBAC denial, and *unknown/ambiguous* category. Split by **incident family and scenario template** rather than random near-identical wording. Keep counterfactuals, redacted evidence, the case generator source, labels and manifest. Leakage/shortcut detection required.

**Arms (same input and test cases):**
- B0 deterministic keyword/rule triage (no HF);
- B1 simple local lexical/TF-IDF classifier or small conventional ML baseline;
- H1 pinned open Hugging Face text classifier with local offline weights after approved license/revision, adapted only using permitted training splits;
- J1 **optional** Jev hosted structured advisor with consent, secret-safe redaction and separate network-cost measurements. It is not an offline baseline and may be unavailable.

**Method:** Freeze labels/holdout, preregister metric definitions, report multiple random seeds / bootstrap intervals and a confusion matrix with counts. Model selection must use validation, never test cases. Measure input-to-typed-decision p50/p95 including preprocessing; report abstention coverage and wrong-high-confidence unsafe recommendation rate. No command execution.

**Publication:** `results/e01-incident-triage/<run>` with dataset and checkpoint SHAs, model card/licensing, raw predictions, latency traces, per-class counts, analysis notebook/script, limitations and reviewer. A failed or negative comparison is useful data.

**Acceptance:** CPU-local benchmark from offline cache; no opaque API required for core reproduction; **no claimed Jev improvement before measured data**. **Issues:** #74/#75/#84/#94/#58/#60/#88.

## E02 — baseline ROS 2 DDS between workers

**Question:** Can the maintained ROS 2 Jazzy deployment reliably deliver cross-worker messages and recover from pod restart?

**Method:** Pin image digest, exact K8s/kind version, RMW, CNI, participant discovery strategy, pod placement and resources. Capture talker/listener pod IDs, worker names, ROS domain id, log timestamps, expected/received sequence IDs. Restart publisher or subscriber and record discovery/recovery window; include a negative misconfiguration to prove verifier detects failure. Avoid using uncalibrated wall clocks across hosts for one-way microsecond latency.

**Baselines:** stable topology; restart; one deliberately incompatible/disconnected scenario. Alternative discovery/Zenoh bridge only after G1 and with distinct transport experimental arms (#48).

**Acceptance:** A [GitHub Actions run for PR #97](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/40587051848) has already shown successful cross-worker messages, a negative discovery failure, restoration and deterministic cleanup on one kind/amd64 host. Review and merge are still pending, and repeat/restart/other RMW or K8s profiles remain experiments, not demonstrated generality. **Issues:** #14/#15/#16/#18; pending PR #97.

## E03 — LeRobotDataset v3 sensor/actor conversion

**Question:** Do frame-state-action alignments, episode boundaries and metadata survive conversion and reload?

**Method:** Generate tiny **synthetic, labeled** task episodes, containing aligned image, joint/state array, target actions, stable fps, task IDs and episode resets; assert dtypes/shapes/timestamps exactly. Convert with **one pinned LeRobot release**, finalize writers, reopen the dataset and compare per-episode frame/action counts and values within stated tolerances. Check camera order, timebase, termination, units, license and rights; do not label a sensor-only rosbag as a valid action-training dataset.

**Storage:** LeRobot v3 packages tabular time-series data (Parquet), videos (MP4) and episode/feature metadata. Hub upload should be **optional and human-approved**, never run from PR CI. [Official LeRobotDataset v3 format](https://huggingface.co/docs/lerobot/lerobot-dataset-v3).

**Acceptance:** A fresh contributor can create, validate, load and inspect one tiny v3 dataset from only synthetic licensed inputs; checksum and round-trip tests pass. **Issues:** #56/#93/#99.

## E04 — zero-shot perception and cloud/edge tradeoffs

**Question:** Is a detector/depth model more useful as an edge-local workload or GPU server at controlled quality and network cost?

**Method:** Use licensed rendered scenes with fixed objects, text prompts, bounding boxes and **actual** reference depth if claiming quantitative depth errors. Candidate models: [Grounding DINO](https://huggingface.co/docs/transformers/model_doc/grounding-dino) for text-guided detection and [Depth Anything V2](https://huggingface.co/docs/transformers/model_doc/depth_anything_v2) for monocular depth. Pin exact weights and processor commit. For relative depth predictions, report scale-invariant/rank quality rather than calling values meters unless using a calibrated metric-depth checkpoint.

**Controls:** same image batch / resolution / prompt set, model variant, warmup, host and GPU label; compare image transfer/encoding separately from model computation. Use dummy prediction adapter for CPU CI; optional models need declared resource tiers. Collect mAP/recall on detection annotations, depth error with appropriate calibration, end-to-end p50/p95, server utilization and payload bytes. Do not equate visual examples with benchmarked accuracy.

**Acceptance:** one repeatable local run with manifest+raw predictions; cloud/edge claims only after equal-quality and transport measurement. **Issue:** #106.

## E05 — action freshness vs continuity: flagship PhD direction

**Question:** For matched simulated tasks, at what network/runtime conditions does offloading policy inference reduce **valid completed actions** despite possibly improving raw compute time?

**Execution matrix (initial proposal to preregister):**
- Placement: deterministic local mock / local pinned model / same-host remote / K8s remote server;
- Delay one-way: 0, 25, 75, 150 ms via isolated controlled simulator or `netem` when authorized;
- Packet loss: 0, 1, 3% with documented distribution; jitter: 0 and a documented stochastic profile;
- Server load: idle, competing request, cold model cache;
- Recovery: normal, server restart, network partition, stale reply, disconnect/reconnect;
- Replications: at least **5 independent seeds per critical condition** initially; refine sample size from pilot variance;
- Comparison modes: synchronous, upstream aligned chunking, bounded safe fallback, optional RTC if checkpoint supports it.

**Critical definitions:** Observation age and action age must use monotonic local capture/dispatch stamps and carefully documented clock conversion; server response time and client received time are not interchangeable. Each outgoing command from a simulated action sink must record whether its originating observation was fresh within deadline. "Action starvation" is a measurable state, not an assumed system crash. Follow upstream LeRobot remote transport/contract semantics (Zenoh and policy-specific action chunking in current main docs); verify pinned version first.

**Outcomes:** valid action rate, freshness-deadline miss ratio, p50/p95/p99 inference+network turnaround, duration of uninterrupted valid action playback, fallback frequency, simulated task success, bytes/second and resources. Quality must be matched; a faster but worse policy is not a win.

**Threats to validity:** training/test shifts, different preprocessing and hardware between arms, uncalibrated clocks, scheduler contention, nondeterministic GPU kernels, simulator differences and unsafe action semantics. Record them rather than bury them.

**Acceptance:** replayable impairment schedule; action gate provably rejects expired/duplicate commands; 95% confidence intervals where appropriate; artifact manifest and ethics/safety review. **Issues:** #61/#62/#85/#96, #55/#57/#58/#59/#60.

## E06 — SmolVLA simulation evaluation

**Question:** What model/task compatibility and observation/action assumptions dominate apparent success under viewpoint and latency perturbation?

**Before running:** Determine exact policy checkpoint, policy license, processor/camera expectations, action semantics, simulator task, evaluation API and version. The project currently **does not establish** that a default SmolVLA checkpoint can be scored unmodified in LIBERO. A compatibility adapter may be required. Do not claim task success from merely loading weights or generating tensors.

**Arms:** pinned licensed model / matching task baseline / intentionally out-of-distribution camera/task / optional remote serving. Multiple seeds, unmodified task success conditions and no train/test leakage. Report measured success, action validity, runtime and failure mode under the **simulated** environment.

**Issues:** #95, #57, #58, #60. [Official SmolVLA](https://huggingface.co/docs/lerobot/main/smolvla).

## E07 — model serving fairness and cache placement

**Question:** Under fleet contention, does model-aware admission/batching/cache policy improve the **worst served robot client's** valid requests relative to FIFO without reducing overall success?

**Start with deterministic discrete-event CPU simulator:** clients request models M1/M2 at known rates/compute sizes; servers have a bounded model cache and queue budget. Compare FIFO, earliest-deadline-first, fair-queueing, and model locality/batching. Workload instances, model sizes and deadlines are openly specified. Inject cache misses and bursts.

**Outcomes:** Jain's fairness index **on fulfilled valid work**; worst-client completion ratio; per-client deadline misses; p50/p95 queue delay; evictions/cache hit rate; throughput; rejection/abstention and resource traces. Only after simulation is correct run optional GPU confirmation on exact pinned revisions.

**Distinct from #87:** #87 dispatches high-level **robot tasks**; E07 schedules **model inference service slots and cache residency**. **Issues:** #107/#69/#58/#60.

## E08 — embodied task movement and continuity

**Question:** Can an independent verifier replay a simulated task relocation after worker loss without duplicate execution or unauthorized continuation?

**Scope:** move a **mission/agent task**, not a physical robot or an AI model's network parameters. Document which state survives (task id, goal, current step, lease epoch, data pointer, policy revision, authorization and deadlines), and which remains local (hardware driver/actuator). Compare stay, restart from scratch, transfer with checkpoint+fencing, and naive duplicate executor.

**Faults:** crash before and after checkpoint, partition during transfer, delayed completion, stale coordinator, wrong worker/model authorization, replayed receipt. Record fencing decisions and provenance receipt digests; no unsafe actuators.

**Outcomes:** lost/duplicate simulated actions, resume latency, valid task completion, proof completeness/verification failures, transfer overhead. Maintain boundaries with separate dedicated agent-mobility research; do not silently vendor proprietary or experimental components. **Issue:** #104.

## E09 — energy / cost / quality optimization

Use E05/E07 traces only as **hypotheses**. Actual joules require a calibrated power sensor/provider metric and accounted idle/background power. Actual cost needs recorded price/usage and location/time assumptions. Compare task-validity-constrained Pareto frontier; never present CPU% as measured energy. **Issue:** #70.

## Common data science requirements

1. **Prerequisite:** explicit null/unknown state rather than invented model or run results. Track `proposed → implemented/tested → reproducibly benchmarked → reviewed/published` independently.
2. **Reproducibility:** pinned source commit, image digest, `uv.lock`/pip lock or environment record, model/dataset revision SHA, seeds, hardware/software inventory, stable test split ids.
3. **Statistics:** predefined primary endpoint, baselines matched for input/task, disjoint test families, independent seeds, confidence intervals and per-group error analysis. Negative results must be published when appropriate.
4. **Performance:** distinguish cold vs warm model caching; measure full observation → dispatch end-to-end and model-only time separately. Record synchronized clocks or avoid invalid cross-host one-way latency claims.
5. **Security/privacy:** opt-in external providers; synthetic/authorized data; no access tokens in repo/CI artifacts; no high-privileged Kubernetes workload by default; prevent prompt injection, data contamination, runtime code execution and unsafe actions with deterministic allowlists.
6. **Human approval:** only public, license-reviewed, reproduced runs can update `site/scenarios/data/experiments.json` from `null` to measured values. PRs must show exact commands and actual output; never auto-merge.

## Collaboration / learning path

- **Beginner:** E00 mock contract or E03 tiny dataset validator; issue #55 or #93 with review by a maintainer.
- **MSc:** E01 triage casebook+classifier (#74/#94), E04 perception metric adapter (#106).
- **PhD:** E05 action freshness (#62), E07 fairness (#107), E08 mission continuity (#104).
- **Infrastructure/MLOps:** E02 kind DDS, artifact reproducibility, model cache (#14/#58).
- **Security/ethics:** action gate, redaction, safe publishing (#59/#67/#88).
- **Teacher:** turn passing artifact into a lesson+rubric (#66), not a new unmeasured experiment.

**Next action:** implement **E00**, then E01 and E02 in parallel only when their independent prerequisites are ready. See [program roadmap](PROGRAM-ROADMAP-2026-2027.md) for gate sequencing.
