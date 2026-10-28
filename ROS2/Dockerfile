# syntax=docker/dockerfile:1
# Supported ROS 2 container baseline (not an upgrade of the legacy Vagrant cluster).
# Official multi-platform Jazzy/Noble ROS base; this OCI index digest is immutable.
# Ref: https://hub.docker.com/layers/library/ros/jazzy-ros-base-noble/images/sha256-f652c502c971653afc2ed9b9e5929643df644e6125b6ee68349408b6cc2f64cd
FROM docker.io/library/ros:jazzy-ros-base-noble@sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4

LABEL org.opencontainers.image.source="https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment" \
      org.opencontainers.image.description="ROS 2 Jazzy on Ubuntu 24.04: demo_nodes_cpp, stress-ng and opt-in ros2_pulse telemetry for educational experiments"

ARG DEBIAN_FRONTEND=noninteractive
# Direct apt package versions observed in successful 2026-10-12 CI build.
# Transitive apt dependencies still need a snapshot for fully hermetic rebuilds.
ARG ROS_DEMO_NODES_CPP_VERSION=0.33.11-1noble.20260920.235420
ARG STRESS_NG_VERSION=0.17.06-1build1
# Optional ros2_pulse telemetry pilot (issue #52), Apache-2.0. Installed but inert: nothing is
# preloaded unless a workload sets LD_PRELOAD (see ROS2/jazzy/README.md). Resolved 2026-10-28
# from the main packages.ros.org noble index. rosdistro jazzy already releases 0.7.0-1, but that
# build is only in ros2-testing until the next Jazzy sync; move this pin then instead of adding
# the testing repository to this image.
ARG ROS2_PULSE_VERSION=0.5.0-1noble.20260914.160740
# Only hosts the pulse-export venv below (Ubuntu noble-updates version, 2026-10-28).
ARG PYTHON3_VENV_VERSION=3.12.3-0ubuntu2.1
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      "ros-jazzy-demo-nodes-cpp=${ROS_DEMO_NODES_CPP_VERSION}" \
      "stress-ng=${STRESS_NG_VERSION}" \
      "ros-jazzy-ros2-pulse=${ROS2_PULSE_VERSION}" \
      "python3-venv=${PYTHON3_VENV_VERSION}"; \
    rm -rf /var/lib/apt/lists/*

# pulse-export serves the probe's log files as Prometheus /metrics for the optional sidecar.
# It ships in the ros2-pulse-top wheel (Apache-2.0), pinned by version and wheel sha256 (latest
# on PyPI, 2026-10-28). --no-deps: pulse-export is stdlib only; the wheel's textual dependency
# is for the pulse-top terminal UI, which is removed rather than left half-installed.
ARG ROS2_PULSE_TOP_VERSION=0.6.1
ARG ROS2_PULSE_TOP_WHEEL_SHA256=3a5cf388e836029fd82d416d4f81c348f0371a2c7e9a8e4e279607448610075a
RUN set -eux; \
    python3 -m venv /opt/pulse-export; \
    printf 'ros2-pulse-top==%s --hash=sha256:%s\n' \
      "${ROS2_PULSE_TOP_VERSION}" "${ROS2_PULSE_TOP_WHEEL_SHA256}" > /tmp/pulse-export.txt; \
    /opt/pulse-export/bin/pip install --no-cache-dir --disable-pip-version-check \
      --no-deps --only-binary :all: --require-hashes -r /tmp/pulse-export.txt; \
    rm /tmp/pulse-export.txt /opt/pulse-export/bin/pulse-top; \
    /opt/pulse-export/bin/pulse-export --help > /dev/null

# Keep the upstream /ros_entrypoint.sh to source /opt/ros/jazzy/setup.bash.
# Image and local DDS smoke test: scripts/test-ros2-image.sh.
# Opt-in ros2_pulse probe and pulse-export check: scripts/test-ros2-pulse.sh.
CMD ["bash"]
