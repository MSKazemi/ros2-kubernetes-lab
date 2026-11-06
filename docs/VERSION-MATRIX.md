# Version and dependency matrix

**Purpose:** one place that says which versions this repository actually pins, where (file and line), which stack each pin belongs to, and what has and has not been run. It exists because versions were stated in several READMEs and drifted ([#44](https://github.com/MSKazemi/robo-resilience-lab/issues/44)). When a pin changes, update this page in the same pull request.

> **Read this first.** A version listed here is a *declared* pin in a file. It is not evidence that the component was installed, started or tested, unless the "Evidence" column says so. Static checks (Markdown links, shell syntax, manifest schemas) do **not** prove cross-node ROS 2 or DDS delivery. This is an educational/research lab, not a production or safety-critical platform.

**How to read the "Where" column.** Paths are repository-relative with a line number (`file:line`). Rows marked **[main]** cite files that exist on public `origin/main` (commit `3e4d7aa`, 2026-11-06 inspection) but not yet on branch `docs/contributors-and-ai-guide-refresh`; they were read from a read-only copy of `main`, not from this branch. Every other row was read from the branch tree.

**Last reviewed:** 2026-11-06. External end-of-life dates below are quoted from this repository's own files; they were **not** re-fetched from upstream in this review.

## 1. The three stacks

| Stack | Role | Support state ([definitions](./ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)) |
|---|---|---|
| **Modern container baseline**: ROS 2 Jazzy on Ubuntu 24.04 | Current image for experiments | `container tested` (one container, linux/amd64) |
| **Lightweight kind profile**: 1 control plane + 2 workers | Current way to run ROS 2 across Kubernetes workers | `cross-worker verified` for this profile only, per [`docs/KIND-DEMO.md`](./KIND-DEMO.md) **[main]** |
| **Historical Vagrant lab**: Foxy, Kubernetes 1.29, Weave Net | Original teaching material | `legacy` (end-of-life or archived components) |

Do not mix pins across stacks. For example, the Jazzy image is **not** referenced by the Foxy `ROS2/ros_dep_*.yaml` manifests, and nothing in this table shows that the Vagrant cluster still provisions today.

## 2. Modern container baseline (Jazzy / Ubuntu 24.04)

| Component | Pinned value | Where | Evidence recorded in the repository |
|---|---|---|---|
| Base image | `docker.io/library/ros:jazzy-ros-base-noble@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617` (branch). `main` still carries `sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4`. | `ROS2/Dockerfile:5`; **[main]** `ROS2/Dockerfile:5` | Commit `63f8d2b` (2026-10-31) states: docker build and `scripts/test-ros2-image.sh` passed locally, single container only; the publish job was not run |
| `ros-jazzy-demo-nodes-cpp` | `0.33.11-1noble.20260920.235420` | `ROS2/Dockerfile:13` | Same smoke test. Direct apt versions only: **transitive apt packages are not locked**, so a rebuild can differ |
| `stress-ng` | `0.17.06-1build1` | `ROS2/Dockerfile:14` | Same |
| `ros-jazzy-ros2-pulse` (opt-in telemetry pilot) | `0.5.0-1noble.20260914.160740` | **[main]** `ROS2/Dockerfile:20` | Built and tested on amd64 in that pull request's CI, per `ROS2/jazzy/README.md` on `main` |
| `python3-venv` (hosts the `pulse-export` venv) | `3.12.3-0ubuntu2.1` | **[main]** `ROS2/Dockerfile:22` | Same |
| `ros2-pulse-top` (PyPI, provides `pulse-export`) | `0.6.1`, wheel sha256 `3a5cf388e836029fd82d416d4f81c348f0371a2c7e9a8e4e279607448610075a`, `--no-deps` | **[main]** `ROS2/Dockerfile:36-37` | Same |
| ROS 2 distribution | Jazzy Jalisco, Ubuntu 24.04 (Noble). Repository documents support "through May 2029" | `ROS2/jazzy/README.md:5` | Distro and OS are asserted at run time by `scripts/test-ros2-image.sh:12,19` (`ROS_DISTRO == jazzy`, `VERSION_ID == 24.04`) |
| Platform | `linux/amd64` only | `ROS2/jazzy/README.md` ("Build and verify locally") | arm64 is **not** claimed. A contributor reported arm64 only builds with extra build arguments (**[main]** `ROS2/jazzy/README.md`, "Reported kind run") and the maintainers have not reproduced it |
| Last published image | `ros-jazzy-with-stress-ng:sha-475988ae383e361ebbc60c1c6e0614ecd93694d1`, OCI index digest `sha256:8dd782f9382c123dc319330f8c0d012d790ae93b6752e26df6b2b47a4cdb720c` | `ROS2/jazzy/README.md` ("First verified published image") | Published and smoke-tested in Actions run 38228962264 (2026-10-12). It **predates** the base-digest refresh and the ros2_pulse additions. Public pull access was not independently checked |
| Local image names | `ros-jazzy-lab:local` (stress example, test commands); `ros2k8s-demo-ros:local` (kind profile) | `ROS2/jazzy/stress-deployment.yaml:29`; **[main]** `Makefile:15` | Built locally, never pushed |

## 3. Lightweight kind profile

| Component | Pinned value | Where | Evidence recorded in the repository |
|---|---|---|---|
| kind | `v0.33.0` (Makefile asks for "v0.33.0 or newer") | **[main]** `.github/workflows/kind-demo.yml:26` (sha256 on line 27); **[main]** `Makefile:33` | Run once on one host, 2026-10-27, commit `862b026`: `make demo` exit 0, `make verify` exit 0, `make verify-negative` exit 0 (`docs/KIND-DEMO.md`, "Measured on this host") |
| Node image | `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5` for all three nodes | **[main]** `kind/ros2k8s-demo.yaml:15,20,24` | Same run |
| kubectl | `v1.37.1` in CI (sha256 on line 29); Makefile asks for "any version within one minor of Kubernetes 1.37" | **[main]** `.github/workflows/kind-demo.yml:28`; **[main]** `Makefile:34` | Same run used kubectl v1.37.1 |
| Cluster name / context | `ros2k8s-demo` / `kind-ros2k8s-demo` | **[main]** `kind/ros2k8s-demo.yaml:12`; **[main]** `Makefile:14,18` | Same run |
| CNI | kindnetd (the kind default) | **[main]** `docs/KIND-DEMO.md` ("What `make demo` creates") | Default multicast discovery **did not** deliver on this CNI, across workers or on one worker; delivery worked through a Fast DDS Discovery Server |
| DDS settings | `ROS_DOMAIN_ID=42`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_DISCOVERY_SERVER=discovery-server.ros.svc.cluster.local:11811`, `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` | **[main]** `ROS2/jazzy/talker-listener.yaml:37-42` | Same run |
| CI for the profile | `.github/workflows/kind-demo.yml` runs `make demo`, `make verify`, `make verify-negative`, `make clean` on `ubuntu-24.04` | **[main]** `.github/workflows/kind-demo.yml` | `docs/KIND-DEMO.md` ("CI") says the workflow **had not been executed** when written. This review did not confirm a green run |
| Not covered | arm64, macOS, Windows/WSL, other CNIs, a real multi-machine cluster, QoS other than the demo defaults | **[main]** `docs/KIND-DEMO.md` ("Limits") | Not run |

Branch-only artefact: `ROS2/jazzy/talker-listener-kind.yaml` (lines 43, 71, 107) points at the published image digest `sha256:8dd782f9…` and a Fast DDS Discovery Server. It is an earlier, manual variant that the self-starting `ROS2/jazzy/talker-listener.yaml` on `main` supersedes. Keep only one of them in the integrated tree and make `ROS2/README.md` name that one.

## 4. Historical Vagrant lab (legacy)

| Component | Pinned value | Where | Status |
|---|---|---|---|
| Vagrant box | `ubuntu/jammy64` (Ubuntu 22.04, x86-64 VirtualBox only) | `Vagrantfile:49` | Not run in this review |
| VM sizing | Default profile 18240 MB / 14 vCPUs (control plane) and 6096 MB / 2 vCPUs (each of 2 workers): 30432 MB and 18 vCPUs in total. `small` profile 8192/4 and 4096/2, "NOT validated end to end" | `Vagrantfile:22-23` (comment at `Vagrantfile:17`) | Read from the file only |
| Kubernetes | minor `1.29` through `pkgs.k8s.io`, packages held with `apt-mark hold` | `KubernetesClusterSetup/kubeadm_kubelet_kubectl.sh:10,26` | The script itself says 1.29 is end-of-life upstream (2025-02-28, comment at lines 8-9). Not run |
| Pod CIDR / API address | `10.244.0.0/16` / `192.168.56.10` | `KubernetesClusterSetup/create_cluster.sh:15` | Not run |
| CNI | Weave Net `v2.8.1`, upstream archived 2024-06-20 | `Network/network_plugin.sh:8` (comment at line 3) | Not run. Whether Weave Net passes multicast for ROS 2 discovery was never verified |
| Kubernetes Dashboard | `v2.7.0` manifest | `MonitoringSystem/monitoring.sh:16` | Not run. Roadmap item [#4](https://github.com/MSKazemi/robo-resilience-lab/issues/4) tracks replacing the archived Dashboard |
| Helm chart `kube-prometheus-stack` | **Unpinned** in `monitoring.sh:68`. `helm template` and `kubeconform` were run against chart `92.16.1` (app v0.94.2) with Helm v4.3.1 and kubeconform v0.8.0 | `MonitoringSystem/README.md:177,186` | Chart install into kind was **not** completed; Prometheus and Grafana health checks were **not** run |
| ROS image (Foxy) | `docker.io/kazemi/ros-foxy-with-stress-ng` (manifests); `osrf/ros:foxy-desktop` base in the recipe. Foxy end of life 2023-06-20 per the ROS 2 release table cited by the DDS guide | `ROS2/ros_dep_1.yaml:32`; `ROS2/legacy/foxy/Dockerfile:4` | The manifests start `stress-ng`, **not** a talker or listener. A Foxy talker/listener on kind delivered 0 messages in a manual test on 2026-10-31 (`ROS2/README.md`) |

## 5. Offline analysis and tooling

| Component | Pinned value | Where | Evidence |
|---|---|---|---|
| Python for the offline analysis | 3.12 (numpy 2.5 needs 3.12 or newer); verified 2026-10-28 on 3.12.3, Linux | **[main]** `DataAnalysis/requirements-offline.txt:1-3` | Pinned file written from a verified environment, per its header |
| matplotlib / numpy / pytest | `3.11.2` / `2.5.4` / `9.2.0` plus 13 transitive pins | **[main]** `DataAnalysis/requirements-offline.txt:17-19` | Same |
| Notebook and live-Prometheus stack (the branch's pins, reference only) | matplotlib 3.11.2, numpy 2.5.4, pandas 3.1.0, prometheus-api-client 0.7.2, requests 2.34.2, PyYAML 6.0.3, ipython 9.18.0, ipykernel 7.4.0, nbconvert 7.17.2 | Not in the integrated tree: the branch's `DataAnalysis/requirements.txt` is dropped in favour of main's `requirements-offline.txt` | The branch file's header said "latest stable PyPI releases" at 2026-10-31. Nothing in the repository installs these packages now |
| Python for repo scripts and CI | `3.12` | `.github/workflows/cross-platform.yml:37`, `.github/workflows/validate-markdown-links.yml:35`; **[main]** `mock-policy-contract.yml:33` | CI config only |
| Mock-policy contract | Python 3.10 or newer, standard library only | **[main]** `examples/cloud-robotics/mock-policy/README.md` ("Verify") | 84 unit tests, `OK`, exit 0, run by this review against a read-only copy of `main` (see section 7) |
| kubeconform | `v0.8.0`, sha256 verified on download; schemas for Kubernetes `1.29.0` | **[main]** `scripts/validate-k8s-manifests.py:49,59`; **[main]** `.github/workflows/validate-k8s.yml:26` | Static schema check, no cluster |
| CI runners | `ubuntu-24.04`; `windows-2025` and `macos-15` for the cross-platform job | `.github/workflows/*.yml` (`runs-on`); `.github/workflows/cross-platform.yml:23` | Windows/macOS cover the static tooling only. They have no Vagrant or VirtualBox |

Only **[main]** `DataAnalysis/requirements-offline.txt` is pinned (offline, tested). The packages that `backup.py`, `helper.py` and the notebooks import (`prometheus_api_client`, `pandas`, `IPython`) are not pinned anywhere in the repository.

## 6. GitHub Actions pins

| Action | Version (comment in file) | Commit SHA | Where |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | `.github/workflows/pages.yml:32`, `main.yaml:25`, `ros2-image-ci.yml:23`, `cross-platform.yml:32`, `validate-markdown-links.yml:30`, `validate-shell.yml:20`; **[main]** `kind-demo.yml:39` |
| `actions/checkout` | v4.2.2 (per comment in `mock-policy-contract.yml`) | `11bd71901bbe5b1630ceea73d27597364c9af683` | **[main]** `validate-k8s.yml:32`, `analysis-offline.yml:30`, `mock-policy-contract.yml:28` |
| `actions/setup-python` | v7.1.0 (per comment) | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | `cross-platform.yml:35`, `validate-markdown-links.yml:33`; **[main]** `analysis-offline.yml:33`, `mock-policy-contract.yml:31` |
| `docker/login-action` / `setup-buildx-action` / `build-push-action` | v4.7.0 / v4.4.1 / v7.4.0 | `81c6f93d…` / `f87e5991…` / `c3c9e263…` | `main.yaml:41,46,49` |
| `actions/configure-pages` / `upload-pages-artifact` / `deploy-pages` | v6.0.0 / v5.0.0 / v5.0.1 | `45bfe019…` / `fc324d35…` / `368f8252…` | `pages.yml:60,61,65` |

## 7. Drift found while building this matrix

These are mismatches between files, found by reading them. None has been fixed outside the files this page's author owns.

1. **Two `actions/checkout` pins.** Branch workflows use v7.0.1 (`3d3c42e5…`); three workflows that exist only on `main` still use v4.2.2 (`11bd7190…`). After integration, align them.
2. **Two base-image digests.** Branch `8eed0a46…` (refreshed 2026-10-31, commit `63f8d2b`) versus `main` `2589a8fb…`. The branch is newer. Integration must keep the branch digest **and** `main`'s ros2_pulse lines in `ROS2/Dockerfile`; a plain rebase may conflict there.
3. **Repository slug in `main`.** `ROS2/Dockerfile` label (`org.opencontainers.image.source`) and `docs/KIND-DEMO.md` (which still uses the older name `Vagrant-Kubernetes-ROS2-Deployment`) on `main` do not use `robo-resilience-lab`. `docs/KIND-DEMO.md` is not owned by the technical-docs role; the lead should update it.
4. **Published image is older than the source.** The Docker Hub digest recorded in `ROS2/jazzy/README.md` was built from commit `475988a` and contains neither the refreshed base nor ros2_pulse. Do not use it to describe the current Dockerfile.
5. **Monitoring chart is unpinned** in `monitoring.sh` but the only verification used 92.16.1; `MonitoringSystem/README.md:186` already says so.
6. **`DataAnalysis` has two diverging READMEs** (branch hardening versus `main` offline analysis). Merged proposal in the plans directory named above.

## 8. How these claims were checked in this review

| Check | Command (from the repository root unless noted) | Result |
|---|---|---|
| Local Markdown links and anchors on the branch tree | `python3 -I scripts/check-markdown-links.py` | On the branch tree alone the checker reports links to files that exist only on public `main` (for example `docs/KIND-DEMO.md`); on a copy of `main` with this documentation overlaid it reported 0 broken links in 70 files, exit 0. The checker only reads Git-tracked files, so a new file must be added to Git before it is covered in CI |
| Mock-policy unit tests (read-only copy of `main`) | `python3 -B -m unittest discover -s examples/cloud-robotics/mock-policy/tests` | 84 tests, `OK`, exit 0 |
| Mock-policy fixtures not drifted (same copy) | `python3 -B examples/cloud-robotics/mock-policy/fixture_gen.py --check` | exit 0. With `python3 -I` it fails (`No module named 'contract'`) because `-I` removes the script directory from the import path; use the plain command shown in that README |
| Offline analysis tests (same copy) | `python3 -B -m unittest discover -s DataAnalysis/tests` | **Not run to completion**: `pytest` is not installed on this host, so the test module fails at import. This is an environment gap, not a test result |
| Docker build, kind cluster, `make demo` / `make verify` | not run | Out of scope for this review (no image builds, no clusters) |
