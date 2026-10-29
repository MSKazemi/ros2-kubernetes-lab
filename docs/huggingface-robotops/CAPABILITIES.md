# Hugging Face capabilities: what this repository can responsibly use

> **Current capability map, not a verified integration inventory.** Verify current HF documentation, account entitlements, supported LeRobot release, and model/dataset licenses at implementation time.

| HF tool/platform | Intended use in this lab | Typical first deliverable | Key limitations |
| --- | --- | --- | --- |
| **Hub Datasets & Viewer** | Share approved robotics episodes, incident classifications, split/license/semantic metadata | Synthetic dataset card and read-only metadata sample | Private/unknown-licensed recordings cannot be uploaded; Viewer support depends on data structure |
| **LeRobotDataset v3** | Record/load/replay versioned robot observation/action episodes with Parquet/video/metadata | Converter design and official loader round-trip (#56/#93) | Validate camera/action units, episodes and version; a JSON manifest alone is **not** a v3 dataset |
| **Hub Models & Model Cards** | Reference compatible VLA/classifier checkpoints, processors, intended use and evaluation | Model card template and exact revision manifest (#58/#99) | Hub availability is not proof of policy/task compatibility, nor any task-success result |
| **LeRobot / SmolVLA** | Optional fine-tuning and task-conditioned action-chunk policy research | Model/dataset compatibility matrix (#95) | Base model often needs task-specific data, compatible cameras/action schema and GPU |
| **LeRobot LIBERO / benchmarks** | Evaluate a compatible policy on seeded simulated manipulation tasks | Actual `lerobot-eval` run manifest and per-task outcomes (#95) | Simulator, model processor/control modes and licensing must match; no physical robotics claim |
| **LeRobot remote inference** | Test a compatible pinned policy across a verified network and server/robot-side contract | Mock admission/timeout matrix then isolated policy server (#61/#96) | Uses **Zenoh**, not an automatically working ROS 2 DDS bridge; position-hold/session semantics and security are non-optional |
| **Hugging Face Spaces** | Publish attractive student-facing, safe read-only demos | Static HTML Space starter in this repository (#98) | Static Space offers browser JS, **not private server-side secrets**; Gradio/Docker, GPUs and always-on hosting may require paid plan/hardware |
| **HF Collections** | Group paper, verified dataset, model and Space into a discoverable research collection | Publication checklist (#99) | Do not invent a live Collection/model/dataset URL |
| **HF Inference Providers** | Optional, separately chosen text-classification/other available model baseline | Costed experimental client if a compatible model/task is offered | Not automatically a robotics motor policy service or Jev host; model/provider/task availability and billing vary |
| **HF Jobs** | Optional paid, isolated CPU/GPU batch conversion/training/evaluation | Preapproved pinned job recipe with budget, output and logs | Job is remote compute with usage charges and secret management; no auto-run in CI |

## First three worthwhile Hugging Face publishing paths

**A. Dataset** — once issue #56 produces actual valid licensed v3 data, upload the dataset repo with a complete dataset card, exact pinned revision, dataset format/version, episode task/feature map and demo-only caveat. A toy JSON record is not an HF LeRobotDataset.

**B. Model** — only if a *real* trained/tested classifier or policy exists and license permits publication. The model card includes base model, tokenizer/processor, dataset provenance, supported embodiment/camera/action semantics, evaluation, limitations and evidence. Do not upload arbitrary model weights for discoverability.

**C. Space** — copy the static educational starter into an HF Space owned by the authorized user. The Space illustrates published/non-published research statuses and links back to GitHub issues; it does **not** call hosted models or control robots. Only then add its *actual* URL to the website/Hub Collection and optionally embed it in a crawler-friendly page.

## Separating research components

- **TypeSafe Jev is separate from HF:** comparing Jev with HF classifiers does not mean Jev is an HF model, an Inference Provider, a VLA checkpoint or a direct replacement for deterministic safety policy.
- **Jev Choice vs HF text classifier:** valid comparative study on *the same* labeled synthetic incident task (S6). Classifier must actually be trained/adapted to the intended classes.
- **HF VLA policy vs Jev:** a VLA outputs action chunks for a supported embodiment; Jev can only give high-level advisory classification/placement, not trajectories, deadlines, collision constraints or safety decisions.
- **HF Hub vs Kubernetes:** the Hub stores/distributes immutable artifacts; a secure Kubernetes workload (if implemented) actually serves/executes model code. A Hub checkpoint URL alone does not launch a worker.
- **Spaces vs Jobs:** a Space is a presentational/interactive app; Jobs are separately started and potentially billable batch compute. Neither should receive sensitive real robot data from a public website.

## Resource budget and research access

- CPU-only static docs and synthetic contract tests are the **default** and require no HF token.
- A Static Space is publicly documented as available without compute hosting charges; check the currently applicable account rules before creation.
- Treat Inference Providers, Jobs, GPU Spaces, cloud VMs and physical equipment as **opt-in paid** experiments, not promised free capacity. Record cost estimate, hard cap, relevant hardware, quota and cancellation/cleanup.
- Never put access tokens/TypeSafe API keys into a Static Space or a client-side GitHub Pages script. Server-backed secrets only where a separate backend has been approved and reviewed.

## Official references

- LeRobot: https://huggingface.co/docs/lerobot/main
- LeRobotDataset v3: https://huggingface.co/docs/lerobot/main/api/datasets
- LIBERO: https://huggingface.co/docs/lerobot/main/libero
- SmolVLA: https://huggingface.co/docs/lerobot/main/smolvla
- LeRobot remote: https://huggingface.co/docs/lerobot/main/remote_inference
- Spaces: https://huggingface.co/docs/hub/spaces-overview
- Static Spaces: https://huggingface.co/docs/hub/spaces-sdks-static
- Model cards: https://huggingface.co/docs/hub/model-cards
- Dataset cards: https://huggingface.co/docs/hub/datasets-cards
- Collections: https://huggingface.co/docs/hub/collections
- Jobs: https://huggingface.co/docs/hub/jobs-overview
- Inference Provider pricing: https://huggingface.co/docs/inference-providers/pricing
