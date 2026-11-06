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

# Offline analysis helpers (issue #46). Nothing in this group starts Vagrant, Kubernetes or Docker.
# Python >= 3.12 is required (see DataAnalysis/requirements-offline.txt).
VENV ?= .venv
PY   := $(VENV)/bin/python

.PHONY: help check-prereqs demo verify verify-negative clean analysis-venv analyze-sample analysis-offline analysis-test offline-checks seqprobe-test e02-test placement-test placement-sim serving-test serving-sim lerobot-dq-test agent-mobility-test

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
	@echo 'Offline analysis (no Docker, Kubernetes or Vagrant needed):'
	@echo '  make analysis-venv     create $(VENV) and install the pinned offline dependencies'
	@echo '  make analyze-sample    summary CSV of the default committed sample -> DataAnalysis/output/ (stdlib only)'
	@echo '  make analysis-offline  all samples + CPU plot + tests -> DataAnalysis/output/'
	@echo '  make analysis-test     run the offline pytest suite'
	@echo
	@echo 'Offline research modules (standard library, CPU only; SYNTHETIC fixtures / SIMULATION output, no cluster, no ROS):'
	@echo '  make offline-checks       all offline checks: shell, YAML, unit tests, Markdown links, site, secret scan'
	@echo '  make seqprobe-test        ROS 2 sequence probe unit tests (examples/ros2-sequence-probe)'
	@echo '  make e02-test             DDS resilience harness tests on synthetic traces (needs PyYAML)'
	@echo '  make placement-test       edge/cloud placement simulator tests;  make placement-sim  prints its SIMULATION table'
	@echo '  make serving-test         model-serving fairness simulator tests;  make serving-sim  prints its SIMULATION table'
	@echo '  make lerobot-dq-test      LeRobot data-quality contract tests (examples/lerobot-data-quality)'
	@echo '  make agent-mobility-test  mission-state handoff simulator tests (examples/cloud-robotics/agent-mobility)'
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

# ---- Offline analysis (issue #46) ----
analysis-venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install -r DataAnalysis/requirements-offline.txt

analyze-sample:
	python3 DataAnalysis/analyze_sample.py

analysis-offline:
	PYTHON=$(abspath $(PY)) bash scripts/run-analysis-offline.sh

analysis-test:
	$(PY) -m pytest DataAnalysis

# Offline research modules. Standard library only (e02 also needs PyYAML); no Docker, Kubernetes, ROS 2 or network.
offline-checks:
	bash scripts/ci/run-offline-checks.sh

seqprobe-test:
	python3 -m unittest discover -s examples/ros2-sequence-probe/tests -t examples/ros2-sequence-probe

e02-test:
	python3 -m unittest discover -s experiments/e02-dds-resilience/tests -t experiments/e02-dds-resilience

placement-test:
	python3 -m unittest discover -s experiments/edge-cloud-placement/tests -t experiments/edge-cloud-placement

placement-sim:
	python3 experiments/edge-cloud-placement/placement_sim.py --config experiments/edge-cloud-placement/configs/default.json

serving-test:
	python3 -m unittest discover -s experiments/model-serving-fairness/tests -t experiments/model-serving-fairness

serving-sim:
	python3 experiments/model-serving-fairness/run_simulation.py --seeds 1,2,3

lerobot-dq-test:
	python3 -m unittest discover -s examples/lerobot-data-quality/tests -t examples/lerobot-data-quality

agent-mobility-test:
	python3 -m unittest discover -s examples/cloud-robotics/agent-mobility/tests
