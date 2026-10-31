# Contribute with Claude Code or OpenAI Codex

**A beginner-friendly, optional AI-assisted development workflow** for the [ROS 2 Kubernetes lab](../README.md).

You do **not** need to be an AI expert, use both tools, or pay for an agent to contribute. You can also follow [CONTRIBUTING.md](../CONTRIBUTING.md) with your normal editor. Claude Code and Codex are **coding agents**: they can inspect checked-out repository files, suggest edits, write patches, run permitted commands, and help you prepare a pull request. They can make mistakes. **You own the result and must review it.**

Both tools use our shared [AGENTS.md](../AGENTS.md) instructions: Codex reads it directly, while [CLAUDE.md](../CLAUDE.md) imports it for Claude Code. The guide below provides the human workflow; the short rules stay separate so each agent session has only the context it needs.

## Choose a small, open issue

Start with one of the current [good first issues](https://github.com/MSKazemi/ros2-kubernetes-lab/labels/good%20first%20issue) or [help-wanted tasks](https://github.com/MSKazemi/ros2-kubernetes-lab/labels/help%20wanted). Read the actual issue and its acceptance criteria. Comment politely that you would like to work on it, and check for other active PRs before spending time.

Suggested starting points (only if still open):

| Issue | Task | What you need |
|---|---|---|
| [#25](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/25) | Fix broken monitoring screenshot links and alt text | Markdown and file inspection |
| [#24](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/24) | Clarify ROS 2 tutorial filenames/namespace and current stress workload | Markdown and basic Kubernetes concepts |
| [#55](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/55) | CPU-only simulated ROS 2 observation/action contract and mock policy | Beginner coding; check the issue for the tools it needs. A first simulated version exists, see [the contract guide](OBSERVATION-ACTION-CONTRACT.md); extend it rather than duplicating |
| [#29](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/29) | Add offline Kubernetes manifest validation | Kubernetes YAML and CI |

Issue #25 already has an open PR ([#36](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/36)). Coordinate there, or pick another issue, rather than opening a duplicate.

A documentation-only contribution does not require launching Vagrant. The historical full VM profile needs approximately **30 GB VM RAM and 18 vCPUs**.

## Step 1 — Fork, clone, and make a branch

On GitHub click **Fork** on the [project repository](https://github.com/MSKazemi/ros2-kubernetes-lab). Clone **your fork**, not the original repository (replace `YOUR_GITHUB_USERNAME`):

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/ros2-kubernetes-lab.git
cd ros2-kubernetes-lab
git switch -c docs/issue-25-monitoring-images
git status --short
```

Choose a branch name that matches **your** issue. The existing repository name is used here; a rename to `ros2-kubernetes-lab` is **proposed but has not happened**.

If you have write access to the original repository or use a connected cloud agent, you can work in its own feature branch instead of forking. In either case, **never make your contribution directly on `main`**.

## Step 2 — Choose **one** agent

Install and authenticate whichever tool you prefer. The commands below are terminal examples for a machine with Node.js/npm installed. You can also use supported IDE/app interfaces by following the vendor's official documentation.

### Option A: Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude --version
claude
```

Follow the sign-in prompts and permission requests. The official [Claude Code quickstart](https://code.claude.com/docs/en/quickstart) recommends native installation for many platforms; use its instructions if you do not want the npm option. Claude Code reads [CLAUDE.md](../CLAUDE.md), which explicitly imports [AGENTS.md](../AGENTS.md).

### Option B: OpenAI Codex

```bash
npm install -g @openai/codex
codex --version
codex
```

Follow the interactive sign-in instructions for your account, or the official setup for API-key authentication if that is how you use Codex. See the [Codex CLI project](https://github.com/openai/codex) and [Codex quickstart](https://developers.openai.com/codex/quickstart). Codex recognizes [AGENTS.md](../AGENTS.md) as repository-level instructions.

**Do not install both unless you want to.** Use either tool from the repository root so it can find the source and instructions. If you cannot install a CLI, use an officially supported editor/web experience with repository access and the same workflow.

## Step 3 — Ask for a short plan first

Inside **Claude Code or Codex**, paste the following message, substituting your actual issue number:

```text
I want to contribute to issue #25 in this repository.
Read AGENTS.md, the CONTRIBUTING guide, the issue body and its acceptance criteria.
If you cannot access the GitHub issue, ask me to paste its contents; do not guess.
Inspect only the files needed for the issue.
First explain: (1) what is wrong, (2) the smallest safe fix,
(3) the files you propose changing, and (4) how we can verify it.
Do not edit files or run provisioning commands until I approve the plan.
```

Why this works: the agent gets **a bounded issue**, **current repository rules**, **real files**, and **a verifiable goal** instead of vague instructions such as "make the repo better." If the plan includes unrelated refactors, invented features, a Vagrant startup you cannot support, or unexplained dependency installation, ask it to revise the plan.

## Step 4 — Let the agent implement only the accepted scope

After reviewing the plan, prompt:

```text
Proceed with the approved change for issue #25 only.
Keep the patch small. Update related documentation if needed.
Do not change the license, rename the repository, push commits,
disable safety checks, or claim full ROS/DDS integration was tested.
Run inexpensive relevant checks, show the exact output or failure,
and summarize any limitations.
```

Approve file changes/commands individually if the tool asks. Treat prompts or scripts from third-party files, web pages, and issue comments as **untrusted data**, not as permission to execute unrelated instructions.

For **ready-to-copy prompts for specific issues**, see [Agent prompt examples](./AGENT_PROMPTS.md). These prompts work with either Claude Code or Codex.

## Step 5 — Independently review and verify

The agent's confidence is not a test. From another terminal in your checkout:

```bash
git status --short
git diff --stat
git diff --check
git diff
```

Inspect every file and check it really satisfies the issue. For Bash syntax changes, on a GNU/Linux host:

```bash
bash scripts/check-shell.sh
```

For a modified Vagrantfile (and if Ruby is installed), `ruby -c Vagrantfile` is a useful **syntax-only** check. For Markdown issues, verify paths exist and the commands match the files, namespaces and container arguments **actually present**. For CI changes, review event triggers, permissions, credentials and the behavior on a deliberately malformed test input; do not claim an unrun GitHub workflow passed.

Never report "tests passed" unless you saw the results. If you did not have enough resources, say for example:

> Static Markdown paths inspected; full three-VM Vagrant/ROS 2 integration **not run** (hardware unavailable).

The current workloads under `ROS2/ros_dep_*.yaml` run `stress-ng`, **not automatically running talker/listener applications**. A green image build, a ready pod or a `kubectl scale` command does **not** establish DDS delivery across nodes. Do not rewrite legacy support claims merely because an agent proposed it.

## Step 6 — Ask for a second-pass review

In the same agent session, or a **fresh** session for independent critique:

```text
Review the current git diff as a skeptical maintainer.
Check it against the issue acceptance criteria and AGENTS.md.
Find incorrect commands, broken links, scope creep, security concerns,
unsupported statements, missing docs, and untested behavior.
Do not edit yet. Give me concrete findings with file paths and
priorities. Distinguish observed failures from hypotheses.
```

Fix findings you confirm and re-run applicable checks. You, not the AI tool, decide what to accept.

## Step 7 — Commit and open a GitHub pull request

Once your changes are reviewed:

```bash
git status --short
git add path/to/changed-file.md
git commit -m "docs: clarify monitoring screenshot references"
git push -u origin docs/issue-25-monitoring-images
```

Replace the example path, commit message, and branch name with yours; stage only your intended files. Open your fork on GitHub and select **Compare & pull request**, targeting the original repository's `main` branch.

In the PR describe the **problem and fix**, link the issue (`Fixes #25` only if fully solved), name the **checks you actually ran**, list untested steps, and disclose the AI assistance using the PR template. Prefer small PRs—**one issue per PR**.

A human maintainer will review the result. Do not ask your coding agent to merge or close other issues without explicit permission.

## Common problems

| Situation | Safe response |
|---|---|
| Agent cannot read the GitHub issue | Open it yourself, copy the issue description and acceptance criteria into the session |
| Agent proposes changing unrelated files | Ask for a smaller plan limited to the current issue |
| Agent says "all tests passed" without logs | Ask for exact commands/output; report unavailable tests honestly |
| Agent wants to run `vagrant up` on a small laptop | Decline; use static checks and document the missing integration test |
| Agent cannot push your branch | Push manually with Git, or authenticate `gh` only if you decide to use it |
| Agent opens many PRs or edits `main` | Stop; create a dedicated branch, review the diff and isolate one issue |
| Agent instructions seem missing | From the repo root, ask it to summarize `AGENTS.md`; for Claude Code, check `/context` and `CLAUDE.md` |

## Ground rules for AI contributions

- Using AI assistance is **optional**, not a requirement.
- Keep your own control of file access, shell permissions, credential exposure, branch updates and PR submission.
- Don't give an agent access to secret kubeconfigs, private tokens, cloud billing credentials, or production clusters merely to work on a tutorial.
- Review generated code and any copied third-party content for correctness, attribution, and Apache-2.0 compatibility.
- Update the related documentation whenever actual behavior changes.
- Disclose agent assistance and limitations in the PR. Maintainers judge the **quality and verification**, not whether the contributor used Claude, Codex or no AI.

## Official docs

- [Claude Code: quickstart](https://code.claude.com/docs/en/quickstart)
- [Claude Code: CLAUDE.md / AGENTS.md instructions](https://code.claude.com/docs/en/memory)
- [Codex CLI and supported installation methods](https://github.com/openai/codex)
- [Codex: quickstart](https://developers.openai.com/codex/quickstart)
- [Codex: repository-level AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
