# Lightweight kind demo: ROS 2 talker/listener across two Kubernetes workers

**Scope:** an educational lab profile that runs a three-node Kubernetes cluster as Docker containers ([kind](https://kind.sigs.k8s.io/)), starts a ROS 2 Jazzy talker and listener **on two different workers**, and checks with a script that messages cross between them. It is not a production or safety-critical platform, and it does **not** replace or validate the historical [Vagrant/kubeadm cluster](../README.md). Issues: [#14](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/14) (self-starting, cross-worker demo) and [#16](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/16) (lightweight profile).

All numbers below were **measured once on one host** (see [Measured on this host](#measured-on-this-host)). They are not guarantees for other machines, and no claim is made about 8 GB hosts.

## Quick start

```bash
git clone https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment.git
cd Vagrant-Kubernetes-ROS2-Deployment
make help      # prerequisites and targets
make demo      # build the image, create the kind cluster, deploy discovery server + talker + listener
make verify    # exit code 0 only if messages crossed between two different workers
make clean     # delete the cluster and the image built by `make demo`
```

Expected tail of `make verify` (from the recorded run):

```text
== 3/4 placement
POD                NODE                         NAME
talker             ros2k8s-demo-worker          talker-79db666498-8fr2x
listener           ros2k8s-demo-worker2         listener-6789f67db8-mpk29
discovery-server   ros2k8s-demo-worker2         discovery-server-79d9cd87bb-c5lwk
== 4/4 message delivery across nodes (ros2k8s-demo-worker -> ros2k8s-demo-worker2)
listener heard 'Hello World: 6' .. 'Hello World: 10' (counter advanced by 4)
PASS: ROS 2 messages crossed from ros2k8s-demo-worker to ros2k8s-demo-worker2
```

Pod names, counters and timestamps differ on every run.

### Prerequisites

| Tool | Version used | Notes |
|---|---|---|
| Linux, `amd64` | Linux 7.0 kernel on the test host | Only `amd64` was run. `arm64`, macOS and Windows/WSL were **not** tested. |
| Docker | 29.9.2 | The daemon must be reachable without `sudo` (`docker info`). |
| kind | v0.33.0 | The node image `kindest/node:v1.37.0@sha256:...` is pinned in [`kind/ros2k8s-demo.yaml`](../kind/ros2k8s-demo.yaml); `kind` downloads it (about 1.3 GB on disk) if it is not already cached. |
| kubectl | v1.37.1 | |
| `make`, `bash` | | |

`make` fails with a clear message when `docker`, `kind` or `kubectl` is missing or the Docker daemon is unreachable. The first `make demo` also needs internet access to pull the pinned `ros:jazzy-ros-base-noble` image, the node image and Ubuntu apt packages. Nothing is pushed or published; the image never leaves your Docker engine and is loaded into the workers with `kind load docker-image`.

## What `make demo` creates

| Object | Name | Purpose |
|---|---|---|
| Docker image | `ros2k8s-demo-ros:local` | Built from [`ROS2/Dockerfile`](../ROS2/Dockerfile) (ROS 2 Jazzy, Ubuntu 24.04) |
| kind cluster | `ros2k8s-demo` (context `kind-ros2k8s-demo`) | 1 control plane + 2 workers, default kind CNI (kindnetd) |
| Node labels | `ros2k8s-demo/role=talker` on worker 1, `ros2k8s-demo/role=listener` on worker 2 | Deterministic placement: the talker and listener `nodeSelector`s can only be satisfied by different workers |
| Namespace | `ros` | Shared with the legacy examples; labelled for Pod Security `warn`/`audit` = `restricted` |
| ConfigMap `ros2-dds-config` | `ROS_DOMAIN_ID=42`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_DISCOVERY_SERVER=discovery-server.ros.svc.cluster.local:11811` | Explicit domain, middleware and discovery settings |
| Deployment + Service `discovery-server` | UDP 11811 | Fast DDS Discovery Server (see [DDS discovery findings](#dds-discovery-findings-what-was-tested)) |
| Deployments `talker`, `listener` | `ros2 run demo_nodes_cpp talker` / `listener` | Start by themselves; no `kubectl exec` is needed |

All manifests are in [`ROS2/jazzy/talker-listener.yaml`](../ROS2/jazzy/talker-listener.yaml). The pods run as UID 1000 (non-root), with `allowPrivilegeEscalation: false`, all capabilities dropped, the `RuntimeDefault` seccomp profile, a read-only root filesystem (a size-limited `emptyDir` for `/tmp`), no mounted service-account token, and no privileged mode or host networking. The stress-ng examples (`ROS2/ros_dep_*.yaml`, [`ROS2/jazzy/stress-deployment.yaml`](../ROS2/jazzy/stress-deployment.yaml)) are unchanged and separate.

## Resource table

Requests and limits are what the manifests set. "Measured" values come from the recorded run below.

| Component | CPU request / limit | Memory request / limit | Measured memory |
|---|---|---|---|
| `talker` pod | 50m / 250m | 48Mi / 128Mi | about 30 MB (`crictl stats`) |
| `listener` pod | 50m / 250m | 48Mi / 128Mi | about 30 MB (`crictl stats`) |
| `discovery-server` pod | 20m / 100m | 16Mi / 64Mi | about 6 MB (`crictl stats`) |
| kind node containers (control plane, worker, worker 2) | none set | none set | 593 MiB, 269 MiB, 290 MiB (`docker stats --no-stream`, about 45 s after `make demo` finished) |

| Profile | RAM | CPU | Disk | Source |
|---|---|---|---|---|
| **kind (this document)** | about 1.1 GiB summed over the three node containers | 12 logical CPUs on the test host, no limit set; the node containers used 4 to 24 percent of one CPU at the sample | host free space went from 15 GB to 7.9 GB while the cluster and the built image existed (Docker volumes: 1.19 GB + 2.09 GB + 2.09 GB; image: 1.59 GB on disk, 364 MB of content); the cached node image (about 1.3 GB) and the Docker build cache (about 2 GB) were already present and are extra on a fresh host | measured |
| Vagrant, three VirtualBox VMs ([`Vagrantfile`](../Vagrantfile)) | 18240 MB + 2 x 6096 MB = 30432 MB requested | 14 + 2 + 2 = 18 vCPUs requested | not measured | read from the `Vagrantfile`; **not run** |

The Docker daemon and the image build need additional memory that was not measured. Whether the profile fits an 8 to 12 GB machine was **not tested**; the issue #16 goal of a measured baseline on such hardware remains open. Optional monitoring (`MonitoringSystem/`) is not part of this profile.

## Measured on this host

| Item | Value |
|---|---|
| Date and tree | 2026-10-27, commit `862b026` (implementation commit) |
| Host | 12 logical CPUs, 31 GB RAM, Docker 29.9.2, kind v0.33.0, Kubernetes v1.37.0, containerd 2.3.4, CNI kindnetd |
| `make demo` (warm: Docker build cache and node image already present locally) | 82 s wall clock (`/usr/bin/time`: 1:22.24) |
| Cold image build, measured separately before the cluster existed (base image pulled, apt install) | 3 min 21 s (`/usr/bin/time -v docker build`) |
| `make verify` | 8.0 s wall clock when the pods had been running for about 10 s; exit code 0 |
| `make verify-negative` | 63 s in one earlier run of the same script (the time of the final run was not recorded); exit code 0 in both |
| Time to pull the `kindest/node` image | **not measured** (it was already cached) |
| `make clean` | about 6 s |

Commands used for these numbers: `/usr/bin/time -f 'wall=%E' make demo`, `make verify`, `docker stats --no-stream`, `docker system df -v`, `df -h /` and `docker exec <node> crictl stats`.

## DDS discovery findings: what was tested

The default was tried **first**, then a documented fix. All runs below used the same image, the same two workers and the same kind CNI (kindnetd), with `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` and `ROS_DOMAIN_ID=42`.

| # | Approach | Result observed |
|---|---|---|
| A | Default Fast DDS multicast discovery (no `ROS_DISCOVERY_SERVER`), talker on worker 1, listener on worker 2 | **Failed.** The talker had logged 43 `Publishing` lines after 45 s and the listener logged **0** `I heard` lines. |
| A-control | Same default discovery, listener moved to the **same** worker as the talker | **Also failed** (0 `I heard` lines in the checks made up to about 45 s after the listener started). On this CNI the multicast discovery did not work between two pods on one node either, so the cross-worker failure is not specific to inter-node routing. |
| A-probe | Plain UDP test between the two pods (Python sockets, port 17400) | Unicast to the listener pod IP: **received**. Multicast to 239.255.0.1 from the talker pod to the listener pod: **timed out**. So pod-to-pod UDP unicast crosses workers; multicast does not. |
| B | **Fast DDS Discovery Server** reached through a ClusterIP Service DNS name (`ROS_DISCOVERY_SERVER`) | **Worked.** The listener on worker 2 logged `I heard` for the talker on worker 1 (29 `I heard` lines when the talker had published 32 messages, in a manual check; `make verify` passes). This is what the profile uses. |
| C | Fast DDS initial peers (unicast XML profile) or CycloneDDS unicast peers | **Not tried**, because B worked. The image contains only `rmw_fastrtps_cpp`, not CycloneDDS. |

Other things observed while building this (single observations on this host):

- **Open-files limit and memory.** Under kind's container runtime the pods inherited an open-files limit of about 1.07e9. In that state a talker container used about 299 MB (RSS about 160 MB per process) and was OOM-killed at a 256Mi limit, versus about 30 MB after `ulimit -n 1024` (the manifest runs `ulimit -n 1024 && exec ...`). The same limit set through `docker run --ulimit` did not reproduce the growth, so the cause was **not** established.
- **`ROS_DOMAIN_ID` is not isolation through a shared discovery server.** In one run, a listener started with `ROS_DOMAIN_ID=43` still received messages from the domain-42 talker through the same Discovery Server and `make verify` still passed. Do not rely on domain IDs to separate workloads that share one server. This is why the negative test breaks the discovery server address instead.
- **Discovery Server flags.** `fastdds discovery --server-id ... --ip-address ... --port ...` was rejected in this image (`Unknown arguments`); the manifest runs `fast-discovery-server -i 0 -l 0.0.0.0 -p 11811`.

## What `make verify` checks

[`scripts/verify-ros2.sh`](../scripts/verify-ros2.sh) (Bash, `set -euo pipefail`, every `kubectl` call has a request timeout; `VERIFY_TIMEOUT`, default 120 s, bounds each waiting stage):

1. the cluster is reachable and the `discovery-server`, `talker` and `listener` Deployments finish rolling out;
2. their pods are Ready;
3. the talker and listener pods are on **different nodes** (the placement table is printed);
4. the listener log contains `I heard: [Hello World: N]` lines whose counter keeps advancing (at least three new messages), and the latest `N` appears in the **talker pod's** own log as `Publishing: 'Hello World: N'`.

Exit codes: `0` verified, `1` verification failed (diagnostics are printed to stderr: nodes, pods, events, descriptions and the last log lines of each app), `2` usage error or `kubectl` missing. It reads pod state and logs only; it does not print kubeconfig or Secret contents.

### Negative test

`make verify-negative` runs `scripts/verify-ros2.sh --negative-test`: it verifies (must pass), points the listener at a dead discovery-server address while the pods stay Ready and on different nodes, verifies again (must fail **at the delivery check**), restores the listener, and verifies once more (must pass). Recorded result: the broken state produced `ERROR: FAIL delivery: listener (...) logged no 'I heard' message from the talker (...) within 45s` and exit status 1; the final line was `PASS: negative test (broken delivery was detected with exit status 1, then recovered)`.

A second negative check, scaling the talker to 0 replicas and running the script with `VERIFY_TIMEOUT=15`, also exited with status 1 and was then restored.

## Cleanup

```bash
make clean                                    # kind delete cluster --name ros2k8s-demo; docker image rm ros2k8s-demo-ros:local
kind get clusters                             # expect: No kind clusters found (or only clusters that are not yours)
docker ps -a --filter name=ros2k8s-demo       # expect: no containers
docker images | grep ros2k8s-demo             # expect: nothing
```

`make clean` touches only the cluster `ros2k8s-demo` and the image `ros2k8s-demo-ros:local`. It deliberately leaves shared Docker objects alone. If you want the extra space back and know nothing else uses these, remove them yourself: `docker image rm ros:jazzy-ros-base-noble` (the pinned upstream base image), `docker image rm kindest/node:v1.37.0` (the kind node image) and the Docker build cache (`docker builder prune`, which affects **all** your builds). Do not run `docker system prune` unless you intend to remove unrelated images, containers and volumes.

For the Vagrant profile, cleanup is `vagrant destroy -f` from the repository root; that profile was **not** run for this document.

## Support states

This repository uses three states ([definitions](./ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)):

| State | Applies to |
|---|---|
| `legacy` | Vagrant profile (Ubuntu 22.04, Kubernetes 1.29, Weave Net) and the Foxy stress-ng manifests |
| `container tested` | The Jazzy image checked inside a single container by CI |
| `cross-worker verified` | **Only this kind profile on kindnetd**, as recorded above: commit `862b026`, 2026-10-27, `make demo && make verify` (exit 0) on one host. It does not extend to other CNIs, other clusters, the Vagrant profile or other hosts. |

## CI

[`.github/workflows/kind-demo.yml`](../.github/workflows/kind-demo.yml) runs `make demo`, `make verify`, `make verify-negative` and `make clean` on `ubuntu-24.04` for pull requests that touch the relevant paths, and on manual dispatch. It pins `actions/checkout` to a commit SHA, installs checksum-verified kind and kubectl binaries, and uses `contents: read` permissions. **This workflow has not been executed yet** (it could not be run in the environment where it was written); treat the first GitHub run as the first real test.

## Limits

- One host, one run per measurement; numbers vary with caches, disk and load.
- `amd64` only: the image was built and run only for `linux/amd64` (see [`ROS2/jazzy/README.md`](../ROS2/jazzy/README.md) for its provenance and limits).
- kind shares the host kernel and network namespaces with Docker; behaviour on a real multi-machine cluster or another CNI can differ, especially for multicast and UDP.
- Message delivery was shown for the stock `demo_nodes_cpp` talker and listener only, not for other message types, QoS settings or node counts.
- The Discovery Server is a single replica and a single point of failure for discovery in this lab.
