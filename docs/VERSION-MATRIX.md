# Version and dependency matrix

**Purpose:** one place that says which versions this repository pins, in which file and line, which stack each pin belongs to, and what has and has not been run. Versions were stated in several READMEs and drifted ([#44](https://github.com/MSKazemi/robo-resilience-lab/issues/44)). When a pin changes, update this page in the same pull request.

> **Read this first.** A version listed here is a *declared* pin in a file. It is not evidence that the component was installed, started or tested, unless the "Evidence" column says so. Static checks (Markdown links, shell syntax, manifest schemas) do **not** prove cross-node ROS 2 or DDS delivery. This is an educational/research lab, not a production or safety-critical platform.

Paths are repository-relative with a line number (`file:line`) as of 2026-11-06. External end-of-life dates are quoted from this repository's own files; they were **not** re-fetched from upstream. Evidence quoted from `docs/KIND-DEMO.md` or `ROS2/jazzy/README.md` was **not** re-run for this page.

## 1. The three stacks

| Stack | Role | Support state ([definitions](./ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)) |
|---|---|---|
| **Modern container baseline**: ROS 2 Jazzy on Ubuntu 24.04 | Current image for experiments | `container tested` (one container, linux/amd64) |
| **Lightweight kind profile**: 1 control plane + 2 workers | Current way to run ROS 2 across Kubernetes workers | `cross-worker verified` for this profile only, per [`docs/KIND-DEMO.md`](./KIND-DEMO.md) |
| **Historical Vagrant lab**: Foxy, Kubernetes 1.29, Weave Net | Original teaching material | `legacy` (end-of-life or archived components) |

Do not mix pins across stacks. The Jazzy image is **not** referenced by the Foxy `ROS2/ros_dep_*.yaml` manifests, and nothing here shows that the Vagrant cluster provisions today.

## 2. Modern container baseline (Jazzy / Ubuntu 24.04)

| Component | Pinned value | Where | Evidence recorded in the repository |
|---|---|---|---|
| Base image | `docker.io/library/ros:jazzy-ros-base-noble@sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4` | `ROS2/Dockerfile:5` | `ROS2/Dockerfile:11` says the direct apt versions were observed in a successful 2026-10-12 CI build |
| `ros-jazzy-demo-nodes-cpp` | `0.33.11-1noble.20260920.235420` | `ROS2/Dockerfile:13` | Same. Direct apt versions only: **transitive apt packages are not locked**, so a rebuild can differ |
| `stress-ng` | `0.17.06-1build1` | `ROS2/Dockerfile:14` | Same |
| `ros-jazzy-ros2-pulse` (opt-in telemetry pilot) | `0.5.0-1noble.20260914.160740` | `ROS2/Dockerfile:20` | `ROS2/jazzy/README.md` ("Image provenance, version pinning and limits") says it was resolved on 2026-10-28 and built and tested on amd64 in that pull request's CI |
| `python3-venv` (hosts the `pulse-export` venv) | `3.12.3-0ubuntu2.1` | `ROS2/Dockerfile:22` | Same |
| `ros2-pulse-top` (PyPI, provides `pulse-export`) | `0.6.1`, wheel sha256 `3a5cf388e836029fd82d416d4f81c348f0371a2c7e9a8e4e279607448610075a`, `--no-deps` | `ROS2/Dockerfile:36-37` | Same |
| ROS 2 distribution | Jazzy Jalisco, Ubuntu 24.04 (Noble); `ROS2/jazzy/README.md` states support "through May 2029" | `ROS2/jazzy/README.md:5` | Distro and OS are asserted at run time by `scripts/test-ros2-image.sh:12,19` (`ROS_DISTRO == jazzy`, `VERSION_ID == 24.04`) |
| Platform | `linux/amd64` only | `ROS2/jazzy/README.md` ("Build and verify locally") | arm64 is **not** claimed; the README records a contributor-reported arm64 build that needed extra build arguments and was not reproduced |
| Lyrical | Not supported | `ROS2/jazzy/README.md` ("Image provenance, version pinning and limits": "Lyrical profile ... Deferred; no claim of support") | None |
| Last published image | Tag `sha-475988ae383e361ebbc60c1c6e0614ecd93694d1`, OCI index digest `sha256:8dd782f9382c123dc319330f8c0d012d790ae93b6752e26df6b2b47a4cdb720c` | `ROS2/jazzy/README.md` ("First verified published image") | Published and smoke-tested in Actions run 38228962264 (2026-10-12). The README states it predates `ros2_pulse` ("The image is `ros-jazzy-lab:local` ... The published Docker Hub digest above predates ros2_pulse"). Public pull access was not independently checked |
| Local image names | `ros-jazzy-lab:local` (stress example and test commands); `ros2k8s-demo-ros:local` (kind profile) | `ROS2/jazzy/stress-deployment.yaml:29`; `Makefile:15` | Built locally, never pushed |

## 3. Lightweight kind profile

| Component | Pinned value | Where | Evidence recorded in the repository |
|---|---|---|---|
| kind | `v0.33.0` in CI; `Makefile` asks for "v0.33.0 or newer" | `.github/workflows/kind-demo.yml:26` (sha256 on line 27); `Makefile:33` | One run on one host, 2026-10-27, commit `862b026`: `make demo` exit 0, `make verify` exit 0, `make verify-negative` exit 0 (`docs/KIND-DEMO.md`, "Measured on this host") |
| Node image | `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5` for all three nodes | `kind/ros2k8s-demo.yaml:15,20,24` | Same run |
| kubectl | `v1.37.1` in CI (sha256 on line 29); `Makefile` asks for "any version within one minor of Kubernetes 1.37" | `.github/workflows/kind-demo.yml:28`; `Makefile:34` | Same run used kubectl v1.37.1 |
| Cluster name / context | `ros2k8s-demo` / `kind-ros2k8s-demo` | `kind/ros2k8s-demo.yaml:12`; `Makefile:14` | Same run |
| CNI | kindnetd (the kind default) | `docs/KIND-DEMO.md` ("What `make demo` creates") | Default multicast discovery **did not** deliver on this CNI, across workers or on one worker; delivery worked through a Fast DDS Discovery Server |
| DDS settings | `ROS_DOMAIN_ID=42`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_DISCOVERY_SERVER=discovery-server.ros.svc.cluster.local:11811`, `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` | `ROS2/jazzy/talker-listener.yaml:37-42` | Same run |
| CI for the profile | `.github/workflows/kind-demo.yml` runs `make demo`, `make verify`, `make verify-negative`, `make clean` on `ubuntu-24.04` | `docs/KIND-DEMO.md` ("CI") | That page says the workflow had not been executed when it was written. This page does not check GitHub for a run |
| Not covered | arm64, macOS, Windows/WSL, other CNIs, a real multi-machine cluster, QoS other than the demo defaults | `docs/KIND-DEMO.md` ("Limits") | Not run |

## 4. Historical Vagrant lab (legacy)

| Component | Pinned value | Where | Status |
|---|---|---|---|
| Vagrant box | `ubuntu/jammy64` (Ubuntu 22.04, x86-64 VirtualBox only) | `Vagrantfile:49` | Not run for this page |
| VM sizing | Default profile 18240 MB / 14 vCPUs (control plane) and 6096 MB / 2 vCPUs for each of two workers: 30432 MB and 18 vCPUs in total. `small` profile 8192/4 and 4096/2, described in the file as "NOT validated end to end" | `Vagrantfile:22-23` (comment at lines 17-18) | Read from the file only |
| Kubernetes | `v1.29` apt repository on `pkgs.k8s.io`; packages held with `apt-mark hold` | `KubernetesClusterSetup/kubeadm_kubelet_kubectl.sh:11,14,19` | The DDS guide (`docs/ROS2-KUBERNETES-DDS-GUIDE.md:132`) calls 1.29 end of support. Not run |
| API address / pod CIDR | `192.168.56.10` / `10.244.0.0/16` | `KubernetesClusterSetup/create_cluster.sh:6` | Not run |
| CNI | Weave Net `v2.8.1` | `Network/network_plugin.sh:4` | The DDS guide (`docs/ROS2-KUBERNETES-DDS-GUIDE.md:19`) says it is archived upstream. Not run; whether Weave Net passes multicast for ROS 2 discovery was never verified |
| Kubernetes Dashboard | `v2.7.0` manifest | `MonitoringSystem/monitoring.sh:12` | Not run. Roadmap item [#4](https://github.com/MSKazemi/robo-resilience-lab/issues/4) tracks replacing the archived Dashboard |
| Helm chart `kube-prometheus-stack` | **Unpinned**: `helm install` without `--version` | `MonitoringSystem/monitoring.sh:61` | Not run |
| ROS image (Foxy) | `docker.io/kazemi/ros-foxy-with-stress-ng` in the manifests; `osrf/ros:foxy-desktop` base in the recipe. The recipe states Foxy reached end of life in June 2023 | `ROS2/ros_dep_1.yaml:32`; `ROS2/legacy/foxy/Dockerfile:1,4` | The manifests start `stress-ng`, **not** a talker or listener |

## 5. Offline analysis and tooling

| Component | Pinned value | Where | Evidence |
|---|---|---|---|
| Python for the offline analysis | 3.12 (numpy 2.5 needs 3.12 or newer); the header says it was verified on 3.12.3, Linux, 2026-10-28 | `DataAnalysis/requirements-offline.txt:2-3` | Header statement; not re-run for this page |
| matplotlib / numpy / pytest | `3.11.2` / `2.5.4` / `9.2.0`, plus pinned transitive packages | `DataAnalysis/requirements-offline.txt:17-19` | Same |
| Notebooks and live-Prometheus scripts | **No pinned file.** `requirements-offline.txt` deliberately excludes `prometheus-api-client`, `requests`, `pandas` and Jupyter (its header, lines 12-14) | `DataAnalysis/requirements-offline.txt` | None |
| Python for repo scripts and CI | `3.12` | `.github/workflows/offline-checks.yml:32`, `validate-markdown-links.yml:37`, `cross-platform.yml:39`, `analysis-offline.yml:37`, `mock-policy-contract.yml:35` | CI configuration only |
| Mock-policy contract | Python 3.10 or newer, standard library only | `examples/cloud-robotics/mock-policy/README.md` ("Verify") | Unit tests and a fixture drift check; see the [experiment registry](./EXPERIMENT-STATUS.md#h-observationaction-contract-and-mock-policy-e00) |
| kubeconform | `v0.8.0`, sha256 verified on download; schemas for Kubernetes `1.29.0` | `scripts/validate-k8s-manifests.py:49,59`; `.github/workflows/validate-k8s.yml:26` | Static schema check, no cluster |
| CI runners | `ubuntu-24.04`; `windows-2025` and `macos-15` for the cross-platform job | `.github/workflows/*.yml` (`runs-on`); `.github/workflows/cross-platform.yml:25` | Windows and macOS cover the static tooling only; they have no Vagrant or VirtualBox |

## 6. GitHub Actions pins

| Action | Version (from comments in the files) | Where |
|---|---|---|
| `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` | v4.2.2 | `cross-platform.yml:34`, `mock-policy-contract.yml:30`, `analysis-offline.yml:32`, `main.yaml:28,45`, `validate-k8s.yml:34`, `validate-shell.yml:22`, `ros2-image-ci.yml:26`, `validate-markdown-links.yml:32` |
| `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` | v7.0.1 | `offline-checks.yml:25`, `kind-demo.yml:41`, `pages.yml:34,60` |
| `actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | v7.1.0 | `cross-platform.yml:37`, `validate-markdown-links.yml:35`, `analysis-offline.yml:35`, `mock-policy-contract.yml:33`, `offline-checks.yml:30` |
| `docker/login-action@v3`, `docker/setup-buildx-action@v3`, `docker/build-push-action@v6` | Mutable major tags, **not** pinned to a commit | `main.yaml:47,52,55` |
| `actions/configure-pages@45bfe019…` / `upload-pages-artifact@fc324d35…` / `deploy-pages@368f8252…` | v6.0.0 / v5.0.0 / v5.0.1 | `pages.yml:63,64,68` |

## 7. Drift visible in the files

These are mismatches found by reading the files. They are listed so they can be fixed; this page does not fix them.

1. **Two `actions/checkout` pins** (v4.2.2 and v7.0.1) are in use; see section 6.
2. **`main.yaml` uses mutable tags** for the three Docker actions (`@v3`, `@v3`, `@v6`) while the other workflows pin commit SHAs.
3. **Monitoring defaults are broad.** `MonitoringSystem/monitoring.sh:53,55` runs `chmod -R 777`, line 23 appends the Dashboard token to a file named `token` in the current directory, and `MonitoringSystem/admin-user.yaml:25` binds `cluster-admin`. `MonitoringSystem/README.md` does not say so; treat the monitoring scripts as a lab convenience, not a safe default.
4. **Published image is older than the source.** The digest in `ROS2/jazzy/README.md` ("First verified published image") was built from commit `475988a` and, per that README, contains no `ros2_pulse`. Do not use it to describe the current Dockerfile.
5. **Glossary is stale on one point.** `docs/GLOSSARY.md` ("Support States") still says `cross-worker verified` is "Not achieved yet", while `docs/KIND-DEMO.md` ("Support states") records it for the kind profile.
6. **Old repository name in places.** `docs/KIND-DEMO.md` uses the older name `Vagrant-Kubernetes-ROS2-Deployment` in its clone commands and issue links.
7. **Monitoring chart is unpinned** (section 4), so a rerun can install a different chart version than any earlier run.

## 8. How the claims on this page were checked

| Check | Command (repository root) | Result on 2026-11-06 |
|---|---|---|
| Local Markdown links and anchors | `python3 scripts/check-markdown-links.py` | See the report that accompanies this change; the checker reads only Git-tracked files |
| Whole-repository unit tests | `python3 -I -B -m unittest discover -s tests` | exit 0 |
| Per-module unit tests | the commands in [`EXPERIMENT-STATUS.md`](./EXPERIMENT-STATUS.md) | exit 0 each |
| Docker build, kind cluster, `make demo` / `make verify` | not run | Out of scope: no image builds and no clusters were created |
