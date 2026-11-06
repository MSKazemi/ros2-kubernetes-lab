# Monitoring System

## Table of Contents

- [Monitoring System](#monitoring-system)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Key Components of the Monitoring System](#key-components-of-the-monitoring-system)
    - [Metrics Server](#metrics-server)
    - [Kubernetes Dashboard](#kubernetes-dashboard)
      - [Dashboard Access and Security](#dashboard-access-and-security)
    - [Prometheus and Grafana](#prometheus-and-grafana)
      - [Helm Installation](#helm-installation)
      - [Prometheus and Grafana Setup](#prometheus-and-grafana-setup)
        - [Add the Prometheus Helm Chart Repository](#add-the-prometheus-helm-chart-repository)
        - [Install Prometheus and Grafana Helm Chart](#install-prometheus-and-grafana-helm-chart)
        - [Persistent Volume Configuration](#persistent-volume-configuration)
        - [Verifying the Installation](#verifying-the-installation)
        - [Access Prometheus](#access-prometheus)
      - [Grafana](#grafana)
  - [Access URLs and Credentials](#access-urls-and-credentials)


## Overview

This project uses Vagrant alongside bash scripts to automate the creation and configuration of virtual machines (VMs) in VirtualBox. This setup includes a Kubernetes cluster with a comprehensive monitoring system. The included `Vagrantfile` and various scripts handle the entire setup process, negating the need for manual configuration commands.

## Key Components of the Monitoring System

### Metrics Server

The Metrics Server is a scalable, efficient source of container resource metrics for Kubernetes built-in autoscaling pipelines. The Metrics Server plays a crucial role in Kubernetes monitoring and management systems due to its ability to provide core metrics about clusters, which include metrics on CPU and memory usage for nodes and pods. The Metrics Server is installed using a direct `kubectl apply -f` command, fetching the latest components from the official GitHub repository.

```shell
vagrant ssh controlplane
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

or

```shell
vagrant ssh controlplane
kubectl apply -f https://raw.githubusercontent.com/techiescamp/kubeadm-scripts/main/manifests/metrics-server.yaml
```

### Kubernetes Dashboard

The Kubernetes Dashboard offers a web-based Kubernetes user interface. It allows users to manage applications running in the cluster and troubleshoot them, as well as manage the cluster itself. Installation is performed through `kubectl apply -f` from the Kubernetes official repository.

```shell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
```

https://github.com/kubernetes/dashboard
https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/

#### Dashboard Access and Security

After installing the Kubernetes Dashboard, an `admin-user` service account is created and bound to the built-in `cluster-admin` role (see `admin-user.yaml`). A token for it is written by `monitoring.sh` to `/home/vagrant/dashboard-token` inside the `controlplane` VM (mode `0600`, owned by the `vagrant` user). It is not written to `./MonitoringSystem/token` or to `vagrant.log` any more. To read it, run this inside the VM:

```shell
vagrant ssh controlplane
cat /home/vagrant/dashboard-token
```

You can also retrieve the token with `kubectl` from the control plane (the token is printed to your terminal, so do not paste it anywhere public):

```shell
kubectl -n kubernetes-dashboard get secret admin-user -o go-template='{{.data.token | base64decode}}'
```

Open the site in your browser: https://192.168.56.10:30664/#/login (this URL assumes the dashboard Service was exposed on NodePort 30664; the upstream v2.7.0 manifest that `monitoring.sh` applies creates a `ClusterIP` Service, so this port is not set by the repository's scripts).

> **Security warning:** `admin-user` has full cluster-admin rights. For read-only browsing use `MonitoringSystem/admin-user-readonly.yaml` (binds the built-in `view` role; it cannot read Secrets or change anything). The lab dashboard should not be exposed beyond a trusted network.

### Prometheus and Grafana

#### Helm Installation

Helm, the package manager for Kubernetes, is installed using a script that downloads and configures the necessary repositories and packages. This tool is crucial for managing Kubernetes applications, including Prometheus and Grafana.

```shell
vagrant ssh controlplane
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
sudo apt-get install apt-transport-https --yes
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install helm
```

#### Prometheus and Grafana Setup

Prometheus, a powerful monitoring and alerting toolkit, is integrated into the system using Helm. The script includes commands to add the Prometheus Helm chart repository, update it, and install Prometheus with custom configurations (`--values /home/vagrant/codes/MonitoringSystem/kube-prometheus-stack-values.yaml`) to adjust its default settings, like changing the service type to `NodePort` to allow external access.

Configuration changes:

- Grafana:
  - service type: from `ClusterIP` to `NodePort`
  - `PersistentVolumeClaim`

- Prometheus:
  - service type: from `ClusterIP` to `NodePort` (`nodePort: 30090`)
  - `PersistentVolumeClaim`: `storageSpec.volumeClaimTemplate` (10Gi, `local-storage`). The chart silently ignores a `volumeClaimTemplate` placed as a sibling of `storageSpec`; this was broken before and is fixed in the values file (checked with `helm template`, see Verification status below).
  - Retention: how long to retain metrics, `retention: 1y`, capped by `retentionSize: "8GB"` so the 10Gi volume cannot fill up.

- Alertmanager: the same `storage.volumeClaimTemplate` nesting is fixed (`retention: 1200h`).


##### Add the Prometheus Helm Chart Repository

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

##### Install Prometheus and Grafana Helm Chart


```bash
# Creating Persistent Volume for Prometheus and Grafana
kubectl apply -f /home/vagrant/codes/MonitoringSystem/pv.yaml

# Creating namespace for Prometheus
kubectl create namespace prometheus

# Installing Prometheus and Grafana using Helm
helm install prometheus prometheus-community/kube-prometheus-stack -n prometheus --values /home/vagrant/codes/MonitoringSystem/kube-prometheus-stack-values.yaml
``` 
##### Persistent Volume Configuration

The script also sets up necessary persistent volumes for Prometheus and Grafana, ensuring data persistence across pod restarts and deletions. This is crucial for maintaining historical data for analysis.

##### Verifying the Installation
```bash
kubectl get all -n prometheus
```


##### Access Prometheus

Prometheus is exposed as a NodePort on port `30090` (from the values file: `prometheus.service.nodePort`), i.e. `http://<node-ip>:30090`. **Prometheus has no login.** Anyone who can reach that port can query metrics and the API. Prefer a port-forward on untrusted networks:

```bash
kubectl -n prometheus port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
curl -s http://127.0.0.1:9090/-/ready
```

Below are screenshots of the Prometheus graph and rules pages from the original lab run.

![Prometheus graph of the node:node_cpu_utilization:ratio_rate5m query over 15 minutes, with node CPU utilization rising to about 0.02](../images/p1.png)
![Prometheus Rules page listing the Alertmanager alerting rules, each in the OK state](../images/p2.png)

#### Grafana

Grafana is used for visualization and analytics of metrics gathered from Prometheus. It is installed and configured similarly to Prometheus, using Helm. The script sets up persistent volumes required for storing data and ensures that Grafana is accessible via a NodePort.

Grafana is exposed as a NodePort on port `30000` (from the values file: `grafana.service.nodePort`), i.e. `http://<node-ip>:30000`. Login is `admin` / `prom-operator` **unless you override it**. That password is a well-known default published in this README and in the values file, and the NodePort reaches every node IP. Before exposing the lab, set your own password at install time (`--set grafana.adminPassword='<strong-password>'`) or use a port-forward:

```bash
kubectl -n prometheus port-forward svc/prometheus-grafana 3000:80
curl -s http://127.0.0.1:3000/api/health
```

The Grafana screenshots below show node metrics, per-pod network traffic, and Kubernetes API server health from the original lab run.

![Grafana Node Exporter / Nodes dashboard for instance 192.168.56.10:9100 with CPU, load average, memory, disk and network panels](../images/g1.png)
![Grafana Kubernetes / Networking / Pod dashboard for the ros pod ending 9wdkl, showing receive and transmit bandwidth](../images/g2.png)
![Grafana Kubernetes / Networking / Pod dashboard for the ros pod ending vd8rs, showing receive and transmit bandwidth](../images/g3.png)
![Grafana Kubernetes / Networking / Pod dashboard for the ros pod ending x4hcb, showing receive and transmit bandwidth](../images/g4.png)
![Grafana Kubernetes / Networking / Pod dashboard for the weave-net pod, showing receive and transmit bandwidth](../images/g5.png)
![Grafana Kubernetes / Networking / Pod dashboard for the etcd-controlplane pod, showing receive and transmit bandwidth](../images/g6.png)
![Grafana Kubernetes / Networking / Pod dashboard for the ros pod ending vd8rs with the Bandwidth, Packets and Errors sections expanded](../images/g7.png)
![Grafana Kubernetes / API server dashboard with availability, request, work queue, memory, CPU and goroutine panels](../images/g8.png)

## Verification status

What was actually run (Helm v4.3.1, kubeconform v0.8.0, kind v0.33.0 with Kubernetes 1.37 node image, chart `prometheus-community/kube-prometheus-stack` **92.16.1**, app v0.94.2):

- `helm template` of the chart with `kube-prometheus-stack-values.yaml` succeeds. The rendered Prometheus and Alertmanager objects now carry the 10Gi `local-storage` claim template (before the fix they had no storage at all).
- `kubeconform -strict` on the rendered output: 78 valid, 0 invalid; 50 CRD-kinds skipped (no schema) with `-ignore-missing-schemas`.
- `pv.yaml`, `pvc.yaml`, `admin-user.yaml` and `admin-user-readonly.yaml` pass `kubeconform -strict` and a server-side `kubectl apply --dry-run=server` on kind. `pv.yaml`, `admin-user.yaml` and `admin-user-readonly.yaml` were also applied to a throwaway kind cluster. RBAC was checked with `kubectl auth can-i`: `admin-user` can read Secrets and delete pods in `kube-system`; `dashboard-viewer` can list pods but cannot read Secrets or delete pods.
- The chart install into kind was **not** completed. The Prometheus/Grafana pods never started, because `kube-proxy` on the test node could not start (`fsnotify watcher init: too many open files`: the host's per-user inotify instance limit was exhausted by other clusters). Live Prometheus/Grafana health checks (`/-/ready`, `/api/health`) therefore have **not** been run.
- Fixed during testing: the pinned admission certgen image (an ingress-nginx image from 2022) rejects the `--secret-type` flag that chart 92.x passes, so the install hung at the admission hook. The chart's own image (`jkroepke/kube-webhook-certgen:1.11.0`) is now pinned in the values file.
- Not verified on the lab's Kubernetes 1.29 cluster. The chart declares `kubeVersion >=1.25.0-0`.

Note that `monitoring.sh` does not pin the chart version. To reproduce the tested chart version, add `--version 92.16.1` to its `helm upgrade --install` line.

## Access URLs and Credentials

- **Kubernetes Dashboard**: https://192.168.56.10:30664/#/login (port not set by the repository's scripts; see the Dashboard section). Token: `/home/vagrant/dashboard-token` inside the controlplane VM.
- **Prometheus**: `http://<node-ip>:30090` (NodePort from the values file; no login, use port-forward on untrusted networks)
- **Grafana**: `http://<node-ip>:30000` (default login `admin` / `prom-operator` unless overridden; change it)

Using the values in `kube-prometheus-stack-values.yaml` the lab's node IP is `192.168.56.10` (the controlplane VM), so the lab URLs are `http://192.168.56.10:30090` and `http://192.168.56.10:30000`.

For more detailed information on the monitoring setup and modifications, refer to the `./MonitoringSystem/monitoring.sh` in the repository.