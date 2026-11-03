#!/bin/bash
# Install metrics-server, Kubernetes Dashboard, Helm and kube-prometheus-stack.
# Safe to re-run (apply / upgrade --install). The dashboard token is written to a
# 0600 file in the vagrant home directory and is NOT printed to the console.
set -euo pipefail

echo "Installing monitoring tools"

# Install Metrics Server
# NOTE: `latest` is unpinned; pin a version compatible with the cluster minor when known.
echo "Installing Metrics Server"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Install Kubernetes Dashboard
echo "Installing Kubernetes Dashboard"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

echo "Creating admin-user for dashboard"
kubectl apply -f /home/vagrant/codes/MonitoringSystem/admin-user.yaml

# Dashboard token: wait until the service-account token controller populates it,
# then store it with restrictive permissions. Never echo it to the provisioning log.
TOKEN_FILE=/home/vagrant/dashboard-token
echo "Waiting for the dashboard token to be populated"
for _ in $(seq 1 30); do
  token_b64="$(kubectl -n kubernetes-dashboard get secret admin-user -o jsonpath='{.data.token}' 2>/dev/null || true)"
  [ -n "$token_b64" ] && break
  sleep 2
done
[ -n "${token_b64:-}" ] || { echo 'ERROR: dashboard token was not populated' >&2; exit 1; }
(umask 077 && printf '%s' "$token_b64" | base64 -d > "$TOKEN_FILE")
chown vagrant:vagrant "$TOKEN_FILE"
echo "Dashboard token saved to $TOKEN_FILE (readable only by the vagrant user)."

# Install Helm (signing key and apt source as documented by Helm)
echo "Installing Helm"
curl -fsSL https://baltocdn.com/helm/signing.asc | gpg --batch --yes --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
sudo apt-get install -y apt-transport-https
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list > /dev/null
sudo apt-get update
sudo apt-get install -y helm

# Persistent Volumes for Prometheus and Grafana
echo "Creating Persistent Volume for Prometheus and Grafana"
kubectl apply -f /home/vagrant/codes/MonitoringSystem/pv.yaml

# Install Prometheus
echo "Prometheus"
echo "Adding Prometheus Helm repository"
if ! helm repo list 2>/dev/null | grep -q '^prometheus-community[[:space:]]'; then
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
fi
helm repo update

# Host directories backing the local PVs. Group 2000 matches the Prometheus pod's
# fsGroup in kube-prometheus-stack-values.yaml; mode 0775 instead of the earlier
# world-writable 777. Grafana's fsGroup is not covered here; verify on a real cluster.
for i in {1..5}; do
  sudo mkdir -p "/mnt/data$i"
  sudo chgrp 2000 "/mnt/data$i"
  sudo chmod 0775 "/mnt/data$i"
done

echo "Creating namespace for Prometheus"
kubectl create namespace prometheus --dry-run=client -o yaml | kubectl apply -f -

echo "Installing Prometheus"
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  -n prometheus \
  --values /home/vagrant/codes/MonitoringSystem/kube-prometheus-stack-values.yaml \
  --wait --timeout 15m
