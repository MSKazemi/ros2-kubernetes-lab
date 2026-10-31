# Security policy — Vagrant-Kubernetes-ROS2-Deployment

**Published:** 2026-10-17  
**Support commitment:** No specific security response deadline, support window or fix guarantee is promised by this file. Maintainership and available updates depend on the project and applicable law.

## Reporting a vulnerability

**Do not publish exploits, credentials, unredacted data or attack instructions in public issues or pull requests.**

1. If GitHub's private vulnerability reporting is enabled, use [Report a vulnerability](https://github.com/MSKazemi/ros2-kubernetes-lab/security/advisories/new).
2. If that feature is unavailable, email the security contact publicly designated by the maintainer in the [KubeIntellect security policy](https://github.com/MSKazemi/kubeintellect/blob/main/SECURITY.md) with subject `SECURITY: ros2-kubernetes-lab` and ask for a coordinated private channel. Include only what is necessary to triage the report.
3. If you cannot reach a private channel, open a non-sensitive public issue **only to request a private reporting contact**; do not disclose technical exploit details there.

Include the affected version/commit, reproducible conditions, likely impact and a minimal safe proof of concept. Please do not access third-party data, scan systems without authorization or disrupt live users.

## Areas of interest

Vagrant VM provisioning, Kubernetes manifests, ROS 2 messages, networking, resource stressors and host escape. Report any vulnerability that may compromise confidentiality, integrity, availability, authorization or independent human supervision.

## Supported versions

Only the actual current release, maintained branch or published support policy (if any) should be assumed eligible for attention. **No version receives a contractual maintenance or security-fix promise from this policy alone.** Legacy research examples and unmaintained releases may have known vulnerabilities; do not deploy them without separate assessment.

## Coordinated disclosure

Where practical, the maintainer can investigate privately, assess impact, implement a fix and publish an advisory. There is no guaranteed schedule or certification. Obligations under applicable data protection, incident-reporting, cybersecurity and product laws continue to apply irrespective of this policy or the [Disclaimer](DISCLAIMER.md).
