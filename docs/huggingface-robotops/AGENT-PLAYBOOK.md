# Claude Code / Codex research development playbook

> **One issue per contribution.** Read the current issue, root [AGENTS.md](../../AGENTS.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), [CAPABILITIES.md](CAPABILITIES.md) and relevant actual source files. Do not regenerate work already present in the staged HF website PR. Humans review all changes; never autonomously publish or push to `main`.

## Reference architecture and boundaries

Existing website (draft PR #90) has base animations and result registry. This extension adds four HF pages and a separate HF trace script:
- `site/scenarios/hf-lerobot-dataset.html`
- `site/scenarios/hf-jev-classifier.html`
- `site/scenarios/hf-smolvla-libero.html`
- `site/scenarios/hf-robotics-remote-inference.html`
- `site/assets/hf-scenarios.js` (preauthored text, no model provider calls)
- `integrations/huggingface/spaces/robotops-research-explorer/` (Static Space starter, **not published**).

Do not rename the repository, add generic React bundles without a proven need, copy arbitrary third-party robot art, or confuse website illustrations with a working HF/ROS2 integration.

## Prompt A — dataset integrity (#93)

```text
Read AGENTS.md, epic #92, issue #93, #56 and #58. Inspect the existing
HF scenario docs and the currently installed LeRobot release before coding.
Propose a synthetic-only ROS 2 episode metadata validator with units, FPS,
task ID, timestamps, camera/action feature shapes, license and consent checks.
Define positive/negative/unknown fixtures. A JSON fixture is not a genuine
LeRobotDataset v3 until official library output is finalized and reloaded
successfully. Never upload data or run paid jobs automatically; report exact
commands run, untested dependencies and human-review checklist.
```

## Prompt B — Jev vs HF open classifier (#94)

```text
Read AGENTS.md, #92, #94, #74/#75/#84. Build a comparison plan with
deterministic rules, optional pinned licensed HF text classifier, and optional
TypeSafe Jev Choice. Use identical family-held-out synthetic fault fixtures,
explicit unknown, independent hard source checks and development-set
abstention thresholds. Do not pretend a generic pretrained classifier knows
ROS 2 classes. No paid network calls/default CI secrets. Record every error,
model revision, prompt/criteria hash and input split. Show raw evidence for
any measured result; never fabricate accuracy/latency.
```

## Prompt C — SmolVLA / LIBERO (#95)

```text
Read AGENTS.md, #92, #95, #57/#58/#60. Select and pin a compatible released
LeRobot version, documented LIBERO suite, eligible checkpoint, exact Hub
revision and image/action processor. Compare camera mapping, action dims,
relative/absolute modes and data licenses before running. Plan CPU-only
contract checks and optionally GPU simulator tests with explicit user
permission. Do not claim a foundation model can manipulate an arbitrary
robot. No published task-success numbers without actual episodes and seeds.
```

## Prompt D — LeRobot remote GPU (#96)

```text
Read AGENTS.md, #92, #96, #61/#62/#55/#59. Follow pinned upstream LeRobot
remote inference docs and Zenoh transport; ROS2 DDS across K8s nodes is a
separate unverified problem. First define a CPU synthetic server/client
admission and stale-action contract with deterministic rejection. Model
identity, action semantics, position-hold support, auth, timeout and privacy
must pass before any simulator. Jev is an advisory placement/diagnostic
comparator only. No real motor actuation, public unauthenticated service or
automatic GPU billing. Show diff, tests and unverified claims.
```

## Prompt E — Static Hugging Face Space (#98)

```text
Read AGENTS.md, #92, #98, and docs/huggingface-robotops/SPACE-PUBLICATION.md.
Inspect the committed Static Space README with sdk: static and index.html.
Improve accessibility and student usability using only public synthetic
content. Do NOT add HF/TypeSafe secrets to browser JavaScript; do not add
a fake model output or benchmark. Validate the local HTML and links, test
mobile/keyboard when browser available, and show actual test evidence.
Publication to HF requires separate explicit human permission; never
invent a live Space URL or deploy on your own.
```

## Prompt F — cards, collection and provenance (#99)

```text
Read AGENTS.md, #92, #99 and #58. Improve model/dataset card templates
with exact feature/action units, licenses, provenance, base model,
processor/camera keys, revision hashes, evaluation and limitations. Distinguish
templates from actually published HF artifacts. Reject mutable revisions in
release-quality runs. A collection may list only verified public resources.
No model upload, secrets or fabricated metrics.
```

## Before proposing a PR

- Static checks: `python3 scripts/validate-site.py`, `node --check site/assets/hf-scenarios.js`, `python3 scripts/check-markdown-links.py` (follow existing known-issue policy).
- Visual QA: desktop/mobile 360/390/768/1024/1440 px, keyboard focus, no-JS content, reduced motion, contrast and console errors **in an actual browser**.
- For dataset/policy modifications: offline unit tests plus *conditional* official LeRobot API integration tests pinned to the version; never claim unrun GPU/robot tests passed.
- For HF uploads: verify owner access, data/model license, read-only by default, no personal data, explicit user action/approval, and real repository URL.
- For benchmark changes: raw run manifest, complete failures, seeds, model/dataset hashes, hardware/network details, confidence intervals and independent scientific review.

No Claude or Codex agent is permitted to autonomously merge either staged PR, push to `main`, publish a public HF Space, launch paid Jobs or operate physical robot hardware.
