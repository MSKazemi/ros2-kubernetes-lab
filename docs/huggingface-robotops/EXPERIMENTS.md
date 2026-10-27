# Four Hugging Face RobotOps experiments: operational research protocols

> All statuses: **NOT RUN**. A static animation is not evidence of an actual LeRobot dataset, LIBERO evaluation, hosted Jev test or remote policy service. Existing experiment protocol #60 and publication governance #88 remain authoritative.

## Shared controls

1. **Pre-register a falsifiable hypothesis**, primary metric and null hypothesis before viewing a held-out test set.
2. **Define a compatible physical/simulated semantics contract**: ROS 2 data timebase and QoS context; camera key, state/action tensor dimensions and physical units; task description; policy processor; robot/simulator identity. A successful model download is not a policy run.
3. **Freeze artifacts**: repo name, exact Hub commit SHA (not `main`), licensing, data split/episode family hash, model/processor config, image/source SHA, hardware and network profile, run seed and algorithm.
4. **Baseline**: deterministic offline approach before a hosted Jev model or paid GPU. Same input/evaluation budget and class taxonomy where methods are directly comparable.
5. **Count failures**: no discard of mispredictions, schema rejects, provider errors, disconnections, timeouts, aborted simulator episodes, out-of-domain data, invalid submissions.
6. **Report uncertainty**: raw data and reproducible scripts, per-category denominators, confidence intervals or bootstrapping across independent incident/episode families.
7. **Human review**: only share allowed public data and only mark metrics verified after independent analysis/rights and safety review.

## S5 — Dataset integrity and Hugging Face Hub publication

**Null:** strict semantics, privacy and rights checks reject no more invalid cases than naive parsing. **Alternative:** a typed validator prevents invalid LeRobot metadata and disallowed publication.

**Synthetic arms:** permissive JSON parse versus schema/unit/timebase/license validator; full official LeRobot v3 loader round-trip becomes an *optional separately validated integration*.

**Proposed cases:** valid metadata; incompatible camera/frame metadata; mixed degrees/radians; invalid FPS; missing episode bounds; wrong action vector size; missing task label; unknown license; private video marker; contradictory timestamps; unknown robot type.

**Metrics:** invalid-case detection/valid-case acceptance, reason-code agreement with human label, official LeRobot loader pass/fail once real data created, reproducibility/metadata completeness; later optional time-to-convert and file size from real conversion.

**Deliverables:** synthetic casebook, schema, rejection tests, code-backed conversion only with official package and pinned version, dataset card and revision once actual Hub publication is authorized. Links: #56, #58, #93.

## S6 — Jev Choice versus Hugging Face open text classifier

**Null:** Jev does not improve macro-F1/selective risk vs deterministic rules and a pinned local HF model when hosted cost/latency are considered.

**Design:** group-separated synthetic DDS/QoS/network/resource/healthy/unknown incidents. Baselines: rule parser/always unknown; HF classifier pretrained or fine-tuned **for the actual category map**, never inferred from arbitrary labels; optional TypeSafe Jev Choice. Do not give Jev more unredacted contextual data than the local model, and retain question order/model revision.

**Metrics:** family-held-out macro-F1, per-class recall, unknown/OOD, selective risk at fixed coverage, Choice probability Brier/ECE where valid, wall-clock p50/p95/p99, availability, 429 failures and costs including retries. Resolve thresholds using dev split only.

**Negative cases:** contradiction, missing evidence, injection in synthetic log, misordered choice options, provider outage, unknown/model drift.

**Deliverables:** frozen labels/splits, independent rule baseline and actual HF model path/cache, optional Jev client with opt-in and redaction, real predictions/run manifest and plots **only after tests**. Links: #74/#75/#84/#94.

## S7 — LeRobot/SmolVLA in LIBERO

**Null:** under fixed compatible simulator and checkpoint, investigated factor has no effect on actual task success. Document how and why the chosen pretrained or fine-tuned policy is compatible; a base model does not guarantee pick-place skill.

**Control:** fixed released LeRobot, chosen LIBERO suite/task IDs, selected policy/model processor, camera feature map, action relative/absolute mode, same simulator initial state, episode count and reset scheme; record GPU/CPU and camera image dimensions.

**Experimental factors:** action semantics compatibility (reject wrong mode/dimensions before running), camera mapping, policy/data revision, repeated seeds, scene variation, timing/resources. Analyze matched seeds; do not compare runs using different tasks/model revisions as if equivalent.

**Primary:** task completion fraction by task/suite with uncertainty; secondary actual inference latency, failed rollouts, GPU/VRAM and total run costs. Never infer safety or real hardware success from LIBERO.

**Deliverables:** verified CLI invocation for the *installed* pinned LeRobot version, actual task-compatible weights, raw episode results, analysis and honest model card. If GPU/hardware absent, document `NOT_RUN` and do not issue a fabricated score. Links: #57/#58/#60/#95.

## S8 — Remote inference in an isolated Kubernetes simulator study

**Null:** remote GPU policy serving does not improve valid-action completion once network freshness/failure costs are considered.

**Setup:** compatible LeRobot local baseline → pinned remote policy server via supported **Zenoh** contract (not ROS 2 DDS) → bounded simulated client → deterministic safety/authorization/action-age gate. ROS 2 bridge and DDS cross-worker validation remain independently unverified.

**Variables:** same-host vs trusted LAN vs Kubernetes service, RTT/jitter/loss/partition profiles, server resource throttle, action chunk scheduling, client driver support for hold position, model/processor mismatches and admission errors.

**Metrics:** p50/p95/p99 true sensor-to-valid-action age, explicit timeout/rejects, task completion in compatible simulator, recovery behavior and error rate, GPU/queue cost. Status changes must be sourced to a timestamped raw run trace and source/image/model digest.

**Expected failure behavior:** no authorization on timeout, no accepting stale chunks, no anonymous external ingress, no Jev-initiated motor commands. Jev may classify placement options **after** hard eligibility filters, never set deadlines/calculate hard quotas or override simulator stop.

**Deliverables:** CPU/mock negative contract tests, version-locked remote inference plan, opt-in secure K8s simulator deployment with run evidence, comparison across controlled networks. Links: #14/#15/#16/#55/#58/#59/#60/#61/#62/#96.

## Results board

The site-wide [results registry](../../site/scenarios/results.html) includes four additional HF tracks, all `planned` and every numerical `result` **null**. Evidence submission policy: [results publication](../scenario-lab/RESULTS-PUBLICATION.md) and [issue #88](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/88). New metrics may appear only after real raw data, immutable artifact and independent review.
