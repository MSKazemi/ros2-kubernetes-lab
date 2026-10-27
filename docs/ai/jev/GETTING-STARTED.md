# Getting started — a Jev research demo that does not require a robot

> **Today this is a documentation-only exercise, not a runnable Jev-integrated ROS 2 app.** First prove the fixture/request shape; issue [#74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74) tracks the offline baseline and optional live adapter.

**Audience:** ROS 2 students, Kubernetes developers, new AI contributors, and MSc/PhD researchers.
**Requirements for the offline steps:** a repository checkout, Python 3 and a text editor. No VM, Kubernetes cluster, GPU, ROS installation, cloud account or API key.

## Exercise A — inspect synthetic incident evidence (offline)

From the repository root:

```bash
python3 -m json.tool docs/ai/jev/examples/synthetic-incident.json >/dev/null
python3 -m json.tool docs/ai/jev/examples/jev-choice-request.json >/dev/null
```

These commands **only verify JSON syntax**. They do *not* validate a JSON Schema, run a classifier, call Jev or verify ROS 2 DDS communication. A successful exit code is evidence of parseable JSON only.

Read [synthetic-incident.json](examples/synthetic-incident.json). Why are DDS discovery failure and network isolation sometimes indistinguishable given a short log? Why should a classifier have an `unknown` option?

Read [jev-choice-request.json](examples/jev-choice-request.json). Identify:
- `state`: the synthetic case described in plain language and limited structured metadata.
- `questions.fault_class`: `Choice` plus mutually described candidate categories and `unknown`.
- `questions.review_required`: `Noul` for an *advisory* binary question.
- `questions.triage_urgency`: `Score` on an ordered, **qualitative** review scale (not a physical severity estimate).

## Exercise B — compare question types

| Ask | Appropriate Jev primitive | What remains code-owned |
| --- | --- | --- |
| "Which incident category best fits?" | Choice | Class allowlist, source verification, abstention policy |
| "Is evidence contradictory?" | Noul | Human-review routing, thresholds selected using development data |
| "What is the qualitative review urgency?" | Score | Any real-time deadlines and numeric priorities |
| "Is this event older than 100ms?" | **None** | Parse timestamps and compare in deterministic code |
| "Which pod should I kill to fix the robot?" | **None** | This PoC never performs mutations or actuation |

Jev also documents optional image/Box capabilities, but this lab's first exercise deliberately uses **text and synthetic events only**.

## Exercise C — *optional* hosted Jev request (not necessary for the exercise)

This is the **official TypeSafe** endpoint example, not an independently tested command in this repository. Only proceed if you own a valid TypeSafe account/key, accept the provider's terms, understand potential charges, and approve sending the **synthetic JSON state** to a hosted service.

1. Check the [official API reference](https://docs.typesafe.ai/api/system-one) and [available models](https://docs.typesafe.ai/api/list-models); request only documented capabilities.
2. Set `TYPESAFE_API_KEY` privately in your shell/session using your preferred secret-handling method. **Do not put a value into a file, command history, issue, PR, or pasted chat.**
3. Optionally send the example from the repository root:

```bash
if [ -z "$TYPESAFE_API_KEY" ]; then
  echo "TYPESAFE_API_KEY is missing; no request sent."
else
  curl --fail-with-body --show-error --silent --max-time 15 \
    https://api.typesafe.ai/v1/systemone \
    -H "Authorization: Bearer $TYPESAFE_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary @docs/ai/jev/examples/jev-choice-request.json
fi
```

**Do not** run this network request in default CI or against private telemetry. The example uses `jev-latest` for exploration; for *research*, select an available exact version and record actual `model` returned by the service. If credentials, model name, network access or request schema are not accepted, the call may fail: that is **not** evidence that a fallback or classifier exists.

**Response expectations (not predicted measurements):** the official API returns `answers` keyed by question name plus response `model` and token usage. Choice has `choice`, `probabilities` and `confidence`; Noul has `noul` (no separate confidence); Score has rubric-related fields. Do not hardcode a success class or invent sample probability values. See [official docs](https://docs.typesafe.ai/introduction).

## Exercise D — design a baseline, then test it

Before implementing, propose a **deterministic** offline rule:
- If explicit incompatibility in QoS reliability/durability is present, classify `qos_mismatch`.
- If input lacks enough trustworthy evidence, classify `unknown`.
- If clues for different classes conflict, return `REVIEW_REQUIRED`, not a forced decision.
- If stale, malformed, unauthorized or privacy-sensitive, refuse any hosted call.

A production-quality rule baseline must be specified and tested more carefully; those lines are *teaching examples*, not currently shipped executable behavior.

Next: read [architecture](ARCHITECTURE.md), contribute one small bounded task under [issue #74](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/74), and use [benchmark protocol](BENCHMARK-PROTOCOL.md) for honest comparisons.

## Common mistakes

- Calling a syntactically valid JSON file a working Jev implementation.
- Labeling the offline rule baseline as Jev, or treating Choice confidence as verified clinical/robotics correctness.
- Passing arbitrary provider output into an unrestricted robot skill or `kubectl` executor.
- Claiming the old Vagrant/Foxy setup or same-container Jazzy test validates a modern Kubernetes multi-robot system.
- Using live hosted requests in CI, exposing API keys, or publishing non-synthetic incident content.
