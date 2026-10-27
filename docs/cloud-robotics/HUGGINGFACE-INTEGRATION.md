# Hugging Face integration plan: LeRobot, datasets, VLA models and robot AI

> **Integration design, not a shipped feature.** Study upstream docs for the **specific pinned release** before writing code. LeRobot APIs and compatibility may change, including policy support and remote inference semantics.

## Strategic decision: integrate rather than clone

Hugging Face already provides model/dataset repositories, model and dataset cards, LeRobotDataset, training/evaluation and a remote-inference implementation. The proposed laboratory contributes ROS 2/Kubernetes infrastructure, **repeatable tests, reliability evidence, semantic validation and education** around these tools. It should not recreate a new Hugging Face Hub, VLA training framework or undocumented LeRobot server.

| Existing ecosystem | Reuse | Differentiated work |
| --- | --- | --- |
| [LeRobot docs](https://huggingface.co/docs/lerobot/) | Supported robot/policy APIs, recording, training and rollout | ROS 2 + K8s profiles with controlled manifests, clean-room tests |
| [LeRobotDataset v3](https://huggingface.co/docs/lerobot/lerobot-dataset-v3) | Episode metadata, low-dimensional Parquet, video MP4 and tasks | Correct ROS 2 time/unit/frame mappings and negative tests |
| [Community ROS bridges](https://huggingface.co/docs/lerobot/main/third_party_robots) | Existing leros2, lerobot_robot_ros2_zenoh and Rosetta options | Compare licenses, pinned versions, message/action semantics and safety |
| [Remote inference](https://huggingface.co/docs/lerobot/main/remote_inference) | Upstream action chunks, admission, client/server, optional async/RTC modes | Secure deployment/placement/failure experiments; do not invent protocol |
| [SmolVLA](https://huggingface.co/docs/lerobot/smolvla) | Open VLA candidate, if model and chosen simulator/embodiment match | Test compatible workload and action age, not arbitrary sensor inference |
| [Hub Spaces](https://huggingface.co/docs/hub/spaces-overview) | Accessible static/interactive app hosting | Read-only verified benchmark explorer; not a robot control surface |

## Four concrete integration tracks

### HF-1. ROS 2 -> versioned robotics dataset (first value)

**Why:** Most ROS bags contain messages, but a supervised robot-learning dataset needs semantically aligned **observations, actions, tasks and episodes**.

1. Choose a genuinely redistributable simulation/fixture with a camera frame, a named and unit-specified robot state, a matching target action, task text/ID, and episode boundaries. Synthetic images and deterministic actions are valid *test fixtures* but do **not** prove useful policies or realistic robot skills.
2. Document mapping of ROS image encoding, frame ID, camera properties, state order/dimension, action order/unit, frequency, source clocks, synchronization tolerance and missing data.
3. Use upstream LeRobotDataset v3 API to store low-dimensional state/action/timestamp in Parquet; camera videos in MP4; episode/task/feature schema in metadata. Verify roundtrip through LeRobot's loader **in a pinned version**.
4. Fail invalid or under-specified examples, report dropped/misaligned frames and keep manifest, license and checksums with the result.
5. Produce a *reviewed* dataset card; no public upload without license/consent and manual approval.

**Illustrative observation contract (proposal, not current code):**

```json
{
  "contract_version": "robotops-observation-v1",
  "episode_id": "synthetic-001",
  "sequence_id": 17,
  "source_time_ns": 1250000000,
  "source_clock": "simulation",
  "frame_id": "camera_front",
  "image": {
    "encoding": "rgb8",
    "shape_hwc": [64, 64, 3],
    "artifact_sha256": "SYNTHETIC_FIXTURE_HASH_NOT_REAL"
  },
  "robot_state": {
    "names": ["joint_1", "joint_2"],
    "units": ["rad", "rad"],
    "values": [0.0, 0.1]
  },
  "task_id": "sim_pick_place_fixture",
  "action_semantics_id": "sim_arm_rad_v1",
  "model_revision": "mock-v1"
}
```

This is a **schema sketch**. Use a real JSON Schema and validate units, monotonic time and exact model/action compatibility in [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55). The placeholder hash must not be interpreted as a real checksum. Timestamps must not be subtracted across unrelated clocks without explicit conversion/sync.

### HF-2. Pin and cache model/dataset identities

Treat **model and processor files as versioned code/data**, not as a moving string. A Hub repo ID alone is not enough: record immutable commit revision, license, original model card, size, processor/tokenizer revision, expected embodiment and artifact hashes. For caching, explicitly test:

| Condition | Expected behavior |
| --- | --- |
| Exact artifact cached, offline | Load verified artifact without network request |
| Exact revision absent, offline | Clear deterministic failure; no silent fallback to latest |
| New revision available, run pinned to old | Old is used unless reviewed new release is requested |
| Model/processor revision mismatch | Reject before action prediction |
| Corrupted cache | Hash/format failure and no simulated actuation |
| Restricted/gated or unclear license | Document review blocker; never embed token in repo |

No unconditional remote code execution: document whether a model needs custom code or special deserialization and gate it through sandboxed/reviewed execution. Don't load arbitrary pickle-like weights on an untrusted machine.

### HF-3. Reuse *upstream* remote policy serving

LeRobot's current remote inference documentation describes **Zenoh-based** endpoints and action chunks. It contains explicit settings for refill, merge, freshness, client/server admission and supported robots/policies. These are **not** the same channel or assumptions as ROS 2 DDS discovery. Treat them as two transports and two contracts.

**Server responsibilities:** pinned checkpoint+processor; compatible robot semantic contract; bounded requests; resource limitations; protected endpoint; explicit replica/instance identity; logging/model revision.

**Client responsibilities:** observe simulated state; sequence/clock; verify expected deployment/semantics; apply bounded timeout, action freshness and admission; forward only **candidate** actions into the independent simulated gate.

**Operations responsibilities:** exact image digest, privacy-safe network logs, namespace + RBAC, private connectivity, GPU resource requests if needed, non-root image, read-only mounts, cache integrity, no public anonymous ingress, automatic cleanup.

**Important upstream limits:** the current remote-inference docs state one active client per server process and position-hold support requirements for hardware, with specific policy-contract restrictions. Do not promise arbitrary multi-client pooling or blanket support for mobile bases, SmolVLA, any robot or any ROS image. Inspect pinned version before designing server scale-out.

An upstream policy server's own timeout/hold mechanisms are useful engineering behavior but **not a certified safety component**. For this educational project, actions must terminate at the simulation gate; it may not connect to a physical motor.

### HF-4. Optional public Hugging Face Space

Create a **read-only** exploration site only from verified/public/approved artifacts. Proposed tabs: "architecture", "experiment manifest", "latency distribution", "failure gallery" and "reproduce this trial". Show raw metrics and assumptions alongside figures. Label mock-policy, synthetic and unrun results conspicuously. A Space must not host kubeconfigs, access tokens, production maps or actuator controls.

## Bridge decision gate before implementation

Research these projects as *third-party candidates*, with pin/version/license status:
- [leros2](https://huggingface.co/docs/lerobot/main/third_party_robots) — ROS 2 topics/actions bridge listed by Hugging Face.
- [lerobot_robot_ros2_zenoh](https://huggingface.co/docs/lerobot/main/third_party_robots) — ROS 2 to LeRobot via Zenoh; confirm it's not confused with ROS-specific DDS/Zenoh benchmarks.
- [lerobot-robot-rosetta](https://huggingface.co/docs/lerobot/main/third_party_robots) — YAML contract-based bridge as described by upstream.

### Required comparison columns
Upstream project/URL; license; last tested LeRobot version; Jazzy compatibility; ROS messages and QoS; ROS middleware and transport; observation and action ordering; camera mapping; calibration; action/FPS semantics; dependency pin; status of integration tests; hardware/simulator proof; privacy handling; gaps; retain-or-reject decision. This is the scope of [#57](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57).

## Model choice is a compatibility problem

A demo should start with a **mock policy**. Then evaluate a real checkpoint **only if** matching robot action dimensions, actuator ordering and units, observation features, cameras and preprocessing, rate, language task and simulator are known. SmolVLA is attractive as an optional VLA example, but it is not a drop-in replacement for arbitrary ROS 2 publishers.

**Pass levels:** (1) load succeeds; (2) typed observation/response contract succeeds; (3) action validity and deadlines hold; (4) simulated task success is measured; (5) physical task validation needs *separate* qualified safety review and remains out of first phases. Never collapse these into "robot AI works."

## Publishable research opportunities

- **Dataset alignment:** Compare timestamp synchronization tolerances and camera FPS jitter against reproducible data corruption metrics.
- **Model provenance:** Measure cold-start, prefetch and offline reliability with exact weights/processors pinned to revisions.
- **Action freshness:** Compare remote vs local (when compatible) under controlled latency/loss and action-chunk settings. Report source age and policy deadlines.
- **Resource/energy:** When power is measurable, report cost/energy per **valid** task outcome, not raw model forward speed.
- **Multi-client isolation:** One server process per client as an upstream baseline; fair/pooling proposals are new research requiring measured comparison.

## Implementation issue map

- [#56](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/56) licensed dataset converter; [#57](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/57) plugin/policy compatibility; [#58](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/58) Hub immutable revisions; [#61](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/61) server; [#62](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/62) edge-cloud experiment; [#68](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/68) public read-only Space.

No Hugging Face user account, model/dataset repository or Space has been created by this planning work.

