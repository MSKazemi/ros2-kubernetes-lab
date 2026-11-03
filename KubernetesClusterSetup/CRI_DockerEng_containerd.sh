#!/bin/bash
# Install Docker Engine + containerd and configure containerd for kubeadm (systemd cgroups).
# Safe to re-run: the original config is backed up once, then regenerated each time.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Docker's official GPG key and apt repository.
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get -y update

sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Group membership takes effect at the next login. Do not run `newgrp` here: in a
# non-interactive provisioning shell it replaces the script's shell.
sudo usermod -aG docker vagrant

# containerd: the containerd.io package ships a config with `disabled_plugins = ["cri"]`,
# which breaks kubeadm. Replace it with the default config and enable SystemdCgroup.
CONFIG_FILE=/etc/containerd/config.toml
BACKUP_FILE="${CONFIG_FILE}.backup"
sudo mkdir -p /etc/containerd
if [ -f "$CONFIG_FILE" ] && [ ! -f "$BACKUP_FILE" ]; then
  sudo cp -p "$CONFIG_FILE" "$BACKUP_FILE"
fi

tmp_config="$(mktemp)"
trap 'rm -f "$tmp_config"' EXIT
containerd config default > "$tmp_config"
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' "$tmp_config"
grep -q 'SystemdCgroup = true' "$tmp_config" \
  || { echo 'ERROR: SystemdCgroup not enabled in generated containerd config' >&2; exit 1; }

sudo install -m 0644 "$tmp_config" "$CONFIG_FILE"
sudo systemctl restart containerd
sudo systemctl is-active --quiet containerd
