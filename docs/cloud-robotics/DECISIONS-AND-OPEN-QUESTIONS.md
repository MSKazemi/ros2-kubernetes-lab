# Design decisions, proposed ADRs and review questions

> **Discussion aid:** decisions below are *proposed defaults*, not verified runtime choices or permission to publish/actuate. Maintainer/issue review, exact compatibility tests and license/safety screening control the outcome.

## D-01 Program naming (proposed)

**Recommended visible research track:** **Cloud Robotics + AI/LLM Lab**; optional **RobotOps Lab** shorthand for deploy/observe/benchmark teaching. Keep existing canonical repository name until [#22](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/22) is deliberately decided. Repo slug proposal `ros2-kubernetes-lab` improves ROS/Kubernetes discoverability; adding AI only to the display/tagline avoids overpromising that the legacy code already supports it.

**Alternatives:** `cloud-robotics-lab` (broad, less exact ROS/Kubernetes search intent), `robotops-lab` (memorable but ambiguous); use dual branding carefully, do not fork overlapping repos prematurely.

## D-02 Flagship educational example (proposal)

**Select:** deterministic synthetic camera + joint state + action target + task/episode ID using CPU-only mock policy and a strict simulator-only gate.

**Why not begin with:** full humanoid, self-driving robot, Nav2 autonomy, real arm/teleop, multi-robot fleet or GPU VLA model. These add incompatible embodiment/actions, compute budgets and real-world hazards before the message/measurement baseline is reliable.

**Gate to revisit:** verified small ROS-to-policy contract and licensed fixture with LeRobotDataset v3 roundtrip; then evaluate one compatible real policy/simulator pair.

## D-03 Small deployment profile (undecided)

**Alternatives:** kind, k3d, and legacy Vagrant; benchmark *two distinct worker* delivery, supported CNI/discovery, CPU/memory footprint and reproducible setup/teardown on documented Linux host. Do not assume all modes support the same multicast or advanced ROS traffic. Choose only after actual #15/#16 tests.

## D-04 ROS middleware and policy inference are separate (proposed architecture)

ROS 2 DDS/RMW delivery is first research network. A ROS-specific Zenoh bridge is a controlled alternative in #48, not an unverified automatic replacement for DDS. LeRobot remote inference's own Zenoh endpoints/action chunks form another path and require their own identity/auth/freshness semantics. Document all three explicitly.

## D-05 Hugging Face model and bridge (undecided)

Candidates include community ROS 2 LeRobot bridges and SmolVLA. **Decision criterion:** exact pinned upstream version + license + compatible camera/state/action/processor, simulated embodiment, optional GPU requirements and negative mismatch tests. A model that loads but outputs misaligned actions must be rejected. No requirement that the first student lesson use SmolVLA.

## D-06 Agentic AI role (proposed)

Start with **read-only diagnostic RAG**. A subsequent natural-language planner may propose **typed allowlisted simulator skills** under deterministic validation and approved execution; never let LLMs issue raw actuator/velocity commands, arbitrary shell or unrestricted Kubernetes writes. Claude Code/Codex remain contributors' coding tools, not the robot policy.

## D-07 Data publication (proposed)

Public repo contains synthetic/license-reviewed fixtures and explanatory results; HF public dataset/model/Space are separate publication actions requiring license, consent/security and reviewer decision. Hub files are immutable-pinned for reproducibility. No private laboratory/worker images, faces/voices or credentials may be published by default.

## D-08 Research success definition (proposed)

Passing a build or policy handshake does not mean task success. Use a graded R0–R3 evidence maturity record; require independent reruns, raw failures and exact artifact identifiers for benchmark claims. For metrics, compare valid **observation-to-action freshness** and simulator outcomes, not just API throughput.

## D-09 Real robot pathway (deferred)

Physical robotics is **not an early phase**. Separate institutional review, legal/safety engineer, qualified operator, independent safeguard/control plane, permits and a validated site-specific policy are mandatory before even proposing a physical trial. A software "simulator hold" and cloud restart policy have no certification value.

## Questions that matter for the next engineering decision

1. Which licensed, readily runnable simulated robot/fixture can generate *aligned action labels*, not merely camera data, on ordinary CPU hardware?
2. Which kind/k3d version + CNI/discovery choice passes an independently rerun two-worker ROS test on documented hardware?
3. Which exact LeRobot release, third-party bridge and *task-compatible* policy/checkpoint can run under the selected simulator with known action units?
4. Should the first interactive public demo be a read-only local static figure viewer, or a Hub Space backed by genuinely public run artifacts?
5. What externally reviewable evidence is needed before a research claim or course lesson moves from proposal to supported?
6. Which of placement reliability, LLM skill authorization or dataset provenance has a defensible research novelty after related-work review?

**Proposed decision process:** open a small dated ADR with chosen option, rejected alternatives, evidence, test/run link, privacy/license note and rollback. Then update documentation and acceptance criteria. Do not infer answers from broad promises or tie them to arbitrary fixed dates.

## Changelog

- **2026-10-27:** Initial discussion record prepared alongside 16 granular AI/LLM/cloud-robotics proposal issues. No simulator, model evaluation, cloud run, web page or production robot capability has been implemented by this decision log.

