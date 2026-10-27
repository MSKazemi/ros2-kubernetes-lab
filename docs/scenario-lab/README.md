# Cloud–Edge Robotics Scenario Lab — research and collaboration program

> **Status (2026-10-27): scenario website content and synthetic conceptual animations are proposed for review; no runtime Jev integration or scientifically verified performance outcomes.** The existing ROS 2 Kubernetes repository has a historical Foxy/Kubernetes 1.29 Vagrant profile and a newer Jazzy image-local test, **not** a validated cross-worker DDS fleet.

## Website and research goals

Audience: undergraduates learning ROS 2/Kubernetes, MSc students building reproducible experiments, PhD researchers designing studies, university instructors, infrastructure engineers and robotics/AI contributors.

The site at [site/scenarios/](../../site/scenarios/index.html) provides interactive explanations, testable hypotheses, research metrics and issue links, all **static** and **no real robot model/API calls**. It uses the existing [website brand](../../site/BRAND.md) and [site validator](../../scripts/validate-site.py). Proposed canonical Pages URL is determined by existing site configuration; verify public availability separately before promotion.

### Scenario ladder

| Scenario | Website page | Question | Collaboration | Dependency |
| --- | --- | --- | --- | --- |
| S1 beginner — fault triage | [DDS/QoS diagnosis](../../site/scenarios/ros2-fault-triage.html) | Can Jev improve diagnostics over rule baselines on synthetic held-out incidents? | [#84](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/84) | #74, #55, #59 |
| S2 systems — placement | [Edge vs cloud](../../site/scenarios/edge-cloud-inference.html) | Is structured advice useful after hard eligibility, network and action freshness constraints? | [#85](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/85) | #62, #60, #61 |
| S3 LLM agents — screening | [Agent skill safety](../../site/scenarios/robot-agent-safety.html) | Does Jev advisory screening augment independently enforced simulator policies? | [#86](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/86) | #64, #55, #59 |
| S4 fleet research — dispatch | [Multi-robot scheduling](../../site/scenarios/multi-robot-scheduling.html) | Does Jev ranking of prequalified simulated robots improve fit/fairness? | [#87](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/87) | #69, #60, #59 |

**Future ideas:** ROS 2 incident routing, VLA checkpoint/embodiment compatibility review and more. Do not create large numbers of thin placeholder pages to target keywords.

### Reproducible results

- [Website evidence board](../../site/scenarios/results.html)
- [Machine-readable initial registry](../../site/scenarios/data/experiments.json): four \`planned\` records; every performance value is **null**.
- [Result publication / peer-review contract](RESULTS-PUBLICATION.md)
- [#88 Results and reproducibility](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/88)
- [#75 Jev benchmark protocol](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75); [#60 general experiment manifest](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60)

### Build and review

The static site is under \`site/\` and uses no frontend package manager. Review with a local server:

\`\`\`sh
python3 -m http.server 8000 --directory site
# open http://localhost:8000/scenarios/
python3 scripts/validate-site.py
node --check site/assets/scenarios.js
\`\`\`

The script validator verifies metadata, internal links, sitemap and registry status/evidence conditions; a passing result does **not** prove live Jev correctness or scientifically valid results. Test visually and with keyboard/screen-reader/motion preferences at 360/390/768/1024/1440 px, on localhost or a reviewed Pages preview. If the environment has no browser, clearly state visual QA was not performed.

**Motion controls:** no autoplay, an explicitly activated conceptual walkthrough, pause/reset behavior, accessible stage buttons, native reduced-motion preference, and static visible explanations without JavaScript. The conceptual animation never performs a Jev call, ROS command or Kubernetes mutation.

### Contribute

- [Epic #83](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/83): track the overall program.
- [#84](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/84) and [#89](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/89) welcome beginners; scoped language/fixture/UX tasks need no robot or cloud account.
- [Claude Code / Codex playbook](CLAUDE-DEVELOPMENT-PLAYBOOK.md) covers issue-first development and review.
- [Student discoverability & SEO plan](SEO-CONTENT-PLAN.md) covers page intent and evidence-based growth.

Observe root [AGENTS.md](../../AGENTS.md), [CONTRIBUTING.md](../../CONTRIBUTING.md) and [SAFETY.md](../../SAFETY.md). No autonomous push to \`main\`, merged PR, live robot actuation, unapproved cloud bills or secret/data publishing.

### Research honesty checklist

- [ ] No benchmark result without raw evidence, script and immutable run provenance.
- [ ] No claimed physical robot safety or real-time guarantees.
- [ ] No assumption of modern ROS 2 cross-worker validation (#14/#15/#16 remain open).
- [ ] Jev answers are advisory, never permissions, resource thresholds or executable instructions.
- [ ] Student exercises are synthetic and readable without animation or JavaScript.
- [ ] Model and provider references are current and do not imply TypeSafe sponsorship.
