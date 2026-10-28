# ROS 2 Jazzy image — Ubuntu 24.04 (container-level baseline)

This directory describes the **new ROS 2 Jazzy container baseline** from [`ROS2/Dockerfile`](../Dockerfile). It is separate from the [historical Foxy Vagrant/Kubernetes lab](../README.md).

**ROS 2 Jazzy Jalisco** is an LTS distribution with official Ubuntu 24.04 (Noble) support through May 2029. The image builds from the official `ros:jazzy-ros-base-noble` image pinned to a specific OCI registry digest, and installs:

- `ros-jazzy-demo-nodes-cpp` for talker and listener examples;
- `stress-ng` for CPU/memory workloads.

This is a **container baseline only**, not a claim that the historical Kubernetes 1.29 / Weave Net / Vagrant cluster is updated or that talker and listener communicate between **different Kubernetes workers**.

## Build and verify locally

Requires a running Docker engine and enough disk/network capacity to download the ROS base image and apt packages. For the first validated build, CI targets **linux/amd64**. The upstream ROS base also offers arm64, but this repository does not claim that its own image has passed arm64 tests.

From the **repository root**:

```bash
docker build --platform linux/amd64 --file ROS2/Dockerfile --tag ros-jazzy-lab:local .
docker run --rm -i --platform linux/amd64 ros-jazzy-lab:local bash -s < scripts/test-ros2-image.sh
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

## Image provenance, version pinning and limits

| Layer | Choice | Verification level |
|---|---|---|
| ROS distribution | Jazzy Jalisco, LTS to May 2029 | Official upstream support documented |
| Ubuntu | Noble 24.04 | Docker base target; enforced by smoke script |
| Base image | `docker.io/library/ros:jazzy-ros-base-noble` with fixed `sha256` index in Dockerfile | Digest recorded in source, image pull/build verified by CI when green |
| Repository-built image | `ros-jazzy-with-stress-ng:sha-475988ae383e361ebbc60c1c6e0614ecd93694d1` | Published and smoke-tested in [run 38228962264](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/38228962264); digest recorded above; public pull access not yet independently checked |
| Architectures | `linux/amd64` | CI-covered when green; arm64 not validated |
| Additional apt packages | `ros-jazzy-demo-nodes-cpp=0.33.11-1noble.20260920.235420`, `stress-ng=0.17.06-1build1` | Direct package versions pinned from the successful 2026-10-12 CI installation; **transitive dependency versions are not locked** |
| Full Kubernetes environment | Legacy Kubernetes 1.29 / Weave Net | **Not modernized or tested** in this PR |
| Lyrical profile | Ubuntu 26.04 platform | Deferred; no claim of support |

**Reproducibility caveat:** The base-image digest is fixed, and a pushed image is referenced by a content digest and a source-commit tag. However, apt repositories can update. A rebuild from the same Git commit may resolve different apt package versions; fully hermetic/reproducible rebuilds require an apt snapshot or version lock and are still future work under [#7](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/7) / [#6](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/6). Consume a **published image digest** when an exact artifact matters.

**Original Foxy reference:** [`ROS2/legacy/foxy/Dockerfile`](../legacy/foxy/Dockerfile). The existing root-level Kubernetes YAML files still refer to the old Foxy stress image and **have deliberately not been silently migrated to an untested modern cluster**.

**Drone-specific image:** The original issue mentioned a drone use case, but no actual drone runtime/executables or tests exist in the current Dockerfile; this step installs only `demo_nodes_cpp` and `stress-ng`. A specific drone example will need its own requirements and validation.

## References

- [ROS 2 Jazzy LTS release and Ubuntu Noble support](https://www.openrobotics.org/blog/2024/5/ros-jazzy-jalisco-released)
- [Docker Official ROS image tags](https://hub.docker.com/_/ros)
- [Fast DDS in ROS 2](https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html)
