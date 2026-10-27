---
title: ROS 2 + Hugging Face RobotOps Research Explorer
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: static
license: apache-2.0
---

# ROS 2 + Hugging Face RobotOps Research Explorer

**Status:** Independent, static, synthetic-only educational demo. The HTML does **not** run any Hugging Face models, LeRobot simulator, Jev API, Kubernetes workload or physical robot. No real benchmark is claimed.

This folder is a **ready-to-copy template** for an optional public Hugging Face **Static HTML Space**. It is **not yet a published Hugging Face Space**. Before posting a public URL, the repository owner must create a Space using their authorized account, review the license/visibility and upload this folder manually or via an approved Hub tool.

The four research tracks are: (1) validate synthetic robot episode metadata before attempting LeRobotDataset v3 conversion, (2) design Jev-vs-HF text classifier benchmarks, (3) define compatible SmolVLA/LIBERO experiments, and (4) study Kubernetes-hosted LeRobot remote policy inference and stale-action constraints.

## Offline preview

```sh
python3 -m http.server 8001 --directory integrations/huggingface/spaces/robotops-research-explorer
# http://localhost:8001
```

**No API credentials, model weights or GPU are needed.** Do not add HF/TypeSafe tokens to `index.html` or browser JavaScript; browser code is public. Never make this a physical robot controller.

Research epic: https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/92

Publishing and verification steps: https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/blob/main/docs/huggingface-robotops/SPACE-PUBLICATION.md (this path becomes available on `main` only after the review PRs merge).
