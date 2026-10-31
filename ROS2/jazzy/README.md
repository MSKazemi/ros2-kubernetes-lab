# ROS 2 Jazzy image — Ubuntu 24.04 (container-level baseline)

This directory describes the **new ROS 2 Jazzy container baseline** from [`ROS2/Dockerfile`](../Dockerfile). It is separate from the [historical Foxy Vagrant/Kubernetes lab](../README.md).

**ROS 2 Jazzy Jalisco** is an LTS distribution with official Ubuntu 24.04 (Noble) support through May 2029. The image builds from the official `ros:jazzy-ros-base-noble` image pinned to a specific OCI registry digest, and installs:

- `ros-jazzy-demo-nodes-cpp` for talker and listener examples;
- `stress-ng` for CPU/memory workloads;
- `ros-jazzy-ros2-pulse` and `pulse-export` for the [optional ros2_pulse telemetry pilot](#optional-ros2_pulse-telemetry-pilot-issue-52). Both are inert unless a workload opts in.

This is a **container baseline only**, not a claim that the historical Kubernetes 1.29 / Weave Net / Vagrant cluster is updated or that talker and listener communicate between **different Kubernetes workers**.

## Build and verify locally

Requires a running Docker engine and enough disk/network capacity to download the ROS base image and apt packages. For the first validated build, CI targets **linux/amd64**. The upstream ROS base also offers arm64, but this repository does not claim that its own image has passed arm64 tests.

From the **repository root**:

```bash
docker build --platform linux/amd64 --file ROS2/Dockerfile --tag ros-jazzy-lab:local .
docker run --rm -i --platform linux/amd64 ros-jazzy-lab:local bash -s < scripts/test-ros2-image.sh
```

On **Windows PowerShell**, which has no `<` input redirection, mount the scripts folder instead (this form was verified on Linux amd64, not yet on Windows; see the [Windows and macOS guide](../../docs/WINDOWS-AND-MAC.md)):

```powershell
docker run --rm --platform linux/amd64 -v "${PWD}/scripts:/scripts:ro" ros-jazzy-lab:local bash /scripts/test-ros2-image.sh
```

The smoke script checks Ubuntu 24.04, `ROS_DISTRO=jazzy`, the ROS C++ talker/listener executables and `stress-ng`. It launches both ROS 2 example processes **inside one container**, and fails if the listener receives no message in 45 seconds. The complete smoke test is automated on PRs by [`.github/workflows/ros2-image-ci.yml`](../../.github/workflows/ros2-image-ci.yml).

The smoke test is **not** a Kubernetes, multi-pod, cross-worker or DDS-discovery-server test. Those release gates are tracked in [#14](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/14) and [#15](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/15).

To inspect the image without starting Kubernetes:

```bash
docker run --rm -it --platform linux/amd64 ros-jazzy-lab:local bash
# Inside the container:
/opt/ros/jazzy/bin/ros2 --help
stress-ng --version
```

## First verified published image (12 October 2026)

The [post-merge GitHub Actions run](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/38228962264) passed the amd64 image smoke test **and** Docker Hub publication. The workflow recorded:

- Source commit: `475988ae383e361ebbc60c1c6e0614ecd93694d1`.
- Repository: `<configured-Docker-Hub-namespace>/ros-jazzy-with-stress-ng`.
- Source-tagged image: `sha-475988ae383e361ebbc60c1c6e0614ecd93694d1`.
- **Published OCI index digest:** `sha256:8dd782f9382c123dc319330f8c0d012d790ae93b6752e26df6b2b47a4cdb720c`.

For a registry consumer with access to the **actual configured namespace**, use the digest rather than relying solely on a mutable tag:

```bash
export DOCKERHUB_NAMESPACE=YOUR_DOCKERHUB_NAMESPACE
docker pull --platform linux/amd64 "docker.io/${DOCKERHUB_NAMESPACE}/ros-jazzy-with-stress-ng@sha256:8dd782f9382c123dc319330f8c0d012d790ae93b6752e26df6b2b47a4cdb720c"
```

The GitHub workflow confirms authenticated publication; **public/unrestricted Docker Hub pull access has not been independently verified**. If you distribute the image to the community, confirm the repository is public and publish the namespace in GitHub's About/documentation once verified. The [build workflow](../../.github/workflows/main.yaml) uses Docker Hub credentials stored as GitHub secrets and does not reveal their values.

## Optional local-image Kubernetes stress example

[`stress-deployment.yaml`](./stress-deployment.yaml) is an **opt-in stress workload**, not a ROS talker/listener Deployment. It references `ros-jazzy-lab:local` with `imagePullPolicy: Never`. You **must preload that exact image into the container runtime of every node that may schedule it** before applying the manifest.

Do **not** apply it directly to an unmodified Vagrant cluster and expect an image pull or DDS exchange; that cluster uses separate VMs and containerd, with no automatic import from the developer's Docker engine.

If your **own** Kubernetes cluster is already configured and each worker has the image:

```bash
kubectl apply -f ROS2/jazzy/stress-deployment.yaml
kubectl -n ros get pods -l app=ros-jazzy-stress -o wide
# Cleanup when done:
kubectl -n ros delete deployment ros-jazzy-stress
```

No working Kubernetes setup is provided by this container-only migration. The first verified lightweight installation is a separate project task [#16](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/16).

## Optional ros2_pulse telemetry pilot (issue #52)

> **Status: pilot.** Only the same-container check below is automated. The Kubernetes manifest has had one contributor-reported run on a 3-node kind cluster ([details](#reported-kind-run-contributor-reported-not-reproduced)) that the maintainers have **not** reproduced. In that run the pods started, but talker-to-listener delivery between pods worked only after a discovery server was added, which this manifest does not include. No DDS-vs-Zenoh result is claimed.

[ros2_pulse](https://github.com/TanayK07/ros2_pulse) is an `LD_PRELOAD` probe. Inside each ROS 2 process it counts how often each topic is published and how often subscription callbacks run, and appends one window of rates per period to a log file. It needs no ROS rebuild, adds no node and sends no DDS traffic. The image installs it but does not enable it: a process is instrumented only when its own environment sets `LD_PRELOAD`.

| Added to the image | Exact version and source | License |
|---|---|---|
| Probe `/opt/ros/jazzy/lib/libros2_pulse.so` and `/opt/ros/jazzy/lib/ros2_pulse/pulse-check` | apt `ros-jazzy-ros2-pulse=0.5.0-1noble.20260914.160740`, main `packages.ros.org/ros2` repository | Apache-2.0 |
| `/opt/pulse-export/bin/pulse-export` (Prometheus `/metrics` over the probe's logs) | PyPI `ros2-pulse-top==0.6.1`, wheel sha256 `3a5cf388e836029fd82d416d4f81c348f0371a2c7e9a8e4e279607448610075a`, `--no-deps` venv | Apache-2.0 |
| `python3-venv`, only to hold that venv | Ubuntu noble `3.12.3-0ubuntu2.1` | Python (PSF) |

**How the versions were resolved (2026-10-28).** rosdistro `jazzy/distribution.yaml` releases ros2_pulse `0.7.0-1`, but that build (`0.7.0-1noble.20261021.153920`) is still only in `ros2-testing`. The main repository's noble index, which this image already uses for every other ROS package, lists `0.5.0-1noble.20260914.160740`, so that is the pin. Everything the pilot uses (the probe, jsonl output, `pulse-check` and its exit codes) exists in 0.5.0, and pulse-export 0.6.1 (the latest `ros2-pulse-top` on PyPI) reads 0.5.0 logs. After the next Jazzy sync the main index will list only the new build and this pin will stop installing; then update `ROS2_PULSE_VERSION` in the Dockerfile from `apt-cache policy ros-jazzy-ros2-pulse` (the `demo_nodes_cpp` pin may need the same refresh). pulse-export is stdlib only; the wheel's `textual` dependency is for the `pulse-top` terminal UI, which is removed from the venv.

The probe is configured per process with four variables, used in both the CI check and the manifest:

| Variable | Value here | Meaning |
|---|---|---|
| `LD_PRELOAD` | `/opt/ros/jazzy/lib/libros2_pulse.so` | Turns the probe on for this process. Unset means uninstrumented. |
| `ROS_TOPIC_STATS_OUTPUT_FILE` | `/var/log/ros2_pulse/talker.jsonl` or `listener.jsonl` in the pods | Log file. Without it the probe writes `$TMPDIR/topic_freq.<pid>.log`. |
| `ROS_TOPIC_STATS_FORMAT` | `jsonl` | One JSON object per window per line. |
| `ROS_TOPIC_STATISTICS_PUBLISH_PERIOD` | `5.0` | Window length and flush interval, in seconds. |

### Same-container check (automated in CI)

```bash
docker build --platform linux/amd64 --file ROS2/Dockerfile --tag ros-jazzy-lab:local .
docker run --rm -i --platform linux/amd64 --user 1000:1000 ros-jazzy-lab:local bash -s < scripts/test-ros2-pulse.sh
```

[`scripts/test-ros2-pulse.sh`](../../scripts/test-ros2-pulse.sh) fails if the image sets `LD_PRELOAD` by default or if the probe, `pulse-check` or `pulse-export` is missing. It then starts the `demo_nodes_cpp` listener and talker with the four variables on those two processes only, waits for three 5 s windows from each, and requires the probe start banner and an `I heard:` line. `pulse-check` must then pass a spec asking for `/chatter` at 0.5 Hz or more on the publish side (talker log) and the callback side (listener log), with `/talker` and `/listener` present. Last, `pulse-export` runs on `127.0.0.1:9464` and `/metrics` must carry positive `/chatter` publish and receive series. The existing `scripts/test-ros2-image.sh` still runs first with nothing preloaded.

### Kubernetes example (pilot)

[`pulse-talker-listener.yaml`](./pulse-talker-listener.yaml) creates the namespace `ros2-pulse-pilot` with two one-replica Deployments in separate pods: `pulse-talker` (containers `talker` and `pulse-export`) and `pulse-listener` (containers `listener` and `pulse-export`). In each pod:

- the probe variables are set on the ROS container only, not in the image and not on the sidecar;
- an `emptyDir` (64 Mi limit) is mounted read-write in the ROS container and read-only in `pulse-export`;
- `pulse-export` listens on `127.0.0.1:9464`; there is no Service, NodePort, LoadBalancer, hostPath or privileged container;
- containers run as uid 1000 with no privilege escalation, all capabilities dropped, the `RuntimeDefault` seccomp profile and no service account token, each with CPU and memory requests and limits.

The image is `ros-jazzy-lab:local` with `imagePullPolicy: Never`, like the stress example: build it from this commit and load it on every node that may run the pods. The published Docker Hub digest above predates ros2_pulse and does not contain it.

```bash
# Start (load the image into each node's container runtime first; on kind: kind load docker-image ros-jazzy-lab:local)
kubectl apply -f ROS2/jazzy/pulse-talker-listener.yaml
kubectl -n ros2-pulse-pilot wait --for=condition=Available deployment --all --timeout=180s
kubectl -n ros2-pulse-pilot get pods -o wide        # which node each pod runs on

# Verify: probe banner, demo traffic, and the latest window from each process
kubectl -n ros2-pulse-pilot logs deployment/pulse-talker -c talker | grep -m1 'ros2_pulse'
kubectl -n ros2-pulse-pilot logs deployment/pulse-listener -c listener --tail=3
kubectl -n ros2-pulse-pilot exec deployment/pulse-talker -c talker -- tail -n 1 /var/log/ros2_pulse/talker.jsonl
kubectl -n ros2-pulse-pilot exec deployment/pulse-listener -c listener -- tail -n 1 /var/log/ros2_pulse/listener.jsonl

# Metrics, forwarded to your own machine only (stop with Ctrl+C)
kubectl -n ros2-pulse-pilot port-forward deployment/pulse-talker 9464:9464
curl -s http://127.0.0.1:9464/metrics | grep 'topic="/chatter"'      # in a second terminal
kubectl -n ros2-pulse-pilot port-forward deployment/pulse-listener 9465:9464
curl -s http://127.0.0.1:9465/metrics | grep 'topic="/chatter"'

# Turn the probe off for one workload (the pod restarts uninstrumented)
kubectl -n ros2-pulse-pilot set env deployment/pulse-talker -c talker LD_PRELOAD-

# Clean up: removes both Deployments, their pods and the emptyDir logs
kubectl delete namespace ros2-pulse-pilot
```

The demo talker publishes once per second, so a working talker pod shows `ros2_pulse_topic_publish_rate_hertz{pid="talker.jsonl",topic="/chatter",path="inter"}` near 1. The listener pod shows a matching `ros2_pulse_topic_receive_rate_hertz` only if the two pods discovered each other. If it has no `/chatter` series and no `I heard:` lines, discovery between the pods failed, which is common on CNIs without multicast (see the [DDS guide](../../docs/ROS2-KUBERNETES-DDS-GUIDE.md)). This pilot does not fix discovery. With an explicit `ROS_TOPIC_STATS_OUTPUT_FILE`, pulse-export labels series with the file name (`pid="talker.jsonl"`), not a process id.

### Reported kind run (contributor-reported, not reproduced)

The contributor ran this manifest unchanged on a 3-node kind cluster (kind v0.33.0, Kubernetes v1.37.0, the node layout proposed in [#97](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/97)) in GitHub Actions on their fork, on amd64 and arm64, with an image built from this PR: [run 41160572458](https://github.com/TanayK07/ros2-kubernetes-lab/actions/runs/41160572458). Reported results:

- Both pods `2/2 Running` with 0 restarts over about 4 minutes, talker and listener on different workers; `kubectl port-forward` to the exporter worked.
- The talker's `/chatter` publish rate was 1.0 Hz on every scrape.
- **The listener received nothing**, and its `/chatter` series was absent rather than 0: multicast discovery did not reach between pods, also with both pods on one worker. With a Fast DDS discovery server added only in the contributor's CI overlay (not in this repository), the listener's `/chatter` rate was 1.0 Hz, 61 messages heard for 61 published.
- Each ROS container used about 155 MiB of its 256 Mi limit, flat, with no OOM kill; pulse-export used about 13 MB.
- arm64 built only when the arm64 apt pins were passed as build arguments, because the build farm stamps arm64 package versions differently. The Dockerfile pins are amd64 pins.

Not covered by that run: a real multi-machine cluster, other CNIs, restarts, scaling, more than one subscriber, long runs. **Until a discovery mechanism is added, treat the listener pod of this example as expected to report no `/chatter` series** on clusters without multicast between pods; see the [DDS guide](../../docs/ROS2-KUBERNETES-DDS-GUIDE.md). A discovery-server variant is a follow-up.

### Reading the numbers

- **Per-process counts, not end-to-end delivery.** The publish rate is `publish()` calls counted inside the talker process; the receive rate is subscription callbacks counted inside the listener process; each is a count divided by the window length. Nothing matches a received message to a sent one, so equal rates are consistent with delivery but do not prove that every message arrived once, in order or on time.
- **Multiple subscribers.** Each subscribing process reports its own callbacks. With K listener processes (for example `--replicas=2`, each with its own exporter) the receive rates add up to about K times the publish rate, and `pulse-check` sums receive rates across logs. Compare per process, not the sum.
- **Restarts.** A container restart inside the same pod keeps the `emptyDir`: the new process appends to the same file, its series keeps the same label, and its first window is a ramp-up window. With the probe's default `topic_freq.<pid>.log` names a new process gets a new `pid` series, but in containers process ids repeat (here the ROS process is PID 1 every time), so neither is a reliable restart marker; use the pod's `RESTARTS` count. A new pod starts with an empty volume, and earlier windows are gone unless copied out first.
- **Loss and QoS.** The demo uses reliable QoS. With best-effort QoS a dropped message shows up as a callback deficit (receive rate below publish rate). With reliable QoS retransmissions are invisible here: a message that needed several retransmits counts once on each side, so rates can match while the network does extra work. Reliable delivery can still lose messages when a history queue overflows.
- **Window alignment.** Each process starts its own window clock, so talker and listener windows are offset and one window can differ by a message (0.2 Hz at 1 Hz with 5 s windows). Compare several windows or totals over a longer interval, and skip each process's first window (ramp-up) and last window (cut short at exit). Before discovery completes the listener's windows have no `/chatter` entry at all; an absent topic means "not measured", not 0.

### What CI verifies and what still needs a cluster

| Check | Where | Status |
|---|---|---|
| Image builds with the pinned packages; `pulse-export --help` runs at build time | CI, [`ros2-image-ci.yml`](../../.github/workflows/ros2-image-ci.yml) | Automated on PRs touching the Dockerfile or test scripts |
| Default image unchanged: existing smoke test with nothing preloaded, no `LD_PRELOAD` in the image environment | CI | Automated |
| Probe, `pulse-check` and `pulse-export` with talker and listener in one container, as uid 1000 | CI, `scripts/test-ros2-pulse.sh` | Automated |
| Manifest applies; pods start with these security settings, limits and volume | 3-node kind | Contributor-reported, not reproduced |
| Talker to listener between two pods on one node | 3-node kind | Contributor-reported: **no delivery** without a discovery server; delivery with one (CI overlay only) |
| Talker to listener across workers | 3-node kind; real multi-node cluster ([#14](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/14), [#15](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/15)) | kind: contributor-reported, as above; real multi-node cluster **not run** |
| `kubectl port-forward` to the `127.0.0.1`-bound exporter | 3-node kind | Contributor-reported, not reproduced |
| Restarts, scaling, several subscribers | Any cluster | **Not run** |
| arm64 image | Contributor's fork CI | Builds only with arm64 apt pins passed as build arguments; the repository CI is amd64 only |

### Validating the counts later with sequence-numbered messages

For the broader benchmark ([#18](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/18), [#48](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/48)), check the probe counts against an independent count:

1. Publish test messages carrying a sequence number that increases by one per message, plus a send timestamp, at a fixed rate. For a first look, the demo talker's `Hello World: N` already carries a counter.
2. In the subscriber, record every received sequence number and derive received, missing, duplicate and out-of-order counts.
3. Over the same interval, compare messages sent (last minus first sequence number, plus one) with the talker's windows (sum of rate times `window_s`), and unique messages received with the listener's windows.
4. Use intervals much longer than one window (for example 60 s with 5 s windows), drop each process's first and last window, and repeat per RMW (DDS, Zenoh), QoS profile and topology.

Agreement within about one message per window boundary supports using the probe counts for that setup. A mismatch marks a setup where the per-process counts cannot stand in for delivery.

## Image provenance, version pinning and limits

| Layer | Choice | Verification level |
|---|---|---|
| ROS distribution | Jazzy Jalisco, LTS to May 2029 | Official upstream support documented |
| Ubuntu | Noble 24.04 | Docker base target; enforced by smoke script |
| Base image | `docker.io/library/ros:jazzy-ros-base-noble` with fixed `sha256` index in Dockerfile | Digest recorded in source, image pull/build verified by CI when green |
| Repository-built image | `ros-jazzy-with-stress-ng:sha-475988ae383e361ebbc60c1c6e0614ecd93694d1` | Published and smoke-tested in [run 38228962264](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/38228962264); digest recorded above; public pull access not yet independently checked |
| Architectures | `linux/amd64` | CI-covered when green; arm64 not validated |
| Additional apt packages | `ros-jazzy-demo-nodes-cpp=0.33.11-1noble.20260920.235420`, `stress-ng=0.17.06-1build1` | Direct package versions pinned from the successful 2026-10-12 CI installation; **transitive dependency versions are not locked** |
| ros2_pulse pilot packages | `ros-jazzy-ros2-pulse=0.5.0-1noble.20260914.160740`, `python3-venv=3.12.3-0ubuntu2.1`, PyPI `ros2-pulse-top==0.6.1` (wheel sha256 pinned, `--no-deps`) | Resolved from the package indexes on 2026-10-28; built and tested on amd64 in the PR's CI; **transitive apt versions are not locked** |
| Full Kubernetes environment | Legacy Kubernetes 1.29 / Weave Net | **Not modernized or tested** in this PR |
| Lyrical profile | Ubuntu 26.04 platform | Deferred; no claim of support |

**Reproducibility caveat:** The base-image digest is fixed, and a pushed image is referenced by a content digest and a source-commit tag. However, apt repositories can update. A rebuild from the same Git commit may resolve different apt package versions; fully hermetic/reproducible rebuilds require an apt snapshot or version lock and are still future work under [#7](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/7) / [#6](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/6). Consume a **published image digest** when an exact artifact matters.

**Original Foxy reference:** [`ROS2/legacy/foxy/Dockerfile`](../legacy/foxy/Dockerfile). The existing root-level Kubernetes YAML files still refer to the old Foxy stress image and **have deliberately not been silently migrated to an untested modern cluster**.

**Drone-specific image:** The original issue mentioned a drone use case, but no actual drone runtime/executables or tests exist in the current Dockerfile; this step installs only `demo_nodes_cpp` and `stress-ng`. A specific drone example will need its own requirements and validation.

## References

- [ROS 2 Jazzy LTS release and Ubuntu Noble support](https://www.openrobotics.org/blog/2024/5/ros-jazzy-jalisco-released)
- [Docker Official ROS image tags](https://hub.docker.com/_/ros)
- [Fast DDS in ROS 2](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html)
