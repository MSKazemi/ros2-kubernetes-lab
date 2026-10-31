# Model / robot-policy card template

> **Template.** Use with the [Hugging Face model card guidance](https://huggingface.co/docs/hub/model-cards); do not claim a checkpoint is compatible with a robot based solely on its popularity or a successful import.

## Identity and provenance
- Model name and upstream HF repo: TBD
- Exact immutable **model revision**: TBD
- Processor/tokenizer/config revision: TBD
- Original model card and research citation: TBD
- License, restrictions and expected use: TBD
- Container digest, LeRobot version and dependencies: TBD
- Training dataset identities and exact revisions, rights assessment: TBD
- Evaluation artifact and result-maturity level (R0–R3): TBD

## Contract and embodiment compatibility

| Property | Required documented value | Verified? |
| --- | --- | --- |
| Robot/simulator identity | ___ | No |
| Number/order/names of actuators | ___ | No |
| Action units, bounds and update FPS | ___ | No |
| Camera names, resolution, channels, calibration | ___ | No |
| State feature names/dtypes/shapes/units | ___ | No |
| Task or language feature contract | ___ | No |
| Processor/postprocessor and normalization | ___ | No |
| Policy inference mode, chunk horizon and server API | ___ | No |
| Remote admission/endpoint/authentication | ___ | No |
| Supported CPU/GPU, VRAM and time budget | Measured, not assumed | No |
| Client fallback/timeout/action gate | Simulation only until qualified review | No |

## Intended uses / known prohibited uses
Specify the named simulator and tasks actually evaluated. **Prohibit claiming** suitability for unsupervised physical motion, safety-rated applications or arbitrary ROS 2 topics. Document limitations for unseen observations and mismatch cases.

## Validation levels (report each independently)
1. Artifact hash, license and loader success.
2. Observation/action schema contract and invalid-input failure tests.
3. Simulated validator gate, stale/error conditions and complete logs.
4. Measured compatible simulator task success with independent trials.
5. Real robot physical safety review **separate and out of initial project scope**.

## Risks and mitigations
Wrong coordinate frame, calibration, stale observations, model-server overload, action chunk starvation, prompt injection if language-conditioned, biased training data, license risk, external code execution, remote endpoint credentials, domain shift, unsafe fallback. Name the real control that blocks each and the test evidence.

## Performance and reproducibility
List actual run IDs/paths, model/dataset image digests, CPU/GPU environment, FPS, network profile, raw latency distribution, task outcomes, failures, variance, comparator policies, clock assumptions and regeneration script. A model card must not include synthetic placeholder numbers as findings.

## Review and release
Model owner / public role, reviewer, review date, approved simulated scopes, external security/ethics dependencies, next review trigger and rollback/disabling method.

**Reference:** [LeRobot plan](../HUGGINGFACE-INTEGRATION.md), [#57 compatibility audit](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57), [#61 remote inference](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61).
