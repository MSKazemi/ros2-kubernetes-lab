#!/bin/bash
# Install kubeadm, kubelet and kubectl from the community pkgs.k8s.io apt repository.
# Safe to re-run. The Kubernetes minor version is a single variable (K8S_MINOR) below.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Kubernetes minor line (pkgs.k8s.io path is core:/stable:/v<minor>/deb/).
# 1.29 is the historical lab version documented in AGENTS.md and is end-of-life
# upstream (2025-02-28); bump only after a full multi-VM test.
K8S_MINOR="1.29"

sudo apt-get update
# apt-transport-https may be a dummy package on newer releases; harmless if so.
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/v${K8S_MINOR}/deb/Release.key" \
  | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Overwrites any existing configuration in /etc/apt/sources.list.d/kubernetes.list
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${K8S_MINOR}/deb/ /" \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list > /dev/null

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

sudo systemctl enable --now kubelet
