# Contributing to the Jev Cloud–Edge Robotics Decision Lab

**Current status:** documentation/research proposal only; no Jev integration or benchmark results are available yet. The safest contribution is a small synthetic-data, offline, read-only research artifact. Start from the main [Jev overview](README.md).

Follow repository [AGENTS.md](../../../AGENTS.md), [CONTRIBUTING.md](../../../CONTRIBUTING.md), and [AI-assisted contribution walkthrough](../../AI_ASSISTED_CONTRIBUTING.md). Work on **one issue at a time**, propose approach and verification first, and keep humans responsible for reviewing diffs. Never autonomously push to main, merge a PR, run the ~30GB Vagrant cluster or contact a paid provider without explicit authorization.

## Contribution paths

| Level | Task | Issue / dependency | What counts as proof |
| --- | --- | --- | --- |
| Beginner | Review synthetic JSON, fault taxonomy, docs clarity and bad examples | [#73](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/73) | Verified JSON parsing + review of named paths |
| Beginner / Python | Offline deterministic incident classifier with `unknown` | [#74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74) | Offline unit tests, zero external calls |
| Intermediate | Typed schemas and sanitized optional Jev adapter | [#74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74), [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55) | Fake API response tests, timeout, 429, schema rejection |
| MSc | Experimental preregistration and dataset-leakage tests | [#75](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75), [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60) | Held-out manifest and reproducible analysis |
| PhD | Jev calibration, drift and abstention vs baselines | [#75](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75) | Predeclared metrics, raw data and uncertainty |
| Advanced | Simulator-only agent screening or placement | [#64](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64), [#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62) | Independent safety gate, network/sim test proof |

## One-issue contribution workflow

1. Read the live issue and its dependencies. Choose a bounded change and say whether you can run only static tests or have a full test environment.
2. Inspect adjacent docs/code; never assume a future directory or script already exists because a research proposal mentions it.
3. Write a short change plan: exact files, acceptance criteria, test matrix, failure behavior, provider/secret budget, and privacy implications.
4. Implement only that issue, preferably starting with an **offline** adapter and synthetic fixtures.
5. Test without network first. For Markdown, inspect relative links; for JSON, run `python3 -m json.tool FILE`; for scripts, run their relevant lint/tests. Static tests do **not** validate robotics deployment.
6. Have a human inspect the patch and PR with explicit "tested / not tested" notes. Never claim host cluster, vendor API, simulator, model quality, ROS 2 cross-worker delivery or physical safety without matching actual evidence.

## Copyable Claude Code / Codex prompt — first Jev PoC (#74)

```text
We are working on issue #74 in
https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment
Read AGENTS.md, the current issue description, and docs/ai/jev/README.md,
ARCHITECTURE.md, SAFETY-PRIVACY.md and GETTING-STARTED.md.
Treat proposed paths as NOT implemented unless files actually exist.
Plan a bounded offline-only ROS 2/Kubernetes incident triage example
with synthetic fixtures, typed input/output, an explicit unknown label,
and zero network access by default. Do not contact TypeSafe or other paid APIs.
Propose tests for contradictory evidence, malicious text in a log, stale
timestamps, absent credentials, unknown labels and unexpected responses.
Do not generate unrestricted kubectl/ROS actions or robot-control code.
Before editing, list files, acceptance criteria and verification commands.
After editing, show the diff, what actually ran and what remains untested.
Never autonomously push to main or merge. Human review is required.
```

## Copyable skeptical research-review prompt — #75

```text
Review this Jev benchmark proposal as a skeptical cloud robotics reviewer.
Read AGENTS.md, issue #75 and docs/ai/jev/BENCHMARK-PROTOCOL.md.
Find leakage between data splits, unbalanced baselines, missing errors,
inadequate abstention metrics, mislabeled vendor confidence, unverifiable
speed/cost claims, and any implied real robot or DDS success.
Check sample JSON and source links; flag all vendor APIs and parameters
that were not actually verified. Identify which proposed tests are offline
and which would require credentials or a paid service.
Do not edit, push, run cloud APIs or invent measurements. Give a prioritized
review checklist with exact file and issue references.
```

## Research contribution template

When opening an issue or PR, include:

- **Research question and null hypothesis:** narrowly falsifiable.
- **Input provenance:** synthetic or approved/licensed, label method and redaction confirmation.
- **Interfaces and trust boundaries:** which fields the model sees, which decisions code alone makes.
- **Baselines:** rules, local model or other justified comparator; fixed conditions.
- **Evidence:** seeds, source/model revisions, option order, replay steps, raw outcomes (including failures).
- **Verification:** exact tests run; test gaps; no unmeasured claims.
- **Privacy and approvals:** no credentials, personal data, physical actuation or irreversible operations.

Related: [Scenario catalog](SCENARIOS.md) · [Benchmark protocol](BENCHMARK-PROTOCOL.md) · [Safety and privacy](SAFETY-PRIVACY.md).
