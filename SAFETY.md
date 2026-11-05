# Safety, limitations and pre-deployment checks — robo-resilience-lab

**Scope:** Vagrant virtual machines, legacy and newer ROS 2 experiments, Kubernetes network and CPU stress workloads.  
**Issued:** 2026-10-17  
**Status:** Risk guidance only. No claim is made that any checklist item is already implemented, tested, legally approved or certified.

This document supplements [DISCLAIMER.md](DISCLAIMER.md) and the existing copyright/license terms without changing either. It does not prevent claims or waive mandatory legal duties.

## Risks to assess

- README identifies historical ROS 2 Foxy, legacy Kubernetes/Weave setup and experiments that are not validated production configurations.
- Stress workloads, elevated Kubernetes permissions and network modifications can disrupt the host, guests or shared network.
- Successful local container-level smoke tests do not establish DDS behavior, robotics safety or multi-node reliability.

## Checks before live use

- [ ] Use dedicated isolated development machines with sufficient resources; avoid production networks and clusters.
- [ ] Verify exact image digests, source integrity, version support and network configuration before each experiment.
- [ ] Exercise provisioning and cleanup in disposable VMs, monitoring memory/CPU/disk/network effects and rollback.
- [ ] Never use this lab as a certified robotics controller or real-time control safety layer.

## User and maintainer responsibilities

Begin in an isolated, authorized test environment; apply least privilege, backups, monitoring and an independent review of any high-impact outputs or actions. Where a project depends on third-party providers or real equipment, comply with vendor terms and safety instructions. Report suspected security flaws privately. Record actual test evidence, versions and unresolved risks rather than inferring that documentation is proof of implementation.

**Mandatory rights preserved:** Liability, product-safety, privacy, security and consumer obligations cannot be eliminated by this notice where applicable law forbids exclusion.
