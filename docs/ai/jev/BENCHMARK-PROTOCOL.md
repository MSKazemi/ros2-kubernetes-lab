# Reproducible research protocol — Jev vs alternative robotics decision methods

> **Protocol draft only; no Jev/ROS 2 benchmark has been performed.** The goal is to measure real outcomes rather than reproduce vendor marketing claims. Align measured experiment structure with [issue #60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60) and [#75](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75).

## 1. Decision problem and falsifiable hypotheses

Initial task: infer a **single synthetic ROS 2/Kubernetes incident category** from fixed evidence (the [scenario S1](SCENARIOS.md#s1--explain-a-missing-ros-2-subscriber-p1-flagship)). No attempt to operate a robot.

- **H1 / diagnostic quality:** On held-out incident families, Jev with predefined Choice criteria has higher macro-F1 than a deterministic rules baseline. **Null:** no meaningful advantage or worse performance.
- **H2 / selective risk:** Choosing to abstain using dev-set rules lowers the error rate among accepted read-only suggestions at a measured coverage cost. **Null:** abstention fails to improve useful triage risk.
- **H3 / availability and speed:** Under a defined remote-network fault profile, an offline baseline offers higher availability and/or lower tail latency than the Jev hosted request, perhaps at lower decision quality.
- **H4 / robustness:** Jev decision labels/probabilities change measurably when criteria order, paraphrasing, contradictory evidence and prompt-injection strings change.
- **H5 / workflow utility:** A human reviewer using advisory Jev outputs resolves a held-out synthetic incident faster/more accurately than a reviewer using the baseline alone, under the same rules and UI.

A negative result is a useful publication outcome. Preregister primary endpoint, sample split, thresholds, α/confidence intervals, repetitions, hardware and any expected smallest effect of interest **before** viewing held-out results.

## 2. Datasets and split policy

Start with **15–30 carefully annotated synthetic fixtures only to verify the pipeline**. This is not enough to support broad accuracy claims. Larger evaluation datasets must document realistic event generation, license, domain coverage, missingness, class prevalence and human labeling process.

| Class | Example *synthetic* evidence | Pitfall |
| --- | --- | --- |
| `dds_discovery` | Participants not discovered, discovery-server configuration mentioned | Could also be network isolation |
| `qos_mismatch` | Explicit incompatible reliability or durability | Distinguish subscriber starvation |
| `network_connectivity` | Simulated blocked pod-to-pod path | Do not mislabel as guaranteed DDS failure |
| `resource_pressure` | OOMKilled / Pending / quota exhaustion | Separate symptoms from ultimate cause |
| `healthy` | Verified synthetic message receipt and no error | Avoid labeling absence of logs as success |
| `unknown` | Insufficient/conflicting cues or new incident family | Essential for abstention and honest scope |

Use **group-level** splits: group all paraphrases of an incident template and all sibling perturbations in the same train/dev/test partition. Do not allow the same underlying incident template to appear on both sides. Isolate a realistic *out-of-distribution* test set from a distinct logger, ROS distro or new simulated fault family. Publish exact fixture IDs, license, provenance, label-adjudication method and hashes.

No private ROS bags, live production metrics, geolocations, participant data, real credentials or screenshots with secrets. Begin with text-only synthetic events.

## 3. Predeclared comparators

| Arm | Description | Network needed | What can be claimed |
| --- | --- | --- | --- |
| A0 | Majority-class baseline + always-unknown control | No | Dataset difficulty and coverage floor |
| A1 | Versioned deterministic parser/rules + `unknown` | No | Reproducible, hardware-free diagnostic baseline |
| A2 | Optional local supervised classifier, trained only on training split | No | Offline ML comparator with declared hardware |
| A3 | Optional TypeSafe Jev `Choice` using fixed bounded question criteria | Yes | Hosted structured decision behavior, once measured |
| A4 | Optional constrained-output generative LLM | Depends | Relative model quality/cost with equivalent data constraints |

**Avoid an unfair comparison:** all methods receive the same allowed evidence, class definitions and evaluation examples; record model revisions, question wording, API tokens, rate limits, device, budget, timeout and caching. Jev's `confidence` is a derived distribution statistic, **not** necessarily the probability that its chosen class is correct. Evaluate the entire categorical `probabilities` map separately. `Noul` outputs a yes-probability, not another confidence score.

An additional predeclared ablation may compare one `Choice` call with a two-stage `Noul`→`Choice` approach, **not** assume multi-question responses are sequentially conditioned (they are independently evaluated per TypeSafe docs). Source: [official API](https://docs.typesafe.ai/api/system-one).

## 4. Procedure for each run

1. Freeze fixture dataset+hash, class taxonomy, criteria text, order, model/API/SDK revision, evaluation code, development-derived thresholds and budget.
2. Validate schema and redact; record input count, bytes, event-time freshness, missing fields, telemetry type and the synthetic marker.
3. Run A0/A1 locally as a CPU-only reproducible baseline. On missing/unusable data return `unknown`/`NO_RECOMMENDATION`, not forced class labels.
4. With an explicitly opted-in account, run A3 and optionally A4 on the same sealed synthetic split. Never execute paid/networked tests as ordinary CI.
5. Record every trial including bad requests, provider errors, timeouts, retries, duplicate outcomes and rejections. Do not discard failed experiments from the denominator.
6. Repeat independent runs and parameterized order tests (minimum three independent repetitions as a **starting point**, increase based on variance / planned power).
7. Regenerate plots/tables from raw structured results, publish scripts + immutable references + redacted evidence; report omissions as `N/A`, not zero.

## 5. Primary and secondary metrics

| Metric | Definition / caveat |
| --- | --- |
| Macro-F1; per-class precision/recall | Count abstentions as non-correct predictions in the **end-to-end** metric; also report classification metrics on the non-abstained subset separately |
| Coverage and selective risk | Coverage = number of accepted diagnostic suggestions / number of eligible requests; selective risk = error rate **among accepted suggestions** |
| Calibration | Multiclass Brier score on full Choice probabilities where valid; Noul Brier for a separately labeled yes/no target; ECE + reliability diagrams with bin definitions |
| Unknown/OOD behavior | Forced confident misclassifications and abstention on unseen categories; class-balanced risk |
| p50/p95/p99 duration | End-to-end monotonic client interval, plus local preprocessing and network RTT where instrumented; report successful-only latency **and** failure/timeout rates |
| Availability | Eligible requests returning a valid, policy-accepted advisory before a prespecified deadline / all eligible requests |
| Cost | Report actual measured tokens and dated provider tariff, raw request count including retries; never extrapolate a universal cost from marketing examples |
| Review effort (later) | Blind reviewer agreement and elapsed time on same cases; human participants require appropriate approval |

Use bootstrapped confidence intervals **clustered by incident family** if related fixtures are sampled; predefine handling of ties, multiple hypotheses and missing/invalid probability vectors. No generic claim of "faster", "more accurate", "calibrated" or "safe" without data.

## 6. Reproducibility manifest (fields to require; schema planned in #60)

```json
{
  "experiment_id": "TEMPLATE_NOT_RUN",
  "experiment_status": "NOT_RUN",
  "synthetic_data_only": true,
  "source_commit": "REPLACE_WITH_COMMIT_SHA",
  "dataset_revision_and_sha256": "REPLACE",
  "question_set_version": "jev-fault-triage-v0",
  "question_criteria_hash": "REPLACE",
  "choice_option_order": ["dds_discovery", "qos_mismatch", "network_connectivity", "resource_pressure", "healthy", "unknown"],
  "provider": "offline_rules_OR_opt_in_jev",
  "requested_model": "PIN_IF_USING_JEV",
  "observed_model_revision": null,
  "api_or_sdk_version": null,
  "ros_distro": "not_applicable_to_synthetic_fixture_only",
  "kubernetes_version": "not_applicable_to_synthetic_fixture_only",
  "run_seed": null,
  "input_sample_count": null,
  "timeout_ms": null,
  "repetitions": null,
  "clock_source": "monotonic_client_for_duration",
  "network_rtt_profile": null,
  "total_attempts": null,
  "successful_decisions": null,
  "cost_currency_and_tariff_date": null,
  "raw_result_hash": null,
  "conclusion": "NOT_MEASURED"
}
```

This is a **documentation template**, not validated run output or a finalized schema. Remove all placeholders before presenting experimental evidence. Do not commit tokens, raw provider responses containing user data, vendor account identifiers, or private network details.

## 7. Test matrix and exit criteria

| Scenario | Must test | When |
| --- | --- | --- |
| Happy-path synthetic class | Schema, class boundary, provenance | Offline CI (#74) |
| Contradictory / sparse evidence | Unknown or review behavior | Offline CI |
| Prompt injection in a log entry | Treat as data; no instruction execution | Offline CI + optional vendor tests |
| Stale observation, invalid units or unknown command | Deterministic rejection | Offline CI (#55/#59) |
| Missing API key, 401, 422, 429, 5xx, timeout | No recommendation; bounded retry policy | Fake HTTP client tests |
| Reordered Choice options and changed criteria | Quantify stability; do not cherry-pick | Opt-in research (#75) |
| Cross-worker DDS or robot action | **Not supported by this protocol** | Separate verified experiments (#14/#15/#16) |

## 8. Publication checklist

- [ ] Primary and secondary outcomes registered before the held-out evaluation.
- [ ] All fixtures legally shareable, synthetic marker retained, no secrets.
- [ ] Schema/normalization rules and model/criteria revisions published.
- [ ] Raw data, failures, analysis scripts and uncertainty estimators reproducible.
- [ ] Negative outcomes, provider outages, cost estimates and unknown responses included.
- [ ] Explicit external validity limits: synthetic ROS 2 incidents are **not** real fleet telemetry.
- [ ] No safety certification, robot-actuation or multicluster success claims.

Related [Architecture](ARCHITECTURE.md) · [Safety/privacy](SAFETY-PRIVACY.md) · [#75 research issue](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75).
