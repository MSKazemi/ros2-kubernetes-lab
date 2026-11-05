# ROS 2 on Kubernetes: DDS discovery across pods and nodes

**Scope:** A practical explanation of DDS communication in Kubernetes and the limitations of the current [Vagrant-Kubernetes-ROS2-Deployment](../README.md) lab. This guide documents the **historical ROS 2 Foxy / Weave Net / Kubernetes 1.29 Vagrant and manifest checkout** (support state: *legacy*). The repository also contains a separate ROS 2 Jazzy / Ubuntu 24.04 container image (support state: *container tested*, see [Support states](#support-states-and-evidence)). Neither is evidence of successful current-version Kubernetes deployment or cross-node message delivery.

## Why ROS 2 discovery matters on Kubernetes

ROS 2 applications typically use the Data Distribution Service (DDS) through an ROS Middleware (RMW) implementation for publish/subscribe communications. A **ROS 2 node** is an application-level computation process; a **Kubernetes node** is a machine hosting pods. Two ROS 2 applications may run in different Kubernetes pods, on the same worker or on different workers.

DDS participants must discover each other before exchanging messages. The discovery mechanism depends on the RMW, DDS vendor, and configuration. Default DDS simple discovery commonly uses multicast, which is not guaranteed to work across all pod network topologies. **ROS 2 does not universally require multicast**: supported alternatives include a Fast DDS Discovery Server and other explicit peer-discovery configurations.

Read the upstream [Fast DDS ROS 2 Discovery Server tutorial](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html) to understand the client/server mode. A Discovery Server can remove the requirement for multicast *discovery*, but application data delivery, addresses, ports, QoS and network policies still need testing. Single-host Docker tests of these configurations (including a stopped-server negative control) are listed in [Discovery configurations verified in Docker](#discovery-configurations-verified-in-docker-2026-10-31); they do not cover Kubernetes.

## Discovery configurations verified in Docker (2026-10-31)

**Verified in Docker on 2026-10-31, on one host, with containers on user-defined Docker bridge networks.** This is **not** Kubernetes, pod-network, CNI, `hostNetwork`, or cross-node evidence. The containers shared one Linux host and one bridge network; no pod, Service, or node was involved.

Image: `ros:jazzy-ros-base-noble` (Ubuntu 24.04.5, ROS 2 Jazzy; `fast-discovery-server` is in `/opt/ros/jazzy/bin`). It does **not** include `demo_nodes_cpp` or `rmw_cyclonedds_cpp`, so the tests used `ros2 topic pub` / `ros2 topic echo` on `/agent10_chatter` (`std_msgs/msg/String`). CycloneDDS tests used an image with `apt-get install ros-jazzy-rmw-cyclonedds-cpp` added. Each run passed when `ros2 topic echo --once` printed the published `data:` line.

| # | Configuration (both nodes unless noted) | Result |
|---|---|---|
| A | `ROS_DOMAIN_ID=10`, default RMW (Fast DDS), default `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` | message received |
| B | as A, plus `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (no server) | **no message** (timeout); `ros2 topic info /agent10_chatter -v` prints `Unknown topic` |
| C | `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, `ROS_DISCOVERY_SERVER=<server-ip>:11811` | message received |
| D | as C, with `ROS_DISCOVERY_SERVER=<server-container-name>:11811` | message received |
| E | as C, with `ROS_AUTOMATIC_DISCOVERY_RANGE` left at `SUBNET` | message received |
| F | as C, server container stopped | **no message**; Fast DDS logs `SERVER_CLIENT_DISCOVERY Error ... Wrong domain name passed into the server's list` |
| G | as C, server restarted | message received |
| H | publisher `ROS_DOMAIN_ID=10`, subscriber `ROS_DOMAIN_ID=11` | **no message** |
| I | `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, default multicast | message received |
| J | Cyclone, `CYCLONEDDS_URI` with `AllowMulticast=false` and two `Peer` addresses (fixed IPs on a `/24` subnet) | message received |
| K | Cyclone, `CYCLONEDDS_URI` with `AllowMulticast=false` and no peers | **no message** |
| L | Cyclone, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, no `ROS_STATIC_PEERS` | **no message** |
| M | Cyclone, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` and `ROS_STATIC_PEERS="172.30.0.10;172.30.0.20"` | message received |
| N | publisher on Cyclone (default config), subscriber on Fast DDS (default config) | message received |

Snippets that were run (the server container used `fast-discovery-server -i 0 -l 0.0.0.0 -p 11811`, which prints `Server Addresses: UDPv4:[0.0.0.0]:11811`):

```bash
# Fast DDS discovery server (test C/D/F/G)
fast-discovery-server -i 0 -l 0.0.0.0 -p 11811

# Talker and listener environment (test C/D)
export ROS_DOMAIN_ID=10
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_DISCOVERY_SERVER=agent10-ds:11811   # or the server's IP and :11811

# CycloneDDS with explicit unicast peers (test J)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><AllowMulticast>false</AllowMulticast></General><Discovery><Peers><Peer address="172.30.0.10"/><Peer address="172.30.0.20"/></Peers><ParticipantIndex>auto</ParticipantIndex></Discovery></Domain></CycloneDDS>'

# CycloneDDS with a static peer list (test M)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_STATIC_PEERS="172.30.0.10;172.30.0.20"

# Publisher and subscriber used by every test
ros2 topic pub -r 2 /agent10_chatter std_msgs/msg/String "{data: hello-from-agent10}"
ros2 topic echo /agent10_chatter std_msgs/msg/String --once
```

What the results do and do not show:

- Tests B, F, H and K are negative controls: each failed in the way the explanation predicts, so the positive results are not an artefact of the harness.
- Test C shows the Fast DDS discovery server delivered data with the range set to `LOCALHOST`. We did **not** inspect the wire traffic, so this run does not prove which transports Fast DDS used internally; it shows only that the configuration worked in this single-host setup.
- `ROS_STATIC_PEERS` was tested only with CycloneDDS (test M). Test N shows that the default configurations of the two RMW implementations delivered to each other on this host; it is not a general interoperability guarantee.
- The results come from one Docker bridge on one machine. They say nothing about pod IP routing, CNI multicast policy, Kubernetes Services, `hostNetwork`, or workers on different machines. Those still need a cluster test (see [#14](https://github.com/MSKazemi/robo-resilience-lab/issues/14) and [#15](https://github.com/MSKazemi/robo-resilience-lab/issues/15)).
- Upstream ROS 2 and Fast DDS documentation pages could not be read in this review (the docs site presents a bot challenge to automated fetches), so the configuration names above are taken from the runnable tests and from `fast-discovery-server --help`, not from quoted upstream text.

### Troubleshooting table (commands verified in the same Docker tests)

| Symptom | Likely cause | Check |
|---|---|---|
| `ros2 topic echo` waits and never prints | Publisher and subscriber use different `ROS_DOMAIN_ID` (test H) | `printenv ROS_DOMAIN_ID` on both sides |
| Topic missing on the subscriber side | No discovery path: multicast is off and no discovery server or peers are set (test B) | `ros2 topic info /TOPIC_NAME -v` shows `Unknown topic` on the subscriber; a working topic shows `Publisher count: 1` |
| Nothing received with a discovery server set | Server not running, or the address is wrong (test F) | `printenv ROS_DISCOVERY_SERVER`; check that the server process is running. Fast DDS prints `SERVER_CLIENT_DISCOVERY Error` in the node output when the server name cannot be used |
| Cyclone publisher and subscriber cannot see each other with multicast off | No `Peer` entries in `CYCLONEDDS_URI` (test K) | `printenv CYCLONEDDS_URI`; the XML must list every peer address |
| Cyclone works only with multicast on | `ROS_STATIC_PEERS` is missing while the discovery range is `LOCALHOST` (test L) | `printenv ROS_AUTOMATIC_DISCOVERY_RANGE ROS_STATIC_PEERS` |

Do **not** use `ros2 node list` to check for a `ros2 topic pub` publisher: that node is hidden and is reported as `_ros2cli_*`, so the list can look empty while the topic works. Use `ros2 topic info -v`.

## What this repository currently provides

| Area | Existing code | What can be claimed |
|---|---|---|
| Virtual machines | [`Vagrantfile`](../Vagrantfile) | Three Ubuntu 22.04 VMs are defined: a control plane and two workers |
| Cluster setup | [`KubernetesClusterSetup/`](../KubernetesClusterSetup/) | Scripts request a kubeadm Kubernetes 1.29 cluster (1.29 reached end of life on 2025-02-28, per [kubernetes.io](https://kubernetes.io/releases/1.29/)) |
| Pod networking | [`Network/network_plugin.sh`](../Network/network_plugin.sh) | Installs a Weave Net v2.8.1 manifest. The upstream [`weaveworks/weave`](https://github.com/weaveworks/weave) repository was archived (read-only) on 2024-06-20, so this manifest is not maintained |
| ROS image (modern, container only) | [`ROS2/Dockerfile`](../ROS2/Dockerfile) | Builds from the ROS 2 Jazzy / Ubuntu 24.04 base with `demo_nodes_cpp` and `stress-ng`; checked only by an in-image local talker/listener test ([`scripts/test-ros2-image.sh`](../scripts/test-ros2-image.sh)). It is **not** referenced by the legacy `ROS2/ros_dep_*.yaml` manifests |
| ROS image (legacy) | [`ROS2/legacy/foxy/Dockerfile`](../ROS2/legacy/foxy/Dockerfile) | Preserved recipe for ROS 2 Foxy (end of life 2023-06-20, per the [ROS 2 release table](https://docs.ros.org/en/iron/Releases.html)) with `stress-ng`; the original manifests still pull a Foxy-based image (`kazemi/ros-foxy-with-stress-ng`) |
| Kubernetes workload | [`ROS2/ros_dep_1.yaml`](../ROS2/ros_dep_1.yaml) | Starts a CPU stress workload with an HPA, **not** talker/listener |
| Manual example | [`ROS2/README.md`](../ROS2/README.md) | Describes launching `demo_nodes_cpp` talker/listener from interactive shells; review corrections in [#24](https://github.com/MSKazemi/robo-resilience-lab/issues/24) |

## Support states and evidence

Three explicit states are used across the repository documentation. Only the first two are populated today.

| State | Meaning | Applies to | Evidence |
|---|---|---|---|
| `legacy` | Historical, unverified in this review, and built on end-of-life or archived components | Vagrant VMs (Ubuntu 22.04), kubeadm Kubernetes 1.29, Weave Net 2.8.1, ROS 2 Foxy images and `ROS2/ros_dep_*.yaml` / `ROS2/VPA.yaml` / `ROS2/ros_one.yaml` manifests | None executed in this review; static file inspection only |
| `container tested` | The Jazzy image builds and passes a local talker/listener check **inside one container** | `ROS2/Dockerfile` (ROS 2 Jazzy, Ubuntu 24.04, linux/amd64) | [`.github/workflows/ros2-image-ci.yml`](../.github/workflows/ros2-image-ci.yml) runs [`scripts/test-ros2-image.sh`](../scripts/test-ros2-image.sh) in the container; this checks the Jazzy distro, Ubuntu 24.04, `demo_nodes_cpp`, `stress-ng` and one listener receiving one talker message locally |
| `cross-worker verified` | A talker and listener scheduled on different Kubernetes workers exchange messages, with a repeatable scripted check | **Nothing yet.** Tracked in [#14](https://github.com/MSKazemi/robo-resilience-lab/issues/14) and [#15](https://github.com/MSKazemi/robo-resilience-lab/issues/15) | None |

Compatibility status (review date **2026-10-27**, repository base commit `7b9cb44`):

| Component | Version in the repository | Support state |
|---|---|---|
| ROS 2 image `ROS2/Dockerfile` | Jazzy / Ubuntu 24.04 | `container tested` (single container, amd64 only) |
| ROS 2 image `ROS2/legacy/foxy/Dockerfile` and Foxy-based images used by `ROS2/ros_dep_*.yaml` | Foxy (EOL) | `legacy` |
| Vagrant VMs, kubeadm Kubernetes, Weave Net | Ubuntu 22.04, Kubernetes 1.29, Weave Net 2.8.1 | `legacy` |
| Optional Jazzy stress manifest [`ROS2/jazzy/stress-deployment.yaml`](../ROS2/jazzy/stress-deployment.yaml) | Jazzy image, `ros-jazzy-lab:local`, a `stress-ng` workload only | `container tested` for the image only; the manifest was not applied to any cluster in this review |
| DDS discovery and talker/listener delivery across Kubernetes workers | any | `cross-worker verified`: **not achieved** |

Basis of this table: static inspection of the repository files at commit `7b9cb44`. Runtime evidence is limited to what the image workflow and [`scripts/test-ros2-image.sh`](../scripts/test-ros2-image.sh) exercise inside a single container; that workflow does **not** create a Kubernetes cluster and does **not** validate Kubernetes or DDS across nodes. **No Vagrant cluster was executed** for this review, and the CI result was not re-run here.

**Important distinction:** `kubectl scale deployment ros --replicas=3` creates stress-workload replicas in the original manifest. It does not itself demonstrate DDS communication.

## Inspect the historical Kubernetes networking setup

The following commands describe how to inspect a cluster **after successful Vagrant provisioning**. They are not a verified one-command modern installation path.

On your **host machine**:

```bash
vagrant status
vagrant ssh controlplane
```

Then inside the **control-plane VM**:

```bash
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get pods -n kube-system -o wide
kubectl get pods -n ros -o wide
```

If the `ros` namespace does not exist yet, the ROS stress manifest has not been applied. Applying it is **not** a replacement for configuring and launching separate ROS 2 talker/listener processes:

```bash
kubectl apply -f /home/vagrant/codes/ROS2/ros_dep_1.yaml
kubectl get pods -n ros -o wide
```

To make a **cross-worker** DDS claim, the talker and listener must be visibly scheduled to *different Kubernetes workers*, then a repeatable subscriber must receive messages from the remote publisher. Pod readiness, `kubectl get pods` alone, or output from a single machine is insufficient evidence.

## Troubleshooting checklist

1. **Check which machines host the pods:** use `kubectl get pods -n ros -o wide` and compare the `NODE` column.
2. **Check the container command:** `kubectl describe pod -n ros POD_NAME`. The current stress manifests run `stress-ng`; they do not start ROS 2 nodes.
3. **Inspect the network plugin:** review `kubectl get pods -n kube-system` and Weave logs if present. Do not assume the old Weave manifest functions on a newer Kubernetes version.
4. **Check ROS middleware settings:** `ROS_DOMAIN_ID`, `RMW_IMPLEMENTATION`, DDS discovery settings and QoS must be compatible between participants.
5. **Check connectivity:** firewalls, pod-to-pod routes, DNS, address advertisement and policies can affect the discovery and data paths even if pods are Running.
6. **Distinguish multicast from alternatives:** if multicast is unavailable, evaluate supported explicit-discovery options with a documented RMW rather than weakening the cluster firewall blindly.
7. **Capture actual evidence:** include the pod-to-node mapping, ROS distribution, RMW, discovery mode, commands, subscriber output and network configuration in any bug report.

Do not expose authentication tokens, cluster-admin kubeconfigs, private addresses, or credentials in pasted logs.

## Why not use this as a production robotics reference?

The Vagrant and Kubernetes manifest part of the current checkout depends on ROS 2 Foxy (end of life June 2023), Kubernetes 1.29 (end of support), and an archived Weave Net version; the separate Jazzy container image is `container tested` only (see [Support states](#support-states-and-evidence)). It lacks verified deterministic cross-node DDS integration tests and is sized for a powerful local workstation. Use it as **historical learning material** and follow the work to add a maintained lab:

- [Modern ROS image baseline #7](https://github.com/MSKazemi/robo-resilience-lab/issues/7)
- [Maintained DDS networking #15](https://github.com/MSKazemi/robo-resilience-lab/issues/15)
- [Verified talker/listener across different workers #14](https://github.com/MSKazemi/robo-resilience-lab/issues/14)
- [Lightweight kind/k3d profile #16](https://github.com/MSKazemi/robo-resilience-lab/issues/16)

## Further reading

- [ROS 2 documentation](https://docs.ros.org/en/rolling/)
- [ROS 2 distributions and support](https://docs.ros.org/en/rolling/Releases.html)
- [Fast DDS: Using Discovery Server in ROS 2](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html)
- [Kubernetes networking model](https://kubernetes.io/docs/concepts/services-networking/)
