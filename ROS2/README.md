# Deploying ROS2 Talker and Listener Nodes on a Kubernetes Cluster

> **Historical Foxy/Kubernetes tutorial:** This document describes the original ROS 2 Foxy experiment. The Kubernetes manifests it uses (`ROS2/ros_dep_1.yaml`, `ros_dep_2.yaml`, `ros_dep_3.yaml`) are **stress-ng autoscaling workloads**: applying them does **not** start a ROS 2 talker or listener. The talker/listener part of this guide is a **manual** procedure that was **not re-run** while correcting the commands (static review only); a self-starting, scripted cross-worker talker/listener demo exists **only for the lightweight kind profile** (not for this Vagrant/Foxy cluster): see [`docs/KIND-DEMO.md`](../docs/KIND-DEMO.md) ([issue #14](https://github.com/MSKazemi/robo-resilience-lab/issues/14)). For the **new Jazzy/Ubuntu 24.04 container image and local ROS message smoke test**, use [`jazzy/README.md`](./jazzy/README.md). It does not upgrade or validate this legacy Kubernetes cluster.

## Table of Contents

- [Deploying ROS2 Talker and Listener Nodes on a Kubernetes Cluster](#deploying-ros2-talker-and-listener-nodes-on-a-kubernetes-cluster)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
    - [ROS2 (Robot Operating System 2)](#ros2-robot-operating-system-2)
    - [ROS2 Nodes vs. Kubernetes Nodes:](#ros2-nodes-vs-kubernetes-nodes)
      - [ROS2 Node:](#ros2-node)
      - [Kubernetes Node:](#kubernetes-node)
  - [ROS2 Talker and Listener Nodes](#ros2-talker-and-listener-nodes)
    - [What the Manifests Run, and What Is Manual or Planned](#what-the-manifests-run-and-what-is-manual-or-planned)
    - [Deploying the ROS2 Nodes](#deploying-the-ros2-nodes)
    - [Testing the ROS2 Nodes](#testing-the-ros2-nodes)

## Overview

This guide shows how to deploy a ROS2-based workload on a Kubernetes cluster and how to start ROS2 Talker and Listener nodes **manually** inside its pods. The Kubernetes manifests deploy a CPU-stress workload (`stress-ng`) with autoscaling; they do not launch the Talker or Listener themselves.

### ROS2 (Robot Operating System 2) 

ROS2 is an open-source framework designed for building and managing complex robotic systems. It's an evolution of the original ROS, incorporating lessons learned from the previous version and updated to handle the demands of modern robotics, including real-time systems, more modular software architecture, and support for new hardware. ROS2 Communication Middleware, built on the Data Distribution Service (DDS), provides a robust method for managing message passing between nodes. This guide will demonstrate how to deploy ROS2 nodes on a Kubernetes cluster, showcasing the communication capabilities of ROS2 in a cloud environment.

### ROS2 Nodes vs. Kubernetes Nodes:

When discussing nodes in the context of ROS2 and Kubernetes, we are referring to different concepts, as "node" is a term used broadly in computing to refer to different components depending on the system or architecture in discussion.

#### ROS2 Node:

In ROS2, a node is a fundamental component that performs computation. A single ROS2 node can be thought of as a process that performs a specific task or a group of related functionalities within a robotic system. For example, one node might handle laser data processing while another manages motor control. Nodes communicate with each other using a publish-subscribe messaging model, services, or actions over topics.

#### Kubernetes Node:

In Kubernetes, a node is a physical or virtual machine that is part of the Kubernetes cluster. Each node hosts multiple pods, which are the smallest deployable units managed by Kubernetes. A Kubernetes node provides the necessary resources (CPU, memory, network connectivity) to run the pods. Kubernetes nodes are managed by a control plane (or master), which handles scheduling, deployment, and orchestration of containers across the nodes in the cluster.


## ROS2 Talker and Listener Nodes

The ROS2 Talker and Listener nodes demonstrate a fundamental communication pattern in robotics systems using the ROS2 framework. The Talker node is designed to publish messages, typically containing data such as sensor readings or status information, to a specific topic. In contrast, the Listener node subscribes to that topic to receive the messages sent by the Talker. This simple yet powerful publish-subscribe model allows for decoupled and asynchronous communication between different parts of a robotic system. By employing ROS2's robust middleware, these nodes can reliably exchange information, making them vital components in the orchestration of complex behaviors and interactions within robotic applications. This model not only facilitates straightforward data sharing but also underpins more complex distributed computing tasks common in robotics.

### What the Manifests Run, and What Is Manual or Planned

| Item | Status |
|---|---|
| `ROS2/ros_dep_1.yaml`, `ros_dep_2.yaml`, `ros_dep_3.yaml` | **Current.** Each creates the `ros` namespace, a Deployment named `ros` and a HorizontalPodAutoscaler named `ros-hpa` (CPU target 70%). The container image is `docker.io/kazemi/ros-foxy-with-stress-ng` and its command is `stress-ng --cpu 1 --cpu-load 80 --timeout 3600s`. The three files differ only in the pod CPU/memory requests and limits (`ros_dep_1.yaml`: 50m/100Mi requests, 100m/200Mi limits; `ros_dep_2.yaml`: 250m/500Mi, 500m/1Gi; `ros_dep_3.yaml`: 1000m/2Gi, 2000m/4Gi). They share object names, so apply only one of them at a time. |
| `ROS2/VPA.yaml`, `ROS2/ros_one.yaml` | **Current, other stress/autoscaling experiments** in the same `ros` namespace: `VPA.yaml` runs staged `stress-ng` phases with a VerticalPodAutoscaler (it needs the VPA components installed in the cluster and pins the pod to the `controlplane` node); `ros_one.yaml` intentionally exits after 30 seconds to demonstrate a crashing pod. |
| Talker/listener commands below (Foxy, `kubectl exec`) | **Manual; did not deliver messages in our kind test.** Nothing in the manifests starts them. On a kind cluster (1 control-plane + 2 workers, Kubernetes v1.37.0, 2026-10-31) the Foxy talker and listener delivered **0 messages** both across two workers and on the same worker, so the default DDS multicast discovery did not work in that network. Whether it works on the Vagrant cluster was not tested. |
| Automated, tested talker/listener demo across Kubernetes workers | **Available for the kind profile only**: [`docs/KIND-DEMO.md`](../docs/KIND-DEMO.md) (`make demo`, `make verify`). It is **not** available for the Vagrant/Foxy cluster described in this file ([issue #14](https://github.com/MSKazemi/robo-resilience-lab/issues/14)). Its recorded run is one host on 2026-10-27; its GitHub Actions workflow had not been executed when that page was written. |

### Deploying the ROS2 Nodes

Follow these steps to deploy the stress-ng autoscaling workload on your Kubernetes cluster. The pods it creates can then be used for the manual talker/listener exercise in the next section. All objects live in the **`ros`** namespace, so every `kubectl` command below uses `-n ros`.

1. **Create the Deployment:**
   Apply `ros_dep_1.yaml` to create the `ros` namespace, the `ros` Deployment and the `ros-hpa` autoscaler. This is a **stress-ng autoscaling workload**; it does not start any ROS2 Talker or Listener node. (Use `ros_dep_2.yaml` or `ros_dep_3.yaml` instead for larger per-pod resource requests; do not apply them together.)

    ```bash
    kubectl apply -f ./ROS2/ros_dep_1.yaml
    ```

    Run this from the repository root. Inside the Vagrant control-plane VM, the repository is mounted at `/home/vagrant/codes`, so the path there is `/home/vagrant/codes/ROS2/ros_dep_1.yaml`.

2. **Scale the Deployment:**
   To get more pods to attach to, scale the deployment. This example scales it to three replicas of the stress-ng pod. Because `ros-hpa` also manages this Deployment, the autoscaler may change the replica count again, depending on measured CPU load and on whether the cluster provides pod metrics (for example through metrics-server). On a kind cluster without metrics-server, `kubectl get hpa -n ros` showed `cpu: <unknown>/70%` with `ScalingActive` `False` (observed 2026-10-31), so the HPA did not scale.

    ```bash
    kubectl scale deployment ros --replicas=3 -n ros
    ```

### Testing the ROS2 Nodes

> **Manual; tested on kind on 2026-10-31 with no messages received.** The pods created above run `stress-ng`, not ROS2 nodes, so you start the Talker and Listener yourself. The image contains the Foxy `demo_nodes_cpp` package at `/opt/ros/foxy` (checked: `ros2 pkg prefix` path present, Ubuntu 20.04). In our kind test, a talker and a listener run concurrently in two pods on different workers received 0 messages, and two pods on the same worker also received 0. Check the listener's output before assuming ROS 2 traffic works in your cluster. For the cross-worker example that did deliver messages on kind, see [Jazzy talker/listener on kind](#jazzy-talkerlistener-on-kind-scripted-demo) below.

After deploying the pods, you can try the manual Talker/Listener exercise:

1. **List the Pods:**
   Check the names of the pods in the `ros` namespace (they run stress-ng) to identify which pods to attach to. Add `-o wide` to also see which Kubernetes node each pod is on.

    ```bash
    kubectl get pods -n ros
    ```

2. **Attach to a Pod and Run the Talker Node:**
   Use `kubectl exec` to attach to one of the pods and start the ROS2 talker node.

    ```bash
    kubectl exec -it -n ros <pod-name> -- /bin/bash
    ```
    then run the following commands inside the pod:
    ```bash
    source /opt/ros/foxy/setup.bash
    ros2 run demo_nodes_cpp talker
    ```

3. **Start the Listener Node in Another Pod:**
   In a separate terminal, attach to another pod to start the listener node.

    ```bash
    kubectl exec -it -n ros <another-pod-name> -- /bin/bash
    ```

    then run the following commands inside the pod:
    
    ```bash 
    source /opt/ros/foxy/setup.bash
    ros2 run demo_nodes_cpp listener
    ```

   If the listener prints the talker's messages, the two ROS2 nodes can communicate in your setup. In our kind test the listener printed nothing, so this step did not succeed there.

![Architecture Diagram](../images/cmd.png)

### Jazzy talker/listener on kind (scripted demo)

The only cross-worker ROS 2 example in this repository that is backed by a repeatable check is the **lightweight kind profile** (1 control plane + 2 workers). It is documented, with its measured run and limits, in [`docs/KIND-DEMO.md`](../docs/KIND-DEMO.md). It is **not** the Vagrant cluster, and it does not run the Foxy image used above.

```bash
make demo     # build the Jazzy image, create the kind cluster, deploy discovery server + talker + listener
make verify   # exit code 0 only if pods are Ready, on different workers, and the listener hears the talker
make clean    # delete the cluster and the image
```

What that page records (quoted, not re-run for this README): default Fast DDS multicast discovery delivered nothing on the kind CNI (kindnetd), across two workers and also on one worker; delivery worked once a Fast DDS Discovery Server was reached through a ClusterIP Service. The profile was run once on one host (2026-10-27, commit `862b026`); `make verify` and `make verify-negative` exited 0 there. Other CNIs, a real multi-machine cluster and the Vagrant/Weave Net setup are **not** covered.

An earlier manual variant of the same idea (a Jazzy talker and listener on different workers behind a Discovery Server, placed by pod anti-affinity, run by hand on kind on 2026-10-31) is superseded by this scripted profile.
