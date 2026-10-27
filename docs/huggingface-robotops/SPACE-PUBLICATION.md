# Publish the Hugging Face research Space (when authorized)

> **Current status:** The Static Space is published at https://huggingface.co/spaces/mskazemi/robotops-research-explorer (public, `sdk: static`, `apache-2.0`; created and checked on 2026-10-28 from this starter). No Hugging Face Collection, model or dataset exists yet. This guide does not initiate any HF upload and never exposes secrets.

## Why a Static Space first?

A [Static HTML Space](https://huggingface.co/docs/hub/spaces-sdks-static) can present an appealing student-facing illustration without a paid model server, remote robot control or private API key. It is public browser code, so it **cannot securely contain private tokens or server-side provider credentials**. Keep Jev and HF model execution **disabled** in this first demonstrator.

Potential future upgrades are a *separate, approved* Gradio or Docker Space with limited server-side synthetic classification, rate limits, secret storage, user abuse protection, billing approval and separate human safety review. Creation of Gradio/Docker Spaces and GPUs may be subject to plan/compute conditions. Do not assume this is free or perpetually available. Source: [Spaces overview](https://huggingface.co/docs/hub/spaces-overview).

## Starter files in this GitHub repository

```text
integrations/huggingface/spaces/robotops-research-explorer/
    README.md         # Hugging Face YAML front matter (sdk: static)
    index.html        # standalone responsive student research explorer
```

The starter demonstrates **four synthetic study concepts**, displays direct GitHub collaboration links and makes the absence of results explicit. It makes no requests to Jev, LeRobot, Hugging Face APIs or robotics hardware and does not download weights.

## Human-reviewed publication steps

1. Read and review [#98](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/98), current [HF Static Space documentation](https://huggingface.co/docs/hub/spaces-sdks-static), the Space source and the repository [AGENTS.md](../../AGENTS.md).
2. Confirm you have the appropriate HF account/organization permissions, repository license, accurate project name, approved visibility and no secret/personal content. If the owner is known and permitted, create a new **Static HTML** Space through the HF UI.
3. Copy only the contents of the starter directory to the Space repo root (including `README.md` with `sdk: static` front matter and `index.html`). Do not upload a Kubernetes manifest, credentials or actual ROS recordings.
4. Open the **real** `https://huggingface.co/spaces/OWNER/SPACE` returned by HF, verify its rendered app, mobile/keyboard interaction, static status and links. No invented Space URL should be written into source.
5. Add the *verified* Space URL to the main website, Hugging Face profile/Collection, GitHub README and issue #98 through a reviewed PR; link back to the exact GitHub repository and planned experiment issues.
6. Add an HF **Collection** (if useful) tying **only actual published** models/datasets/Space/paper references, with correct revision, license, provenance and scope. Avoid invented HF models or uploading untested checkpoints.
7. Optionally embed the Space into GitHub Pages only after verified deployment and a security/privacy/consent review. Give users an external link as an accessible alternative, and don't make crawler-readable scientific content depend on an iframe.

## Preview without Hugging Face

Serve this directory as static HTML:

```sh
python3 -m http.server 8001 --directory integrations/huggingface/spaces/robotops-research-explorer
# open http://localhost:8001/
```

This is a local preview, **not proof that a Hugging Face Space exists**.

## Optional advanced workflows (not included)

- [LeRobotDataset v3](https://huggingface.co/docs/lerobot/main/api/datasets) upload only after real converter validation and rights approval.
- [Model Cards](https://huggingface.co/docs/hub/model-cards) only for real trained or tested compatible models and pinned source artifacts.
- [Hugging Face Jobs](https://huggingface.co/docs/hub/jobs-overview) for separately authorized paid batch experiments; set a budget/time cap, immutable code and data refs, and a cancellation plan.
- [Inference Providers](https://huggingface.co/docs/inference-providers/pricing) only for supported model/tasks with correct billing. They do not automatically host LeRobot motor controllers or TypeSafe Jev.

## Privacy and correctness

- No secret in `index.html`, static JS or public Space variables. No private video or real robot addresses.
- No model predictions or benchmark numbers on the initial Space; a nice animation is **not** an executed inference system.
- No automated Space uploads in GitHub CI without human consent and credentials scoped appropriately.
- No claim of official affiliation with Hugging Face, TypeSafe, ROS or Open Robotics.
- Any future interactive robotics simulator requires independent safety and resource controls, not merely an iframe or hosted model response.

Contributor entry points: [epic #92](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/92) and [Space issue #98](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/98).
