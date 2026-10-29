# TEMPLATE — Hugging Face RobotOps classifier or VLA policy model card (NOT PUBLISHED)

> **No model is trained, evaluated, or hosted by this template.** Do not add fake benchmark results, model-index performance metadata or incompatible HF license tags. Publish only when an actual legal artifact and accurate evidence exist.

## Model identity and release

- **Exact HF Model repo:** NOT_CREATED
- **Immutable model revision / checkpoint SHA:** NOT_AVAILABLE
- **Base model / original copyright and license:** NOT_REVIEWED
- **GitHub source + image digest:** NOT_AVAILABLE
- **Processor/tokenizer/camera normalization and version:** NOT_SELECTED
- **Associated training Dataset Hub ID + exact immutable revision:** NOT_AVAILABLE

## Task and intended use

Specify **one** supported use: bounded ROS 2 incident *text classification*, or an embodiment-compatible VLA simulator policy. They require very different contracts; do not claim that an incident classifier generates robot actions or that a VLA model is safe for arbitrary hardware.

## Model inputs/outputs and limitations

For a text classifier: normalization, fault classes, unknown/OOD handling, tokenizer version, probabilities and calibration. For a VLA: task, embodiment, camera configuration, state/action dimensions, physical units and frames, action chunk semantics, processor mappings, supported inference mode/driver, controls for off-policy behavior.

Document supported ROS 2/LeRobot/K8s versions only **where actually tested**; distinguish simulator from real robot; list known inappropriate applications and failure modes.

## Training and datasets

Data license/provenance, split design, training method, versions, random seed, device/VRAM, hyperparameters, compute and privacy controls. If there is no training, say so explicitly (do not invent fine-tuning).

## Evaluation

| Metric | Actual measured value | Evidence URL |
| --- | --- | --- |
| Primary endpoint (declare unit) | NOT_MEASURED | NOT_AVAILABLE |
| Class-specific or task-specific score | NOT_MEASURED | NOT_AVAILABLE |
| Hosted/client latency and failures | NOT_MEASURED | NOT_AVAILABLE |
| OOD/abstention or model compatibility errors | NOT_MEASURED | NOT_AVAILABLE |

Method, denominators, error cases, confidence intervals, task splits, input preprocessing and exact raw evidence are required. A plausible demonstration or model download is not evidence.

## Ethics, limitations, governance

Use synthetic/approved data and independently audited licenses; keep confidential footage, participant data, robot addresses and credentials private. Do not claim a robot action is safe because an LLM/decision model approved it. Model cards do not certify physical hardware.

## Final publication review

- [ ] Exact model/processor/data commits pinned; no mutable `main` or unspecified revision in reproducibility records.
- [ ] Source rights and license valid and reviewed.
- [ ] Actual model artifact exists and can be loaded with named compatible dependencies.
- [ ] Evaluation has raw runs and statistical methods, including failures.
- [ ] No invented URLs, GPU use, accuracy or physical robot operation.
- [ ] Maintainer approves public HF upload and README/card metadata.

Until then **STATUS: TEMPLATE / NOT_PUBLISHED**.
