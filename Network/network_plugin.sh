#!/bin/bash
# Install Weave Net (historical CNI for this lab).
# Upstream weaveworks/weave was archived in June 2024; v2.8.1 is its last release.
# Kept for the historical Vagrant lab. Consider Calico or Flannel for new work.
set -euo pipefail

echo "Installing Weave Net"
kubectl apply -f https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s.yaml

echo "Waiting for Weave Net DaemonSet to roll out"
kubectl -n kube-system rollout status daemonset/weave-net --timeout=300s
