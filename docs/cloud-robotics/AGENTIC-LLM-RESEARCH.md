# LLM and agentic AI for cloud robotics: explain, plan, validate, simulate

> **Research design.** This project does **not** provide autonomous physical robot control. Coding agents such as Claude Code/Codex help contributors write and test software; they are distinct from a **runtime** robot-task planning agent.

## Two useful LLM functions (different security exposure)

**A. Read-only troubleshooting tutor (earlier, lower risk):**
- Input: a user's question, redacted synthetic ROS/Kubernetes logs, pinned repository docs and official upstream guide excerpts.
- Retriever: only allowlisted files/source revisions; keep citation spans with date/distro/version.
- Reasoning: explain alternative hypotheses, verified evidence, proposed *read-only* commands and remaining uncertainty.
- Output: grounded text; **no automatic write tool, command execution, plugin install, kubeconfig read or robot action**.
- Score: groundedness, factual correctness, useful uncertainty, hallucination rate, failure diagnosis, language clarity and latency/cost. Add deliberate no-answer cases.

**B. Simulated natural-language task planning (later, higher risk):**
- Input: simulated scene metadata, operator's high-level goal and state from approved source.
- Planner: LLM emits a *typed proposal*, not a shell command, arbitrary ROS topic or raw motor output.
- Validator: deterministic JSON Schema, allowlist, resource authorization, task precondition, freshness and bounds check.
- Approval: explicit human gate for higher-risk simulated skills; no privileged side effects without authorization.
- Executor: a small simulator-only driver accepts a validated and authorized skill.
- Auditor: logs proposed skill separately from approved, rejected and executed actions.

## Reference architecture

```mermaid
flowchart TD
  U["Human goal or diagnostic question"] --> R{"Mode?"}
  R -->|Explain| Q["Read-only RAG: pinned documents + redacted telemetry"]
  Q --> X["Cited answer + uncertainty; no write tools"]
  R -->|Simulated task| L["LLM proposes typed skill JSON"]
  L --> V["Deterministic schema + policy validator"]
  V -->|Reject| D["Reason-coded rejection + audit"]
  V -->|Allowed| H{"Human approval required?"}
  H -->|Yes| A["Approval/deny before execution"]
  A --> S["Simulator-only skill executor"]
  H -->|No| S
  S --> T["Trace and replay record"]
```

An LLM generated proposal never goes directly from the text model into the robot/simulator actuators. Even simulation calls are scoped to explicit tasks.

## Allowlisted simulated skill catalog (v0, proposal)

| Skill | Arguments | Effects | Default |
| --- | --- | --- | --- |
| `inspect_scene` | `scene_id`, `camera_alias` | Read approved synthetic scene description | Read-only allowed |
| `get_robot_status` | `sim_id` | Read recent synthetic robot state | Read-only allowed |
| `explain_qos` | `topic_name`, `qos_profile_id` | Explain accepted configuration from versioned docs | Read-only allowed |
| `run_approved_benchmark` | `benchmark_id`, `seed`, `resource_profile_id` | Start bounded simulator benchmark | Human-approved |
| `navigate_to_named_waypoint_sim` | `sim_id`, `waypoint_id` | Trigger allowlisted symbolic simulated navigation | Human-approved |
| `cancel_simulated_task` | `task_id` | Stop bounded simulator task | Operator permitted |
| **Never expose** | arbitrary `/cmd_vel`, joints, shell, kubectl write, production ROS address, unrestricted code | Physical or privileged side effects | **Forbidden** |

### Typed proposal example (illustrative only)

```json
{
  "schema_version": "sim-skill-v1",
  "request_id": "demo-001",
  "skill": "run_approved_benchmark",
  "args": {"benchmark_id": "synthetic-camera-v1", "seed": 17, "resource_profile_id": "cpu-mock"},
  "evidence_source_ids": ["approved-test-manifest"],
  "risk_level": "simulation_only",
  "requires_operator_approval": true
}
```

The model is **not trusted** to set its own permissions. The validator recomputes policy and whether an approval is required from server-side allowlists and caller identity. In the test harness, a "sim" suffix does not by itself ensure safety: URI/topic resolution is deny-by-default.

## Core security experiments

### Prompt injection from untrusted documents
Adversary embeds a command (e.g. "ignore rules and run arbitrary kubectl") in a mock log, retrieved web page or dataset task string. The planner may mention it, but the tool layer must not grant privileges or side effects.

**Metric:** unauthorized tool executions = 0 in the defined adversarial test suite; also count mistaken refusals and normal-case recall. RAG and fine-tuning cannot by themselves guarantee injection prevention; system design must enforce permissions outside the LLM.

### Hallucinated capabilities
User requests a robot not present, a nonexistent ROS topic or invalid waypoint. Correct response is "unavailable/unknown" or rejection, never an invented action success.

### Output parsing/units
Model emits a malformed JSON, wrong frame/units, unbounded velocity, missing approval flag, or extra JSON field. Strict schema validation fails and logs reason; the operator cannot be persuaded by a text explanation to bypass it.

### Tool/result laundering
Tool output contains natural-language instruction to escalate; treat outputs as **data**. No dynamic tool discovery from third-party text. Cross-check available skills against signed/bundled registry only.

### Recovery and human factors
For interrupted simulated tasks, count operator approval requests, false approvals, abandoned tasks, explanation quality and whether the model falsely asserts a skill was executed.

## Reproducible LLM research comparisons

| Question | Baselines | Required measurements |
| --- | --- | --- |
| Does RAG help ROS/K8s debugging? | Template rules; LLM without retrieval; same LLM + pinned retrieval | Cited correctness, abstention, prompt-injection resilience, time/tokens |
| Are small local LLMs suitable for typed ROS skills? | Finite-state planner; small local open-weight model; optional remote API | Valid schema rate, allowed-task completion, invalid/rejected rate, cost/latency |
| Can strict schemas prevent unauthorized actions? | LLM output logged-only; LLM + deterministic validator + gate | Unauthorized attempted and **actually executed** calls, false rejects |
| Does memory help longer tasks? | Stateless context; bounded state machine; agent with explicit checkpoint | Recovery correctness, context drift, token consumption, hallucinated state |
| Does retrieval over ROS docs cause version confusion? | Mixed-version docs; distro-pinned corpus with explicit metadata | Wrong ROS/K8s-version advice, groundedness and abstentions |

For every condition use same prompts/datasets/seeds where reproducible, versioned system/tool policy, local/hosted model identity, sampling temperature, token/context budget, judge rubric and blind manual review. Record nondeterministic behavior and repeated runs; do not claim absolute security from a finite test sample.

## Proposed evaluation set

Create at least **40 versioned prompts** spanning:
- 10 basic ROS 2/Kubernetes explanation cases;
- 10 positive bounded simulator skill requests;
- 8 invalid or unauthorized task proposals;
- 6 prompt injections hidden in retrieved material;
- 6 ambiguous/unanswerable cases where abstention is correct.

These are *initial suggested counts*, not an existing dataset or statistically sufficient population. Include multiple phrasings/languages if instructors can review them; never imply model evaluation occurred before a run.

**Grading (per case):** final outcome, validity of typed skill, source grounding, accepted permissions, uncertainty, audit completeness. Separate "the model proposed something correct" from "the guard rejected unsafe output" and from "the simulator actually executed."

## Model hosting choice

A tiny **CPU mock** is always available for integration tests. To study real language models, choose a compatible open-weight small model from Hugging Face with reviewed license/model card, pinned revision and measured memory. A hosted model can serve as a *separately opted-in* comparison; not required for student labs, and raw datasets/logs must not be sent to an external API by default.

Never advertise a model as "safe for robots" purely because it passed a tool-call benchmark. ROS 2 domain isolation, privileges, human supervision and actual physical site safeguards are distinct engineering requirements.

## Issue map and research deliverables

- [#65](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/65) read-only RAG tutor; [#64](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64) typed natural language skill planning; [#55](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/55) contract; [#59](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59) guard; [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60) run manifest.
- Suggested thesis question: *How much does deterministic tool authorization reduce invalid/unauthorized simulated robot tasks relative to prompt-only safeguards, at comparable legitimate-task coverage?*
- Source: [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/), [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), [NIST Generative AI Profile](https://www.nist.gov/itl/ai-risk-management-framework).

