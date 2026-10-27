# Publishing reproducible experiments and honest results

> This is a **data-publication contract**, not evidence of a completed experiment. Apply the research/evaluation specification in [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60), [#75](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/75) and [#88](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/88).

## Why a registry instead of a chart with example numbers?

A public education/research website should let students follow the full scientific cycle: hypotheses, baseline, controlled trials, raw evidence, error analysis and negative results. Publishing imaginary latency bars, model accuracy or robot-task success would mislead users and compromise reproducibility. Thus [site/scenarios/data/experiments.json](../../site/scenarios/data/experiments.json) starts with four `planned` entries, every `result: null`.

## Status contract

- **planned** — task, class taxonomy, hypothesis and baseline planned. Metric value must be null; no run_count/evidence metadata.
- **collecting** — run setup or submission under review. Value remains null and cannot be advertised as a measured improvement.
- **verified** — a measured numeric result supported by a **public, legally shareable** result archive, a 64-character SHA-256 run-manifest digest, an exact source commit, raw data and analysis-script links, independent reviewer and review date.

A local validator enforces the metadata shape, not scientific soundness or remote link content. Human scientific review is mandatory before status becomes `verified`.

## Minimal research artifact set

A complete contribution should link to or archive these items, using a stable release or permissively licensed public data repository and unambiguous version identifiers:

```text
experiment-<id>/
  README.md                # hypothesis, null, limitations, hardware/simulation declaration
  manifest.json            # exact commit/images, ROS/K8s/RMW, model + criteria, clocks, seeds, dataset revision
  observations.jsonl       # timestamped synthetic/licensed inputs + rejection outcomes
  predictions.jsonl        # model/rules outputs, abstentions, errors, retries, actual model ID
  metrics.json             # measured quantities, units, denominators, unknowns, confidence intervals
  analysis.py              # pin dependencies, reproduce every published aggregate
  hashes.sha256            # integrity references
  LICENSE                  # only data/code you have permission to publish
```

Do not commit these files to the main repository merely because a template mentions them. For large artifacts, use a suitable public research archive with retention/terms/licensing review and link from the issue/PR.

## Suggested experiment manifest fields

```json
{
  "experiment_id": "EXAMPLE_NOT_RUN",
  "status": "NOT_RUN",
  "scenario": "fault-triage",
  "synthetic": true,
  "hypothesis_pre_registration_url": null,
  "source_commit": null,
  "dataset_name_revision_sha256": null,
  "dataset_license": null,
  "model_provider": null,
  "model_id_returned_by_api": null,
  "question_set_hash": null,
  "choice_order": null,
  "experiment_hardware_and_network": null,
  "clock_source_and_sync": null,
  "run_seeds": [],
  "run_count": 0,
  "all_attempts_including_failures": 0,
  "primary_metric_value": null,
  "primary_metric_unit": null,
  "confidence_interval": null,
  "raw_data_public_url": null,
  "analysis_script_public_url": null,
  "limitations": "No experiment was run."
}
```

This is an **illustrative manifest**, not the final schema defined in #60. Never substitute placeholder IDs for real hashes.

## Scenario-specific metrics and units

| Scenario | Proposed primary measure | What must be included |
| --- | --- | --- |
| Fault triage | Macro-F1, fraction; coverage vs selective risk | Class counts, abstentions, unknowns, held-out family split, confusion matrix |
| Edge/cloud placement | p95 sensor-to-valid-action age, milliseconds | Clock basis, packet/profile seeds, failed/unavailable requests, TTL rejects |
| Simulator skill review | Deliberately unauthorized fixture recall, fraction | Corpus scope, independent policy verdict, model-only false positives, review burden |
| Multi-robot dispatch | Simulator task completion/fairness, fraction | Feasible task definition, workload seeds, constraints, backlog, rejected recommendations |

A scalar registry field is **one** selected primary endpoint, not the entire paper. Keep other measures, distributions and confidence intervals in the evidence archive and explain comparative protocol.

## Publishing steps

1. Comment on the relevant scenario issue with task, baseline, independent variables, data provenance, target metrics and test budget.
2. Preregister experimental design/splits *before* viewing held-out outcomes; discuss sensitive data/robot risks separately.
3. Implement and validate the deterministic baseline and any provider adapter with offline tests. Do not rely on mock Jev outputs as model evidence.
4. Execute authorized experiments with reproducible environment manifests, explicit hosted API consent/budget if needed, and complete failure logging.
5. Publish data/script/licenses and immutable SHA-256 manifest; run independent reproduction where feasible.
6. Submit a small PR changing the specific registry record and linking all evidence. Maintain `planned`/null unless a reviewer verifies the above.
7. Document negative/zero/no-improvement findings and limitations. Do not cherry-pick only successful runs or disguise missing data as zeros.

## Security, ethics and trust

No real robot IPs, production incident logs, participant recordings, private datasets, personal data, unlicensed model weights or service-account tokens in public artifacts. Human subject studies, physical trials or industrial deployments require additional qualified legal/ethics/safety review. The static lab cannot validate safety certification.

**Important:** green JSON validation, a GitHub PR and a model's confidence do not imply successful experiments or scientific truth. Source references must accompany the exact claim they support.
