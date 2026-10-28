# syntax=docker/dockerfile:1
# Supported ROS 2 container baseline (not an upgrade of the legacy Vagrant cluster).
# Official multi-platform Jazzy/Noble ROS base; this OCI index digest is immutable.
# Ref: https://hub.docker.com/layers/library/ros/jazzy-ros-base-noble/images/sha256-f652c502c971653afc2ed9b9e5929643df644e6125b6ee68349408b6cc2f64cd
FROM docker.io/library/ros:jazzy-ros-base-noble@sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4

LABEL org.opencontainers.image.source="https://github.com/MSKazemi/ros2-kubernetes-lab" \
      org.opencontainers.image.description="ROS 2 Jazzy on Ubuntu 24.04: demo_nodes_cpp and stress-ng for educational experiments"

ARG DEBIAN_FRONTEND=noninteractive
# Direct apt package versions observed in successful 2026-10-12 CI build.
# Transitive apt dependencies still need a snapshot for fully hermetic rebuilds.
ARG ROS_DEMO_NODES_CPP_VERSION=0.33.11-1noble.20260920.235420
ARG STRESS_NG_VERSION=0.17.06-1build1
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      "ros-jazzy-demo-nodes-cpp=${ROS_DEMO_NODES_CPP_VERSION}" \
      "stress-ng=${STRESS_NG_VERSION}"; \
    rm -rf /var/lib/apt/lists/*

# Keep the upstream /ros_entrypoint.sh to source /opt/ros/jazzy/setup.bash.
# Image and local DDS smoke test: scripts/test-ros2-image.sh.
CMD ["bash"]
