# Contributing to Vagrant-Kubernetes-ROS2-Deployment

Welcome! Contributions from robotics engineers, Kubernetes users, students, researchers, writers and first-time GitHub contributors are appreciated.

**You do not need VirtualBox, a Kubernetes cluster or a powerful workstation to start.** Many documentation, example-data and static CI issues can be completed with a text editor and GitHub.

## Find a first task

- [Good first issues](https://github.com/MSKazemi/ros2-kubernetes-lab/labels/good%20first%20issue) — small, well-scoped tasks suitable for a first PR.
- [Help wanted](https://github.com/MSKazemi/ros2-kubernetes-lab/labels/help%20wanted) — bounded tasks where outside help is especially valuable.
- [Project modernization roadmap](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/23) — proposed longer-term goals and dependencies. The roadmap may change before it merges.
- [All open issues](https://github.com/MSKazemi/ros2-kubernetes-lab/issues).

**Please read the full issue description before starting.** For first contributions, choose one small issue and comment “I'd like to work on this.” Issues are intentionally left unassigned initially so contributors can volunteer; a comment is an invitation to coordinate, not a guarantee of exclusive ownership. If someone else is already working on the task, coordinate in the issue instead of duplicating work.

### Suggested first contributions

- Improve instructions that reference a nonexistent manifest or omit the Kubernetes namespace.
- Check that monitoring screenshots have working file paths and helpful alt text.
- Explain common ROS 2/DDS/Kubernetes concepts in plain English.
- Document existing historical metrics JSON files.
- Introduce standalone CI checks that do not require running virtual machines.

These are examples, not a separate issue backlog; please use the linked labeled GitHub issues for the up-to-date list.

## Optional: contribute with Claude Code or Codex

Coding agents are welcome as **assistants**, not substitutes for reviewing and testing your work. You do **not** have to use an AI tool to contribute. If you want help understanding this codebase, writing a bounded patch, or reviewing your diff:

1. Pick one open issue and comment that you would like to work on it.
2. Fork/clone and create a feature branch **before** starting Claude Code (`claude`) or OpenAI Codex (`codex`) inside the repository.
3. Ask the agent to follow [AGENTS.md](./AGENTS.md) and read the issue. If it cannot access GitHub, paste the issue description. Ask for a small plan **before** editing.
4. Review every change and run relevant checks yourself; never report unrun integration tests as passed.
5. Document the agent assistance, testing evidence, and limitations in the PR.

**Step-by-step beginner tutorial:** [AI-assisted contributions with Claude Code or Codex](./docs/AI_ASSISTED_CONTRIBUTING.md). **Copyable issue-specific prompts:** [Agent prompts](./docs/AGENT_PROMPTS.md).

The repository uses one concise [AGENTS.md](./AGENTS.md) instruction set for Codex and [CLAUDE.md](./CLAUDE.md) for Claude Code (which imports the shared rules). Neither file authorizes an agent to push to `main`, publish images, use secrets, or merge PRs autonomously.

## Make a small pull request

1. Fork this repository (if needed), or clone it:
   ```sh
   git clone https://github.com/MSKazemi/ros2-kubernetes-lab.git
   cd ros2-kubernetes-lab
   ```
2. Create a branch for **one** issue, for example:
   ```sh
   git switch -c docs/clarify-ros2-commands
   ```
3. Make the smallest change that meets the issue's acceptance criteria. Update the related README or other docs when the behavior changes.
4. Run checks appropriate for your contribution (see below), commit, push and open a pull request against `main`. Link the issue, for example `Closes #24` for a complete fix or `Related to #14` for partial preparatory work.
5. In the PR, explain **what you changed, how you tested it, and what you did not test**. Screenshots or terminal output help when appropriate.

### Checks you can run without a cluster

For Bash shell scripts, from the repository root:

```sh
bash scripts/check-shell.sh
# To inspect one file without running it:
bash scripts/check-shell.sh KubernetesClusterSetup/create_cluster.sh
```

The [shell validation workflow](.github/workflows/validate-shell.yml) runs the same checker on every pull request and push to `main`, with no VirtualBox, cluster or Docker Hub credentials. It reports a failure when a tracked `.sh` file contains a Bash **syntax** error; it does **not** verify Kubernetes provisioning, script behavior, shell lint best practices, or ROS 2 DDS messaging. ShellCheck can provide additional lint feedback but is not part of this check.

For Markdown changes, check each modified relative link against a committed file and verify that commands match filenames, namespaces, images and paths in the repository. Do not add images that reveal credentials. There is not yet a full documentation validation workflow.

For sample data changes, provide a small local command or script to verify that the checked-in files parse correctly. Do not change historical measurements to make results look better.

### GitHub Actions workflow scope

The lightweight [shell syntax workflow](.github/workflows/validate-shell.yml) checks tracked Bash scripts on pull requests and `main` pushes without cloud or Docker Hub credentials.

The separate [Jazzy image verification workflow](.github/workflows/ros2-image-ci.yml) builds an **amd64 ROS 2 Jazzy container** and tests local talker/listener communication **in one container**, without Docker Hub credentials. A second step preloads the opt-in ros2_pulse probe into that talker and listener and checks their `/chatter` publish and callback rates, still in one container. The [Docker build/publish workflow](.github/workflows/main.yaml) verifies first, then publishes the **Jazzy image** to Docker Hub using a source-commit tag **only on relevant image/test/workflow changes on `main`** (or authorized manual dispatch). The old Foxy image recipe is retained under `ROS2/legacy/foxy/Dockerfile`, but no longer published by the default workflow. README, tutorial, issue-template and agent-instruction changes must not cause needless image publishing. A successful image build or same-container smoke test **does not prove cross-worker Kubernetes/DDS communication**. This remains an explicit release gate.

### Environment and scope limitations

The existing three-VM `Vagrantfile` allocates roughly **30 GB RAM and 18 vCPUs** by default. Do not run it on under-provisioned hosts merely to satisfy a documentation PR. If you are not able to run it, explicitly say `Not run: Vagrant/VirtualBox cluster (hardware unavailable)` in your PR.

**Important:** The repository still contains historical ROS 2 Foxy, Kubernetes 1.29 and Weave Net code. The modernization roadmap does *not* mean current code is verified on new versions. Never claim a modern cluster or DDS test passes unless you actually ran and documented the test.

A successful Docker build or Bash syntax check does not establish end-to-end ROS 2 messaging. If a feature needs live verification, keep the task open or document the missing validation clearly.

## Quality, security and collaboration

- Be respectful; ask focused questions in the relevant GitHub issue.
- Keep PRs scoped and explain design choices in simple terms.
- Prefer primary technical sources and original explanatory text; include appropriate attribution for external figures or code.
- Never commit passwords, access tokens, kubeconfigs, private host addresses, personal data or sensitive logs. Inspect screenshots and notebooks for such material before submitting.
- Avoid default cluster-wide admin permissions or broadly writable storage in new examples. Security-sensitive changes need extra review.
- Do not submit unreviewed generated code or documentation; you are responsible for correctness and licensing.
- Contributions to this project are submitted under the repository's [Apache-2.0 license](LICENSE); only contribute material you have rights to submit.

Thank you for making the robotics/Kubernetes learning experience easier for others.
