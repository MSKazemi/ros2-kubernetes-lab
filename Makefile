# Lightweight kind profile for the ROS 2 Kubernetes lab (issues #14 and #16).
# Full guide: docs/KIND-DEMO.md. This does NOT start the Vagrant/VirtualBox cluster.
#
#   make help      prerequisites and targets
#   make demo      build image, create a 3-node kind cluster, deploy talker/listener
#   make verify    check that messages cross between two different workers (exit 0 = verified)
#   make clean     delete the kind cluster and the image built by `make demo`
#
# Everything is named with the prefix ros2k8s-demo; nothing else on the host is touched.
SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

CLUSTER     ?= ros2k8s-demo
IMAGE       ?= ros2k8s-demo-ros:local
KIND_CONFIG ?= kind/ros2k8s-demo.yaml
MANIFEST    ?= ROS2/jazzy/talker-listener.yaml
KCTX        := kind-$(CLUSTER)
WORKERS     := $(CLUSTER)-worker,$(CLUSTER)-worker2

.PHONY: help check-prereqs demo verify verify-negative clean

help:
	@echo 'ROS 2 on Kubernetes - lightweight kind profile (cluster "$(CLUSTER)")'
	@echo
	@echo 'Prerequisites (Linux, amd64 tested; no root needed beyond Docker access):'
	@echo '  docker   a running daemon you can use without sudo   (docker info)'
	@echo '  kind     v0.33.0 or newer                             (kind version)'
	@echo '  kubectl  any version within one minor of Kubernetes 1.37 (kubectl version --client)'
	@echo '  make, bash, about 10 GB free disk and ~1.1 GiB RAM for the three node containers (measured on one host; see docs/KIND-DEMO.md)'
	@echo
	@echo 'Targets:'
	@echo '  make demo             build $(IMAGE), create the kind cluster, deploy discovery server + talker + listener'
	@echo '  make verify           exit 0 only if pods are Ready, on different workers, and the listener hears the talker'
	@echo '  make verify-negative  prove that verify fails when delivery is broken, then restore and re-verify'
	@echo '  make clean            delete cluster "$(CLUSTER)" and image $(IMAGE) (leaves other Docker objects alone)'
	@echo
	@echo 'Exit codes: 0 success; non-zero on any failure (missing prerequisite, build, cluster or verification failure).'

# Fail early with a clear message when a required tool is missing or Docker is unreachable.
check-prereqs:
	@missing=0; \
	for tool in docker kind kubectl; do \
	  if ! command -v "$$tool" >/dev/null 2>&1; then \
	    echo "ERROR: '$$tool' not found in PATH. See 'make help' and docs/KIND-DEMO.md." >&2; missing=1; \
	  fi; \
	done; \
	if (( missing )); then exit 1; fi; \
	if ! docker info >/dev/null 2>&1; then \
	  echo "ERROR: cannot talk to the Docker daemon (is it running, and is your user allowed to use it?)." >&2; exit 1; \
	fi

demo: check-prereqs
	@start=$$SECONDS; \
	echo '== 1/5 build $(IMAGE) from ROS2/Dockerfile (local only, never pushed)'; \
	docker build --file ROS2/Dockerfile --tag '$(IMAGE)' .; \
	if kind get clusters 2>/dev/null | grep -qx '$(CLUSTER)'; then \
	  echo '== 2/5 kind cluster $(CLUSTER) already exists; reusing it'; \
	else \
	  echo '== 2/5 create kind cluster $(CLUSTER) (1 control plane + 2 workers)'; \
	  kind create cluster --config '$(KIND_CONFIG)' --wait 120s; \
	fi; \
	echo '== 3/5 load $(IMAGE) into the two worker nodes'; \
	kind load docker-image '$(IMAGE)' --name '$(CLUSTER)' --nodes '$(WORKERS)'; \
	echo '== 4/5 deploy $(MANIFEST)'; \
	kubectl --context '$(KCTX)' apply -f '$(MANIFEST)'; \
	echo '== 5/5 wait for rollouts'; \
	for d in discovery-server talker listener; do \
	  kubectl --context '$(KCTX)' -n ros rollout status "deployment/$$d" --timeout=180s; \
	done; \
	kubectl --context '$(KCTX)' -n ros get pods -o wide; \
	echo "demo ready in $$((SECONDS - start)) s. Next: make verify"

verify: check-prereqs
	@KUBE_CONTEXT='$(KCTX)' bash scripts/verify-ros2.sh

verify-negative: check-prereqs
	@KUBE_CONTEXT='$(KCTX)' bash scripts/verify-ros2.sh --negative-test

clean: check-prereqs
	@if kind get clusters 2>/dev/null | grep -qx '$(CLUSTER)'; then \
	  echo 'deleting kind cluster $(CLUSTER)'; kind delete cluster --name '$(CLUSTER)'; \
	else \
	  echo 'kind cluster $(CLUSTER) not present'; \
	fi; \
	if docker image inspect '$(IMAGE)' >/dev/null 2>&1; then \
	  echo 'removing image $(IMAGE)'; docker image rm '$(IMAGE)'; \
	else \
	  echo 'image $(IMAGE) not present'; \
	fi
	@echo 'clean done. The upstream ROS base image and Docker build cache are not removed (see docs/KIND-DEMO.md).'
