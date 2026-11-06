# README for Network Setup

## Table of Contents

- [README for Network Setup](#readme-for-network-setup)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Network Configuration](#network-configuration)
    - [VMs/Nodes Network Configuration](#vmsnodes-network-configuration)
    - [Kubernetes Network Plugin](#kubernetes-network-plugin)
      - [Weave Net for Docker and Kubernetes](#weave-net-for-docker-and-kubernetes)
      - [Configuration](#configuration)
      - [Weave Net Installation Command](#weave-net-installation-command)
      - [Verification of Network Setup](#verification-of-network-setup)
    - [Further Information](#further-information)

## Overview

This project utilizes Vagrant to automatically create and configure virtual machines (VMs) in VirtualBox. These VMs act as the nodes for our Kubernetes cluster. Detailed network configurations are provided to support customization for specific use cases beyond the local workstation and Vagrant environments.
I should emphasize that the following commands are not necessary for creating a network. Everything will be configured by the Vagrantfile and other scripts of the project. The information below is simply to introduce some parts of the codes.

## Network Configuration

### VMs/Nodes Network Configuration

Each VM is configured with a private network IP address using the `vm.network` setting in the `Vagrantfile`. This address facilitates internal communication among the VMs. This setup forms the infrastructure for the Kubernetes (K8s) cluster.

### Kubernetes Network Plugin

#### Weave Net for Docker and Kubernetes

Weave Net is a robust networking plugin for Docker and Kubernetes that simplifies the creation of a network for containers, enabling them to communicate across multiple hosts. It supports multicasting to meet the ROS2 requirements, crucial for our project.

- **GitHub Repository:** [Weave Net on GitHub](https://github.com/weaveworks/weave)
- **Installation Guide:** [Weave Net Kubernetes Addon](https://github.com/weaveworks/weave/blob/master/site/kubernetes/kube-addon.md)

#### Configuration

The Kubernetes network plugin is critical as it ensures all Kubernetes pods can communicate seamlessly, implementing the [Kubernetes Networking Model](https://kubernetes.io/docs/concepts/cluster-administration/networking/).

We use the following script to configure our network plugin:

```bash
cp.vm.provision "shell", path: "./Network/network_plugin.sh"
```

This script sets up the Container Network Interface (CNI) plugin, with specific steps including downloading plugin binaries, positioning them on the VMs, and configuring Kubernetes to utilize the plugin.

#### Weave Net Installation Command

```bash
kubectl apply -f https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s.yaml
```
#### Verification of Network Setup

After installing the Weave Net plugin, you should verify that all nodes and pods in your Kubernetes cluster are running correctly:

1. Check the status of all nodes in the cluster:

    ```sh
    kubectl get nodes -o wide
    ```

    All nodes should be in the `Ready` state.

2. Check the status of all pods in the cluster:

    ```sh
    kubectl get pods -A -o wide
    ```

    All pods should be in the `Running` state, and there should be no errors.

### Further Information
For more details on the network setup, please refer to the Vagrantfile and `./Network/network_plugin.sh` script.
This README serves as a quick guide for setting up the network components of our Kubernetes cluster using Weave Net. Modify configurations as necessary to fit the specific needs of your deployment environment.
