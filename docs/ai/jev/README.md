# Jev + ROS 2 + Kubernetes — Cloud–Edge Decision Intelligence Lab

> **Status (2026-10-27): research design and documentation only. No Jev adapter, benchmark, runtime demo, robot actuation, or integration test has been implemented by these documents.**
>
> This is an independent educational experiment in the [ROS 2 on Kubernetes Lab](../../../README.md), **not** an official TypeSafe project or an approved safety-critical robot controller.

## Research goal

Study **when a narrow, probabilistic decision model is useful alongside deterministic software, robot middleware and generative agents**. Jev, TypeSafe AI's System One model, returns typed judgments about supplied state rather than free-form generated text. A bounded `Choice` can suggest a diagnosis, `Score` can describe graded urgency, and `Noul` can estimate a yes/no proposition. Results are **advisory**; code, human review and independent safety controls remain authoritative.

**Three questions:** Can Jev improve incident triage quality? Is that improvement worth hosted API latency/cost? How robust are classifications to ambiguity, untrusted logs and changing decision criteria?

This repo's Vagrant/Foxy/Kubernetes 1.29 configuration is historical. The Jazzy image's same-container message smoke test does **not** demonstrate cross-node DDS or a robotics fleet. The experiments below start with **synthetic read-only incidents** and do not require those unverified capabilities.

## Start here

| I am a ... | Read first | First safe activity |
| --- | --- | --- |
| Student / beginner | [Getting started](GETTING-STARTED.md) | Check two synthetic JSON examples locally; design one fault class |
| ROS 2 / K8s engineer | [Architecture](ARCHITECTURE.md) | Review event normalization and independent policy boundaries |
| MSc / PhD researcher | [Benchmark protocol](BENCHMARK-PROTOCOL.md) | Preregister a hypothesis and an offline rule baseline |
| AI/LLM researcher | [Scenario catalog](SCENARIOS.md) | Evaluate Jev as an advisory reviewer of high-level agent proposals |
| Industry / safety reviewer | [Safety and privacy](SAFETY-PRIVACY.md) | Threat-model data sharing, failures and human oversight |
| Contributor using Claude Code/Codex | [Contributor guide](CONTRIBUTOR-GUIDE.md) | Work on one issue and request a skeptical diff review |

**Examples (no code execution):** [Synthetic ROS 2 incident](examples/synthetic-incident.json) · [Illustrative official API request](examples/jev-choice-request.json). The example request is **not** a stored model answer or evidence of model accuracy.

## Where Jev belongs (and where it does not)

`synthetic ROS 2/K8s evidence → source checks + redaction → optional Jev inference → typed advisory result → deterministic policy + review → read-only diagnostic UI / experiment record`

Jev belongs at the **supervisory/decision-support layer**, never in emergency stop, raw actuator, hard-real-time, or unbounded autonomous command loops. No Jev answer can grant Kubernetes permissions, bypass the simulator action gate or override resource/latency limits.

Current vendor access is a hosted API that requires credentials and may incur costs. The **offline baseline** will work without a Jev account once issue [#74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74) is implemented; it is **not present today**.

## Eight proposed research scenarios

| Priority | Scenario | Jev primitive | Proposed measurement | Delivery |
| --- | --- | --- | --- | --- |
| P1 | ROS 2 / Kubernetes fault triage | Choice + optional Noul | Macro-F1, abstention, cost | [#74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74) |
| P2 | LLM-proposed simulator skill screening | Choice / Noul | Unsafe-proposal recall + reviewer workload | [#64](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64) |
| P2 | Edge vs cloud inference placement advice | Choice | Task outcomes, eligible-placement regret | [#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62) |
| P2 | Observability alert grouping and routing | Choice / Score | Incident triage quality | Proposal |
| P3 | Multi-robot simulated task candidate ranking | Choice | Fairness and task completion | [#69](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/69) |
| P3 | Hugging Face policy candidate review | Choice / Score | Compatibility errors and review agreement | [#57](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57) |
| P3 | Maintenance advisory classification | Choice / Noul | Recall and false-alarm burden | Proposal |
| P3 | Policy-server capacity review | Score / Choice | Queueing, workload cost | Proposal |

See [Scenarios](SCENARIOS.md) for event contracts, baselines, constraints and research hypotheses. All items are **proposals**, not available product features.

## First vertical slice: fault triage

1. Specify synthetic, non-identifying incident types: `dds_discovery`, `qos_mismatch`, `network_connectivity`, `resource_pressure`, `healthy`, and `unknown`.
2. Build a deterministic, offline rule baseline and fixed input/output contracts (**issue #74**, not yet implemented).
3. Add a **separate, explicitly opt-in** Jev provider using the [official API](https://docs.typesafe.ai/api/system-one) or [Python SDK](https://docs.typesafe.ai/sdk/python).
4. Keep exact timestamps, counters, authorization, network/resource eligibility and all enforcement **in code**.
5. Benchmark against the offline baseline on held-out synthetic incidents; report all errors, latency, model revision, option order, costs and uncertainty (**issue #75**).

Use the [Getting started](GETTING-STARTED.md) page to validate the example JSON without any service account.

## Evidence and dependency ladder

| Area | Verified in this repository today? | Requirement before a claim |
| --- | --- | --- |
| Jev-specific documentation and static example requests | Documentation proposed in this change | Review Markdown/JSON and official references |
| Offline Jev-comparator baseline | **No** | Implement and test issue #74 |
| Live Jev classification | **No** | Opt-in integration, provider credentials and response validation |
| Experimental Jev-vs-LLM results | **No** | #75 and #60 reproducibility checks |
| Cross-worker ROS 2 / DDS | **Not validated** | #14 / #15 / #16 |
| Actuation or robot safety | **Not supported** | Separate certified design/review beyond this lab |

## Source documents, roadmap and attribution

- [TypeSafe introduction](https://docs.typesafe.ai/introduction), [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul), [API](https://docs.typesafe.ai/api/system-one).
- [Known Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13): math, timestamps, option order, adversarial input and overly broad state need independent handling.
- [Architecture](ARCHITECTURE.md) · [Scenarios](SCENARIOS.md) · [Benchmark protocol](BENCHMARK-PROTOCOL.md) · [Safety/privacy](SAFETY-PRIVACY.md) · [Contribute](CONTRIBUTOR-GUIDE.md).
- Planning: [#73 Jev umbrella](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/73), [#74 offline PoC](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74), [#75 evaluation](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75).
- Related work planned elsewhere in this repo: [#72 general Cloud Robotics/AI docs PR](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/pull/72) and [#63 GitHub Pages site PR](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/pull/63). These are **not** proof of shipped Jev support.

**Brand and data integrity:** TypeSafe and Jev are their owners' names/marks. Do not imply sponsorship. Never commit API keys, unlicensed images, physical robot locations, private user logs or invented benchmark results.
