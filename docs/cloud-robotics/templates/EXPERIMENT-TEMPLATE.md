# Experiment preregistration, run record and replication template

> **Blank research template.** Fill before executing a proposed scenario. Never copy placeholder metrics into a publication or present mock results as measured. Run may be "blocked" or "negative"; preserve that as valid scientific evidence.

## A. Preregister before collecting data

| Field | Fill in |
| --- | --- |
| Title / scenario ID | CR-__ / descriptive title |
| Question and explicit falsifiable hypothesis | ___ |
| Prior art and smallest novelty claim | Cite FogROS2, LeRobot, relevant methodology |
| Experimental owner/reviewer | Project role or public username; no private identity needed |
| Research level | BSc / MSc / PhD / independent replication / industry evaluation |
| Control condition | ___ |
| Intervention and treatment levels | ___ |
| Dependent metrics, units and deadlines | ___ |
| Clock synchronization method and uncertainty | ___ |
| Randomization, seeds and run order | ___ |
| Warmup, trial length and stop conditions | ___ |
| Independent runs / statistical power justification | ___ |
| Failure/drop/exclusion rule (predeclared) | ___ |
| Data/model/robot semantics and exact versions | ___ |
| Risks, licenses, affected people and approval | ___ |
| Hardware and optional paid services | ___ |
| Limitations that would invalidate inference | ___ |

## B. Resource/profile gate

- [ ] Offline CPU-only / same-container ROS test / cross-worker k8s / optional GPU / licensed hardware (requires separate approval)
- [ ] ROS distro, OS, K8s, CNI, RMW, middleware and QoS are **recorded**, or marked N/A.
- [ ] Dataset origin, redistribution license, model processor/policy/embodiment, camera and action units checked.
- [ ] Simulator-vs-physical boundary verified; no unreviewed actuator endpoints.
- [ ] Credentials not in git/logs; model/data cards and risk register reviewed.
- [ ] Clean host and cleanup steps described (do not invent missing commands).

## C. Machine-readable run schema target

Below is **illustrative only**, not yet validated against an executable schema:

```json
{
  "schema_version": "cloud-robotics-run-v0-proposal",
  "run_id": "<unique-run-id>",
  "status": "<fixture_only|completed|failed|blocked|interrupted>",
  "scenario": "CR-00",
  "utc_start": "<ISO-8601>",
  "source_commit": "<git-40-char-sha>",
  "container_digest": "<sha256-or-not-applicable>",
  "environment": {
    "ros_distro": "<version-or-null>",
    "rmw": "<id-or-null>",
    "kubernetes": "<version-or-null>",
    "cni": "<version-or-null>",
    "os_arch": "<value>",
    "cpu": "<model>",
    "gpu": "<model-or-null>"
  },
  "simulator": {"id": "<name>", "revision": "<sha-or-version>", "seed": 0},
  "artifacts": {
    "dataset_repo": "<source-or-local-fixture>",
    "dataset_commit": "<commit-or-fixture-revision>",
    "model_repo": "<source-or-mock>",
    "model_commit": "<commit-or-mock-revision>",
    "license_review": "<approved-or-blocked>"
  },
  "semantics": {
    "observation_schema": "<version>",
    "action_schema": "<version>",
    "action_units": ["<unit>"],
    "task_id": "<task>",
    "rate_hz": null
  },
  "placement": {"profile": "<local|k8s|remote>", "nodes": []},
  "network": {"profile": "<baseline|impairment>", "seed": 0, "measured_rtt_ms": null},
  "clock": {"duration_source": "<monotonic>", "cross_host_sync": "<method-or-N/A>"},
  "trial": {"condition": "<name>", "repeat_index": 0},
  "outcome": {"success": null, "failure_reason": null, "rejected_action_count": null},
  "artifacts_out": {"raw_data": "<path>", "plot_script": "<command>", "logs_redacted": true}
}
```

Replace placeholders with actual run values. Log model/dataset/image revisions, manifest checksums and run status. This proposal is tracked in [#60](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/60).

## D. Raw data and measurement documentation

| Column | Description / unit | Clock and source | Missing/failure meaning |
| --- | --- | --- | --- |
| run_id, trial_id | Unique trial | Recorder | Reject missing |
| observation_id, seq_id | Causal linkage | Sim/ROS | Reordered/missing observed separately |
| observation_source_ns | Source capture time | ROS/simulation clock | Not wall time unless declared |
| request_sent_ns | Client-local monotonic | Client | Optional when unavailable |
| response_received_ns | Client-local monotonic | Client | Timeout must be recorded |
| server_compute_ns | Server-local monotonic duration | Policy process | No cross-clock subtraction |
| gate_result | accepted, expired, wrong-unit, unauthorized, etc. | Validator | No silent missing |
| simulated_action_ack | Whether simulator acknowledged valid action | Simulation | Not a real-world actuator result |
| outcome_label | Success/failure/unknown per task definition | Test-specific adjudicator | Unknown not counted as success |
| resource_sample_* | Units, collector and exact interval | Monitoring exporter | Not estimated if unmeasured |

## E. Report results (after actually running)

- **Actual environment and run URLs:** ___
- **Raw input/output location and checksums:** ___
- **Measured samples/trials per condition:** ___
- **Predeclared successes, failures and exclusions:** ___
- **Main effect, dispersion/CI and tail sample sizes:** ___
- **Statistical analysis script / lockfile:** ___
- **Independent reproduction performed by and on:** ___
- **Threats to validity:** ___
- **Unexpected failures, negative findings and next steps:** ___
- **Public result maturity R0/R1/R2/R3:** ___
- **Ethics/legal/physical review status:** ___

## F. Evidence-based publication gate

- [ ] Links to raw artifacts actually exist and contain valid redistributable data.
- [ ] Nothing in the report implies physical robot/production validation unless independently approved and documented.
- [ ] Claims distinguish model inference, safe gate acceptance, ROS message delivery and simulator task success.
- [ ] All clock and statistical assumptions are explicit; no p99 claims from a tiny sample.
- [ ] Reproduce script, limitations, negative cases and source versions are included.

