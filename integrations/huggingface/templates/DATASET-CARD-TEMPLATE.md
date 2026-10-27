# TEMPLATE — LeRobot robot episode dataset card (NOT PUBLISHED)

> This document is a **template**, not a Hub dataset and not evidence of a valid LeRobotDataset v3. Add accurate HF YAML metadata (license, dataset tags and task categories) only when rights and target Hub repo are confirmed. Never advertise this template as an uploaded dataset.

## Proposed title and repo

- **Hub dataset repo ID:** NOT_CREATED
- **Visibility:** NOT_SELECTED
- **License / source redistribution rights:** NOT_REVIEWED
- **Approved source:** [synthetic casebook / permitted camera episodes; describe source, consent, privacy filter]
- **Exact Hub dataset commit:** NOT_AVAILABLE
- **Source GitHub SHA and converter revision:** NOT_AVAILABLE
- **LeRobot package + dataset format version:** NOT_SELECTED

## Dataset summary and intended use

Explain the precise simulated or real task, robot embodiment, research audience and whether the data supports a model training/evaluation claim. State what the data cannot support (e.g. real robot safety, physical deployment, cross-worker DDS). For synthetic examples, disclose **every invented property**.

## Observation/action and camera schema

| Property | Verified value |
| --- | --- |
| Timestamp source and synchronization | TODO: clock, monotonic/wall, ROS2 timestamp / offsets |
| Control/recording FPS | TODO |
| State fields, shape, **units** | TODO (e.g. joint angle rad vs deg, translational m) |
| Action fields, shape, **units** and reference frame | TODO |
| Camera names, geometry, pixel format and calibration | TODO |
| Episode/task ID, task instruction semantics | TODO |
| Sensor frame transforms and RMW/DDS assumptions | TODO (no cross-worker claims) |
| LeRobot v3 metadata/data/video structure | TODO and actual official loader validation |

## Dataset composition and provenance

Number of real episodes/frames/tasks, splits by independent episode families, train/dev/test leakage control, preprocessing, filtering, labeling/adjudication method, duplicates, outliers, missing sensor packets, data collection and model leakage risks.

## Legal, privacy and safety

- Consent and lawfully shareable copyright/license evidence for each source; privacy/face/voice/address risks.
- Raw sensor streams and location-sensitive telemetry MUST NOT be exposed in a public repository without independent approval.
- Relevant robot operator safety policy and scope; no real-world clinical/industrial/safety guarantee.
- Known biases, failure modes, sampling artifacts, geographic/embodiment limitations and unsupported purposes.

## Validation / reproducibility

- [ ] LeRobot v3 created, finalized and **loaded back by the official pinned library release**, actual log attached.
- [ ] Episode counts and offsets, camera/video decoding, feature shapes/units and timestamps checked.
- [ ] Raw source/derivation/transformations and failures recorded with hashes.
- [ ] License, permission and privacy review completed; model training and human evaluations separated.
- [ ] Hub revision pinned to immutable commit and linked to GitHub source; dataset card metadata actually verified on Hub.

Until then, **STATUS: NOT_CREATED / NOT_VALIDATED**.
