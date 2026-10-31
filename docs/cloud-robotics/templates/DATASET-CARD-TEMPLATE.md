# Dataset card template — Cloud Robotics + AI Lab

> **Template only: do not publish unchanged.** To use with Hugging Face Hub, create an actual dataset repository only after consent/license review. [Hugging Face dataset card guide](https://huggingface.co/docs/hub/datasets-cards) explains metadata and publication format.

## Basic metadata (fill before release)

- **Dataset name / intended Hub repo ID:** TBD
- **Maintainers and version / immutable commit:** TBD
- **License with redistribution permission:** TBD; no publication while unknown
- **Origin:** simulated deterministic generator / named public licensed dataset / explicitly approved research collection
- **Content:** named observations, action labels, task IDs, episodes, frame rate, per-camera videos and low-dimensional state data
- **Source robot/simulator and embodiment:** TBD
- **ROS distro, message schemas, coordinate frames, calibration and clocks:** TBD
- **LeRobotDataset v3 API/version and loader proof:** TBD
- **Split strategy, episode counts, action distribution, sampling assumptions:** TBD
- **Data card review (name/role/date, no private signatures):** TBD
- **Public release decision and date:** TBD

## Intended uses

Describe compatible research tasks and allowed analyses, with a concrete example. **Do not** claim a synthetic dataset teaches useful real-world robot control or supports arbitrary VLA checkpoints.

## Not intended for

Real-world safety-critical motor control, biometric surveillance, covert human monitoring, unverifiable generalized autonomy, face/voice identification, or undocumented industrial site use.

## Collection, consent and rights

- Are all frames synthetic? If not, what human/scene rights and institutional approvals exist?
- Which sensors include faces, voices, children, bystanders, homes, facilities or proprietary site maps?
- Is the author legally able to redistribute each video and model artifact under the selected license?
- What is the intended retention/deletion procedure? Are raw/redacted versions clearly separated?
- Are contributors and participants adequately informed (where applicable)?

## Structure and feature semantics

| Feature | Shape/dtype | Units | Source / frame | FPS or sampling | Required |
| --- | --- | --- | --- | --- | --- |
| Observation camera | TBD | pixel/encoding | frame + calibration | TBD | Yes if vision policy |
| Robot state | TBD | per-joint named units | simulator/robot | TBD | Yes |
| Action targets | TBD | ordered units | supported action space | TBD | Yes for action training |
| Task instruction | string/ID | N/A | task manifest | per-episode | If task-conditioned |
| Timestamp | integer/float | explicit ns/s | clock source | per frame | Yes |
| Episode ID and bounds | ID | N/A | data manifest | per-episode | Yes |

A sensor-only ROS bag is not automatically valid LeRobot training data. Document missing action labels and do not fabricate them.

## Processing and quality controls

Conversion program/source commit, dependency lockfile, checksums, clock-sync/align tolerance, missing-frame policy, duplicates, normalization statistics, camera calibration and LeRobot v3 round-trip check. Include **deliberately failing** samples and test output.

## Known limitations, potential bias and risks

Lighting, embodiment, actuator ordering, class/object coverage, simulation-reality gap, action label errors, privacy risks, data imbalance, unsafe uses, quality defects and evaluator uncertainty. Describe identified gaps, not speculative broad claims.

## Reproduction and contact

Exact conversion/validation command after implementation, read-only demo, SHA/source evidence, environment and report issue path. For private security concerns refer to repository SECURITY.md.

**Review gate:** [Ethics/safety policy](../ETHICS-SAFETY-AND-GOVERNANCE.md), [dataset integration issue #56](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/56). No actual dataset or license approval is inferred by filling the template.
