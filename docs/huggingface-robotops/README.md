# Hugging Face × ROS 2 × Kubernetes × Jev — RobotOps research track

> **Planning + website implementation only (2026-10-27).** No LeRobot v3 dataset has been converted, trained/checkpointed SmolVLA policy evaluated, remote policy server deployed, Jev comparison measured, or live Hugging Face Space published by this work. These are designed experiments and static educational visualizations.

## One coherent research lab

**Hypothesis:** the Hugging Face ecosystem can provide reproducible public robotics **data, model and evaluation artifacts**, while ROS 2 and Kubernetes provide a future verified execution/infrastructure testbed, and Jev offers an optional, narrowly bounded *advisory* decision comparator. Neither Jev nor a Hugging Face policy is permitted to bypass independent deterministic safety controls.

**Separate roles, never conflate them:**
- **LeRobot/Hub:** dataset generation/validation, licensed model checkpoints, training/evaluation pipelines, model and dataset cards.
- **LeRobot remote inference:** upstream Zenoh-based policy server, supported action semantics and a compatible client; this is **not** proven equivalent to ROS 2 DDS networking.
- **Kubernetes:** optional isolated resource-managed model-serving environment once network, GPU/security, action-interface and simulator prerequisites are tested.
- **Jev:** separately hosted TypeSafe **System One** inference for structured advisory questions like incident class or eligible-placement qualitative ranking. It is not automatically hosted by Hugging Face or an actuator model.
- **GitHub:** source, experiment protocol, synthetic examples, CI, verified results and discussion.
- **Hugging Face Spaces/Collections:** public discovery and teaching presentations **after actual publication/verification**, not a substitute for scientific evidence.

## The new research pages

| ID | Scenario and research question | Entry level | Proposed HF tools | Contributor issue |
| --- | --- | --- | --- | --- |
| S5 | [LeRobotDataset v3 pipeline](../../site/scenarios/hf-lerobot-dataset.html): when must a ROS 2 episode fail semantic/rights checks before Hub publication? | BSc/MSc, hardware-free metadata | LeRobotDataset, HF Datasets, Dataset Cards | [#93](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/93) |
| S6 | [Jev vs HF classifier](../../site/scenarios/hf-jev-classifier.html): what is the accuracy/abstention/latency utility of a structured hosted model vs an open local text classifier? | MSc/AI systems, CPU baseline | Hub Models, local classifier, Jev, model card | [#94](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/94) |
| S7 | [SmolVLA/LIBERO](../../site/scenarios/hf-smolvla-libero.html): when is a pinned policy actually compatible and successful in a simulator? | MSc/PhD, GPU optional | LeRobot eval, SmolVLA, LIBERO, Hub checkpoint | [#95](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/95) |
| S8 | [HF remote inference](../../site/scenarios/hf-robotics-remote-inference.html): does remote GPU inference preserve valid action age under network faults? | PhD/Cloud/Robotics | LeRobot remote + Zenoh, Hub model cache, K8s, optional Jev | [#96](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/96) |

## Choose by interest

- **Student, no GPU, no robot:** take S5's synthetic episode/unit/permission exercises or S6's simple deterministic fault rules. Requires no HF token.
- **LLM/NLP student:** S6 compares rules, an open Hugging Face classifier and Jev `Choice` on the same family-grouped synthetic ROS 2 incidents. Hosted requests must be explicitly authorized and recorded.
- **Robot-learning researcher:** S7 specifies how to select a LeRobot version and compatible LIBERO model/dataset; raw simulation outcomes require actual simulator execution and compatible checkpoint.
- **Kubernetes/edge researcher:** S8 builds toward a secure LeRobot remote-policy server and network impairment measurements, on a simulator first.
- **Frontend/reproducibility contributor:** work on the [Static Space starter](../../integrations/huggingface/spaces/robotops-research-explorer/) / [#98](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/98), or [model/dataset cards and manifest](../../integrations/huggingface/templates/) / [#99](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/99).

## Navigation / planning

- [Epic #92 — HF + Jev RobotOps research](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/92)
- [Original Cloud Robotics animated site epic #83](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/83)
- [Capabilities and trade-offs](CAPABILITIES.md) · [Trust-boundary architecture](ARCHITECTURE.md) · [Experiment sequence](EXPERIMENTS.md) · [Space publication](SPACE-PUBLICATION.md) · [Claude Code/Codex playbook](AGENT-PLAYBOOK.md)
- Existing prerequisites: [#56 dataset v3 conversion](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/56), [#57 compatibility audit](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57), [#58 immutable Hub artifacts](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/58), [#59 safety gate](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59), [#60 reproducible run manifest](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60), [#61 LeRobot remote server](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61), [#62 network impairment](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62), [#68 public HF visibility](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/68).
- The base website and four original Jev scenarios remain in **draft PR #90**; this HF addition is prepared as a separately reviewed **stacked PR**. Do not claim pages are live until upstream PRs are merged and Pages publishing verified.

## First practical workflow without any HF account

1. Open the [scenario gallery](../../site/scenarios/index.html) via a local HTTP server or inspect the source.
2. Follow the S5 or S6 synthetic cases. Explicitly mark which facts are fabricated, insufficient or inconsistent.
3. Pick one contributor issue; inspect current code and dependencies, agree on a small scope and acceptance tests.
4. Use the offline rule/parser baseline, data contracts and sample manifests **before** any model download or API call.
5. Run static site/docs/JSON tests. A successful static check only proves those aspects, **not** LeRobot runtime or result correctness.

Site preview from the repository root (once site branch is checked out):

```sh
python3 -m http.server 8000 --directory site
# http://localhost:8000/scenarios/
python3 scripts/validate-site.py
node --check site/assets/hf-scenarios.js
```

## Community quality and safety

Public repository: never commit private videos, robot location/network details, tokens, kubeconfigs, restricted weights, sensitive datasets or participant observations. Dataset redistribution requires license/permission; physical robotics and human-subject studies require qualified, independent safety/ethics controls. A high model confidence is never authorization to actuate.

**Research publication gate:** only real runs with source/model/dataset immutable revisions, raw failures, script, seeds, measured metric units, limitations and independent human review may replace N/A with numbers on the results board.
