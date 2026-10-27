# Claude Code / Codex playbook — animated cloud robotics research website

> Read the live issue and [AGENTS.md](../../AGENTS.md) **before work**. The scenario site and its four detailed pages are already authored in the website PR; do not rebuild from scratch or duplicate a finished task. Choose **one issue** and keep the patch bounded. AI tools assist coding, not decisions about ethics, benchmark truth or robotics safety.

## 1. Site design system (source of truth)

- Existing website brand: [site/BRAND.md](../../site/BRAND.md).
- CSS foundation: \`site/assets/docs.css\`; site-specific rules: \`site/assets/scenarios.css\`. Keep native HTML/CSS/JS, no unnecessary package/dependency introduction.
- Site interaction: \`site/assets/scenarios.js\` — static case data and illustrative step animation only; **no Jev API**, no ROS 2 message subscriptions, no model inference, no privileged mutation, no analytics/cookies.
- Pages: \`site/scenarios/index.html\`, \`ros2-fault-triage.html\`, \`edge-cloud-inference.html\`, \`robot-agent-safety.html\`, \`multi-robot-scheduling.html\`, \`results.html\`.
- Evidence: \`site/scenarios/data/experiments.json\`; validator \`scripts/validate-site.py\`; Pages CI \`.github/workflows/pages.yml\`.
- Visual style: deep navy \`#080D18\`, panel \`#101B2E\`, ice text, signal aqua \`#66EBDA\`, infrastructure blue \`#7397FF\`, lilac \`#A193FF\`, warning amber \`#FFA66E\`; Space Grotesk headings, DM Sans body, JetBrains Mono technical details; no false performance badges.
- Header uses existing logo and GitHub repo links, never a TypeSafe vendor logo used without rights or endorsement.
- Animation: gentle wire-dash flows, node pulse and interactive step highlighting. Respect \`prefers-reduced-motion\`, pause control, keyboard interaction, minimum contrast, no autoplay inference and no blocked page content if JavaScript is disabled.

## 2. Site or SEO improvement prompt — issue #89

\`\`\`text
You are implementing one bounded improvement to issue #89 for
MSKazemi/Vagrant-Kubernetes-ROS2-Deployment.
First read the current AGENTS.md, CONTRIBUTING.md, issue #83 and #89.
Inspect site/BRAND.md, site/scenarios/, site/assets/scenarios.css,
site/assets/scenarios.js, scripts/validate-site.py, .github/workflows/pages.yml.
Read any live GitHub PR that is still open. Do not recreate existing files.

Goal: improve student usability and evidence-based discoverability for the
research scenario pages. Keep all meaningful content in static, crawlable
HTML; ensure titles/canonicals/OG/sitemap/links match the published URL.
Make keyboard focus visible, accessible nav and controls, meaningful SVG
descriptions, reduced-motion pause, mobile layouts and no-JS fallback.
Never claim Jev API, ROS 2 DDS multi-node, benchmarks or robot safety work
unless tests actually ran. Do not add fake charts, keyword stuffing,
tracking pixels, spam outreach or made-up Search Console metrics.

Before editing: propose precise files, acceptance checks and review plan.
After editing: run python3 scripts/validate-site.py, node --check for every
changed JS file, and inspect relevant pages in a browser if available.
State exactly what was and was not observed (especially browser QA).
Show git diff; do not autonomously push to main or merge.
\`\`\`

## 3. Scientific casebook prompt — issue #84

\`\`\`text
Read AGENTS.md, issue #83, issue #84, #74 and docs/scenario-lab/README.md.
Create a small offline-only synthetic ROS 2 DDS/QoS/Kubernetes incident casebook
with correct evidence, family-grouped split IDs, true/unknown labels and
abstention examples. Add at least one contradictory and one untrusted-log
case. Do not call Jev or assert any diagnosis came from it; use a deterministic
rule baseline for expected labels. No Vagrant, ROS actuation, cloud account,
real telemetry, personal data or credentials. Check JSON syntax/schema,
disclose which tests were run and show a scoped diff for human review.
\`\`\`

## 4. Benchmark artifact prompt — issue #88

\`\`\`text
Read AGENTS.md, issue #83, #88 and #60 plus
docs/scenario-lab/RESULTS-PUBLICATION.md.
Review the experiment registry and static validator. Propose strict
reproducibility metadata for model/data revisions, exact commit/manifest hash,
run counts, raw data, analysis scripts, units, confidence intervals, rejected
runs and independent reviewer. All existing performance values must remain
null. Test that a fake 'verified' value with no evidence fails offline CI.
Do not publish unmeasured improvements or make paid provider calls.
Only after an actual valid run and human review may a numeric result appear.
\`\`\`

## 5. Epic and child task map

| Issue | Domain | Expected contributor output |
| --- | --- | --- |
| [#83](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/83) | Umbrella | Roadmap, acceptance, cross-dependency review |
| [#84](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/84) | Fault triage | Synthetic fixture casebook and offline diagnostic baseline |
| [#85](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/85) | Edge/cloud | Network/placement experiment matrix and eligibility contract |
| [#86](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/86) | Agents | High-level simulator-skill review threat fixtures |
| [#87](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/87) | Fleet | Synthetic task/fleet scheduling fairness protocol |
| [#88](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/88) | Reproducibility | Evidence metadata validator, measured/failed run publication |
| [#89](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/89) | SEO, a11y | Responsive/keyboard/reduced-motion/browser/SEO audit |

**Dependencies:** Jev PoC #74 and benchmark #75, general scientific manifest #60, typed contract #55, safety gate #59, network/ROS verification #14/#15/#16, research tracks #62/#64/#69.

## 6. Change-management rules

- Do not merge two concurrent PRs with overlapping \`site/index.html\` changes blindly; rebase and human-review. Website PR #63 was already merged; Jev docs PR #76 may still be open.
- Do not create fictitious public websites or claim an unverified URL is live. Verify actual GitHub Pages deployment before outreach.
- Work on a branch and draft PR. No force-push, autonomous main write, secrets, changing license, publishing model weights or deploying physical robot controls.
- Do not create new issues merely to inflate a community count; use current #83–#89 for real, sufficiently bounded work.
- Prefer accepted improvements to accessibility/readability over decorative motion; measure site performance, link integrity and student completion time before changing technical stack.
