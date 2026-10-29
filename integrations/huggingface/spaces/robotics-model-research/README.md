---
title: ROS 2 Cloud Robotics Model Research
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: static
app_file: index.html
pinned: false
license: apache-2.0
models:
  - lerobot/smolvla_base
  - lerobot/xvla-base
  - lerobot/xvla-libero
  - lerobot/pi05_libero_base
  - IDEA-Research/grounding-dino-tiny
  - depth-anything/Depth-Anything-V2-Small-hf
  - facebook/sam2-hiera-small
tags:
  - robotics
  - ros2
  - kubernetes
  - lerobot
  - embodied-ai
  - cloud-edge
short_description: Read-only educational explorer of HF models for cloud-edge robotics research
---

# ROS 2 Cloud Robotics Model Research — Static Space starter

> **SOURCE TEMPLATE ONLY. NOT PUBLISHED ON HUGGING FACE.** The potential brand "RoboLattice" is a working name, not an approved or cleared external trademark. This starter is independent of upstream model creators and has no live inference, robot control or measured benchmark.

This *static HTML* educational Space lists verified model repository links, scopes research questions and sends interested researchers to GitHub's existing issues. No model weights are downloaded, no hidden service is contacted and no passwords or tokens are needed. All experiment performance results are **unmeasured**.

## Publish manually, after human review

1. Review this entire directory against public-project safety, claims and attribution rules.
2. Check that every model card still exists, its intended use and license are suitable, and required Hub commits are recorded for any real experiment. A model link is not a deployment.
3. On Hugging Face, choose **Create new Space**, select **Static**, an approved public name, license and account; confirm the owner and that publishing is intended.
4. Copy this directory's README.md and index.html to the new Space repository, using the actual HF publishing workflow. Do not mirror private repository data, token or telemetry.
5. Inspect the page live on desktop/mobile and keyboard, check references, privacy and accessibility. Only after real publication, link the *verified* Space URL from the GitHub website and your profile.
6. If a public Space is not published, keep the site/docs labeled **source template / not deployed**. No automatic publication action is authorized.

Official: https://huggingface.co/docs/hub/main/spaces-sdks-static ; https://huggingface.co/docs/hub/spaces-overview

## Notes

- Static Spaces run entirely in visitors' browsers and **cannot protect a private inference API key in client JavaScript**. Never add a secret or robot endpoint to this app.
- If real model interaction becomes necessary, design a separate vetted backend with a privacy and resource plan, pinned model contract and explicit approval; do not quietly convert this starter into a GPU service.
- Associated existing research epic: https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/92
- Main research documentation: https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment
