# Hugging Face model discovery for ROS 2 / Kubernetes robotics

**Research catalog, reviewed 2026-10-28. No model has been deployed or benchmarked by this document.** This is an initial *shortlist*, not a live HF inventory or endorsement. Upstream model cards and licenses can change. Always review the exact checkpoint repository and pinned 40-character commit, processor and related data before downloading.

## First integrations to evaluate

| HF model ID | Category | Experimental question | Proposed lane | Risk / prerequisite |
| --- | --- | --- | --- | --- |
| [lerobot/smolvla_base](https://huggingface.co/lerobot/smolvla_base) | VLA base policy | Does remote policy placement beat local inference **after accounting for fresh and valid simulated actions**? | optional GPU simulator | Requires task-specific adaptation and aligned cameras, state/action units, embodiment, action FPS |
| [lerobot/xvla-base](https://huggingface.co/lerobot/xvla-base) | Cross-embodiment VLA base | How much adaptation do different simulated embodiments require? | advanced GPU research | Soft-prompt/domain adaptation; not drop-in any robot |
| [lerobot/xvla-libero](https://huggingface.co/lerobot/xvla-libero) | LIBERO-specific policy | Reproduce a pinned LIBERO reference and compare under controlled perturbations | simulator-only GPU | Verify exact LeRobot/LIBERO environment, control mode and supported processor |
| [lerobot/pi05_libero_base](https://huggingface.co/lerobot/pi05_libero_base) | Larger LIBERO-specific VLA | What are task completion, inference and resource tradeoffs against smaller policies? | high-resource GPU, optional | Large checkpoint; gated PaliGemma tokenizer and model license requirements; no default CI download |
| [IDEA-Research/grounding-dino-tiny](https://huggingface.co/IDEA-Research/grounding-dino-tiny) | Text-grounded detection | Is the remote detector useful after image transfer/latency and outage cost? | perception demo, CPU/GPU optional | Bounding boxes are **not** motion commands; document label prompts and image policy |
| [depth-anything/Depth-Anything-V2-Small-hf](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf) | Monocular relative depth | Does edge vs remote relative-depth inference improve a simulated perception task? | perception demo | Do not present relative depth as metered navigation distance without calibration |
| [facebook/sam2-hiera-small](https://huggingface.co/facebook/sam2-hiera-small) | Image/video segmentation | Segmentation continuity under dropped frames and edge/cloud placement | advanced perception | Check model license, tracker state and GPU requirements before use |

For a first reproducible *real policy* experiment, prefer a task-matched checkpoint and benchmark (e.g., pinned LIBERO policy + LIBERO environment) over loading a generic foundation/base model and assuming valid task actions. The no-GPU first lane should run a **deterministic mock policy** and document its limits rather than claim SmolVLA operates in real time on CPU.

## Why this is not a single plug-and-play model catalog

- **Perception** models return boxes, masks or relative depth. They do not produce robot actuator commands.
- **Action policies** return model-specific action representations, often chunks requiring normalization, camera/state mapping, units, FPS, task and embodiment validation.
- A remotely hosted model that returns syntactically valid vectors may still be physically unsuitable. Simulator-only action and independent safety gate first.
- A model card might describe a paper's upstream performance. Those numbers are **not measurements of this lab** and must not populate our results registry.
- LeRobot remote inference uses its documented Zenoh-based policy transport; this does **not** demonstrate ROS 2 DDS discovery between Kubernetes workers.
- Kubernetes throughput, HTTP timings or successful image builds alone cannot prove robotic task success or valid action freshness.

## Machine-readable catalog and offline integrity check

The **planning-only** source manifest is [integrations/huggingface/model-catalog.json](../../integrations/huggingface/model-catalog.json). Its seven model entries deliberately have null revisions and null results; they **cannot** be used for a publishable model run without separate exact model and processor commit pinning.

From repository root:

~~~sh
python3 scripts/validate-hf-model-catalog.py --self-test
python3 scripts/validate-site.py
~~~

The first command checks candidate metadata, no manufactured results, exact static model links and five negative mutations. This does not download weights or test HF model compatibility. The GitHub Pages PR workflow runs it without credentials or GPU. Follow up in [perception issue #106](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/106) and [model-serving fairness issue #107](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/107).

## Mandatory immutable experiment manifest

Record: source Git SHA; image digest; HF model repository **and immutable commit**; processor/config hashes; dataset repository+revision and license; robot/camera/action schema (names, units, action order); simulator and LeRobot version; random seeds; hardware; action FPS; transport and network profile; metric implementation and raw trace path; limitations and human reviewer.

Start from #58 (artifact pinning), #60 and #88 (evidence), #55/#59 (typed simulated safety gate), #57 (compatibility), #61/#62/#96 (remote inference and impairment). Do not create a competing artifact schema. Do not expose HF tokens or send private ROS camera data to providers.

## Demonstrations and baselines

**Lane A: CPU, offline, hardware-free**
1. Deterministic synthetic observation/action fixture, strict schema and invalid-shape/unit negative tests.
2. Scripted bounded baseline for edge/remote roundtrip and fault-injection; label values as *synthetic*.
3. Static model gallery and read-only HF Space (future #98); no API key or model run implied.

**Lane B: real perception, opt-in**
1. Exact model/processor pin and vetted reusable image fixture with license.
2. Grounding DINO boxes and Depth Anything relative depth are reported separately.
3. Vary CPU/GPU, image size, JPEG encoding, network jitter/loss, deadlines and privacy settings.
4. Publish precision/recall if a labeled reference exists, plus p50/p95/p99 *sensor-to-result* times and missing-frame rate; no fabricated scores.

**Lane C: compatible VLA simulator, opt-in GPU**
1. Choose **one** verified policy/dataset/simulator match and prove a single deterministic rollout.
2. Compare local inference, supported same-host asynchronous mode, and supported upstream LeRobot remote inference *only when compatible*.
3. Inject packet loss, jitter, disconnect and inference server restart; use authoritative local freshness/hold gates.
4. Measure p50/p95/p99 source-to-valid-action age, deadline misses, task success across seeds, GPU allocation and cost. Publish negative cases.

**Lane D: research follow-up**
Cross-embodiment evaluation of X-VLA, uncertainty-aware fallback, multi-robot GPU fairness, model-version rollouts, or language-goal diagnostics. Separate published hypotheses from measured results.

## Primary upstream sources checked

- SmolVLA: https://huggingface.co/docs/lerobot/main/smolvla
- X-VLA and checkpoints: https://huggingface.co/docs/lerobot/xvla
- LIBERO: https://huggingface.co/docs/lerobot/main/libero
- π₀.₅: https://huggingface.co/docs/lerobot/pi05
- Remote inference and current transport: https://huggingface.co/docs/lerobot/main/remote_inference
- HF Hub model cards: https://huggingface.co/docs/hub/model-cards
- Local related epic: https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/92

**Research integrity:** no models, checkpoints, Spaces, generated policies, measured scores or domain registrations were created during this catalog review.
