# GitHub SEO and developer discoverability audit — 11 October 2026

**Repository:** https://github.com/MSKazemi/ros2-kubernetes-lab

**Scope:** Repository-level search, README clarity, truthful descriptions, developer discovery, search landing pages, AI answer citations, and organic community growth. This report combines an **actual static repository inspection** with a limited **GitHub repository-search sample**. It does **not** claim to measure Google Search Console, Bing impressions, ChatGPT recommendations, visitors, or traffic. The Vagrant/Kubernetes stack remains a historical ROS 2 Foxy lab (`legacy`); a separate ROS 2 Jazzy / Ubuntu 24.04 container image is `container tested` only, and `cross-worker verified` has not been achieved (see [support states](ROS2-KUBERNETES-DDS-GUIDE.md#support-states-and-evidence)).

## Baseline (observed 11 October 2026)

| Signal | Observation | Evidence / limitation |
|---|---|---|
| GitHub stars | 6 | Public GitHub API snapshot, not a direct adoption metric |
| GitHub forks | 3 | Public GitHub API snapshot |
| GitHub Pages | Not enabled (`has_pages=false`) | No published project docs website was found in repository settings/API |
| README primary heading | `Vagrant-Kubernetes-ROS2 Deployment` | Main term `ROS 2 on Kubernetes` could be more prominent |
| GitHub About description | Led with ROS 2 Foxy and a long component list | Too implementation-specific; historical tools dominate |
| Topics | 18, including `ros2-foxy` and `weave-net` | Accurate historical topics, but missing some educational intent terms |
| GitHub releases | None observed in prior audit | Do not manufacture a release without validated integration tests |
| `llms.txt` | Present, but claimed automatic working talker/listener flow | Improve factual consistency; no evidence this file itself affects ranking |
| ROS 2 runtime accuracy | `ROS2/ros_dep_1.yaml` starts `stress-ng` | Claim must distinguish stress manifests from manual ROS 2 demo |
| Dependency lifecycle | Foxy EOL; Kubernetes 1.29 EOL; Weave Net archived | Mark as legacy and prioritize modernization |

### Limited GitHub search observation

GitHub repository search returned the repository in position **2** for `ros2 kubernetes in:name,description,topics`, and position **1** for `ROS2 Kubernetes Vagrant` and `DDS Kubernetes ROS2` in the same fields. The latter queries returned few results. Search order is dynamic, personalized and not a measure of Google rankings. **Do not convert these observations into a fictitious “SEO score.”**

GitHub's own documentation identifies repository **name, description, topics, and README** as searchable surfaces: https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories

## Primary positioning — current repository, not yet renamed

- **Primary phrase:** `ROS 2 on Kubernetes`
- **Secondary phrases:** `ROS 2 Kubernetes tutorial`, `ROS 2 Kubernetes Vagrant`, `multi-node Kubernetes lab`, `DDS discovery Kubernetes`, `ROS 2 Docker container`, `Kubernetes ROS 2 monitoring`.
- **Real use case:** Learning how to provision and inspect a local three-VM kubeadm lab and explore ROS 2 middleware, stress workloads and monitoring.
- **Audience:** Robotics engineers, ROS 2 developers, Kubernetes students/instructors, and research teams.
- **Do not target as established features:** `ROS 2 Jazzy Kubernetes`, `production-ready ROS 2`, `real-time robot orchestration`, `one-command modern ROS 2`, `multi-cluster` before implementation and verification.

### Repository name

**Proposed eventual slug:** `ros2-kubernetes-lab` (tracked in [#22](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/22)). This audit makes **no repository rename**. Avoid creating competing canonical URLs before the change decision is made and a migration plan exists.

## Copy/paste GitHub About metadata (requires repository settings access)

**Suggested description** (fits the current implementation):

> Local ROS 2 on Kubernetes lab with Vagrant, VirtualBox, DDS experiments, Prometheus/Grafana monitoring, and autoscaling examples (legacy Foxy).

**Suggested topics** (choose accurately; avoid indiscriminate topic stuffing):

```text
ros2
kubernetes
robotics
cloud-robotics
dds
vagrant
virtualbox
kubeadm
kubernetes-cluster
container-orchestration
robot-operating-system
distributed-systems
prometheus
grafana
monitoring
autoscaling
jupyter-notebook
ros2-foxy
```

Retain a clear Foxy/legacy signal until a modern tested release exists. Do **not** add tags such as `ros2-jazzy`, `production`, `edge-computing` or `multicluster` without verified implementation. GitHub allows a maximum of 20 topics: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics

**Suggested homepage URL:** a dedicated, publicly accessible project docs page **once it has been published**, rather than an unrelated personal homepage. If none is available, avoid claiming a docs site already exists; keep the canonical GitHub URL in content in the meantime.

**Social preview:** a 1280×640 graphic with “ROS 2 on Kubernetes”, a 3-node topology, and clear “Educational lab” context; upload it in **Settings → Social preview**. GitHub requires PNG/JPG/GIF under 1 MB. A committed image alone does not change GitHub's card image: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview

## Search intent → useful content map

| Search intent | Landing content | Status |
|---|---|---|
| What is an ROS 2 Kubernetes lab? | README intro and feature summary | Improve in this PR |
| How to set up a three-node Kubernetes lab with Vagrant? | README Quickstart + `KubernetesClusterSetup/README.md` | Improve introductory accuracy now; maintain older instructions separately |
| How does ROS 2 DDS discovery work across Kubernetes pods? | `docs/ROS2-KUBERNETES-DDS-GUIDE.md` | New in this PR |
| How do I monitor ROS 2 and Kubernetes resource usage? | `MonitoringSystem/README.md`, `DataAnalysis/README.md` | Existing historical material |
| Why does the ROS 2 listener not receive messages on Kubernetes? | DDS guide + link to real troubleshooting tasks | New in this PR; actual validation pending |
| Can I use ROS 2 Jazzy/kind/k3d? | Compatibility warning and planned issues | A Jazzy container image exists (`container tested`, single container). Jazzy on Kubernetes across workers and kind/k3d are not delivered; do not position them as available |
| Can I contribute without a large VM? | Good-first-issue labels + contributor PR #31 | Contributor PR is open, not merged |
| How can I deploy across multiple robot/edge clusters? | Separate exploratory project, not this lab | Do not claim current feature coverage |

## Implementation queue, evidence and limits

| Priority | Action | Status |
|---|---|---|
| P0 | Make main H1, first 150 words, use cases, and FAQ clearly answer ROS 2/Kubernetes queries | In this PR |
| P0 | Correct overclaims about end-to-end DDS, modern support, installation reproducibility | In this PR |
| P0 | Add a linked, useful DDS troubleshooting guide anchored in actual files | In this PR |
| P1 | Align `llms.txt` with current status and primary source links | In this PR; no assumed SEO ranking benefit |
| P1 | Update GitHub About/description/topics/website | **Manual repository metadata action required**; tracked in [#32](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/32) |
| P1 | Upload custom GitHub social preview image | **Manual repository settings action required**; [#32](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/32) |
| P1 | Publish a project docs website with stable canonicals, sitemap and unique pages | Planned in [#19](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/19); not yet live |
| P1 | Create a real verified release and corrected CI once ROS modernization completes | [#20](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/20) |
| P2 | Publish reproducible technical articles and get genuine citations/backlinks | [#21](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/21) |

**Avoid false SEO “fixes”:** GitHub-hosted README Markdown does not let the repository owner set arbitrary HTML `<head>` title/description, robots directives, sitemaps, or structured data. These controls belong on a separately published website. A `robots.txt` file committed to the repository root would not control GitHub crawling. Similarly, `llms.txt` is informational and does not establish search-engine inclusion, traffic, or answer-engine citations.

## Measurement plan (no invented data)

After the change lands, record **date, exact query and search engine** for small controlled checks. For GitHub, repeat:
- `ros2 kubernetes in:name,description,topics`
- `ros2 vagrant kubernetes in:name,description,topics`
- `dds discovery kubernetes in:name,description,topics`

For Google/Bing: check brand and project queries manually, without declaring a site indexed based only on a one-off `site:` search. If a dedicated project docs site launches, verify ownership with Google Search Console and Bing Webmaster Tools, then measure impressions, clicks, indexed URLs and referring queries **from first-party reports**. GitHub Insights gives repository visitors and clones where available. Track real outside issues, forks, PRs, and successful installations as stronger adoption signals.

## Official platform references

- GitHub repository search: https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories
- GitHub topics: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics
- GitHub README: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
- GitHub Pages publishing: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- ROS 2 release support: https://docs.ros.org/en/rolling/Releases.html
- Fast DDS Discovery Server: https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html
