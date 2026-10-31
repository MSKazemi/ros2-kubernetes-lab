# Primary references, ecosystem comparison and evidence notes

> **Source directory reviewed for the Cloud Robotics + AI/LLM research proposal, 27 October 2026.** Links are inputs to design, not certification of compatibility with this repository. Upstream documentation is live and may change; pin exact versions at implementation time. The lab's current state is described in [root README](../../README.md).

## Hugging Face ecosystem

| Resource | Why relevant | Decision or caution |
| --- | --- | --- |
| [LeRobot documentation](https://huggingface.co/docs/lerobot/) | Open robotics learning workflows, robot policies, recording and evaluation | Prefer upstream APIs to handwritten replacement |
| [LeRobotDataset v3](https://huggingface.co/docs/lerobot/lerobot-dataset-v3) | Parquet low-dim measurements, MP4 camera, relational episode metadata | Need real action/task/episode alignment, not just ROS Image |
| [Remote inference](https://huggingface.co/docs/lerobot/main/remote_inference) | Zenoh-based policy client/server and asynchronous action chunks | One-client-per-server semantics and robot/processor compatibility matter |
| [Policy inference guide](https://huggingface.co/docs/lerobot/main/inference) | Local sync, RTC and remote options | Support varies per policy/checkpoint and release |
| [Third-party ROS 2 bridges](https://huggingface.co/docs/lerobot/main/third_party_robots) | Includes leros2, lerobot_robot_ros2_zenoh, Rosetta | Compare/pin compatibility and licenses before inventing adapter |
| [SmolVLA docs](https://huggingface.co/docs/lerobot/smolvla) | Candidate open vision-language-action policy | A model must match actual robot/action semantics |
| [Hugging Face Hub download API](https://huggingface.co/docs/huggingface_hub/package_reference/file_download) | Immutable commit revisions, caches and offline use | Exact revision/processor integrity required |
| [Model cards](https://huggingface.co/docs/hub/model-cards) | Intended use, limitations, training/evaluation, license | Don't claim model safety without review |
| [Dataset cards](https://huggingface.co/docs/hub/datasets-cards) | Dataset origin, bias, content and intended use | Public upload requires license/privacy check |
| [Spaces](https://huggingface.co/docs/hub/spaces-overview) | Read-only public result visualization | Never host a live physical robot command endpoint |

## ROS 2, Kubernetes and simulation

- [ROS 2 Jazzy docs](https://docs.ros.org/en/jazzy/) — maintained official baseline documentation; check exact platform and distro lifecycle for any supported environment.
- [ROS 2 distributions / support](https://docs.ros.org/en/rolling/Releases.html) — pin ROS/Ubuntu versions and record end-of-life.
- [Fast DDS ROS discovery server](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html) — explicit discovery option; not a universal solution by default.
- [ROS-specific Zenoh plugin](https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds) — distinguish bridge benchmarking from **LeRobot remote inference**, which also uses Zenoh differently.
- [ros2_tracing](https://github.com/ros2/ros2_tracing) — evidence source for ROS callbacks/timing where validated.
- [modern Gazebo + ROS control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html) — potential Jazzy+Gazebo Harmonic simulation; don't use EOL Gazebo Classic for new Jazzy lab.
- [Kubernetes concepts](https://kubernetes.io/docs/concepts/) — scheduling, resource constraints and network security (not real-time robotics guarantees).
- Existing lab docs [DDS guide](../ROS2-KUBERNETES-DDS-GUIDE.md), [historical analysis](../../DataAnalysis/) and [modernization plan](../ROADMAP-2026.md).

## Prior art — scope novelty responsibly

| Prior work | Contribution in ecosystem | What we should not claim |
| --- | --- | --- |
| [FogROS2](https://github.com/BerkeleyAutomation/FogROS2), [ICRA 2023](https://ieeexplore.ieee.org/document/10161307/) | ROS 2 computational offloading into cloud/fog | "First cloud ROS 2 solution" or "first robot inference placement" |
| [FogROS2-FT](https://arxiv.org/abs/2412.05408) | Fault-tolerant replicated cloud robot computation | Fault-tolerant cloud robotics is unexplored |
| [FogROS2-PLR](https://arxiv.org/abs/2410.05562) | Network/replica latency reliability research | Optimizing p99 via replicas is wholly new |
| [FogROS2-SGC](https://arxiv.org/abs/2306.17157) | ROS 2 cross-network/cloud secure connectivity | First secure geographically distributed ROS 2 |
| [RobotKube](https://github.com/ika-rwth-aachen/robotkube) | Kubernetes-native cooperative robotics research | "First ROS Kubernetes integration" |
| [Open-RMF](https://github.com/open-rmf) | Multi-fleet resource coordination | Project will replace fleet interoperability |
| [Nav2](https://docs.nav2.org/) | ROS navigation framework | Rebuilding navigation core is initial contribution |

**Candidate differentiated question:** How do model/task/embodiment provenance, validated action contracts, container placement and actual network impairment interact to change **observation-to-valid-action age, failure and replicability** in an accessible cloud robotics lab? This is a hypothesis/research program, **not yet proof of novelty**. Run literature review before paper claims.

## Ethics, security and legal-review sources

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — voluntary AI-risk management; GOVERN, MAP, MEASURE, MANAGE.
- [NIST AI RMF Playbook](https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook) — suggested actions by function; nonbinding.
- [OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — untrusted document/log can alter LLM behavior; RAG alone does not eliminate risk.
- [EU AI Act service desk timeline](https://ai-act-service-desk.ec.europa.eu/en/ai-act/eu-ai-act-implementation-timeline) — phased obligations as of review date; verify current law at deployment, not blanket classification.
- [EU Council timeline](https://www.consilium.europa.eu/en/policies/artificial-intelligence-act/timeline-artificial-intelligence/) — adopted changes and timelines should be checked with legal counsel for particular robotics products.
- [ISO 10218-1:2025](https://www.iso.org/standard/73933.html) — industrial robot design safety; cannot be claimed met by a simulated action gate.
- Project [SAFETY.md](../../SAFETY.md), [SECURITY.md](../../SECURITY.md), [DISCLAIMER.md](../../DISCLAIMER.md) and [AGENTS.md](../../AGENTS.md) — repository-specific policies still apply.

## Source usage rules for contributors

1. Prefer official current vendor/ROS/HF docs and published research to unsourced blog conjecture; distinguish conceptual proposal from observed implementation.
2. Pin a repository commit, release or date with a reproducing toolchain. Some upstream "main" docs can change without warning.
3. Link relevant prior art for paper novelty, and separate results reported by *others* from this project's own evidence.
4. If a source is inaccessible or experimental, label it and avoid claiming verified compatibility.
5. Don't copy code, datasets or weights whose license/redistribution terms are unclear.
6. If a regulation or standard is mentioned, record product category/region, applicable text/version and need for qualified legal or safety review.
7. When a third-party system (LeRobot remote inference or ROS/Zenoh) already provides a feature, evaluate and reuse instead of declaring a first-of-kind invention.
