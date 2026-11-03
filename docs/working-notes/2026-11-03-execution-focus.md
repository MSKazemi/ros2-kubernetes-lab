# Execution focus — 3 November 2026

> **Status:** working note / suggested plan, not an experiment report or confirmation of completed work. Live GitHub states may change. This file records a public-repository-safe brainstorming and prioritization discussion. No personal, private, proprietary, credential, or unpublished research data is included.

## Decision

**Prioritize one reproducible research increment over more proposals, scenarios, epics or branding work.** The near-term opportunity is to make the existing ROS 2 Kubernetes substrate and embodied-agent mobility experiment independently reviewable. The wider program remains [the canonical program roadmap](../PROGRAM-ROADMAP-2026-2027.md) and [experiment portfolio](../EXPERIMENT-PORTFOLIO.md), not this dated note.

### Verified repository snapshot (checked 2026-11-03)

- `main` is public at `MSKazemi/ros2-kubernetes-lab`; observed 64 open issues and 6 open PRs *before this plan PR*. There are already many more proposals than measured research experiments.
- [PR #97](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/97) **merged** on 2026-10-31: a kind/ROS 2 Jazzy/Fast DDS Discovery Server talker+listener path across two separate kind workers, `make demo`, `make verify`, `make verify-negative`, `make clean`. The PR documents testing on **one Linux/amd64 host**; it does not verify the historical Vagrant profile, other operating systems, or physical robots. See [kind guide](../KIND-DEMO.md).
- [PR #109](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/109) is **open and draft**, mergeable at inspection; its E08 offline synthetic handoff workflow, shell and Markdown link checks have passing runs, including [E08 workflow](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/40706129203). It is **single-process/in-memory** teaching code, not actual cloud-to-edge state migration.
- [Issue #110](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/110) has a defined, small next step: a **versioned checkpoint envelope**, refusal codes and **separate-process** synthetic export/import. It builds on #109 and should not recreate its implementation.
- [PR #120](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/120) is open/mergeable, with eight observed passing CI workflows including [kind cross-worker](https://github.com/MSKazemi/ros2-kubernetes-lab/actions/runs/41205300270). Its **main-only Docker publish workflow** is not proven by PR checks; review this separately before merge.
- [PRs #101](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/101) and [#105](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/105) overlap in the Hugging Face / scenario site, README and sitemap; merge neither blindly. Treat them as a coordinated later integration, not today's new project.
- [Issue #55](https://github.com/MSKazemi/ros2-kubernetes-lab/issues/55) is still open even though `examples/cloud-robotics/mock-policy/` is present on `main`. Reconcile issue acceptance with merged evidence later; don't assume all acceptance criteria are done.

## Today: time-boxed execution order (Europe/Rome)

### P0 · 11:30–13:00 — Human-review #109; aim to get the existing E08 increment ready

1. Read `AGENTS.md`, `SAFETY.md`, issue #104, PR #109 and its seven changed files, especially `experiments/e08-task-handoff/simulate.py` and `tests/test_simulate.py`.
2. Re-run on a clean checkout of PR #109 (not performed by the author of this plan):

   ```sh
   python3 experiments/e08-task-handoff/simulate.py --validate-only
   python3 experiments/e08-task-handoff/simulate.py
   python3 -m unittest discover -s experiments/e08-task-handoff/tests -v
   python3 scripts/check-markdown-links.py
   git diff --check
   ```

3. Check replay rejection, stale epoch, invalid/tampered snapshot, bad robot/frame/capability, expired observation and CLI error exits. Inspect whether the expected fictional trace matches the tests.
4. Only after human code/evidence review, decide whether to mark PR ready and merge. Do **not** autonomously merge/push to `main`. If any check fails, fix #109 before starting Phase 3.

**Deliverable:** one review decision, command-level evidence and limitations; no claim of actual Kubernetes or physical robot handoff.

### P1 · 14:00–16:00 — Start Phase 3 of E08 (#110), only if predecessor is integrated or safely rebased

**Research question:** What minimal high-level mission state can be transferred **between two independent OS processes** without implicitly restoring execution permissions, hidden model state or simulator authority?

Smallest useful vertical slice:
1. Write `mission-checkpoint/v0.2` (working label) JSON Schema and explicit canonical serialization/hash rules, including byte limits, version, task ID, movement ID, source/destination execution ID, epoch, cursor, completed steps, frame/map/robot and declared capabilities.
2. Build a **two-process** synthetic export/import test via local file/pipe (no ROS 2, Kubernetes, network, Hugging Face model, cloud account, physical hardware or external dependency).
3. Produce one positive roundtrip and at least five refusal tests: stale epoch, modified digest, wrong map/frame, unsupported runtime/schema and missing capability/authority. Never deserialize pickle or executable checkpoint data.
4. Keep authority external and enforce fail-closed refusals. A checksum is not authentication. Explicitly document copied vs site-bound state and non-goals.

**Deliverable:** a narrow #110 implementation branch/PR with stdlib CPU tests and `--validate-only`, not a broad migration system. Tests are proposed, **not run** at the time this note was written.

### P2 · 16:00–17:00 — Review #120 without risky automation

Confirm CI evidence and inspect new Action majors, the pinned ROS image digest and publishing conditions. Publishing is main-only, so passing PR CI is **necessary but not sufficient**. Avoid mixing #120 with #109/#110 changes or pushing to main without approval.

### P3 · 17:00–17:30 — Explain and invite reproducible contribution

Make the E08 documentation accessible to students: an exact CPU-only command, expected fictional output, the contract/fault cases, the next open issue (#110), and a request for independent reproduction. Link to [the contributor instructions](../AI_ASSISTED_CONTRIBUTING.md). Do not publish a scientific performance number or a verified website result card from these unit tests; keep proposed/unmeasured results as `planned`/`null`.

## End-of-day evidence checklist

- [ ] PR #109 reviewed with exact commands and run outcomes, or blockers recorded clearly.
- [ ] If #109 safely integrated, #110 scoped to a separate-process contract and test; no duplicated code.
- [ ] PR #120 main-only Docker publishing hazard reviewed; no unapproved release/publish.
- [ ] Reader can reproduce the *synthetic* example without a paid service or robot.
- [ ] Public claims stay precise: kind cross-worker messaging is verified only in the documented tested environment; E08 migration remains a synthetic prototype; no accuracy/performance conclusions.

## Copyable Claude Code handoff (one issue per change)

```text
Repository: MSKazemi/ros2-kubernetes-lab (public).
Read AGENTS.md, SAFETY.md, docs/PROGRAM-ROADMAP-2026-2027.md,
the live issue #104 and draft PR #109. First review #109; do not
duplicate its simulator or merge/push it autonomously.
Run its existing offline command and negative unit tests; report
exact passing/failing outcomes and limitations. If #109 is integrated
or can be safely based on main, implement ONLY issue #110 as a
separate minimal PR: strict versioned JSON checkpoint schema,
canonical hash with size limits, two independent OS process
export/import demonstration, fail-closed robot/frame/map/runtime/
epoch/capability refusal tests. Python stdlib + synthetic data only.
No live robot, ROS /cmd_vel, credentials, cloud dependency, secret,
unlicensed dataset, model download, or new research epic.
Do not label toy unit tests as cross-worker Kubernetes validation
or a measured robotics benchmark. Human reviewer decides merge.
```

## What not to do today

Do **not** open more broad epics, rename/rebrand the repository, advertise simulated data as benchmark results, merge the overlapping HF site PRs independently, pay for hosted APIs, or bypass safety/review gates.
