#!/bin/bash
# Bootstrap the control-plane node with kubeadm. Safe to re-run: kubeadm init is
# skipped when the cluster already exists, and shell/taint edits are idempotent.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

ADMIN_CONF=/etc/kubernetes/admin.conf
JOIN_FILE=/home/vagrant/codes/join-command.sh

sudo apt-get update

if [ -f "$ADMIN_CONF" ]; then
  echo "Cluster already initialised ($ADMIN_CONF exists); skipping kubeadm init."
else
  sudo kubeadm init --apiserver-advertise-address=192.168.56.10 --pod-network-cidr=10.244.0.0/16
fi

mkdir -p /home/vagrant/.kube
sudo cp -f "$ADMIN_CONF" /home/vagrant/.kube/config
sudo chown -R vagrant:vagrant /home/vagrant/.kube

mkdir -p "$HOME/.kube"
sudo cp -f "$ADMIN_CONF" "$HOME/.kube/config"
sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"

# Save a join script for the workers. It is written next to the repo (synced folder)
# and contains a bootstrap token, so it is git-ignored and must not be shared.
# The guard lets a re-provisioned worker skip the join when it is already a member.
{
  echo '#!/bin/bash'
  echo 'set -euo pipefail'
  echo 'if [ -f /etc/kubernetes/kubelet.conf ]; then echo "Node already joined."; exit 0; fi'
  sudo kubeadm token create --print-join-command
  echo 'echo "Node joined the cluster."'
} > "$JOIN_FILE"
chmod 0644 "$JOIN_FILE"

# Untaint the control-plane node so pods can be scheduled on it (lab setup only).
# Fails harmlessly when the taint was already removed on a previous run.
# Dashboard, metrics-server and Prometheus run on this node.
kubectl taint nodes controlplane node-role.kubernetes.io/control-plane:NoSchedule- || true

# Auto-completion for kubectl (idempotent: appends the line only once).
sudo apt-get update
sudo apt-get -y install bash-completion

completion_line='source <(kubectl completion bash)'
for rc in "$HOME/.bashrc" /home/vagrant/.bashrc; do
  touch "$rc"
  grep -qxF "$completion_line" "$rc" || echo "$completion_line" >> "$rc"
done
