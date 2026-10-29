# Reusable coding-agent prompts for first contributions

These are **copy-and-paste prompts** for Claude Code and OpenAI Codex. Start either tool in your checkout and make a branch before using them; the [beginner walkthrough](./AI_ASSISTED_CONTRIBUTING.md) explains how. **Read the live issue first**, because its status and requirements may have changed.

Agents must follow [AGENTS.md](../AGENTS.md) and [CONTRIBUTING.md](../CONTRIBUTING.md). If they cannot access the GitHub issue, paste the current description. They should not invent issue requirements, skip review, or claim tests were run without evidence.

## 1. Website audit: issue #89 — student scenario usability and accessibility

```text
I am contributing to issue #89:
https://github.com/MSKazemi/ros2-kubernetes-lab/issues/89

First read AGENTS.md, the current issue body and its parent epic #83, asking me to paste
them if you lack GitHub access. Inspect site/scenarios, site/assets and scripts/validate-site.py.
Audit accessibility and technical SEO for the content that actually exists: headings,
link names, focus order, contrast, reduced-motion behavior, titles, meta descriptions and canonicals.
Test responsive or keyboard behavior in a browser only if a real browser is available;
otherwise say clearly that it was not tested. Do not report invented Lighthouse scores or search rankings.
Propose small, scoped fixes and wait for my approval before editing.
No autonomous push to main, no merge, and no spam outreach.
```

**Human check:** Open the pages yourself at a narrow and a wide viewport and with the keyboard only. Every finding needs the exact URL, viewport and observed behavior, and any screenshot must be free of secrets.

## 2. First coding PR: issue #55 — CPU-only mock policy

```text
I want to implement open issue #55 with a small PR.
Read AGENTS.md, the issue text and its acceptance criteria, and the existing ROS2/ directory.
The issue body is authoritative; if it is not accessible, ask me to paste it and do not guess.
First propose a minimal change that meets the acceptance criteria, listing the files you would add or edit.
It must not need Docker Hub secrets, push container images, start Vagrant VMs,
or rewrite existing workloads. Do not change runtime behavior of current manifests or publish artifacts.
Explain how you will verify the change without a cluster, and which checks you cannot run.
After I approve, implement it, document the verification command where the issue's scope requires it,
and show checks actually run and ones still awaiting GitHub CI.
```

**Human check:** Confirm the issue's acceptance criteria are met and that no check implies a cluster, DDS or hardware test passed.

**Coordinate first:** PR [#113](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/113) already references this issue. Read it and comment there before starting, rather than opening a duplicate.

## 3. Kubernetes validation: issue #29 — manifest schemas

```text
I want to work on issue #29. Read AGENTS.md and the open issue first.
Inspect ROS2/*.yaml and identify built-in Kubernetes resources versus
the VerticalPodAutoscaler custom resource. Propose a maintained offline
schema-checking workflow with pinned tool version.
Do not silently claim a built-in schema covers VerticalPodAutoscaler;
either validate using an appropriate pinned CRD schema or explicitly document
the excluded file. Keep PR checks independent of a cluster or credentials.
After approval, implement minimal CI/doc changes and report actual validation.
```

**Human check:** Any VPA schema exception must be deliberate and documented, not a fake green test.

**Coordinate first:** PR [#112](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/112) already addresses this issue. Read it and comment there before starting, rather than opening a duplicate.

## 4. Advanced issue #14 — ROS 2 talker/listener integration

```text
I want to plan (not immediately implement) issue #14.
Read AGENTS.md, the issue, ROS2/Dockerfile, the workload YAML files,
Network/network_plugin.sh and the relevant documentation.
Explain the dependencies on #7 (supported ROS image) and #15 (DDS discovery),
the difference between ROS 2 nodes and Kubernetes workers, and
how to validate cross-worker communication with explicit node placement.
Propose a phased approach and an executable smoke-test specification with
timeouts, expected observable subscriber output, and failure diagnostics.
Do not claim automatic multi-node DDS works or change production/safety settings.
Wait for human approval before editing.
```

**Human check:** A listener receiving a message is not cross-worker evidence unless node placement and middleware configuration are also verified.

## 5. Skeptical pre-PR review (any issue)

```text
Review my uncommitted changes against AGENTS.md and the selected GitHub issue.
Inspect git diff and relevant tests. List concrete correctness, security,
documentation and scope problems with file paths and severity.
Distinguish tests you observed from ones you did not run.
Do not edit, commit, push, publish artifacts, or merge a PR.
End with a short verification checklist I can execute myself.
```

Use this final prompt even if another agent wrote the patch. When in doubt, ask a maintainer before expanding the scope.
