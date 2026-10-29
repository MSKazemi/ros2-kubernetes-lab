# Deploying a Kubernetes Cluster Using Vagrant and VirtualBox

## Table of Contents

- [Deploying a Kubernetes Cluster Using Vagrant and VirtualBox](#deploying-a-kubernetes-cluster-using-vagrant-and-virtualbox)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
    - [Installation of VirtualBox](#installation-of-virtualbox)
    - [Installation of Vagrant](#installation-of-vagrant)
  - [Creating VMs and Setting up the Kubernetes Cluster](#creating-vms-and-setting-up-the-kubernetes-cluster)
    - [Clsuter Verification](#clsuter-verification)
  - [Cluster VM's Lifecycle Commands](#cluster-vms-lifecycle-commands)
    - [Shutdown the Cluster](#shutdown-the-cluster)
    - [Start the Cluster](#start-the-cluster)
    - [Destroy the Cluster](#destroy-the-cluster)
  - [Some Technical Details](#some-technical-details)
    - [Vagrantfile](#vagrantfile)
    - [Kubeadm](#kubeadm)
    - [Kubectl](#kubectl)
    - [Kubelet](#kubelet)
    - [Container Network Interface Plugin](#container-network-interface-plugin)

## Overview

This guide will walk you through the process of setting up a Kubernetes cluster with one control plane node and two worker nodes using Ubuntu 22.04 as the host operating system. This setup leverages Vagrant and VirtualBox to create and configure virtual machines automatically.

## Prerequisites

Before beginning, ensure you have VirtualBox and Vagrant installed on your machine.

### Installation of VirtualBox

To install VirtualBox, run the following commands:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install virtualbox -y
```

Alternatively, you can download and install VirtualBox from the following link:
- https://www.virtualbox.org/wiki/Linux_Downloads
- https://download.virtualbox.org/virtualbox/7.0.14/virtualbox-7.0_7.0.14-161095~Ubuntu~jammy_amd64.deb

### Installation of Vagrant

Install Vagrant with these commands:

```bash
sudo apt update && sudo apt upgrade -y
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install vagrant
```

Verify the installation:

```bash
vagrant --version
```

## Creating VMs and Setting up the Kubernetes Cluster

This project uses a Vagrantfile to automatically create and configure three VMs:

1. `controlplane`: This is the control plane node of the Kubernetes cluster. It manages the state of the cluster, such as which nodes are part of the cluster, what applications are running, and their desired state.
2. `worker1` and `worker2`: These are the worker nodes where the applications will be deployed.

To create the VMs and set up the Kubernetes cluster, clone the repository and execute the following:

```bash
git clone git@github.com:MSKazemi/ros2-kubernetes-lab.git
cd ros2-kubernetes-lab
vagrant up | tee vagrant.log
```

The `vagrant up` command will read the `Vagrantfile` in your current directory and create the VMs as specified. It will also execute the provisioning scripts defined in the `Vagrantfile` to install necessary packages, set up the Kubernetes cluster, and join the worker nodes to the cluster. So it is not necessary to run any thing else. And following is the explanation of the `Vagrantfile` and the `kubeadm` tool. The command `vagrant up | tee vagrant.log` not only creates a cluster, but also generates a log file. This log file contains important information and a token necessary for logging into the Kubernetes dashboard.

### Clsuter Verification
  
After `vagrant up`, you should verify that all nodes and pods in your Kubernetes cluster are running correctly:

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



## Cluster VM's Lifecycle Commands

To manage the VM's lifecycle, use the following commands:

### Shutdown the Cluster

```shell
vagrant halt
```

### Start the Cluster

```shell
vagrant up
```

### Destroy the Cluster

```shell
vagrant destroy -f
```

> **Warning:** `vagrant destroy -f` permanently deletes all three VirtualBox VMs and everything stored inside them, without asking for confirmation. Use `vagrant status` first to see what exists, and `vagrant halt` if you only want to stop the cluster.

## Some Technical Details

### Vagrantfile

The configuration for these VMs is specified in the `Vagrantfile`. For each VM, we have defined the following settings:

- `vm.network`: The private network IP address of the VM.
- `vm.hostname`: The internal hostname of the VM.
- `vb.name`: The name of the VM as displayed in VirtualBox.
- `vb.memory`: The amount of memory (in MB) allocated to the VM.
- `vb.cpus`: The number of CPUs allocated to the VM.

After running this command, you should have a fully functional Kubernetes cluster ready for use!

### Kubeadm

The cluster setup uses `kubeadm` to initialize the control plane and join worker nodes. The configuration details and initialization commands are managed through the included bash scripts. The `kubeadm` tool is used in the `create_cluster.sh` script to initialize the control plane node with the command `sudo kubeadm init --apiserver-advertise-address=192.168.56.10 --pod-network-cidr=10.244.0.0/16`.
After the control plane node is initialized, a join command is generated with `kubeadm token create --print-join-command` and saved to `/vagrant/join-command.sh`. This command is used to join the worker nodes to the cluster.
The `kubeadm`,`kubectl`, and `kubelet` tools are also installed on all nodes as part of the provisioning process defined in the `Vagrantfile` and the `kubeadm_kubelet_kubectl.sh` script.



### Kubectl

`kubectl` is the command-line tool that allows users to interact with Kubernetes clusters. It provides a wide range of functionalities that enable users to manage applications, check resource statuses, view logs, and execute administrative tasks on Kubernetes clusters. kubectl communicates with the cluster's API server and sends commands to it, which are then executed on the appropriate cluster nodes. This tool is essential for the operation and management of Kubernetes environments, offering both simplicity for beginners and powerful scripting capabilities for advanced users.

### Kubelet

The kubelet is an essential component that runs on every node in a Kubernetes cluster. It is responsible for ensuring that containers are running in a Pod as specified in the PodSpecs. The kubelet takes a set of PodSpecs that are provided through various mechanisms (primarily through the API server) and ensures that the containers described in those PodSpecs are healthy and running. Additionally, it manages the lifecycle of the containers, including starting, stopping, and maintaining application containers organized through Pod manifests based on system and/or Kubernetes instructions.


### Container Network Interface Plugin

In this project, we use Weave Net as our Container Network Interface (CNI) plugin. Weave Net is a powerful cloud native networking toolkit for Kubernetes. It provides a simple and efficient way to connect PODs across Kubernetes clusters.

Following command will download and apply the Weave Net Kubernetes CNI YAML file:
```bash
kubectl apply -f https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s.yaml
```

This README file provides a clear guide on setting up a Kubernetes cluster using Vagrant and includes links to further resources and detailed steps for installing prerequisites. Adjustments can be made to the scripts or Vagrant configuration based on specific needs or changes in your project structure.