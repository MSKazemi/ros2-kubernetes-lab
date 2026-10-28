# Coding-agent implementation handoff: ROS 2 Kubernetes × Hugging Face

> **Status:** proposed work packages. This is an agent-friendly execution guide, **not** a set of implemented CLI commands. Read [AGENTS.md](../AGENTS.md), [the integration roadmap](PROGRAM-ROADMAP-2026-2027.md), [the experiment portfolio](EXPERIMENT-PORTFOLIO.md), the **live** issue, and any overlapping PR before writing code. Preserve existing historical data and provenance. One child issue / one bounded pull request.

## Shared definition of done for every work package

- [ ] State exact repo/branch head, issue number, version pin, inputs/outputs, tests and non-goals.
- [ ] Run fast offline tests that require no secret, model download, Docker privileges, live cluster, physical robot or paid service.
- [ ] Provide a sample synthetic fixture and its license/provenance; do not claim synthetic data represents robotics reality.
- [ ] Guard against expired, repeated, malformed, unauthorized actions; use simulation sink **only** for any robot command.
- [ ] Any optional integration requiring credentials/network/cloud is disabled by default, opt-in, documented, and never exercised from untrusted PRs.
- [ ] Mark each feature status correctly: `proposed`, `implemented/contract-tested`, `container-tested`, `cross-worker-verified`, `benchmarked`, or `published/reviewed`.
- [ ] All new results have reproducible raw data + run manifest. Never replace null entries on the public site with speculative statistics.
- [ ] Human reviews diff, licensing, safety and measurements before merging to `main`.

## Wave 0 — integrate already-open work (human review)

**0A — Cross-worker reference demo, issue #14/#16, PR #97**

Do NOT start a second kind profile. [CI run 40587051848](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/40587051848) already shows actual cross-worker ROS message delivery and a deliberate discovery-failure test with recovery on a hosted amd64 kind cluster. This **does not** validate the Vagrant profile, other network conditions or any model inference. Review the PR's `Makefile`, `kind/ros2k8s-demo.yaml`, ROS 2 image pin, Kubernetes pod placement, Fast DDS Discovery Server and `scripts/verify-ros2.sh` carefully. Ask for actual two-worker test evidence from CI/run logs, negative verification case, CPU/RAM resource requirements, network/port permissions and cleanup behavior. Mark incomplete original Vagrant-specific acceptance conditions as open.

**0B — Documentation reconciliation, PR #91, #36, #50, #51, #72, #76, #101, #105**

Order: small corrections first, historical strategies for reference, then broad research documentation, then Jev/HF website after checking overlapping `README.md`, Pages workflow, scenario index and sitemap. Prefer a single canonical research program navigation; do not replace source-of-truth with cloned docs. PR #41 is conflicting, rebase. **Block PR #102** until its changed source and test evidence actually implement RAG issue #65.

## Wave 1 — three safe first-code PRs

### W1 / PR for #55: typed synthetic ROS 2 observation/action contract

**Goal:** one deterministic, non-ROS-dependent proof that a mock perception state can be transformed into a typed action proposal for a **simulated** sink. Define versioned JSON schema(s); fixtures `valid`, `missing_camera`, `wrong_state_units`, `nan`, `late`, `replayed`, `stale_revision` as applicable. No `kubectl`, model weights or actuators. Separate schema validation from mock policy.

**Acceptance:** stdlib-first schema validator (or explicitly declared test dependency), reproducible fake policy output, negative tests that fail for wrong versions/fields, documented units and clocks. A valid JSON string alone is insufficient.

### W2 / PR for #59: deterministic reject-on-failure gate

**Goal:** consume W1 proposals and allow/deny only **simulated** dispatch. Enforce finite numbers, exact names/units, value bounds, observation TTL, monotonically advancing sequence/epoch, allowed task ids, authorization and per-action expiry. Reject no-op/hold behaviors explicitly; no implicit fallback to last remote action. Include partition/stale-response tests.

**Acceptance:** tests for TTL, clock skew assumptions, replayed seq, unauthorized model, bad units, failure closure, empty action, and no output side effect. Report actual test invocations; no claim that a simulated gate certifies physical safety.

### W3 / PR for #60: canonical run manifest and offline validation

**Goal:** minimal JSON Schema and validator for baseline/seed/source SHA/ROS/RMW/network/resource/model+dataset pins/rights/timestamps/raw-artifact hashes, with allowed **mock** case where model ids remain null. Connect to existing result-status registry #88 without inventing a second schema.

**Acceptance:** valid/invalid example manifests, negative tests, deterministic status; a static HTML animation and unreviewed model result must fail publication readiness.

## Wave 2 — first Hugging Face executable baseline

### W4 / PR for #58: immutable Hub artifact cache

**Goal:** offline-first `repo_id + exact commit revision + file hashes + license`; avoid floating `main` or unreviewed `trust_remote_code`. Optional download only in explicit user-run setup, not default CI. Validate cache miss/invalid hash/processor shape mismatch.

**Acceptance:** 100% of recorded HF runs point to immutable commit SHA; CI can test manifest parser with tiny synthetic fixtures and no network.

### W5 / PR for #74 and follow-up #94: read-only fault triage classifier

**Goal:** one deterministic family-held-out synthetic incident casebook, rules baseline, simple local lexical baseline, optional cached/pinned HF classifier. Jev adapter remains opt-in and **not** a required part of the science.

**Acceptance:** public split manifest, no leakage, per-class counts, macro-F1, abstention/coverage, p50/p95 latency, raw predictions and a reviewer-readable run artifact. No real remediation or `kubectl` mutation. Register validated results only after #88 review.

## Wave 3 — infrastructure/robot-learning integrations (separate PRs)

### W6 / PR for #56: LeRobotDataset v3 synthetic-action converter

Create/validate exactly one tiny dataset with synchronized **state, camera, action, timestamp and task**. Pin LeRobot release and validate round-trip by loading. Do **not** submit sensor-only rosbag as an action-policy training dataset. Optional Hub upload manual/permission-gated.

### W7 / PR for #61: compatible upstream remote inference server

Only after #57 bridge/embodiment compatibility and #55/#58/#59/#60; reuse upstream LeRobot Zenoh policy server and supported robot/policy contract. No new private RPC protocol. First test simulated client inside isolated local cluster, then measure packet-loss/jitter effects (#62/#96). Never attempt physical actuation.

### W8 / PR for #106: licensed perception benchmark

Start with a no-network fake adapter + annotations and metric tests; then optional pinned Grounding DINO/Depth Anything weights in permitted GPU/CPU environment. Separate relative depth from metric depth and preserve annotation rights.

### W9 / PR for #107: model-serving fairness simulator

Discrete-event CPU-only model-cache/queue simulation and baselines (FIFO/EDF/fair queue); after tests, optional GPU validation. Report worst-client deadline-success and distribution, not only aggregate throughput.

### W10 / research protocol for #104: safe task continuity

Define portable **high-level mission state**, lease epochs/fencing, read-only provenance receipts and simulated task sink. Do not confuse copying a container, model deployment, robot migration and task-state continuity.

## Copyable prompt for Claude Code / Codex (choose one issue only)

```text
Repository: MSKazemi/ros2-kubernetes-lab (public).
Read AGENTS.md, docs/README.md, docs/PROGRAM-ROADMAP-2026-2027.md,
docs/EXPERIMENT-PORTFOLIO.md and the full live GitHub issue before coding.
Work ONLY on issue #55 (typed synthetic ROS 2 observation/action + deterministic mock).
First inspect existing main and open PRs for overlapping changes. Do not duplicate
model-server, HF website or scenario implementations and do not rename the repo.
Respond first with: (1) current observed code/files, (2) minimal plan, (3)
input/output schema and safety boundary, (4) tests and expected acceptance,
(5) files that will change. Then implement only the accepted scope.

Requirements:
- CPU only; Python standard library preferred; no cloud, GPU, robot, secret or HF token.
- Versioned camera/state/action schema with units, shape/dtype, capture time,
  episode/sequence id, action expiration and allowlist.
- Fixed-seed synthetic fixtures and deterministic baseline; reject malformed inputs.
- Proposed actions go to a simulated sink only; no physical robot and no shell execution.
- Unit tests for valid and invalid cases, replay, deadline, NaN/inf, wrong units.
- Update adjacent docs and preserve historical Foxy/Vagrant examples.
- Give actual test commands/output, limits and compatibility state.
- Open a focused PR for human review. Never self-merge and never invent results.
```

For other issues, replace `#55` and the specific requirements with the relevant wave description. Do not paste general program text into dozens of issue bodies; link this file and the canonical experiment spec instead.
